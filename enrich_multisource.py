#!/usr/bin/env python3
"""
enrich_multisource.py - Unified Multi-Source Ingestion & Enrichment Engine for Tamil Discography.

Combines:
  1. Wikipedia (Infobox Music + Soundtrack Wikitables)
  2. JioSaavn (Official Tamil Catalog with high fidelity metadata & 320kbps streams)
  3. YouTube Music (ytmusicapi official audio releases)

Pipelines:
  - Phase 1: Clean album titles (strip extraneous '||' wikitable delimiters).
  - Phase 2: Ingest from Wikipedia for all unpopulated albums.
  - Phase 3: Ingest from JioSaavn for remaining albums.
  - Phase 4: Ingest from YouTube Music for remaining albums.
  - Phase 5: Purge junk / deduplicate across all databases.
  - Phase 6: Regenerate all 139 playlist databases in playlists/.
  - Phase 7: Re-export all 1960–2026 annual JSON files in data/.
"""

import sys
import os
import re
import time
import json
import difflib
import sqlite3
import logging
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# Local imports
from fetcher import api_get, extract_tracks_from_wikitext, clean_wiki
from build_playlists import generate_all_playlists
from export import export_year_to_json, export_summary_index

try:
    from ytmusicapi import YTMusic
    YT_AVAILABLE = True
except ImportError:
    YT_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

# =========================================================================
# Utility Functions
# =========================================================================

def normalize_title(t: str) -> str:
    """Normalize string for fuzzy comparison."""
    if not t:
        return ""
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'[^a-zA-Z0-9\s]', ' ', t)
    return " ".join(t.lower().split())

def match_score(a: str, b: str) -> float:
    na = normalize_title(a)
    nb = normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.90
    return difflib.SequenceMatcher(None, na, nb).ratio()

def clean_album_title(title: str) -> str:
    """Clean table-parsing artifacts like '||' or trailing notes."""
    if not title:
        return ""
    t = title.split('||')[0].strip()
    t = re.sub(r'^\s*!+\s*', '', t)
    t = re.sub(r'^\s*\|+\s*', '', t)
    return t.strip()

def format_duration(seconds_val) -> str:
    try:
        sec = int(seconds_val)
        return f"{sec // 60}:{sec % 60:02d}"
    except (ValueError, TypeError):
        return str(seconds_val or "")

# =========================================================================
# Phase 1: Database Hygiene & Title Normalization
# =========================================================================

def clean_existing_album_titles(conn: sqlite3.Connection):
    """Normalize titles with '||' or markdown junk in albums table."""
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM albums WHERE title LIKE '%||%' OR title LIKE '!%' OR title LIKE '|%';")
    rows = cur.fetchall()
    updated = 0
    for aid, raw_title in rows:
        cleaned = clean_album_title(raw_title)
        if cleaned and cleaned != raw_title:
            try:
                cur.execute("UPDATE albums SET title = ? WHERE id = ?;", (cleaned, aid))
            except sqlite3.IntegrityError:
                # Merge duplicate album into existing row
                cur.execute("SELECT id FROM albums WHERE year = (SELECT year FROM albums WHERE id = ?) AND title = ? AND id != ? LIMIT 1;", (aid, cleaned, aid))
                existing = cur.fetchone()
                if existing:
                    target_id = existing[0]
                    cur.execute("UPDATE tracks SET album_id = ? WHERE album_id = ?;", (target_id, aid))
                    cur.execute("DELETE FROM albums WHERE id = ?;", (aid,))
                    logging.info(f"Merged duplicate album {aid} ('{raw_title}') into existing album {target_id} ('{cleaned}').")
            updated += 1
    if updated > 0:
        conn.commit()
        logging.info(f"Cleaned {updated} album titles with pipe/table artifacts.")

# =========================================================================
# Phase 2: Wikipedia Ingestion
# =========================================================================

