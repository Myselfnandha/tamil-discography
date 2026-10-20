#!/usr/bin/env python3
"""
sync_complete_annual_playlists.py - Complete Annual Film Songs Spotify Synchronizer.

Synchronizes 100% full movie songs for each year (1960–2026) into the dedicated
'Year - Complete' Spotify folder:
1. Strict Container Isolation:
   - Files playlists into 'Year - Complete' folder (2effe1b0a46ff274).
   - Names playlists '{Year} - Complete' (e.g. '1985 - Complete', '2024 - Complete').
   - Zero interference or pollution with the curated 'Year' Top 50 folder.
2. Theatrical Release Chronology:
   - Chronological movie order (January -> December) via engine/release_chronology.py.
   - Original track sequence (track_number 1..N) within each movie.
3. Filtering & Deduplication:
   - Excludes instrumental score / pure BGM (songs only).
   - Deduplicates promo/single releases against full album releases.
4. Aggressive 3-Tier Multi-Query Matcher:
   - Tier 1: track:"{clean_title}" album:"{clean_album}"
   - Tier 2: track:"{clean_title}" artist:"{clean_artist}"
   - Tier 3: {clean_title} {composer} fallback
   - Caches resolved URIs to data/complete_songs_spotify_cache.json.
5. Rate-Limit Resilient Batching:
   - Batches of 50 tracks per spclient mutation.
   - Prevents duplicate tracks on Spotify.
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
from typing import Dict, List, Optional, Set, Tuple, Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "complete_songs_spotify_cache.json"
STATE_FILE = DATA_DIR / "complete_annual_sync_state.json"
DB_PATH = BASE_DIR / "tamil_discography.db"

YEAR_COMPLETE_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:2effe1b0a46ff274"
YEAR_COMPLETE_FOLDER_START = "spotify:start-group:2effe1b0a46ff274"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import move_playlists_to_folder, get_folder_contents
from engine.release_chronology import get_annual_movie_chronology, clean_key

def load_uri_cache() -> Dict[str, str]:
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache.update(json.load(f))
        except Exception as e:
            logging.warning(f"Error loading URI cache: {e}")

    # Seed with existing resolved URIs from all 213 local DBs (read-only)
    import glob
    for db_f in glob.glob(str(BASE_DIR / "playlists" / "*" / "*.db")):
        try:
            conn = sqlite3.connect(db_f)
            cur = conn.cursor()
            rows = cur.execute("SELECT discography_track_id, spotify_uri, track_title, album_title FROM tracks WHERE spotify_uri IS NOT NULL AND spotify_uri != '';").fetchall()
            for r in rows:
                tid, uri, t_title, a_title = r[0], r[1], r[2], r[3]
                if tid and uri:
                    cache.setdefault(str(tid), uri)
                if t_title and a_title and uri:
                    cache.setdefault(f"{clean_key(t_title)}:{clean_key(a_title)}", uri)
            conn.close()
        except Exception:
            pass
    return cache

def save_uri_cache(cache: Dict[str, str]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except Exception as e:
        logging.error(f"Error saving URI cache: {e}")

def load_sync_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Error loading sync state: {e}")
    return {
        "version": 1,
        "last_sync_utc": None,
        "completed_years": {},
        "metrics": {}
    }

def save_sync_state(state: dict):
    state["last_sync_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving sync state: {e}")

def search_track_aggressive(client: SpotifyNativeClient, title: str, album: str, composer: str, singers: str) -> Optional[str]:
    """
    3-Tier Aggressive Spotify search:
    Tier 1: title + album
    Tier 2: title + primary singer / composer
    Tier 3: title only
    """
    clean_t = clean_text(title)
    clean_alb = clean_text(album)
    clean_comp = clean_text(composer) if composer and "style=" not in composer else ""
    clean_sing = clean_text(singers.split(",")[0].split("&")[0].split("/")[0].strip()) if singers else ""

    # Tier 1: Title + Album
    if clean_alb:
        res = client.search_track(clean_t, clean_alb)
        if res:
            return res

    # Tier 2: Title + Artist (Singer or Composer)
    primary_artist = clean_sing or clean_comp
    if primary_artist:
        res = client.search_track(clean_t, primary_artist)
        if res:
            return res

    # Tier 3: Title only fallback
    return client.search_track(clean_t, "")

def sync_complete_annual_playlist(
    client: SpotifyNativeClient,
    year: int,
    folder_playlists: Dict[str, str],
    all_playlists: Dict[str, List[Dict[str, str]]],
    uri_cache: Dict[str, str],
    limit_tracks: int = -1,
    dry_run: bool = False
) -> Dict[str, Any]:
    playlist_name = f"{year} - Complete"
    clean_name = clean_text(playlist_name)
    description = f"Complete Tamil cinema movie songs of {year}, sequenced chronologically by theatrical release date (Jan-Dec) and original track order."

    logging.info(f"\n{'='*80}\n 📅 Synchronizing Complete Annual Playlist: [{playlist_name}]\n{'='*80}")

    # 1. Fetch chronological movies and tracks
    movies = get_annual_movie_chronology(year, DB_PATH)
    if not movies:
        logging.warning(f"No movie soundtracks found for year {year}!")
        return {"status": "empty", "year": year}

    ordered_tracks = []
    for m in movies:
        for t in m["tracks"]:
            ordered_tracks.append({
                **t,
                "movie_title": m["title"],
                "composer": m["composer"],
                "release_date": m["release_date"]
            })

    total_catalog_songs = len(ordered_tracks)
    logging.info(f"Loaded {len(movies)} movies with {total_catalog_songs} songs in chronological release order.")

    if limit_tracks > 0:
        ordered_tracks = ordered_tracks[:limit_tracks]
        logging.info(f"Limiting to first {limit_tracks} tracks for test/dry-run.")

    # 2. Find or create playlist on Spotify inside 'Year - Complete' folder
    target_uri = None
    if clean_name in folder_playlists:
        target_uri = folder_playlists[clean_name]
        logging.info(f"  ✅ Found existing '{playlist_name}' inside 'Year - Complete' folder: {target_uri}")
    elif clean_name in all_playlists and all_playlists[clean_name]:
        target_uri = all_playlists[clean_name][0]["uri"]
        logging.info(f"  📍 Found '{playlist_name}' in library (moving to 'Year - Complete' folder): {target_uri}")
        if not dry_run:
            move_playlists_to_folder(client, [target_uri], YEAR_COMPLETE_FOLDER_START)
            folder_playlists[clean_name] = target_uri
    else:
        if dry_run:
            logging.info(f"  [DRY-RUN] Would create new Spotify playlist '{playlist_name}' in 'Year - Complete' folder.")
            return {"status": "dry_run", "year": year, "catalog_songs": total_catalog_songs}
        logging.info(f"  ✨ Creating new Spotify playlist '{playlist_name}'...")
        target_uri = client.create_playlist(playlist_name, description, folder_start_group=YEAR_COMPLETE_FOLDER_START)
        if not target_uri:
            logging.error(f"  ❌ Could not create playlist '{playlist_name}' on Spotify.")
            return {"status": "error", "year": year}
        logging.info(f"  📁 Filed new '{playlist_name}' playlist into 'Year - Complete' folder ({target_uri})")
        folder_playlists[clean_name] = target_uri

    # 3. Resolve Spotify URIs for all ordered tracks
    resolved_track_uris = []
    new_cache_entries = 0
    db_updates = []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for idx, t in enumerate(ordered_tracks, 1):
        t_id = t["id"]
        t_title = t["title"]
        m_title = t["movie_title"]
        composer = t["composer"]
        singers = t.get("singers", "")
        cache_key = f"{t_id}:{clean_key(t_title)}:{clean_key(m_title)}"
        title_album_key = f"{clean_key(t_title)}:{clean_key(m_title)}"

        # Check local JSON cache or pre-existing DB cache
        sp_uri = uri_cache.get(cache_key) or uri_cache.get(title_album_key) or uri_cache.get(str(t_id))

        # If still missing, query Spotify aggressively
        if not sp_uri and not dry_run:
            sp_uri = search_track_aggressive(client, t_title, m_title, composer, singers)
            if sp_uri:
                uri_cache[cache_key] = sp_uri
                uri_cache[title_album_key] = sp_uri
                uri_cache[str(t_id)] = sp_uri
                new_cache_entries += 1
                logging.info(f"    [{idx:3d}/{len(ordered_tracks)}] ✨ Matched: '{t_title}' ({m_title}) -> {sp_uri}")
            else:
                logging.warning(f"    [{idx:3d}/{len(ordered_tracks)}] ⚠️ Not found on Spotify: '{t_title}' ({m_title})")
            time.sleep(0.12)
            if new_cache_entries % 25 == 0:
                save_uri_cache(uri_cache)

        if sp_uri and sp_uri not in resolved_track_uris:
            resolved_track_uris.append(sp_uri)

    conn.close()

    if new_cache_entries > 0:
        save_uri_cache(uri_cache)

    logging.info(f"  📊 Match Resolution: {len(resolved_track_uris)}/{len(ordered_tracks)} tracks resolved ({len(resolved_track_uris)/len(ordered_tracks)*100:.1f}%).")

    if dry_run:
        logging.info(f"  [DRY-RUN] Would synchronize {len(resolved_track_uris)} tracks into '{playlist_name}'.")
        return {
            "status": "dry_run",
            "year": year,
            "catalog_songs": total_catalog_songs,
            "resolved_songs": len(resolved_track_uris)
        }

    # 4. Check existing tracks on Spotify playlist
    existing_spotify_tracks = client.get_playlist_tracks(target_uri)
    existing_track_uris = {t["uri"] for t in existing_spotify_tracks}
    logging.info(f"  🎧 Currently in Spotify playlist: {len(existing_track_uris)} tracks.")

    tracks_to_add = []
    seen = set(existing_track_uris)
    for u in resolved_track_uris:
        if u not in seen:
            tracks_to_add.append(u)
            seen.add(u)

    if not tracks_to_add:
        logging.info(f"  ✨ All {len(existing_track_uris)} tracks already synchronized in '{playlist_name}'.")
        return {
            "status": "synchronized",
            "year": year,
            "catalog_songs": total_catalog_songs,
            "spotify_tracks": len(existing_track_uris),
            "added_now": 0
        }

    # 5. Add missing tracks in 50-track batches
    logging.info(f"  🚀 Adding {len(tracks_to_add)} tracks to '{playlist_name}' in batches of 50...")
    ok = client.add_tracks_to_playlist(target_uri, tracks_to_add, position="BOTTOM_OF_PLAYLIST")
    if ok:
        final_count = len(existing_track_uris) + len(tracks_to_add)
        logging.info(f"  ✅ Successfully synchronized '{playlist_name}' (Total tracks on Spotify: {final_count})!")
        return {
            "status": "success",
            "year": year,
            "catalog_songs": total_catalog_songs,
            "spotify_tracks": final_count,
            "added_now": len(tracks_to_add),
            "playlist_uri": target_uri
        }
    else:
        logging.error(f"  ❌ Error adding some track batches to '{playlist_name}'.")
        return {"status": "partial_error", "year": year}

def main():
    parser = argparse.ArgumentParser(description="Synchronize Complete Annual Tamil Playlists to Spotify.")
    parser.add_argument("--year", type=int, default=None, help="Sync a specific year (e.g. 1985 or 2024)")
    parser.add_argument("--pilot", action="store_true", help="Run 2-Year Pilot (1985 and 2024)")
    parser.add_argument("--all", action="store_true", help="Sync all active years (1960-2026)")
    parser.add_argument("--limit", type=int, default=-1, help="Max tracks to sync per playlist (-1 for all)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without mutating Spotify")
    args = parser.parse_args()

    if not args.year and not args.pilot and not args.all:
        parser.print_help()
        sys.exit(0)

    logging.info("=" * 80)
    logging.info(" 🎬 SPOTIFY 'YEAR - COMPLETE' FULL SONGS ANNUAL SYNCHRONIZATION ENGINE")
    logging.info("=" * 80)

    uri_cache = load_uri_cache()
    state = load_sync_state()
    client = SpotifyNativeClient()

    try:
        # Load 'Year - Complete' folder contents
        logging.info("🔍 Inspecting Spotify 'Year - Complete' folder...")
        folder_items = get_folder_contents(client, YEAR_COMPLETE_FOLDER_URI)
        folder_playlists = {clean_text(it["name"]): it["uri"] for it in folder_items}
        logging.info(f"Found {len(folder_playlists)} playlist(s) inside 'Year - Complete' folder: {list(folder_playlists.keys())}")

        all_spotify = client.get_all_playlists()

        years_to_sync = []
        if args.year:
            years_to_sync = [args.year]
        elif args.pilot:
            years_to_sync = [1985, 2024]
        elif args.all:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            years_to_sync = [r[0] for r in cur.execute("SELECT DISTINCT year FROM albums WHERE album_type = 'film' ORDER BY year ASC;").fetchall()]
            conn.close()

        logging.info(f"Queued {len(years_to_sync)} complete annual playlist(s): {years_to_sync}")

        results = []
        for yr in years_to_sync:
            res = sync_complete_annual_playlist(
                client=client,
                year=yr,
                folder_playlists=folder_playlists,
                all_playlists=all_spotify,
                uri_cache=uri_cache,
                limit_tracks=args.limit,
                dry_run=args.dry_run
            )
            results.append(res)
            time.sleep(1.0)

        logging.info("\n" + "=" * 80)
        logging.info(" 📊 SYNCHRONIZATION SUMMARY REPORT")
        logging.info("=" * 80)
        for r in results:
            logging.info(f"  📅 Year {r.get('year')}: {r.get('status')} | Catalog Songs: {r.get('catalog_songs', 0)} | Spotify: {r.get('spotify_tracks', 0)}")
        logging.info("=" * 80)

        if not args.dry_run:
            for r in results:
                yr_str = str(r.get("year"))
                state["completed_years"][yr_str] = {
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                    "status": r.get("status"),
                    "tracks_count": r.get("spotify_tracks", 0)
                }
            save_sync_state(state)

    finally:
        client.close()

if __name__ == "__main__":
    main()
