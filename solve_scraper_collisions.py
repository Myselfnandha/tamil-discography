#!/usr/bin/env python3
"""
solve_scraper_collisions.py - Comprehensive Remediation Engine for Scraper Collisions.

Resolves:
1. Purging 52 non-movie/junk albums (biographical navbox entries and month headers) and their tracks.
2. Resolving all cross-year duplicate and homonym scraper collisions by:
   - Purging anachronistic modern tracks from vintage album entries.
   - Re-fetching and populating genuine vintage soundtracks from Wikipedia with correct composers.
   - Correcting modern albums (e.g. Karnan 2021, Idimuzhakkam 2026).
3. Re-parsing all column-shifted Wikipedia albums using the corrected parser in fetcher.py.
"""

import sys
import os
import re
import json
import sqlite3
import logging
from pathlib import Path

from fetcher import fetch_soundtrack_tracks, clean_wiki

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"

# 1. Non-movie / biographical / month-header entries to purge
ARTIST_TITLES = [
    'A. R. Rahman', 'Harris Jayaraj', 'Yuvan Shankar Raja', 'G. V. Prakash Kumar',
    'Deva', 'Anirudh Ravichander', 'D. Imman', 'Dhina', 'S. A. Rajkumar',
    'Bharadwaj', 'Pandiarajan', 'Babu Ganesh', 'Santhosh Sivan',
    'Nassar', 'Sriman', 'Ranjith', 'Bose Venkat', 'Meera Krishnan',
    'Krithi Shetty', 'Sonia Agarwal', 'Kullamani', 'Livingston', 'Govind Vasantha'
]

