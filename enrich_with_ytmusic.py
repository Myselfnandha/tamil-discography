#!/usr/bin/env python3
"""
enrich_with_ytmusic.py - Autonomous YouTube Music Enrichment Engine for Tamil Discography.
Queries YouTube Music for all empty albums in tamil_discography.db to:
1. Extract official soundtrack tracklists, artists/singers, durations, and video IDs.
2. Fill missing composers in albums table.
3. Automatically refresh all 139 playlist databases periodically.
4. Includes persistent checkpointing and resume support.
"""

import sys
import os
import re
import time
import difflib
import sqlite3
import argparse
import logging
from pathlib import Path

try:
    from ytmusicapi import YTMusic
except ImportError:
    print("Error: ytmusicapi is not installed. Run: pip install ytmusicapi")
    sys.exit(1)

from build_playlists import generate_all_playlists

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Common junk keywords in YouTube Music album titles to ignore
EXCLUDE_KEYWORDS = [
    r"\bkaraoke\b",
    r"\bcover\b",
    r"\bremix\b",
    r"\blo-?fi\b",
    r"\bacoustic cover\b",
    r"\binstrumental cover\b",
    r"\bdialogues?\b",
    r"\bteaser\b",
    r"\btrailer\b",
    r"\bscene\b",
    r"\btrendingformusic\b"
]

JUNK_ALBUM_PATTERNS = [
    r"rowspan\s*=",
    r"colspan\s*=",
    r"style\s*=",
    r"width\s*=",
    r"background\s*:",
    r"bgcolor\s*=",
    r"align\s*=",
    r"class\s*=",
    r"^--+$",
    r"^[!|]",
    r"^\d{1,2}$",
    r"^\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)$",
    r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)$",
]

def is_junk_album_title(title: str) -> bool:
    """Return True if title is a wikitable header, cell formatting, or raw date."""
    if not title or len(title.strip()) <= 1:
        return True
    t = title.strip()
    for p in JUNK_ALBUM_PATTERNS:
        if re.search(p, t, re.I):
            return True
    return False

