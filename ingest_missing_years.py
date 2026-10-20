#!/usr/bin/env python3
"""
ingest_missing_years.py - Ingest Wikipedia Tamil film lists for 1970–1989 into tamil_discography.db.
Fills the missing 20-year gap so the YouTube Music scraper can enrich their soundtracks.
"""

import sqlite3
import logging
from pathlib import Path
from fetcher import fetch_annual_filmography, clean_wiki

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def ingest_years(start_year=1970, end_year=1989):
    conn = sqlite3.connect(DISCO_DB)
    cur = conn.cursor()

    total_added_albums = 0

    for year in range(start_year, end_year + 1):
        # Check if year already exists
        cur.execute("SELECT COUNT(*) FROM albums WHERE year = ?;", (year,))
        existing = cur.fetchone()[0]
        if existing > 0:
            logging.info(f"Year {year} already has {existing} albums in database. Skipping.")
            continue

        logging.info(f"Fetching filmography for year {year} from Wikipedia...")
        films = fetch_annual_filmography(year)
        if not films:
            logging.warning(f"No films found for year {year}.")
            continue

        added_this_year = 0
        for f in films:
            title = clean_wiki(f.get("title", ""))
            if not title or len(title) < 2:
                continue

            director = clean_wiki(f.get("director", ""))
            composer = clean_wiki(f.get("composer", ""))
            cast = clean_wiki(f.get("cast", ""))
            url = f.get("source_url", "")

            cur.execute("""
                INSERT OR IGNORE INTO albums (year, title, director, producer, composer, cast, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (year, title, director, "", composer, cast, url))
            added_this_year += 1

        conn.commit()
        logging.info(f"✅ Ingested {added_this_year} films for year {year}.")
        total_added_albums += added_this_year

    conn.close()
    print(f"\nSuccessfully ingested {total_added_albums} albums across {start_year}–{end_year} into tamil_discography.db.\n")

if __name__ == "__main__":
    ingest_years(1970, 1989)
