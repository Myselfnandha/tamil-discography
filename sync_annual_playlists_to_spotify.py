#!/usr/bin/env python3
"""
sync_annual_playlists_to_spotify.py - Automated Annual Playlist Spotify Synchronizer.

Synchronizes local annual playlists (1960-2026) to Spotify containers inside the 'Year' folder:
- Creates missing annual playlists with title '{year}'.
- Moves annual playlists into the Spotify 'Year' folder container.
- Matches and caches Spotify URIs in local SQLite databases to prevent redundant API lookups.
- For 2026: prepends newest drops at position 0 (Newest First).
- Rate-limit resilient batching (50 tracks per batch).
- Updates persistent sync state in data/sync_state.json.
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists" / "year"
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "sync_state.json"
YEAR_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:7581063132455cbe"
YEAR_FOLDER_START = "spotify:start-group:7581063132455cbe"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import move_playlists_to_folder, get_folder_contents


def load_sync_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to read sync state: {e}")
    return {
        "version": 1,
        "last_sync_utc": None,
        "synced_track_ids": [],
        "playlist_snapshots": {},
        "recent_discoveries": []
    }


def save_sync_state(state: dict):
    state["last_sync_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save sync state: {e}")


def sync_single_year(
    client: SpotifyNativeClient,
    year_str: str,
    folder_playlists: Dict[str, str],
    all_playlists: Dict[str, List[Dict[str, str]]],
    limit_tracks: int = 50,
    dry_run: bool = False
) -> bool:
    db_path = PLAYLISTS_DIR / f"{year_str}.db"
    if not db_path.exists():
        logging.error(f"Database {db_path} does not exist!")
        return False

    logging.info(f"\n{'='*70}\n 📅 Synchronizing Annual Playlist: [{year_str}]\n{'='*70}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Read playlist metadata
    info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
    total_db_tracks = int(info.get("total_tracks", 0))
    desc = info.get("description", f"Complete Tamil cinema soundtrack discography & essential releases of {year_str}.")

    # 2. Find or create playlist on Spotify
    target_uri = None
    clean_target_name = clean_text(year_str)

    # Check if already inside Year folder
    if clean_target_name in folder_playlists:
        target_uri = folder_playlists[clean_target_name]
        logging.info(f"  ✅ Found existing '{year_str}' playlist inside Year folder: {target_uri}")
    elif clean_target_name in all_playlists and all_playlists[clean_target_name]:
        target_uri = all_playlists[clean_target_name][0]["uri"]
        logging.info(f"  📍 Found '{year_str}' in library (moving to Year folder): {target_uri}")
        if not dry_run:
            move_playlists_to_folder(client, [target_uri], YEAR_FOLDER_START)
            folder_playlists[clean_target_name] = target_uri
    else:
        if dry_run:
            logging.info(f"  [DRY-RUN] Would create new Spotify playlist '{year_str}' in Year folder.")
            conn.close()
            return True
        logging.info(f"  ✨ Creating new Spotify playlist '{year_str}'...")
        target_uri = client.create_playlist(year_str, desc, folder_start_group=YEAR_FOLDER_START)
        if not target_uri:
            logging.error(f"  ❌ Could not create playlist '{year_str}' on Spotify.")
            conn.close()
            return False
        logging.info(f"  📁 Filed new '{year_str}' playlist directly into Year folder ({target_uri})")
        folder_playlists[clean_target_name] = target_uri

    # 3. Read tracks from database
    cur.execute("""
        SELECT id, track_title, album_title, composer, singers, spotify_uri
        FROM tracks
        ORDER BY position ASC
    """)
    rows = cur.fetchall()

    if limit_tracks > 0:
        rows = rows[:limit_tracks]

    logging.info(f"  🔍 Resolving and caching Spotify URIs for {len(rows)} tracks (total in DB: {total_db_tracks})...")

    resolved_uris = []
    updated_db_records = []

    for r in rows:
        track_id, title, album, composer, singers, sp_uri = r[0], r[1], r[2], r[3], r[4], r[5]
        
        if sp_uri and sp_uri.startswith("spotify:track:"):
            resolved_uris.append(sp_uri)
            continue

        if dry_run:
            continue

        # Search Spotify using title + album (soundtrack edition), fallback to composer/singers
        match_uri = client.search_track(title, album)
        if not match_uri and (composer or singers):
            match_uri = client.search_track(title, composer or singers)
        if not match_uri:
            match_uri = client.search_track(title, "")
        if match_uri:
            resolved_uris.append(match_uri)
            updated_db_records.append((match_uri, track_id))
            logging.info(f"    ✨ Matched: '{title}' ({album}) -> {match_uri}")
        else:
            logging.warning(f"    ⚠️ Not found on Spotify: '{title}' ({album})")

        time.sleep(0.15)

    # Cache resolved URIs back to SQLite
    if updated_db_records and not dry_run:
        with conn:
            conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", updated_db_records)
        logging.info(f"  💾 Cached {len(updated_db_records)} newly resolved Spotify URIs into {db_path.name}.")

    conn.close()

    if dry_run:
        logging.info(f"  [DRY-RUN] Would add up to {len(resolved_uris)} tracks to '{year_str}'.")
        return True

    # 4. Check existing tracks in Spotify playlist to avoid duplicates
    existing_spotify_tracks = client.get_playlist_tracks(target_uri)
    existing_track_uris = {t["uri"] for t in existing_spotify_tracks}
    logging.info(f"  🎧 Currently in Spotify playlist: {len(existing_track_uris)} tracks.")

    tracks_to_add = []
    seen = set(existing_track_uris)
    for u in resolved_uris:
        if u not in seen:
            tracks_to_add.append(u)
            seen.add(u)

    if not tracks_to_add:
        logging.info(f"  ✨ All {len(existing_track_uris)} tracks already synchronized in '{year_str}'.")
        return True

    # 5. Add missing tracks
    pos = "TOP_OF_PLAYLIST" if year_str == "2026" else "BOTTOM_OF_PLAYLIST"
    logging.info(f"  🚀 Adding {len(tracks_to_add)} tracks to '{year_str}' ({pos})...")
    ok = client.add_tracks_to_playlist(target_uri, tracks_to_add, position=pos)
    if ok:
        logging.info(f"  ✅ Successfully synchronized '{year_str}' (now {len(existing_track_uris) + len(tracks_to_add)} songs)!")
    else:
        logging.error(f"  ❌ Failed to add some batches to '{year_str}'.")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Synchronize Annual Tamil Playlists to Spotify.")
    parser.add_argument("--year", type=str, default=None, help="Sync a specific year (e.g. 2026 or 1960)")
    parser.add_argument("--all", action="store_true", help="Sync all 63 annual playlists")
    parser.add_argument("--limit", type=int, default=50, help="Max tracks to sync per playlist (default: 50, use -1 for all)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating Spotify")
    args = parser.parse_args()

    if not args.year and not args.all:
        parser.print_help()
        sys.exit(0)

    logging.info("=" * 80)
    logging.info(" 🚀 SPOTIFY ANNUAL PLAYLISTS SYNCHRONIZATION ENGINE")
    logging.info("=" * 80)

    state = load_sync_state()
    client = SpotifyNativeClient()

    try:
        # Load Year folder contents
        logging.info("🔍 Inspecting Spotify 'Year' folder...")
        folder_items = get_folder_contents(client, YEAR_FOLDER_URI)
        folder_playlists = {clean_text(it["name"]): it["uri"] for it in folder_items}
        logging.info(f"Found {len(folder_playlists)} playlist(s) inside Year folder: {list(folder_playlists.keys())}")

        # Load all playlists
        all_spotify = client.get_all_playlists()

        years_to_sync = []
        if args.year:
            years_to_sync = [args.year]
        elif args.all:
            # Sort years chronologically: historical first, 2026 last
            years_to_sync = [p.stem for p in sorted(PLAYLISTS_DIR.glob("*.db"), key=lambda x: int(x.stem))]

        logging.info(f"Queued {len(years_to_sync)} annual playlist(s) for synchronization.")

        success_count = 0
        for yr in years_to_sync:
            ok = sync_single_year(
                client=client,
                year_str=yr,
                folder_playlists=folder_playlists,
                all_playlists=all_spotify,
                limit_tracks=args.limit,
                dry_run=args.dry_run
            )
            if ok:
                success_count += 1
            time.sleep(0.5)

        logging.info("\n" + "=" * 80)
        logging.info(f" ✅ SYNCHRONIZATION COMPLETED: {success_count}/{len(years_to_sync)} annual playlists processed.")
        logging.info("=" * 80)

        if not args.dry_run:
            save_sync_state(state)

    finally:
        client.close()


if __name__ == "__main__":
    main()