# 2. Curated mappings for specific collided albums:
# (album_id, wiki_page_to_fetch, real_composer, real_year_override, action)
COLLIDED_ALBUMS_MAP = [
    # Vintage Rajinikanth / Kamal / Classic Films with modern collisions
    (9178, 'Vikram_(1986_Tamil_film)', 'Ilaiyaraaja', 1986, 'replace'),
    (9011, 'Naan_Sigappu_Manithan_(1985_film)', 'Ilaiyaraaja', 1985, 'replace'),
    (8986, 'Kaakki_Sattai_(1985_film)', 'Ilaiyaraaja', 1985, 'replace'),
    (9117, 'Maaveeran_(1986_film)', 'Ilaiyaraaja', 1986, 'replace'),
    (8876, 'Naan_Mahaan_Alla_(1984_film)', 'Ilaiyaraaja', 1984, 'replace'),
    (8570, 'Netrikkan', 'Ilaiyaraaja', 1981, 'replace'),
    (8608, 'Tik_Tik_Tik_(1981_film)', 'Ilaiyaraaja', 1981, 'replace'),
    (8465, 'Polladhavan_(1980_film)', 'M. S. Viswanathan', 1980, 'replace'),
    (9418, 'Mappillai_(1989_film)', 'Ilaiyaraaja', 1989, 'replace'),
    (9325, None, None, None, 'clear_tracks'), # Mappillai Sir (duplicate of 9418)
    (9482, None, 'Shankar–Ganesh', 1989, 'clear_tracks'), # Vettaiyaadu Vilaiyaadu 1989
    (9475, 'Uthama_Purushan_(1989_film)', 'Shankar–Ganesh', 1989, 'replace'),
    (8848, 'Enakkul_Oruvan_(1984_film)', 'Ilaiyaraaja', 1984, 'replace'),
    (434, 'Oruvan_(1999_film)', 'Deva', 1999, 'replace'),
    (4443, None, 'Deva', 1999, 'clear_tracks'), # Aathavan 1999
    (7365, 'Ellam_Unakkaga', 'K. V. Mahadevan', 1961, 'replace'),
    (8208, None, 'Shankar–Ganesh', 1978, 'clear_tracks'), # Alli Darbar 1978
    (8352, None, 'Shankar–Ganesh', 1979, 'clear_tracks'), # Lakshmi 1979
    (8361, 'Ninaithale_Inikkum_(1979_film)', 'M. S. Viswanathan', 1979, 'replace'),
    (9256, 'Manithan_(1987_film)', 'Chandrabose', 1987, 'replace'),
    (8505, None, 'M. S. Viswanathan', 1981, 'clear_tracks'), # Amara Kaaviyam 1981
    (8520, None, 'M. S. Viswanathan', 1981, 'clear_tracks'), # Deiva Thirumanangal 1981
    (8540, 'Kazhugu_(1981_film)', 'Ilaiyaraaja', 1981, 'replace'),
    (8555, None, 'Ilaiyaraaja', 1981, 'clear_tracks'), # Mayyakkam 1981
    (8586, None, 'Deva', 1981, 'clear_tracks'), # Rajangam 1981
    (8594, 'Sattam_Oru_Iruttarai', 'Shankar–Ganesh', 1981, 'replace'),
    (8625, 'Pokkiri_Raja_(1982_film)', 'M. S. Viswanathan', 1982, 'replace'),
    (8687, None, 'Ilaiyaraaja', 1982, 'clear_tracks'), # Theeradha Vilaiyattu Pillai 1982
    (8972, 'Eetti_(1985_film)', 'Ilaiyaraaja', 1985, 'replace'),
    (9068, None, 'Shankar–Ganesh', 1985, 'clear_tracks'), # Veli 1985
    (9148, None, 'Ilaiyaraaja', 1986, 'clear_tracks'), # Padikkatha Padam 1986
    (9188, None, 'Ilaiyaraaja', 1987, 'clear_tracks'), # Raja Mariyadhai 1987
    (9218, None, 'Ilaiyaraaja', 1987, 'clear_tracks'), # Rekha 1987
    (9289, 'En_Bommukutty_Ammavukku', 'Ilaiyaraaja', 1988, 'replace'),
    (9300, 'Idhu_Namma_Aalu_(1988_film)', 'K. Bhagyaraj', 1988, 'replace'),
    (9306, 'Jeeva_(1988_film)', 'Jaishankar', 1988, 'replace'),
    (9315, None, 'Deva', 1988, 'clear_tracks'), # Katha Nayagan 1988
    (9472, 'Thendral_Sudum', 'Ilaiyaraaja', 1989, 'replace'),
    (8468, None, 'Deva', 1980, 'clear_tracks'), # Porkkaalam 1980
    (8485, None, 'Ilaiyaraaja', 1980, 'clear_tracks'), # Sujatha 1980
    (8532, None, 'Shankar–Ganesh', 1981, 'clear_tracks'), # Kalam Oru Naal Maarum 1981
    (8810, None, 'Ilaiyaraaja', 1983, 'clear_tracks'), # Thalaimagan 1983
    (8842, None, 'Ilaiyaraaja', 1984, 'clear_tracks'), # Azhagu 1984
    (8921, 'Sirai_(film)', 'M. S. Viswanathan', 1984, 'replace'),
    (7794, 'Thalaivan_(1970_film)', 'S. M. Subbaiah Naidu', 1970, 'replace'),
    (7707, None, 'K. V. Mahadevan', 1968, 'clear_tracks'), # Thanga Valayal 1968
    (7775, 'Kaviya_Thalaivi', 'K. V. Mahadevan', 1970, 'replace'),
    (7445, None, 'K. V. Mahadevan', 1963, 'clear_tracks'), # Aayiram Kalathu Payir 1963
    (7692, 'Nimirndhu_Nil_(1968_film)', 'M. S. Viswanathan', 1968, 'replace'),
    (7773, 'Kannan_Varuvan_(1970_film)', 'K. V. Mahadevan', 1970, 'replace'),
    (7765, 'Engal_Thangam', 'M. S. Viswanathan', 1970, 'replace'),
    (7566, None, 'Chitti Babu', 1965, 'clear_tracks'), # Unnaipol Oruvan 1965
    (8221, None, 'M. S. Viswanathan', 1978, 'clear_tracks'), # Ennai Pol Oruvan 1978
    (8074, None, 'K. V. Mahadevan', 1975, 'clear_tracks'), # Thirudanukku Thirudan 1975
    (8429, None, 'Shankar–Ganesh', 1980, 'clear_tracks'), # Kumari Pennin Ullathile 1980
    (4604, None, None, 2010, 'clear_tracks'), # Mandabam 2010
    (2149, 'Karnan_(soundtrack)', 'Santhosh Narayanan', 2021, 'replace'), # Karnan 2021
    (3238, None, 'Yuvan Shankar Raja', 2026, 'clear_tracks'), # Idimuzhakkam 2026
    (7286, None, 'Yuvan Shankar Raja', 2026, 'clear_tracks'), # Idimuzhakkam 2026
    (6255, None, 'K (composer)', 2022, 'clear_tracks'), # Kallan 2022
    (5956, None, 'Ilaiyaraaja', 2019, 'clear_tracks'), # Udhay 2019
    (5581, None, 'Simon K. King', 2017, 'clear_tracks'), # Sathya 2017
    (3596, None, None, 2000, 'clear_tracks'), # Kannula Kaasa Kattappa 2000
    (3446, None, None, 1998, 'clear_tracks'), # Thanga Magal 1998
    (4456, 'Ullathai_Killathe', 'Deva', 1999, 'replace'),
    (3863, None, None, 2005, 'clear_tracks'), # Navarasa 2005
    (1107, None, None, 2008, 'clear_tracks'), # Ponmagal Vandhal 2008
    (4007, None, None, 2007, 'clear_tracks'), # Kanna 2007
    (4764, None, None, 2012, 'clear_tracks'), # Arakkonam 2012
    (1321, None, None, 2009, 'clear_tracks'), # Enakkul Oru Kadhal 2009
    (7831, None, None, 1971, 'clear_tracks'), # Ranga Rattinam 1971
    (7895, None, None, 1972, 'clear_tracks'), # ...Aval! 1972
    (7871, None, 'M. S. Viswanathan', 1972, 'clear_tracks'), # Ponmagal Vandhal 1972
    (7869, None, 'M. S. Viswanathan', 1972, 'clear_tracks'), # Raman Thediya Seethai 1972
    (7897, None, 'V. Kumar', 1972, 'clear_tracks'), # Unakkum Enakkum 1972
    (7948, None, 'M. S. Viswanathan', 1973, 'clear_tracks'), # Sondham 1973
    (7986, 'Naan_Avanillai_(1974_film)', 'M. S. Viswanathan', 1974, 'replace'), # Naan Avanillai 1974
    (7995, None, 'M. S. Viswanathan', 1974, 'clear_tracks'), # Penn Ondru Kanden 1974
    (8013, None, 'M. S. Viswanathan', 1974, 'clear_tracks'), # Thirudi 1974
    (8026, 'Anbe_Aaruyire_(1975_film)', 'M. S. Viswanathan', 1975, 'replace'), # Anbe Aaruyire 1975
    (8030, None, 'M. S. Viswanathan', 1975, 'clear_tracks'), # Avalukku Aayiram Kangal 1975
    (8047, None, 'V. Kumar', 1975, 'clear_tracks'), # Maalai Sooda Vaa 1975
    (8091, None, 'V. Kumar', 1976, 'clear_tracks'), # Etharkkum Thuninthavan 1976
    (8126, None, 'K. V. Mahadevan', 1976, 'clear_tracks'), # Satyam 1976
    (8201, None, 'M. S. Viswanathan', 1977, 'clear_tracks'), # Thoondil Meen 1977
    (8266, None, 'Shankar–Ganesh', 1978, 'clear_tracks'), # Sakka Podu Podu Raja 1978
    (8306, None, 'Shankar–Ganesh', 1979, 'clear_tracks'), # Chellakili 1979
    (8330, None, 'Shankar–Ganesh', 1979, 'clear_tracks'), # Lakshmi 1979
    (8413, 'Guru_(1980_film)', 'Ilaiyaraaja', 1980, 'replace'), # Guru 1980
    (8422, 'Kaali_(1980_film)', 'Ilaiyaraaja', 1980, 'replace'), # Kaali 1980
    (8441, 'Murattu_Kaalai_(1980_film)', 'Ilaiyaraaja', 1980, 'replace'), # Murattu Kaalai 1980
    (7860, None, 'M. S. Viswanathan', 1972, 'clear_tracks'), # Ellai Kodu 1972
    (7777, None, 'Shankar–Ganesh', 1970, 'clear_tracks'), # Maanavan 1970
    (7846, None, 'M. S. Viswanathan', 1971, 'clear_tracks'), # Uyir 1971
    (7843, None, 'M. S. Viswanathan', 1971, 'clear_tracks'), # Thirumagal 1971
]

