#!/usr/bin/env python3
"""
sync_all_categories_to_spotify.py - Master Full Multi-Category Spotify Synchronizer.

Synchronizes all 214 local playlist databases across all 9 categories into Spotify:
  1. Activity (10 playlists)
  2. Artist (60 playlists)
  3. Era (10 playlists)
  4. Genre (15 playlists)
  5. Mood (19 playlists)
  6. Relationship (10 playlists)
  7. Tamil (15 playlists)
  8. Year (63 playlists)
  9. Indie (12 playlists)

Operations per playlist:
- Reconciles live Spotify tracks with local clean database tracks:
  * Purges obsolete, misplaced, and collided tracks from Spotify.
  * Adds missing tracks to Spotify in batches of 50.
  * Searches and caches missing Spotify track URIs into local SQLite databases.
- Preserves invariant: NEVER modifies playlists/indie/all_independent_songs.db.
- Generates comprehensive sync report in data/spotify_full_sync_report.json.
"""

import sys
import time
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import FOLDER_DEFINITIONS, get_folder_contents

PLAYLISTS_DIR = BASE_DIR / "playlists"
DATA_DIR = BASE_DIR / "data"
REPORT_FILE = DATA_DIR / "spotify_full_sync_report.json"
STATE_FILE = DATA_DIR / "sync_state.json"

PROTECTED_DB = "all_independent_songs.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


def get_container_map(client: SpotifyNativeClient, folder_uri: str) -> Dict[str, str]:
    """Builds a lookup map for playlist containers inside a Spotify folder."""
    items = get_folder_contents(client, folder_uri)
    container_map = {}
    for it in items:
        name = it["name"]
        uri = it["uri"]
        container_map[clean_text(name)] = uri
        container_map[name.lower().strip()] = uri
    return container_map, items


def find_matching_container(name: str, stem: str, container_map: Dict[str, str], raw_items: List[Dict[str, str]]) -> Optional[str]:
    """Finds the matching Spotify playlist container URI using exact, clean, stem, or fuzzy match."""
    c_name = clean_text(name)
    c_stem = clean_text(stem)
    name_lower = name.lower().strip()

    if c_name in container_map:
        return container_map[c_name]
    if name_lower in container_map:
        return container_map[name_lower]
    if c_stem in container_map:
        return container_map[c_stem]

    # Substring / partial match
    for it in raw_items:
        it_name = it["name"]
        it_clean = clean_text(it_name)
        if c_name in it_clean or it_clean in c_name:
            return it["uri"]
        if c_stem in it_clean or it_clean in c_stem:
            return it["uri"]

    return None


