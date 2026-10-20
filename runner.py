#!/usr/bin/env python3
"""
runner.py - Resilient batch pipeline for Tamil Discography (1960-2026).
Coordinates Wikipedia scraping, SQLite insertion, checkpoint tracking, and JSON emission.
"""

import sys
import os
import time
import argparse
import logging
from db import init_db, insert_album_with_tracks, update_checkpoint, get_checkpoint
from fetcher import fetch_annual_filmography, fetch_soundtrack_tracks
from export import export_year_to_json, export_summary_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def process_year(year, force=False, delay=0.4):
    """
    Ingest a single year's complete filmography and soundtracks.
    Idempotent and resumable.
    """
    cp = get_checkpoint(year)
    if cp and cp.get("status") == "completed" and not force:
        logging.info(f"Year {year} is already completed ({cp.get('albums_count')} albums, {cp.get('tracks_count')} tracks). Use --force to re-run.")
        return cp.get("albums_count", 0), cp.get("tracks_count", 0)

    logging.info(f"=== Starting Ingestion for Year {year} ===")
    update_checkpoint(year, "in_progress")
    
    films = fetch_annual_filmography(year)
    if not films:
        logging.warning(f"No films found for Year {year}.")
        update_checkpoint(year, "failed", 0, 0)
        return 0, 0
        
    total_albums = len(films)
    total_tracks_year = 0
    
    for idx, f in enumerate(films, 1):
        wiki_page = f.get("wiki_page") or f.get("title")
        title = f.get("title")
        logging.info(f"[{idx}/{total_albums}] Processing '{title}' (Wiki: {wiki_page})...")
        
        tracks = []
        try:
            tracks = fetch_soundtrack_tracks(wiki_page)
        except Exception as e:
            logging.warning(f"Error fetching tracks for '{title}': {e}")
            
        album_id = insert_album_with_tracks(f, tracks)
        total_tracks_year += len(tracks)
        
        if len(tracks) > 0:
            logging.info(f"  -> Extracted {len(tracks)} tracks.")
        else:
            logging.info("  -> Film indexed (soundtrack unlisted on Wikipedia).")
            
        time.sleep(delay)

    # Finalize checkpoint
    update_checkpoint(year, "completed", total_albums, total_tracks_year)
    
    # Emit JSON files
    json_path, _, _ = export_year_to_json(year)
    logging.info(f"Emitted annual OCD JSON: {json_path}")
    
    export_summary_index()
    logging.info(f"=== Finished Year {year}: {total_albums} albums, {total_tracks_year} tracks. ===")
    return total_albums, total_tracks_year

def main():
    parser = argparse.ArgumentParser(description="Tamil Discography Batch Ingestion Pipeline (1960-2026)")
    parser.add_argument("--year", type=int, help="Single year to ingest (e.g., 1960)")
    parser.add_argument("--start", type=int, help="Start year for range (e.g., 1960)")
    parser.add_argument("--end", type=int, help="End year for range (e.g., 1969)")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of already completed years")
    parser.add_argument("--delay", type=float, default=0.3, help="Polite delay between Wikipedia calls in seconds (default 0.3)")
    
    args = parser.parse_args()
    init_db()

    if args.year:
        process_year(args.year, force=args.force, delay=args.delay)
    elif args.start and args.end:
        for y in range(args.start, args.end + 1):
            process_year(y, force=args.force, delay=args.delay)
    else:
        # Default pilot run: 1960
        logging.info("No year specified. Running pilot year 1960 by default.")
        process_year(1960, force=args.force, delay=args.delay)

if __name__ == "__main__":
    main()
