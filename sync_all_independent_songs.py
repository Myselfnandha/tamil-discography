#!/usr/bin/env python3
"""
sync_all_independent_songs.py - Synchronizes all Tamil Independent songs into a dedicated
Spotify playlist 'All Independent Songs' inside the 'Indie' folder container.

Ordering:
- Tiered Evidence & Popularity:
  Tier 1 Mega (105.0) -> Tier 2 Popular (85.0) -> Tier 3 Emerging (50.0) -> Tier 4 Underground (25.0)
- Preserves exact position order from playlists/indie/indie_master.db.
- Aggressive 3-Tier Multi-Query matching for unresolved songs.
- Rate-limit resilient batching (50 tracks per batch).
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PLAYLISTS_DIR = BASE_DIR / "playlists" / "indie"
CACHE_FILE = DATA_DIR / "complete_songs_spotify_cache.json"
INDIE_MASTER_DB = PLAYLISTS_DIR / "indie_master.db"

INDIE_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:859025b00671d970"
INDIE_FOLDER_START = "spotify:start-group:859025b00671d970"
PLAYLIST_NAME = "All Independent Songs"
PLAYLIST_DESC = "The complete definitive collection of Tamil independent, YouTube, and non-film music, ranked by popularity, views, and cultural evidence."

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import move_playlists_to_folder, get_folder_contents
from sync_complete_annual_playlists import search_track_aggressive, load_uri_cache, save_uri_cache
from engine.release_chronology import clean_key

def sync_all_independent_songs(
    limit_tracks: int = -1,
    dry_run: bool = False
) -> Dict[str, Any]:
    if not INDIE_MASTER_DB.exists():
        logging.error(f"Database {INDIE_MASTER_DB} does not exist!")
        return {"status": "error", "message": "Database not found"}

    logging.info("=" * 80)
    logging.info(f" 🌿 SYNCHRONIZING DEDICATED PLAYLIST: [{PLAYLIST_NAME}]")
    logging.info("=" * 80)

    uri_cache = load_uri_cache()
    client = None if dry_run else SpotifyNativeClient()

    try:
        if client:
            logging.info("🔍 Inspecting Spotify 'Indie' folder...")
            folder_items = get_folder_contents(client, INDIE_FOLDER_URI)
            folder_playlists = {clean_text(it["name"]): it["uri"] for it in folder_items}
            logging.info(f"Found {len(folder_playlists)} playlist(s) inside 'Indie' folder: {list(folder_playlists.keys())}")

            all_spotify = client.get_all_playlists()
            clean_target_name = clean_text(PLAYLIST_NAME)

            # 2. Find or create playlist on Spotify inside 'Indie' folder
            target_uri = None
            if clean_target_name in folder_playlists:
                target_uri = folder_playlists[clean_target_name]
                logging.info(f"  ✅ Found existing '{PLAYLIST_NAME}' inside 'Indie' folder: {target_uri}")
            elif clean_target_name in all_spotify and all_spotify[clean_target_name]:
                target_uri = all_spotify[clean_target_name][0]["uri"]
                logging.info(f"  📍 Found '{PLAYLIST_NAME}' in library (moving into 'Indie' folder): {target_uri}")
                move_playlists_to_folder(client, [target_uri], INDIE_FOLDER_START)
                folder_playlists[clean_target_name] = target_uri
            else:
                logging.info(f"  ✨ Creating new Spotify playlist '{PLAYLIST_NAME}' in 'Indie' folder...")
                target_uri = client.create_playlist(PLAYLIST_NAME, PLAYLIST_DESC, folder_start_group=INDIE_FOLDER_START)
                if not target_uri:
                    logging.error(f"  ❌ Could not create playlist '{PLAYLIST_NAME}' on Spotify.")
                    return {"status": "error", "message": "Failed to create playlist"}
                logging.info(f"  📁 Filed new '{PLAYLIST_NAME}' directly into 'Indie' folder ({target_uri})")
                folder_playlists[clean_target_name] = target_uri
        else:
            logging.info("  [DRY-RUN] Simulating catalog resolution and track ordering...")

        # 3. Read all tracks from indie_master.db ordered strictly by position ASC
        conn = sqlite3.connect(INDIE_MASTER_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT id, position, track_title, album_title, composer, singers,
                   evidence_tier, historical_evidence_score, spotify_uri, discography_track_id
            FROM tracks
            ORDER BY position ASC;
        """).fetchall()

        tracks = [dict(r) for r in rows]
        total_tracks = len(tracks)
        logging.info(f"Loaded {total_tracks} independent tracks from {INDIE_MASTER_DB.name} ordered by popularity tier & score.")

        if limit_tracks > 0:
            tracks = tracks[:limit_tracks]
            logging.info(f"Limiting to first {limit_tracks} tracks for test/dry-run.")

        # 4. Resolve Spotify URIs for all ordered tracks
        resolved_uris = []
        new_matches = 0
        db_updates = []

        for idx, t in enumerate(tracks, 1):
            t_id = t["id"]
            disc_id = t["discography_track_id"]
            title = t["track_title"]
            album = t["album_title"]
            composer = t["composer"]
            singers = t["singers"]
            sp_uri = t["spotify_uri"]

            cache_key = f"{disc_id}:{clean_key(title)}:{clean_key(album)}"
            title_key = f"{clean_key(title)}:{clean_key(album)}"

            if not sp_uri or not sp_uri.startswith("spotify:track:"):
                sp_uri = uri_cache.get(cache_key) or uri_cache.get(title_key) or uri_cache.get(str(disc_id))

            if not sp_uri and not dry_run:
                sp_uri = search_track_aggressive(client, title, album, composer, singers)
                if sp_uri:
                    uri_cache[cache_key] = sp_uri
                    uri_cache[title_key] = sp_uri
                    if disc_id:
                        uri_cache[str(disc_id)] = sp_uri
                    new_matches += 1
                    db_updates.append((sp_uri, t_id))
                    logging.info(f"    [{idx:3d}/{len(tracks)}] ✨ Matched: '{title}' ({album}) -> {sp_uri}")
                else:
                    logging.warning(f"    [{idx:3d}/{len(tracks)}] ⚠️ Not found on Spotify: '{title}' ({album})")
                time.sleep(0.12)
                if new_matches % 25 == 0:
                    save_uri_cache(uri_cache)

            if sp_uri and sp_uri not in resolved_uris:
                resolved_uris.append(sp_uri)

        # Update indie_master.db with newly matched URIs
        if db_updates and not dry_run:
            with conn:
                conn.executemany("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", db_updates)
            logging.info(f"  💾 Cached {len(db_updates)} newly resolved Spotify URIs back into {INDIE_MASTER_DB.name}.")

        conn.close()

        if new_matches > 0:
            save_uri_cache(uri_cache)

        match_pct = (len(resolved_uris) / len(tracks)) * 100 if tracks else 0
        logging.info(f"  📊 Match Resolution: {len(resolved_uris)}/{len(tracks)} tracks resolved ({match_pct:.1f}%).")

        if dry_run:
            logging.info(f"  [DRY-RUN] Would synchronize {len(resolved_uris)} tracks into '{PLAYLIST_NAME}'.")
            return {
                "status": "dry_run",
                "playlist_name": PLAYLIST_NAME,
                "total_catalog_tracks": total_tracks,
                "resolved_tracks": len(resolved_uris)
            }

        # 5. Check existing tracks in Spotify playlist to avoid duplicates
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
            logging.info(f"  ✨ All {len(existing_track_uris)} tracks already synchronized in '{PLAYLIST_NAME}'.")
            return {
                "status": "synchronized",
                "playlist_name": PLAYLIST_NAME,
                "total_catalog_tracks": total_tracks,
                "spotify_tracks": len(existing_track_uris),
                "added_now": 0
            }

        # 6. Add tracks in batches of 50
        logging.info(f"  🚀 Adding {len(tracks_to_add)} tracks to '{PLAYLIST_NAME}' in batches of 50...")
        ok = client.add_tracks_to_playlist(target_uri, tracks_to_add, position="BOTTOM_OF_PLAYLIST")
        if ok:
            final_count = len(existing_track_uris) + len(tracks_to_add)
            logging.info(f"  ✅ Successfully synchronized '{PLAYLIST_NAME}' (Total tracks on Spotify: {final_count})!")
            return {
                "status": "success",
                "playlist_name": PLAYLIST_NAME,
                "total_catalog_tracks": total_tracks,
                "spotify_tracks": final_count,
                "added_now": len(tracks_to_add),
                "playlist_uri": target_uri
            }
        else:
            logging.error(f"  ❌ Error adding track batches to '{PLAYLIST_NAME}'.")
            return {"status": "error", "message": "Batch insertion failed"}

    finally:
        if client:
            client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize All Independent Songs playlist to Spotify.")
    parser.add_argument("--limit", type=int, default=-1, help="Max tracks to sync (-1 for all)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating Spotify")
    args = parser.parse_args()

    sync_all_independent_songs(limit_tracks=args.limit, dry_run=args.dry_run)