def enrich_from_wikipedia(conn: sqlite3.Connection, start_year=None, end_year=None, limit=None) -> int:
    """Extract infobox composer and soundtrack tracks from Wikipedia articles."""
    cur = conn.cursor()
    
    query = """
        SELECT a.id, a.title, a.year, a.composer, a.source_url
        FROM albums a
        WHERE a.id NOT IN (SELECT DISTINCT album_id FROM tracks)
    """
    params = []
    if start_year:
        query += " AND a.year >= ?"
        params.append(start_year)
    if end_year:
        query += " AND a.year <= ?"
        params.append(end_year)
    query += " ORDER BY a.year ASC, a.id ASC"
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query, params)
    albums = cur.fetchall()
    total = len(albums)
    logging.info(f"[Wikipedia] Scanning {total} albums lacking tracks...")

    tracks_added = 0
    albums_enriched = 0

    for idx, (aid, raw_title, year, comp, source_url) in enumerate(albums, 1):
        clean_t = clean_album_title(raw_title)
        
        # Determine wiki page name
        page_name = None
        if source_url and "/wiki/" in source_url:
            page_name = urllib.parse.unquote(source_url.split("/wiki/")[-1])
        if not page_name or "List_of" in page_name or "||" in page_name:
            page_name = clean_t.replace(" ", "_")

        data = api_get({"action": "parse", "page": page_name, "redirects": "1", "format": "json", "prop": "wikitext"})
        if not data or "error" in data:
            # Fallback disambiguations
            for alt_suffix in [f"_{year}_film", "_film"]:
                alt_page = clean_t.replace(" ", "_") + alt_suffix
                data = api_get({"action": "parse", "page": alt_page, "redirects": "1", "format": "json", "prop": "wikitext"})
                if data and "parse" in data:
                    page_name = alt_page
                    break

        if not data or "parse" not in data:
            continue

        wt = data["parse"]["wikitext"]["*"]

        # 1. Update composer from Infobox if missing or bogus (e.g. was cast)
        m_comp = re.search(r'\|\s*(?:music|composer)\s*=\s*([^\n|]+)', wt, re.I)
        if m_comp:
            extracted_comp = clean_wiki(m_comp.group(1))
            if extracted_comp and (not comp or len(comp.split(",")) > 4):
                try:
                    cur.execute("UPDATE albums SET composer = ? WHERE id = ?;", (extracted_comp, aid))
                    comp = extracted_comp
                except sqlite3.IntegrityError:
                    pass

        # 2. Extract tracks from wikitext
        tracks = extract_tracks_from_wikitext(wt)
        if tracks:
            for t in tracks:
                cur.execute("""
                    INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    aid,
                    t.get("track_number"),
                    t.get("title"),
                    t.get("singers", ""),
                    t.get("lyricist", ""),
                    t.get("raga", ""),
                    t.get("duration", ""),
                    ""
                ))
            conn.commit()
            albums_enriched += 1
            tracks_added += len(tracks)
            logging.info(f"[Wiki {idx}/{total}] ✅ {clean_t} ({year}): Added {len(tracks)} tracks (Composer: {comp})")
        
        time.sleep(0.15)  # Polite Wikimedia API backoff

    logging.info(f"[Wikipedia Ingestion Complete] Enriched {albums_enriched} albums (+{tracks_added} tracks).")
    return albums_enriched

# =========================================================================
# Phase 3: JioSaavn Ingestion
# =========================================================================

def query_jiosaavn_album(title: str, year: int, composer: str = ""):
    """Search JioSaavn for an official Tamil album and return its detailed tracklist."""
    clean_t = clean_album_title(title)
    queries = [f"{clean_t} Tamil", clean_t]
    if composer and len(composer.split(",")) <= 2:
        queries.insert(0, f"{clean_t} {composer}")

    headers = {"User-Agent": USER_AGENT}

    for q in queries:
        url = f"https://www.jiosaavn.com/api.php?__call=search.getAlbumResults&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=5&p=1&q={urllib.parse.quote(q)}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue

        results = data.get("results", [])
        for r in results:
            if r.get("language") != "tamil":
                continue
            r_title = r.get("title", "")
            r_year = r.get("year", "")
            
            score = match_score(clean_t, r_title)
            # Accept if high match score
            if score >= 0.82:
                # Validate year proximity if available
                if r_year and year:
                    try:
                        if abs(int(r_year) - int(year)) > 3 and score < 0.95:
                            continue
                    except ValueError:
                        pass
                
                # Fetch full album details
                album_id = r.get("id")
                det_url = f"https://www.jiosaavn.com/api.php?__call=content.getAlbumDetails&_format=json&albumid={album_id}"
                det_req = urllib.request.Request(det_url, headers=headers)
                try:
                    with urllib.request.urlopen(det_req, timeout=10) as det_resp:
                        album_details = json.loads(det_resp.read().decode("utf-8"))
                        songs = album_details.get("songs", [])
                        if songs:
                            return album_details
                except Exception:
                    continue

    return None

def enrich_from_jiosaavn(conn: sqlite3.Connection, start_year=None, end_year=None, limit=None) -> int:
    """Query JioSaavn for all remaining empty albums."""
    cur = conn.cursor()
    query = """
        SELECT a.id, a.title, a.year, a.composer
        FROM albums a
        WHERE a.id NOT IN (SELECT DISTINCT album_id FROM tracks)
    """
    params = []
    if start_year:
        query += " AND a.year >= ?"
        params.append(start_year)
    if end_year:
        query += " AND a.year <= ?"
        params.append(end_year)
    query += " ORDER BY a.year ASC, a.id ASC"
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query, params)
    albums = cur.fetchall()
    total = len(albums)
    logging.info(f"[JioSaavn] Scanning {total} albums lacking tracks...")

    albums_enriched = 0
    tracks_added = 0

    for idx, (aid, title, year, composer) in enumerate(albums, 1):
        clean_t = clean_album_title(title)
        album_data = query_jiosaavn_album(clean_t, year, composer)
        if not album_data:
            continue

        songs = album_data.get("songs", [])
        if not songs:
            continue

        # Update composer if empty
        primary_music = album_data.get("more_info", {}).get("music") or songs[0].get("music")
        if primary_music and not composer:
            try:
                cur.execute("UPDATE albums SET composer = ? WHERE id = ?;", (primary_music, aid))
            except sqlite3.IntegrityError:
                pass

        for t_idx, s in enumerate(songs, 1):
            dur_formatted = format_duration(s.get("duration"))
            cur.execute("""
                INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                aid,
                t_idx,
                s.get("song") or s.get("title"),
                s.get("primary_artists") or s.get("singers", ""),
                "",
                "",
                dur_formatted,
                s.get("perma_url") or s.get("media_preview_url", "")
            ))
        conn.commit()
        albums_enriched += 1
        tracks_added += len(songs)
        logging.info(f"[JioSaavn {idx}/{total}] ✅ {clean_t} ({year}): Added {len(songs)} tracks (Music: {primary_music})")
        time.sleep(0.2)

    logging.info(f"[JioSaavn Ingestion Complete] Enriched {albums_enriched} albums (+{tracks_added} tracks).")
    return albums_enriched

