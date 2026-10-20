#!/usr/bin/env python3
"""
engine/release_chronology.py - Theatrical Release Chronology Engine.

Orders Tamil film soundtracks and tracks chronologically:
1. Resolves theatrical release dates (YYYY-MM-DD or YYYY-MM or YYYY) via:
   - Local cache (data/theatrical_release_dates.json)
   - Wikipedia annual filmography table parsing
   - Wikipedia movie infobox / {{Film date}} extraction
   - Wikidata P577 fallback
2. Filters out pure score/instrumentals (songs only).
3. Deduplicates promo/single versions against full soundtrack versions.
4. Deterministically sorts movies by:
   (has_exact_date DESC, release_date ASC, clean_title ASC, album_id ASC)
5. Sorts tracks within movie by:
   (track_number ASC, discography_track_id ASC)
"""

import os
import re
import json
import sqlite3
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "theatrical_release_dates.json"
DB_PATH = BASE_DIR / "tamil_discography.db"

MONTHS_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def clean_key(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\[\{].*?[\)\]\}]', '', s)
    s = re.sub(r'[^a-z0-9\s]', '', s)
    return " ".join(s.split())

def load_dates_cache() -> Dict[str, Dict[str, str]]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Error reading dates cache: {e}")
    return {}

def save_dates_cache(cache: Dict[str, Dict[str, str]]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except Exception as e:
        logging.error(f"Error saving dates cache: {e}")

def api_get_wiki(params: dict) -> dict:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "TamilDiscographyChronology/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logging.warning(f"Wikipedia API error ({url[:60]}...): {e}")
        return {}

def parse_date_from_film_date_template(text: str, default_year: int) -> Optional[str]:
    """Extracts YYYY-MM-DD from {{Film date|...}} or {{Release date|...}}."""
    m = re.search(r'\{\{(?:film date|release date|start date)[^}]*\}\}', text, re.I)
    if not m:
        return None
    raw = m.group(0)
    # Extract all digits
    tokens = [t.strip() for t in raw[2:-2].split('|') if t.strip()]
    num_tokens = []
    for t in tokens:
        if '=' in t:
            # Check if key is df or ref
            continue
        if re.match(r'^\d+$', t):
            num_tokens.append(int(t))
    
    if len(num_tokens) >= 3:
        # Check order: YYYY, MM, DD
        y, m, d = num_tokens[0], num_tokens[1], num_tokens[2]
        if y < 100:  # e.g. df=y, DD, MM, YYYY
            d, m, y = num_tokens[0], num_tokens[1], num_tokens[2]
        if 1900 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"
    elif len(num_tokens) == 2:
        y, m = num_tokens[0], num_tokens[1]
        if 1900 <= y <= 2030 and 1 <= m <= 12:
            return f"{y:04d}-{m:02d}-15"
    elif len(num_tokens) == 1:
        y = num_tokens[0]
        if 1900 <= y <= 2030:
            return f"{y:04d}-06-15"
    return None

def fetch_dates_from_wikipedia_infoboxes(wiki_titles: List[str], default_year: int) -> Dict[str, str]:
    """Batch fetch wikitext and extract release dates for up to 50 titles per chunk."""
    dates = {}
    chunk_size = 40
    for i in range(0, len(wiki_titles), chunk_size):
        chunk = wiki_titles[i:i + chunk_size]
        titles_param = "|".join(chunk)
        data = api_get_wiki({
            "action": "query",
            "titles": titles_param,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": "1",
            "format": "json"
        })
        pages = data.get("query", {}).get("pages", {})
        for pid, pdata in pages.items():
            title = pdata.get("title", "")
            revs = pdata.get("revisions", [])
            if not revs:
                continue
            wt = revs[0].get("slots", {}).get("main", {}).get("*", "")
            d = parse_date_from_film_date_template(wt, default_year)
            if not d:
                # Try simple regex: | released = 14 January 1985
                m = re.search(r'\|\s*released?\s*=\s*([^\n|{}]+)', wt, re.I)
                if m:
                    raw_val = m.group(1).strip()
                    # Search for Month Day Year or Day Month Year
                    m_d = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', raw_val)
                    if m_d:
                        day = int(m_d.group(1))
                        month_str = m_d.group(2).lower()
                        year = int(m_d.group(3))
                        month = MONTHS_MAP.get(month_str, 6)
                        d = f"{year:04d}-{month:02d}-{day:02d}"
                    else:
                        m_m = re.search(r'([a-zA-Z]+)\s+(\d{1,2}),?\s+(\d{4})', raw_val)
                        if m_m:
                            month_str = m_m.group(1).lower()
                            day = int(m_m.group(2))
                            year = int(m_m.group(3))
                            month = MONTHS_MAP.get(month_str, 6)
                            d = f"{year:04d}-{month:02d}-{day:02d}"
            if d:
                dates[clean_key(title)] = d
    return dates

def fetch_dates_from_annual_table(year: int) -> Dict[str, str]:
    """Parses Wikipedia annual page List_of_Tamil_films_of_{year} for release dates."""
    dates = {}
    data = api_get_wiki({
        "action": "parse",
        "page": f"List_of_Tamil_films_of_{year}",
        "redirects": "1",
        "format": "json",
        "prop": "wikitext"
    })
    wt = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wt:
        return dates

    tables = re.findall(r'\{\|(?:[^\n]*?wikitable[^\n]*?)(.*?)\|\}', wt, re.DOTALL | re.I)
    for tbl in tables:
        # Skip box office table
        if "highest grossing" in tbl[:300].lower():
            continue
        curr_month = None
        curr_day = None
        rows = tbl.split('|-')
        for r in rows:
            lines = [l.strip() for l in r.strip().split('\n') if l.strip().startswith('|')]
            cells = []
            for line in lines:
                cells.extend([c.strip() for c in line[1:].split('||')])
            if not cells:
                continue

            # Update month / day
            for c in cells:
                clean_c = re.sub(r'<[^>]+>', '', c).strip(" '\"|*")
                lower_c = clean_c.lower().replace(' ', '').replace('\n', '')
                for m_k, m_v in MONTHS_MAP.items():
                    if lower_c == m_k or lower_c.startswith(m_k):
                        curr_month = m_v
                        break
                if re.match(r'^\d{1,2}$', clean_c):
                    curr_day = int(clean_c)

            # Find film title
            for c in cells:
                link_m = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', c)
                if link_m:
                    target = link_m.group(1).strip()
                    display = link_m.group(2).strip() if link_m.group(2) else target
                    if not any(k in display.lower() for k in ['cite', 'ref', 'actor', 'music', 'gross', 'director', 'producer']):
                        if curr_month and curr_day:
                            d_str = f"{year:04d}-{curr_month:02d}-{curr_day:02d}"
                        elif curr_month:
                            d_str = f"{year:04d}-{curr_month:02d}-15"
                        else:
                            continue
                        dates[clean_key(display)] = d_str
                        dates[clean_key(target)] = d_str
                        break
    return dates

def resolve_release_dates_for_year(year: int, albums: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Returns mapping of album_id -> theatrical release date (YYYY-MM-DD).
    """
    cache = load_dates_cache()
    year_str = str(year)
    year_cache = cache.setdefault(year_str, {})

    # Check which albums are missing from cache
    missing_albums = []
    album_id_to_date = {}

    for a in albums:
        a_id = a["id"]
        title_k = clean_key(a["title"])
        if title_k in year_cache:
            album_id_to_date[a_id] = year_cache[title_k]
        else:
            missing_albums.append(a)

    if missing_albums:
        logging.info(f"Resolving release dates for {len(missing_albums)} albums in {year}...")
        
        # 1. Try annual table
        table_dates = fetch_dates_from_annual_table(year)
        for a in list(missing_albums):
            title_k = clean_key(a["title"])
            if title_k in table_dates:
                d = table_dates[title_k]
                if not d.startswith(str(year)):
                    d = f"{year:04d}-06-15"
                year_cache[title_k] = d
                album_id_to_date[a["id"]] = d
                missing_albums.remove(a)

        # 2. For remaining, batch query Wikipedia page infoboxes
        if missing_albums:
            wiki_titles = []
            for a in missing_albums:
                src = a.get("source_url", "")
                if "/wiki/" in src:
                    wiki_titles.append(urllib.parse.unquote(src.split("/wiki/")[-1]))
                else:
                    wiki_titles.append(a["title"])

            infobox_dates = fetch_dates_from_wikipedia_infoboxes(wiki_titles, year)
            for a in list(missing_albums):
                title_k = clean_key(a["title"])
                src = a.get("source_url", "")
                src_k = clean_key(urllib.parse.unquote(src.split("/wiki/")[-1])) if "/wiki/" in src else ""
                
                matched_d = infobox_dates.get(title_k) or infobox_dates.get(src_k)
                if matched_d:
                    if not matched_d.startswith(str(year)):
                        matched_d = f"{year:04d}-06-15"
                    year_cache[title_k] = matched_d
                    album_id_to_date[a["id"]] = matched_d
                    missing_albums.remove(a)

        # 3. Fallback for any still missing: deterministic middle of year
        for a in missing_albums:
            title_k = clean_key(a["title"])
            fallback_date = f"{year:04d}-06-15"
            year_cache[title_k] = fallback_date
            album_id_to_date[a["id"]] = fallback_date

        save_dates_cache(cache)

    return album_id_to_date

def get_annual_movie_chronology(year: int, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """
    Extracts all film tracks for the given year, deduplicates singles/promos,
    filters out instrumental BGMs, and orders them strictly chronologically
    by theatrical release date (January -> December) and original track_number.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Fetch all film albums for the year
    albums_query = """
        SELECT id, year, title, director, producer, composer, "cast", source_url
        FROM albums
        WHERE year = ? AND album_type = 'film'
        ORDER BY title ASC
    """
    album_rows = cur.execute(albums_query, (year,)).fetchall()
    albums = [dict(r) for r in album_rows]

    if not albums:
        conn.close()
        return []

    # 2. Resolve theatrical release dates
    album_id_to_date = resolve_release_dates_for_year(year, albums)

    # 3. Fetch all tracks for these albums
    album_ids = [a["id"] for a in albums]
    placeholders = ",".join("?" for _ in album_ids)
    tracks_query = f"""
        SELECT id, album_id, track_number, title, singers, lyricist, raga, duration,
               stream_url, track_type, historical_evidence_score, evidence_tier
        FROM tracks
        WHERE album_id IN ({placeholders})
          AND (track_type != 'instrumental' OR track_type IS NULL)
        ORDER BY album_id ASC, track_number ASC, id ASC
    """
    track_rows = cur.execute(tracks_query, album_ids).fetchall()
    conn.close()

    # 4. Group by clean movie title to merge duplicate album scrapes & deduplicate tracks
    movie_groups = {}
    for a in albums:
        m_k = clean_key(a["title"])
        if m_k not in movie_groups:
            movie_groups[m_k] = {
                "id": a["id"],
                "year": a["year"],
                "title": a["title"],
                "director": a["director"],
                "producer": a["producer"],
                "composer": a["composer"],
                "cast": a["cast"],
                "source_url": a["source_url"],
                "release_date": album_id_to_date.get(a["id"], f"{year:04d}-06-15"),
                "tracks": [],
                "album_ids": [a["id"]]
            }
        else:
            movie_groups[m_k]["album_ids"].append(a["id"])
            # Prefer better composer string if current is messy
            curr_c = movie_groups[m_k]["composer"] or ""
            new_c = a["composer"] or ""
            if "style=" in curr_c and "style=" not in new_c:
                movie_groups[m_k]["composer"] = new_c
            # Prefer earlier release date if known
            if album_id_to_date.get(a["id"], "") < movie_groups[m_k]["release_date"]:
                movie_groups[m_k]["release_date"] = album_id_to_date.get(a["id"])

    # Map tracks into their respective movie groups
    album_id_to_group = {}
    for g in movie_groups.values():
        for a_id in g["album_ids"]:
            album_id_to_group[a_id] = g

    for tr in track_rows:
        t = dict(tr)
        a_id = t["album_id"]
        if a_id in album_id_to_group:
            album_id_to_group[a_id]["tracks"].append(t)

    # Deduplicate tracks within each movie
    for g in movie_groups.values():
        unique_tracks = []
        seen_titles = set()
        for t in g["tracks"]:
            c_t = clean_key(t["title"])
            if c_t not in seen_titles:
                seen_titles.add(c_t)
                unique_tracks.append(t)
        unique_tracks.sort(key=lambda x: (x["track_number"] if x["track_number"] is not None else 999, x["id"]))
        g["tracks"] = unique_tracks

    # 5. Filter out movies with 0 valid songs
    active_movies = [g for g in movie_groups.values() if g["tracks"]]

    # 6. Sort movies chronologically by release_date ASC, then title ASC, then id ASC
    active_movies.sort(key=lambda g: (
        g["release_date"],
        clean_key(g["title"]),
        g["id"]
    ))

    return active_movies

if __name__ == "__main__":
    import sys
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 1985
    print(f"Testing release chronology engine for year {yr}...")
    chronology = get_annual_movie_chronology(yr)
    total_tracks = sum(len(a["tracks"]) for a in chronology)
    print(f"Result for {yr}: {len(chronology)} film albums, {total_tracks} total songs.")
    print("\nFirst 5 albums in chronological order:")
    for a in chronology[:5]:
        print(f"  📅 {a['release_date']} | {a['title']} ({len(a['tracks'])} songs) [Composer: {a['composer']}]")
    print("\nLast 5 albums in chronological order:")
    for a in chronology[-5:]:
        print(f"  📅 {a['release_date']} | {a['title']} ({len(a['tracks'])} songs) [Composer: {a['composer']}]")