def purge_fake_albums(conn):
    """Delete non-movie biographical pages and calendar month headers."""
    cur = conn.cursor()
    q = 'SELECT id, title FROM albums WHERE title IN (' + ','.join('?' for _ in ARTIST_TITLES) + ') OR title LIKE "--%"'
    cur.execute(q, ARTIST_TITLES)
    rows = cur.fetchall()
    album_ids = [r[0] for r in rows]
    
    if album_ids:
        cur.execute(f"DELETE FROM tracks WHERE album_id IN ({','.join(str(i) for i in album_ids)})")
        cur.execute(f"DELETE FROM albums WHERE id IN ({','.join(str(i) for i in album_ids)})")
        conn.commit()
    logging.info(f"Purged {len(album_ids)} non-movie/junk albums from tamil_discography.db.")
    return len(album_ids)

def resolve_curated_collisions(conn):
    """Decouple and resolve all curated collision pairs."""
    cur = conn.cursor()
    resolved_count = 0

    for aid, wiki_page, composer, year_override, action in COLLIDED_ALBUMS_MAP:
        cur.execute("SELECT id, title, year FROM albums WHERE id = ?", (aid,))
        alb = cur.fetchone()
        if not alb:
            continue

        # 1. Update album metadata if needed
        if year_override:
            try:
                cur.execute("UPDATE albums SET year = ? WHERE id = ?", (year_override, aid))
            except sqlite3.IntegrityError:
                pass
        if composer:
            try:
                cur.execute("UPDATE albums SET composer = ? WHERE id = ?", (composer, aid))
            except sqlite3.IntegrityError:
                pass

        # 2. Clear corrupted tracks
        cur.execute("DELETE FROM tracks WHERE album_id = ?", (aid,))

        # 3. If action is replace and wiki_page is provided, fetch real tracks
        if action == 'replace' and wiki_page:
            try:
                tracks = fetch_soundtrack_tracks(wiki_page)
                if tracks:
                    for t in tracks:
                        cur.execute("""
                            INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                            VALUES (?, ?, ?, ?, ?, ?, ?, '')
                        """, (aid, t['track_number'], t['title'], t['singers'], t['lyricist'], t.get('raga', ''), t.get('duration', '')))
                    logging.info(f"✅ Album {aid} ({alb[1]}): Restored {len(tracks)} genuine tracks from '{wiki_page}'.")
                else:
                    logging.warning(f"⚠️ No tracks found on Wikipedia for '{wiki_page}' (Album {aid}).")
            except Exception as e:
                logging.error(f"Error fetching tracks for '{wiki_page}': {e}")
        else:
            logging.info(f"🧹 Album {aid} ({alb[1]}): Cleared collided tracks.")

        conn.commit()
        resolved_count += 1

    return resolved_count