def sync_playlist(
    client: SpotifyNativeClient,
    cat_slug: str,
    db_path: Path,
    container_uri: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Synchronizes a single playlist database to its Spotify container."""
    is_protected = (db_path.name == PROTECTED_DB)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Read playlist metadata
    try:
        info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
        pl_name = info.get("name", db_path.stem)
    except Exception:
        pl_name = db_path.stem

    # 2. Read tracks from DB
    cur.execute("""
        SELECT id, track_title, album_title, year, composer, singers, spotify_uri
        FROM tracks
        ORDER BY position ASC;
    """)
    db_rows = cur.fetchall()
    
    target_uris = []
    missing_searches = []
    cached_updates = []
    
    for r in db_rows:
        t_id, title, album, year, composer, singers, sp_uri = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        if sp_uri and sp_uri.startswith("spotify:track:"):
            target_uris.append(sp_uri)
        else:
            missing_searches.append((t_id, title, album, composer, singers))

    # Resolve any missing track URIs
    if missing_searches:
        logging.info(f"    🔍 Resolving {len(missing_searches)} missing Spotify URIs for '{pl_name}'...")
        for t_id, title, album, composer, singers in missing_searches:
            artist_hint = composer or singers or ""
            uri = client.search_track(title, artist_hint)
            if not uri and album:
                uri = client.search_track(title, album)
            if uri:
                target_uris.append(uri)
                if not is_protected and not dry_run:
                    cached_updates.append((uri, t_id))
            time.sleep(0.1)

        if cached_updates and not is_protected and not dry_run:
            with conn:
                conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", cached_updates)
            logging.info(f"    💾 Cached {len(cached_updates)} newly discovered URIs into {db_path.name}.")

    conn.close()

    # 3. Read live tracks currently in Spotify container
    sp_tracks = client.get_playlist_tracks(container_uri)
    existing_sp_uris = {t["uri"] for t in sp_tracks}
    target_uri_set = set(target_uris)

    # 4. Determine mutations
    # Obsolete / miscategorized tracks to remove
    uids_to_remove = [t["uid"] for t in sp_tracks if t["uri"] not in target_uri_set]
    
    # Missing tracks to add
    uris_to_add = []
    seen_in_add = set(existing_sp_uris)
    for u in target_uris:
        if u not in seen_in_add:
            uris_to_add.append(u)
            seen_in_add.add(u)

    result_stat = {
        "category": cat_slug,
        "playlist": pl_name,
        "db": db_path.name,
        "uri": container_uri,
        "db_track_count": len(db_rows),
        "target_uris_count": len(target_uris),
        "initial_spotify_count": len(sp_tracks),
        "removed_count": len(uids_to_remove),
        "added_count": len(uris_to_add),
        "final_count": len(sp_tracks) - len(uids_to_remove) + len(uris_to_add),
        "status": "in_sync"
    }

    if not uids_to_remove and not uris_to_add:
        logging.info(f"  ✨ [{pl_name}] Already in sync ({len(sp_tracks)} tracks).")
        return result_stat

    logging.info(f"  🔄 [{pl_name}] Live: {len(sp_tracks)} | Target: {len(target_uris)} | Remove: {len(uids_to_remove)} | Add: {len(uris_to_add)}")

    if dry_run:
        logging.info(f"    [DRY-RUN] Would remove {len(uids_to_remove)} and add {len(uris_to_add)} tracks.")
        result_stat["status"] = "dry_run"
        return result_stat

    # 5. Execute removals
    if uids_to_remove:
        logging.info(f"    🗑️ Purging {len(uids_to_remove)} obsolete/miscategorized tracks from Spotify...")
        ok_rm = client.remove_tracks_from_playlist(container_uri, uids_to_remove)
        if not ok_rm:
            logging.error(f"    ❌ Failed removing tracks from '{pl_name}'.")
            result_stat["status"] = "remove_failed"

    # 6. Execute additions
    if uris_to_add:
        pos = "TOP_OF_PLAYLIST" if db_path.stem == "2026" else "BOTTOM_OF_PLAYLIST"
        logging.info(f"    🚀 Adding {len(uris_to_add)} missing tracks to Spotify ({pos})...")
        ok_add = client.add_tracks_to_playlist(container_uri, uris_to_add, position=pos)
        if not ok_add:
            logging.error(f"    ❌ Failed adding tracks to '{pl_name}'.")
            result_stat["status"] = "add_failed"

    if result_stat["status"] == "in_sync":
        result_stat["status"] = "reconciled"

    return result_stat


def main():
    parser = argparse.ArgumentParser(description="Master Multi-Category Spotify Full Synchronizer.")
    parser.add_argument("--category", type=str, default=None, help="Sync specific category (activity, artist, era, genre, mood, relationship, tamil, year, indie)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate synchronization without modifying Spotify")
    args = parser.parse_args()

    print("=" * 80)
    print(" 🚀 MASTER SPOTIFY MULTI-CATEGORY SYNCHRONIZATION ENGINE")
    print(f" Mode: {'DRY-RUN SIMULATION' if args.dry_run else 'LIVE SPOTIFY MUTATION'}")
    print("=" * 80)

    categories_to_run = [args.category] if args.category else list(FOLDER_DEFINITIONS.keys())
    categories_to_run = [c for c in categories_to_run if c != "year_complete" and (PLAYLISTS_DIR / c).exists()]

    client = SpotifyNativeClient()
    all_reports = []
    start_time = time.time()

    total_playlists = 0
    total_added = 0
    total_removed = 0
    total_in_sync = 0

    try:
        for cat_slug in categories_to_run:
            defn = FOLDER_DEFINITIONS[cat_slug]
            cat_dir = PLAYLISTS_DIR / cat_slug
            dbs = sorted(cat_dir.glob("*.db"))
            if not dbs:
                continue

            print(f"\n{'='*70}\n📂 CATEGORY: [{defn['display_name'].upper()}] ({len(dbs)} playlists)\n{'='*70}")
            container_map, raw_items = get_container_map(client, defn["folder_uri"])

            for idx, db_path in enumerate(dbs, 1):
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                try:
                    name = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall()).get("name", db_path.stem)
                except Exception:
                    name = db_path.stem
                conn.close()

                target_uri = find_matching_container(name, db_path.stem, container_map, raw_items)
                if not target_uri:
                    logging.error(f"  ❌ No matching Spotify container found for '{name}' ({db_path.name})!")
                    continue

                total_playlists += 1
                stat = sync_playlist(client, cat_slug, db_path, target_uri, dry_run=args.dry_run)
                all_reports.append(stat)

                total_added += stat.get("added_count", 0)
                total_removed += stat.get("removed_count", 0)
                if stat.get("removed_count", 0) == 0 and stat.get("added_count", 0) == 0:
                    total_in_sync += 1

                time.sleep(0.15)

        elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print(" 🎉 FULL MULTI-CATEGORY SYNCHRONIZATION COMPLETED")
        print("=" * 80)
        print(f" Total Playlists Processed : {total_playlists}")
        print(f" Playlists Already in Sync : {total_in_sync}")
        print(f" Obsolete Tracks Purged    : {total_removed}")
        print(f" Missing Tracks Added      : {total_added}")
        print(f" Elapsed Execution Time    : {elapsed:.1f}s")
        print("=" * 80)

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dry_run": args.dry_run,
                "total_playlists": total_playlists,
                "total_in_sync": total_in_sync,
                "total_removed": total_removed,
                "total_added": total_added,
                "elapsed_seconds": round(elapsed, 1),
                "playlists": all_reports
            }, f, indent=2)
        print(f"💾 Report saved to {REPORT_FILE}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
