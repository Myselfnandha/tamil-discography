#!/usr/bin/env python3
"""
scripts/sync_category.py - Robust, Invariant-Preserving Multi-Category Spotify Synchronizer.

Reconciles local discography playlist databases with live Spotify containers:
1. Matches live tracks against local database clean titles & URIs.
2. Purges obsolete, collided, and miscategorized tracks by UID.
3. Adds missing tracks by Spotify URI (batches of 50).
4. Back-propagates confirmed Spotify URIs into local SQLite databases.
5. Invariant: NEVER writes to playlists/indie/all_independent_songs.db.
"""

import sys
import time
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import FOLDER_DEFINITIONS, get_folder_contents

PLAYLISTS_DIR = BASE_DIR / "playlists"
DATA_DIR = BASE_DIR / "data"
PROTECTED_DB = "all_independent_songs.db"

# Anti-collision era boundaries
ERA_RULES = {
    "golden_era": {"max_year": 1980, "forbidden": ["anirudh", "santhosh narayanan", "hiphop tamizha", "yuvan", "harris", "rahman"]},
    "old_is_gold": {"max_year": 1990, "forbidden": ["anirudh", "santhosh narayanan", "hiphop tamizha", "sam c.s.", "harris"]},
    "90s_classics": {"min_year": 1989, "max_year": 2000}
}


