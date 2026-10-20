#!/usr/bin/env python3
"""
sync_indie_playlists_to_spotify.py - Automated Tamil Indie Playlists Spotify Synchronizer.

Synchronizes local independent & YouTube album playlists to Spotify containers inside the 'Indie' folder:
- Creates missing indie playlists with official names and descriptions.
- Moves indie playlists into the Spotify 'Indie' folder container.
- Matches and caches Spotify URIs in local SQLite databases to prevent redundant lookups.
- Avoids duplicate tracks in Spotify playlists.
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
PLAYLISTS_DIR = BASE_DIR / "playlists" / "indie"
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "sync_state.json"
INDIE_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:859025b00671d970"
INDIE_FOLDER_START = "spotify:start-group:859025b00671d970"

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


def sync_single_indie_playlist(
    client: SpotifyNativeClient,
    slug: str,
    folder_playlists: Dict[str, str],
    all_playlists: Dict[str, List[Dict[str, str]]],
    limit_tracks: int = 50,
    dry_run: bool = False
) -> bool:
    db_path = PLAYLISTS_DIR / f"{slug}.db"
    if not db_path.exists():
        logging.error(f"Database {db_path} does not exist!")
        return False

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Read playlist metadata
    info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
    name = info.get("name", slug.replace("_", " ").title())
    desc = info.get("description", "Tamil Independent & Non-Film Music.")
    emoji = info.get("emoji", "🌿")
    total_db_tracks = int(info.get("total_tracks", 0))

    logging.info(f"\n{'='*70}\n {emoji} Synchronizing Indie Playlist: [{name}] ({slug}.db)\n{'='*70}")

    # 2. Find or create playlist on Spotify
    target_uri = None
    clean_target_name = clean_text(name)

    # Check if already inside Indie folder
    if clean_target_name in folder_playlists:
        target_uri = folder_playlists[clean_target_name]
        logging.info(f"  ✅ Found existing '{name}' playlist inside Indie folder: {target_uri}")
    elif clean_target_name in all_playlists and all_playlists[clean_target_name]:
        target_uri = all_playlists[clean_target_name][0]["uri"]
        logging.info(f"  📍 Found '{name}' in library (moving to Indie folder): {target_uri}")
        if not dry_run:
            move_playlists_to_folder(client, [target_uri], INDIE_FOLDER_START)
            folder_playlists[clean_target_name] = target_uri
    else:
        if dry_run:
            logging.info(f"  [DRY-RUN] Would create new Spotify playlist '{name}' in Indie folder.")
            conn.close()
            return True
        logging.info(f"  ✨ Creating new Spotify playlist '{name}'...")
        target_uri = client.create_playlist(name, desc)
        if not target_uri:
            logging.error(f"  ❌ Could not create playlist '{name}' on Spotify.")
            conn.close()
            return False
        logging.info(f"  📁 Moving new '{name}' playlist into Indie folder...")
        move_playlists_to_folder(client, [target_uri], INDIE_FOLDER_START)
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

        # Search Spotify using title and composer/singer
        artist_query = composer or singers or ""
        match_uri = client.search_track(title, artist_query)
        if match_uri:
            resolved_uris.append(match_uri)
            updated_db_records.append((match_uri, track_id))
            logging.info(f"    ✨ Matched: '{title}' ({artist_query}) -> {match_uri}")
        else:
            logging.debug(f"    ⚠️ Not found on Spotify: '{title}' ({artist_query})")

        time.sleep(0.15)

    # Cache resolved URIs back to SQLite
    if updated_db_records and not dry_run:
        with conn:
            conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", updated_db_records)
        logging.info(f"  💾 Cached {len(updated_db_records)} newly resolved Spotify URIs into {db_path.name}.")

    conn.close()

    if dry_run:
        logging.info(f"  [DRY-RUN] Would add up to {len(resolved_uris)} tracks to '{name}'.")
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
        logging.info(f"  ✨ All {len(existing_track_uris)} tracks already synchronized in '{name}'.")
        return True

    # 5. Add missing tracks
    logging.info(f"  🚀 Adding {len(tracks_to_add)} tracks to '{name}'...")
    ok = client.add_tracks_to_playlist(target_uri, tracks_to_add, position="BOTTOM_OF_PLAYLIST")
    if ok:
        logging.info(f"  ✅ Successfully synchronized '{name}' (now {len(existing_track_uris) + len(tracks_to_add)} songs)!")
    else:
        logging.error(f"  ❌ Failed to add some batches to '{name}'.")

    return ok


def main():
    parser = argparse.ArgumentParser(description="Synchronize Tamil Independent Playlists to Spotify.")
    parser.add_argument("--slug", type=str, default=None, help="Sync a specific indie playlist (e.g. indie_master, stephen_zechariah)")
    parser.add_argument("--all", action="store_true", help="Sync all 11 indie playlists")
    parser.add_argument("--limit", type=int, default=50, help="Max tracks to sync per playlist (default: 50, use -1 for all)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating Spotify")
    args = parser.parse_args()

    if not args.slug and not args.all:
        parser.print_help()
        sys.exit(0)

    logging.info("=" * 80)
    logging.info(" 🌿 SPOTIFY TAMIL INDIE PLAYLISTS SYNCHRONIZATION ENGINE")
    logging.info("=" * 80)

    state = load_sync_state()
    client = SpotifyNativeClient()

    try:
        # Load Indie folder contents
        logging.info("🔍 Inspecting Spotify 'Indie' folder...")
        folder_items = get_folder_contents(client, INDIE_FOLDER_URI)
        folder_playlists = {clean_text(it["name"]): it["uri"] for it in folder_items}
        logging.info(f"Found {len(folder_playlists)} playlist(s) inside Indie folder: {list(folder_playlists.keys())}")

        # Load all playlists
        all_spotify = client.get_all_playlists()

        playlists_to_sync = []
        if args.slug:
            playlists_to_sync = [args.slug]
        elif args.all:
            playlists_to_sync = [
                "indie_master",
                "indie_blockbusters",
                "hidden_indie_gems",
                "indie_rap",
                "romantic_indie",
                "folk_gaana_album",
                "stephen_zechariah",
                "kaber_vasuki",
                "arivu_paal_dabba",
                "vaisagh",
                "sean_roldan_pradeep_indie"
            ]

        logging.info(f"Queued {len(playlists_to_sync)} indie playlist(s) for synchronization.")

        success_count = 0
        for pl_slug in playlists_to_sync:
            ok = sync_single_indie_playlist(
                client=client,
                slug=pl_slug,
                folder_playlists=folder_playlists,
                all_playlists=all_spotify,
                limit_tracks=args.limit,
                dry_run=args.dry_run
            )
            if ok:
                success_count += 1
            time.sleep(0.5)

        logging.info("\n" + "=" * 80)
        logging.info(f" ✅ SYNCHRONIZATION COMPLETED: {success_count}/{len(playlists_to_sync)} indie playlists processed.")
        logging.info("=" * 80)

        if not args.dry_run:
            save_sync_state(state)

    finally:
        client.close()


if __name__ == "__main__":
    main()