def init_checkpoint_table(conn):
    """Ensure checkpoint table exists to resume without repeating work."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ytmusic_checkpoints (
                album_id INTEGER PRIMARY KEY,
                album_title TEXT,
                year INTEGER,
                status TEXT, -- 'matched', 'not_found', 'error'
                yt_album_id TEXT,
                tracks_added INTEGER DEFAULT 0,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ytm_status ON ytmusic_checkpoints(status);")


def clean_title_for_matching(title: str) -> str:
    """Strip subtitles and special characters for string comparison."""
    if not title:
        return ""
    # Strip (Original Motion Picture Soundtrack), [Tamil], (Tamil), etc.
    t = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    t = re.sub(r'[-–—|/].*$', '', t)
    t = re.sub(r'[^a-zA-Z0-9]', '', t).lower()
    return t


def match_score(query_title: str, candidate_title: str) -> float:
    """Calculate fuzzy similarity ratio between movie title and candidate album title."""
    q = clean_title_for_matching(query_title)
    c = clean_title_for_matching(candidate_title)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    return difflib.SequenceMatcher(None, q, c).ratio()


def is_excluded_album(cand_title: str) -> bool:
    """Check if candidate is a cover, karaoke, dialogue, or fan-made remix."""
    for pat in EXCLUDE_KEYWORDS:
        if re.search(pat, cand_title, re.I):
            return True
    return False


def find_best_album(yt, movie_title: str, year: int, composer: str = ""):
    """
    Search YouTube Music for the official soundtrack album.
    Tries queries in order:
    1. "{movie_title} {composer}" if composer exists
    2. "{movie_title} Tamil"
    3. "{movie_title}"
    """
    queries = []
    if composer and len(composer) < 30:
        queries.append(f"{movie_title} {composer}")
    queries.append(f"{movie_title} Tamil")
    queries.append(movie_title)

    best_match = None
    best_score = 0.0

    for q in queries:
        try:
            results = yt.search(q, filter="albums")
        except Exception as e:
            logging.debug(f"Search error for '{q}': {e}")
            continue

        for r in results:
            cand_title = r.get("title", "")
            if is_excluded_album(cand_title):
                continue

            score = match_score(movie_title, cand_title)
            if score > best_score:
                best_score = score
                best_match = r

            # If near-perfect match found, accept immediately
            if best_score >= 0.90:
                return best_match, best_score

        if best_match and best_score >= 0.80:
            return best_match, best_score

    if best_score >= 0.75:
        return best_match, best_score

    return None, 0.0


def enrich_albums(limit=None, start_year=None, end_year=None, auto_refresh_interval=50, dry_run=False, retry_not_found=False):
    """Run autonomous YouTube Music enrichment."""
    conn = sqlite3.connect(DISCO_DB)
    conn.row_factory = sqlite3.Row
    init_checkpoint_table(conn)

    yt = YTMusic()

    # Query albums that have 0 tracks and have not been successfully processed yet
    query = """
        SELECT a.id, a.title, a.year, a.composer 
        FROM albums a
        WHERE a.id NOT IN (SELECT DISTINCT album_id FROM tracks)
    """
    if retry_not_found:
        query += " AND a.id NOT IN (SELECT album_id FROM ytmusic_checkpoints WHERE status = 'matched')"
    else:
        query += " AND a.id NOT IN (SELECT album_id FROM ytmusic_checkpoints)"

    params = []
    if start_year:
        query += " AND a.year >= ?"
        params.append(start_year)
    if end_year:
        query += " AND a.year <= ?"
        params.append(end_year)

    query += " ORDER BY a.year DESC, a.title ASC"
    if limit:
        query += f" LIMIT {limit}"

    cur = conn.cursor()
    cur.execute(query, params)
    albums_to_process = cur.fetchall()

    print("\n" + "="*85)
    print(" 🚀 YOUTUBE MUSIC AUTONOMOUS CATALOG ENRICHMENT ENGINE")
    print("="*85)
    print(f"  • Albums queued for search : {len(albums_to_process):,}")
    print(f"  • Auto-refresh interval    : Every {auto_refresh_interval} enriched albums")
    print(f"  • Mode                     : {'DRY RUN (no DB writes)' if dry_run else 'ACTIVE INGESTION'}")
    print("="*85 + "\n")

    matched_count = 0
    not_found_count = 0
    total_tracks_added = 0
    enriched_since_refresh = 0

    for idx, alb in enumerate(albums_to_process, start=1):
        alb_id = alb["id"]
        alb_title = alb["title"].strip()
        alb_year = alb["year"] or 0
        alb_composer = (alb["composer"] or "").strip()

        if is_junk_album_title(alb_title):
            continue

        # Find best album on YouTube Music
        match, score = find_best_album(yt, alb_title, alb_year, alb_composer)

        if not match or score < 0.75:
            logging.info(f"[{idx:>4}/{len(albums_to_process)}] ❌ No match for: \"{alb_title}\" ({alb_year})")
            if not dry_run:
                with conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO ytmusic_checkpoints (album_id, album_title, year, status, yt_album_id, tracks_added)
                        VALUES (?, ?, ?, 'not_found', '', 0);
                    """, (alb_id, alb_title, alb_year))
            not_found_count += 1
            time.sleep(0.3)
            continue

        browse_id = match.get("browseId")
        yt_title = match.get("title", "")
        yt_artists = [a.get("name") for a in match.get("artists", []) if a.get("name")]
        yt_composer = ", ".join(yt_artists)

        # Fetch detailed album tracklist
        try:
            album_details = yt.get_album(browse_id)
        except Exception as e:
            logging.warning(f"Failed to fetch album details for '{browse_id}': {e}")
            time.sleep(0.5)
            continue

        tracks = album_details.get("tracks", [])
        if not tracks:
            logging.info(f"[{idx:>4}/{len(albums_to_process)}] ⚠️ Empty album tracklist on YouTube: \"{yt_title}\"")
            continue

        print(f"[{idx:>4}/{len(albums_to_process)}] ✅ \"{alb_title}\" ({alb_year}) -> \"{yt_title}\" ({len(tracks)} tracks) | Artists: {yt_composer}")

        if not dry_run:
            with conn:
                # 1. Update composer in albums table if empty
                if not alb_composer and yt_composer:
                    conn.execute("UPDATE albums SET composer = ? WHERE id = ?;", (yt_composer, alb_id))

                # 2. Insert tracks
                for pos, t in enumerate(tracks, start=1):
                    t_title = t.get("title", "").strip()
                    if not t_title:
                        continue
                    t_dur = t.get("duration", "") or ""
                    t_artists_list = [a.get("name") for a in t.get("artists", []) if a.get("name")]
                    t_singers = ", ".join(t_artists_list) if t_artists_list else yt_composer
                    vid = t.get("videoId", "") or ""

                    stream_url = f"https://music.youtube.com/watch?v={vid}" if vid else ""

                    conn.execute("""
                        INSERT OR IGNORE INTO tracks (
                            album_id, track_number, title, singers, lyricist, raga, duration, stream_url
                        ) VALUES (?, ?, ?, ?, '', '', ?, ?);
                    """, (alb_id, pos, t_title, t_singers, t_dur, stream_url))

                # 3. Record checkpoint
                conn.execute("""
                    INSERT OR REPLACE INTO ytmusic_checkpoints (album_id, album_title, year, status, yt_album_id, tracks_added)
                    VALUES (?, ?, ?, 'matched', ?, ?);
                """, (alb_id, alb_title, alb_year, browse_id, len(tracks)))

        matched_count += 1
        total_tracks_added += len(tracks)
        enriched_since_refresh += 1

        # Check for auto-refresh trigger
        if not dry_run and enriched_since_refresh >= auto_refresh_interval:
            print(f"\n🔄 Auto-refreshing 139 playlist databases after {enriched_since_refresh} new albums...")
            generate_all_playlists()
            enriched_since_refresh = 0

        time.sleep(0.35)

    conn.close()

    # Final playlist refresh if any new tracks were added
    if not dry_run and enriched_since_refresh > 0:
        print(f"\n🔄 Running final auto-refresh on all 139 playlist databases...")
        generate_all_playlists()

    print("\n" + "="*85)
    print(" ✅ ENRICHMENT SESSION COMPLETE")
    print("="*85)
    print(f"  • Total Albums Matched : {matched_count:,}")
    print(f"  • Total Tracks Added   : {total_tracks_added:,}")
    print(f"  • Albums Not Found     : {not_found_count:,}")
    print("="*85 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Tamil Discography with YouTube Music official tracks.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of albums to enrich")
    parser.add_argument("--start-year", type=int, default=None, help="Start from this year (e.g. 1970)")
    parser.add_argument("--end-year", type=int, default=None, help="End at this year (e.g. 2026)")
    parser.add_argument("--interval", type=int, default=50, help="Playlist auto-refresh interval in albums")
    parser.add_argument("--retry-not-found", action="store_true", help="Re-query albums previously marked as not_found")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing to database")

    args = parser.parse_args()

    enrich_albums(
        limit=args.limit,
        start_year=args.start_year,
        end_year=args.end_year,
        auto_refresh_interval=args.interval,
        dry_run=args.dry_run,
        retry_not_found=args.retry_not_found
    )