# =========================================================================
# Phase 4: YouTube Music Ingestion
# =========================================================================

def enrich_from_ytmusic(conn: sqlite3.Connection, start_year=None, end_year=None, limit=None) -> int:
    """Query YouTube Music for remaining empty albums."""
    if not YT_AVAILABLE:
        logging.warning("ytmusicapi is not installed. Skipping YouTube Music phase.")
        return 0

    from enrich_with_ytmusic import find_best_album

    yt = YTMusic()
    # Enforce strict 8-second network timeout on all requests so it never hangs
    orig_request = yt._session.request
    def request_with_timeout(*args, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 8
        return orig_request(*args, **kwargs)
    yt._session.request = request_with_timeout

    cur = conn.cursor()
    query = """
        SELECT a.id, a.title, a.year, a.composer
        FROM albums a
        WHERE a.id NOT IN (SELECT DISTINCT album_id FROM tracks)
    """
    params = []
    if start_year:
        query += " AND a.year >= ?"
        params.append(start_year)
    if end_year:
        query += " AND a.year <= ?"
        params.append(end_year)
    query += " ORDER BY a.year ASC, a.id ASC"
    if limit:
        query += f" LIMIT {int(limit)}"

    cur.execute(query, params)
    albums = cur.fetchall()
    total = len(albums)
    logging.info(f"[YouTube Music] Scanning {total} albums lacking tracks...")

    albums_enriched = 0
    tracks_added = 0

    for idx, (aid, title, year, composer) in enumerate(albums, 1):
        clean_t = clean_album_title(title)
        if idx % 5 == 0 or idx == 1 or idx == total:
            logging.info(f"[YouTube Music {idx:>4}/{total}] Progress: '{clean_t}' ({year}) | Enriched: {albums_enriched} albums (+{tracks_added} tracks)")

        best_match, score = find_best_album(yt, clean_t, year, composer or "")
        if not best_match:
            continue

        browse_id = best_match.get("browseId")
        if not browse_id:
            continue

        try:
            album_det = yt.get_album(browse_id)
        except Exception as e:
            logging.debug(f"Could not load YT album {browse_id}: {e}")
            continue

        yt_tracks = album_det.get("tracks", [])
        if not yt_tracks:
            continue

        # Update composer from artists if empty
        artists = album_det.get("artists", [])
        if artists and not composer:
            artist_str = ", ".join(a.get("name") for a in artists if a.get("name"))
            try:
                cur.execute("UPDATE albums SET composer = ? WHERE id = ?;", (artist_str, aid))
            except sqlite3.IntegrityError:
                pass

        for t_idx, t in enumerate(yt_tracks, 1):
            vid = t.get("videoId")
            stream_url = f"https://music.youtube.com/watch?v={vid}" if vid else ""
            t_artists = ", ".join(a.get("name") for a in t.get("artists", []) if a.get("name"))
            cur.execute("""
                INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                aid,
                t_idx,
                t.get("title"),
                t_artists,
                "",
                "",
                t.get("duration", ""),
                stream_url
            ))
        conn.commit()
        albums_enriched += 1
        tracks_added += len(yt_tracks)
        logging.info(f"[YouTube Music {idx:>4}/{total}] ✅ MATCH: '{clean_t}' ({year}) -> Added {len(yt_tracks)} tracks! (Score: {score:.2f})")
        time.sleep(0.3)

    logging.info(f"[YouTube Music Complete] Enriched {albums_enriched} albums (+{tracks_added} tracks).")
    return albums_enriched

# =========================================================================
# Phase 5: Hygiene, Deduplication & Export
# =========================================================================

def purge_junk_and_duplicates(conn: sqlite3.Connection):
    """Purge 1-character/junk tracks and exact duplicate tracks."""
    from find_duplicates import is_junk_title
    cur = conn.cursor()
    
    cur.execute("SELECT id, title FROM tracks;")
    all_t = cur.fetchall()
    junk_ids = [r[0] for r in all_t if is_junk_title(r[1])]
    if junk_ids:
        cur.executemany("DELETE FROM tracks WHERE id = ?;", [(jid,) for jid in junk_ids])
        conn.commit()
        logging.info(f"Purged {len(junk_ids)} corrupt/junk track rows.")

    # Deduplicate tracks with exact same (lower(title), album_id) keeping best ID
    cur.execute("""
        SELECT id, LOWER(TRIM(title)), album_id, duration
        FROM tracks
        ORDER BY id ASC;
    """)
    seen = {}
    dup_ids = []
    for tid, t_title, a_id, dur in cur.fetchall():
        key = (t_title, a_id)
        if key in seen:
            prev_id, prev_dur = seen[key]
            # If current has duration and previous does not, replace
            if dur and not prev_dur:
                dup_ids.append(prev_id)
                seen[key] = (tid, dur)
            else:
                dup_ids.append(tid)
        else:
            seen[key] = (tid, dur)

    if dup_ids:
        cur.executemany("DELETE FROM tracks WHERE id = ?;", [(did,) for did in dup_ids])
        conn.commit()
        logging.info(f"Purged {len(dup_ids)} duplicate tracks.")

def export_all_annual_json(conn: sqlite3.Connection):
    """Re-export all 1960–2026 annual JSON files and summary index."""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT year FROM albums ORDER BY year ASC;")
    years = [r[0] for r in cur.fetchall()]
    logging.info(f"Exporting updated JSON files across {len(years)} years (1960–2026)...")
    for yr in years:
        export_year_to_json(yr)
    export_summary_index()
    logging.info("✅ All annual JSON files and discography_summary.json updated.")

# =========================================================================
# Main Coordinator
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Multi-Source Tamil Discography Ingestion & Enrichment Engine")
    parser.add_argument("--start-year", type=int, default=1960, help="Start year (default 1960)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (default 2026)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of albums per source")
    parser.add_argument("--skip-wiki", action="store_true", help="Skip Wikipedia phase")
    parser.add_argument("--skip-saavn", action="store_true", help="Skip JioSaavn phase")
    parser.add_argument("--skip-yt", action="store_true", help="Skip YouTube Music phase")
    parser.add_argument("--skip-playlists", action="store_true", help="Skip playlist rebuild")
    parser.add_argument("--skip-export", action="store_true", help="Skip JSON export")

    args = parser.parse_args()

    print("\n" + "="*80)
    print(" 🚀 STARTING FULL MULTI-SOURCE INGESTION & ENRICHMENT PIPELINE")
    print(f"    Years : {args.start_year} – {args.end_year}")
    print("="*80 + "\n")

    conn = sqlite3.connect(DISCO_DB)

    # 1. Title hygiene
    clean_existing_album_titles(conn)

    # 2. Phase 1: Wikipedia
    if not args.skip_wiki:
        print("\n" + "-"*80)
        print(" 📖 [TIER 1] WIKIPEDIA SOUNDTRACK & INFOBOX EXTRACTION")
        print("-" * 80)
        enrich_from_wikipedia(conn, start_year=args.start_year, end_year=args.end_year, limit=args.limit)

    # 3. Phase 2: JioSaavn
    if not args.skip_saavn:
        print("\n" + "-"*80)
        print(" 🎶 [TIER 2] JIOSAAVN OFFICIAL TAMIL CATALOG INGESTION")
        print("-" * 80)
        enrich_from_jiosaavn(conn, start_year=args.start_year, end_year=args.end_year, limit=args.limit)

    # 4. Phase 3: YouTube Music
    if not args.skip_yt:
        print("\n" + "-"*80)
        print(" 📺 [TIER 3] YOUTUBE MUSIC SOUNDTRACK ENRICHMENT")
        print("-" * 80)
        enrich_from_ytmusic(conn, start_year=args.start_year, end_year=args.end_year, limit=args.limit)

    # 5. Phase 4: Clean Junk & Deduplicate
    print("\n" + "-"*80)
    print(" 🧹 [TIER 4] JUNK PURGE & DEDUPLICATION")
    print("-" * 80)
    purge_junk_and_duplicates(conn)
    conn.close()

    # 6. Phase 5: Rebuild all 139 playlists
    if not args.skip_playlists:
        print("\n" + "-"*80)
        print(" 🗂️ [TIER 5] REBUILDING ALL 139 STANDALONE PLAYLIST DATABASES")
        print("-" * 80)
        generate_all_playlists()

    # 7. Phase 6: Sync JSON exports
    if not args.skip_export:
        print("\n" + "-"*80)
        print(" 📦 [TIER 6] RE-EXPORTING OCD ANNUAL JSON CATALOG (1960–2026)")
        print("-" * 80)
        conn = sqlite3.connect(DISCO_DB)
        export_all_annual_json(conn)
        conn.close()

    print("\n" + "="*80)
    print(" 🎉 ALL MULTI-SOURCE INGESTION & ENRICHMENT STAGES COMPLETE!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