def sync_single_category(client: SpotifyNativeClient, cat_slug: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    defn = FOLDER_DEFINITIONS[cat_slug]
    cat_dir = PLAYLISTS_DIR / cat_slug
    dbs = sorted(cat_dir.glob("*.db"))
    
    print("\n" + "=" * 80)
    print(f"📂 CATEGORY: [{defn['display_name'].upper()}] ({len(dbs)} playlists)")
    print("=" * 80)

    # 1. Fetch live folder containers
    sp_items = get_folder_contents(client, defn["folder_uri"])
    sp_map = {}
    for it in sp_items:
        sp_map[clean_text(it["name"])] = it["uri"]
        sp_map[it["name"].lower().strip()] = it["uri"]

    results = []

    for idx, db_path in enumerate(dbs, 1):
        is_protected = (db_path.name == PROTECTED_DB)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
            pl_name = info.get("name", db_path.stem)
        except Exception:
            pl_name = db_path.stem

        c_name = clean_text(pl_name)
        c_stem = clean_text(db_path.stem)

        # Container matching
        container_uri = sp_map.get(c_name) or sp_map.get(pl_name.lower().strip()) or sp_map.get(c_stem)
        if not container_uri:
            for it in sp_items:
                it_clean = clean_text(it["name"])
                if c_name in it_clean or it_clean in c_name:
                    container_uri = it["uri"]
                    break

        if not container_uri:
            print(f"[{idx:02d}/{len(dbs)}] ❌ No Spotify container found for '{pl_name}' ({db_path.name}). Skipping.")
            conn.close()
            continue

        # Read local DB tracks
        cur.execute("SELECT id, track_title, album_title, year, composer, singers, spotify_uri FROM tracks ORDER BY position ASC;")
        db_rows = cur.fetchall()
        if cat_slug == "year":
            db_rows = db_rows[:50]

        # Build clean title lookup and valid URIs set
        local_title_map = {}
        local_valid_uris = set()
        missing_uri_rows = []

        for r in db_rows:
            t_id, title, album, year, comp, singers, sp_u = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
            ct = clean_text(title)
            local_title_map[ct] = (t_id, sp_u)
            if sp_u and sp_u.startswith("spotify:track:"):
                local_valid_uris.add(sp_u)
            else:
                missing_uri_rows.append(r)

        # 2. Fetch live Spotify tracks
        sp_tracks = client.get_playlist_tracks(container_uri)
        existing_sp_uris = {t["uri"] for t in sp_tracks}

        # 3. Detect obsolete/collided tracks on Spotify
        uids_to_remove = []
        newly_cached_from_spotify = []
        rule = ERA_RULES.get(db_path.stem)

        for t in sp_tracks:
            t_uri = t["uri"]
            t_name = clean_text(t["name"])
            t_artists = clean_text(t["artists"])
            t_yr = t["year"]
            uid = t["uid"]

            # Era rule check
            violates_era = False
            if rule:
                if "max_year" in rule and t_yr != 2099 and t_yr > rule["max_year"]:
                    violates_era = True
                if "min_year" in rule and t_yr != 2099 and t_yr < rule["min_year"]:
                    violates_era = True
                if "forbidden" in rule and any(f in t_artists for f in rule["forbidden"]):
                    violates_era = True

            if violates_era:
                uids_to_remove.append(uid)
                continue

            # Check if URI matches local valid URI
            if t_uri in local_valid_uris:
                continue

            # Check if title matches a local track
            matched_local = False
            for lt, (t_id, existing_u) in local_title_map.items():
                if t_name == lt or (len(lt) > 4 and (lt in t_name or t_name in lt)):
                    matched_local = True
                    # Back-propagate URI into local DB if DB didn't have it
                    if not existing_u and not is_protected and not dry_run:
                        newly_cached_from_spotify.append((t_uri, t_id))
                        local_valid_uris.add(t_uri)
                    break

            if not matched_local:
                # Track on Spotify has no match in cleaned local database -> remove it!
                uids_to_remove.append(uid)

        # Save back-propagated URIs to local SQLite
        if newly_cached_from_spotify and not is_protected:
            with conn:
                conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", newly_cached_from_spotify)

        # 4. Resolve missing URIs for local tracks (if playlist is empty or small)
        if len(sp_tracks) < 10 and len(local_valid_uris) < 10 and missing_uri_rows:
            search_limit = min(50, len(missing_uri_rows))
            searched_updates = []
            for r in missing_uri_rows[:search_limit]:
                t_id, title, album, year, comp, singers, _ = r
                artist_q = comp or singers or ""
                sp_u = client.search_track(title, artist_q)
                if sp_u:
                    local_valid_uris.add(sp_u)
                    if not is_protected and not dry_run:
                        searched_updates.append((sp_u, t_id))
                time.sleep(0.08)
            if searched_updates and not is_protected:
                with conn:
                    conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", searched_updates)

        conn.close()

        # 5. Missing tracks to add to Spotify
        tracks_to_add = []
        for u in local_valid_uris:
            if u not in existing_sp_uris:
                tracks_to_add.append(u)

        pos = "TOP_OF_PLAYLIST" if db_path.stem == "2026" else "BOTTOM_OF_PLAYLIST"
        initial_count = len(sp_tracks)
        final_count = initial_count - len(uids_to_remove) + len(tracks_to_add)

        status_str = f"[{idx:02d}/{len(dbs)}] 🎵 {pl_name:<30} : live {initial_count:>4} | -{len(uids_to_remove):>3} rm | +{len(tracks_to_add):>3} add -> final {final_count:>4}"
        print(status_str)

        if not dry_run:
            if uids_to_remove:
                client.remove_tracks_from_playlist(container_uri, uids_to_remove)
            if tracks_to_add:
                client.add_tracks_to_playlist(container_uri, tracks_to_add, position=pos)

        results.append({
            "category": cat_slug,
            "playlist": pl_name,
            "uri": container_uri,
            "initial": initial_count,
            "removed": len(uids_to_remove),
            "added": len(tracks_to_add),
            "final": final_count
        })
        time.sleep(0.15)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Category Spotify Synchronizer")
    parser.add_argument("--category", type=str, default=None, help="Category slug (activity, artist, era, genre, mood, relationship, tamil, year, indie)")
    parser.add_argument("--all", action="store_true", help="Sync all 9 categories")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating Spotify")
    args = parser.parse_args()

    client = SpotifyNativeClient()

    categories = [
        "activity",
        "relationship",
        "era",
        "genre",
        "tamil",
        "indie",
        "mood",
        "artist",
        "year"
    ]
    if args.category:
        categories = [args.category]

    total_rm = 0
    total_add = 0
    all_res = []

    try:
        for cat in categories:
            res = sync_single_category(client, cat, dry_run=args.dry_run)
            all_res.extend(res)
            total_rm += sum(r["removed"] for r in res)
            total_add += sum(r["added"] for r in res)

        print("\n" + "=" * 80)
        print(" 🎉 SYNCHRONIZATION RUN COMPLETE")
        print("=" * 80)
        print(f" Total Playlists Processed : {len(all_res)}")
        print(f" Total Misplaced Removed   : {total_rm}")
        print(f" Total Missing Added       : {total_add}")
        print("=" * 80)

        # Save summary report
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        report_path = DATA_DIR / "spotify_sync_summary.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dry_run": args.dry_run,
                "total_playlists": len(all_res),
                "total_removed": total_rm,
                "total_added": total_add,
                "details": all_res
            }, f, indent=2)
        print(f"💾 Report saved to {report_path}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