def fix_shifted_albums(conn):
    """Re-fetch all albums that had column-shift errors where singers was duration."""
    cur = conn.cursor()
    # Find albums where any track has singers formatted as duration
    cur.execute("""
        SELECT DISTINCT a.id, a.title, a.source_url
        FROM albums a
        JOIN tracks t ON t.album_id = a.id
        WHERE t.singers GLOB '[0-9]:[0-9][0-9]' OR t.singers GLOB '[0-9][0-9]:[0-9][0-9]'
    """)
    shifted_albums = cur.fetchall()
    logging.info(f"Found {len(shifted_albums)} albums with shifted duration in singers column.")

    updated = 0
    for aid, title, source_url in shifted_albums:
        if not source_url or '/wiki/' not in source_url:
            continue
        wiki_page = source_url.split('/wiki/')[-1]
        try:
            tracks = fetch_soundtrack_tracks(wiki_page)
            # Only update if tracks were found and their singers are NOT pure duration
            if tracks and not any(re.match(r'^\d{1,2}:\d{2}$', t['singers'].strip()) for t in tracks if t['singers']):
                cur.execute("DELETE FROM tracks WHERE album_id = ?", (aid,))
                for t in tracks:
                    cur.execute("""
                        INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, '')
                    """, (aid, t['track_number'], t['title'], t['singers'], t['lyricist'], t.get('raga', ''), t.get('duration', '')))
                conn.commit()
                updated += 1
                logging.info(f"🔄 Re-parsed {title} (ID {aid}): {len(tracks)} tracks cleanly updated.")
        except Exception as e:
            logging.debug(f"Could not re-parse {title}: {e}")

    logging.info(f"Successfully re-parsed and corrected {updated} shifted albums.")
    return updated

def main():
    conn = sqlite3.connect(DISCO_DB)
    logging.info("Starting Scraper Collision Remediation...")

    # Phase 1: Purge non-movie junk
    p_cnt = purge_fake_albums(conn)

    # Phase 2: Resolve curated homonym & anachronism collisions
    c_cnt = resolve_curated_collisions(conn)

    # Phase 3: Re-parse remaining shifted albums
    s_cnt = fix_shifted_albums(conn)

    conn.close()
    logging.info(f"Remediation Complete! Purged {p_cnt} junk albums, resolved {c_cnt} collision groups, re-parsed {s_cnt} shifted albums.")

if __name__ == "__main__":
    main()
