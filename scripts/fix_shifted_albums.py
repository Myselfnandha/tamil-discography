#!/usr/bin/env python3
"""
Fix Shifted Column Albums in tamil_discography.db.
Audits and repairs tracks where Wikipedia table scrapers shifted singer names
into title and durations into singers.
"""

import sqlite3
import urllib.request
import urllib.parse
import json
import re
import time
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tamil_discography.db"

HEADERS = {
    "User-Agent": "TamilDiscographyBot/2.0 (https://github.com/Myselfnandha/tamil-discography; contact: discography@example.com)"
}

def clean_wiki(s):
    if not s:
        return ""
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.DOTALL)
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'\{\{[^}]+\}\}', '', s)
    s = s.replace("'''", "").replace("''", "").replace('"', '').strip()
    # Strip leading/trailing punctuation
    s = re.sub(r'^[,\-–—\s]+|[,\-–—\s]+$', '', s)
    return s.strip()

def fetch_wikitext(page_name):
    # Normalize page name
    page_encoded = urllib.parse.quote(page_name.replace(" ", "_"))
    api_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={page_encoded}&prop=wikitext&format=json&redirects=1"
    req = urllib.request.Request(api_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if "parse" in data and "wikitext" in data["parse"]:
                return data["parse"]["wikitext"]["*"]
    except Exception as e:
        print(f"  [API Error] {page_name}: {e}")
    return None

def parse_tracks_from_wikitext(wt):
    tracks = []
    
    # Strategy 1: Check for {{Track listing template
    tl_matches = re.findall(r'\{\{[Tt]rack\s*listing(.*?)\n\}\}', wt, re.DOTALL)
    for content in tl_matches:
        track_nums = set(re.findall(r'\|(?:\s*title|\s*length|\s*singer)(\d+)\s*=', content, re.I))
        if track_nums:
            curr_tracks = []
            for num in sorted([int(n) for n in track_nums]):
                t_m = re.search(r'\|\s*title' + str(num) + r'\s*=\s*([^|\n]+)', content, re.I)
                s_m = re.search(r'\|\s*(?:singer|note|extra)' + str(num) + r'\s*=\s*([^|\n]+)', content, re.I)
                l_m = re.search(r'\|\s*length' + str(num) + r'\s*=\s*([^|\n]+)', content, re.I)
                title = clean_wiki(t_m.group(1)) if t_m else ''
                singers = clean_wiki(s_m.group(1)) if s_m else ''
                length = clean_wiki(l_m.group(1)) if l_m else ''
                if title and not re.match(r'^\d{1,2}:\d{2}$', title):
                    curr_tracks.append((num, title, singers, length))
            if len(curr_tracks) >= 2:
                return curr_tracks

    # Strategy 2: Check for wikitables
    tables = re.findall(r'\{\|\s*class=\"wikitable.*?\n(.*?)\|\}', wt, re.DOTALL)
    for table in tables:
        rows = [r.strip() for r in table.split('|-') if r.strip()]
        if len(rows) <= 1:
            continue
        header = rows[0].lower()
        if not any(k in header for k in ['song', 'title', 'singer', 'length', 'duration']):
            continue

        header_cols = []
        for line in rows[0].split('\n'):
            line = line.strip()
            if line.startswith('!'):
                line = line[1:].strip()
            for p in line.split('!!'):
                header_cols.append(p.strip().lower())

        curr_tracks = []
        for idx, dr in enumerate(rows[1:], 1):
            cells = []
            for line in dr.split('\n'):
                line = line.strip()
                if line.startswith('|'):
                    line = line[1:].strip()
                if not line:
                    continue
                for p in line.split('||'):
                    cells.append(p.strip())

            # Find duration cell
            dur_idx = -1
            for c_i, c in enumerate(cells):
                if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', c.strip()):
                    dur_idx = c_i
                    break

            if dur_idx != -1 and len(cells) >= 2:
                dur = cells[dur_idx].strip()
                non_dur = [clean_wiki(c) for i, c in enumerate(cells) if i != dur_idx]
                
                # Check if first cell is track number
                t_num = idx
                if non_dur and re.match(r'^\d+$', non_dur[0]):
                    t_num = int(non_dur[0])
                    non_dur = non_dur[1:]

                title = ''
                singers = ''
                if len(non_dur) == 1:
                    title = non_dur[0]
                elif len(non_dur) == 2:
                    # In some tables headers are inverted (e.g. Nethaji)
                    # Test if non_dur[0] is singer and non_dur[1] is song or vice-versa
                    title, singers = non_dur[0], non_dur[1]
                elif len(non_dur) >= 3:
                    title = non_dur[0]
                    singers = non_dur[2] if 'sing' in ''.join(header_cols[2:]) else non_dur[1]

                if title and not re.match(r'^\d{1,2}:\d{2}$', title):
                    curr_tracks.append((t_num, title, singers, dur))

        if len(curr_tracks) >= 2:
            return curr_tracks

    return tracks

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Find affected albums
    affected_albums = c.execute("""
        SELECT DISTINCT a.id, a.title, a.year, a.source_url
        FROM tracks t
        JOIN albums a ON a.id = t.album_id
        WHERE (t.singers GLOB '[0-9]:[0-9][0-9]' 
           OR t.singers GLOB '[0-9][0-9]:[0-9][0-9]'
           OR t.title GLOB '[0-9]:[0-9][0-9]' 
           OR t.title GLOB '[0-9][0-9]:[0-9][0-9]')
           AND a.id != 6194
        ORDER BY a.year ASC, a.title ASC;
    """).fetchall()

    print(f"=== Found {len(affected_albums)} affected albums in {DB_PATH.name} ===")

    fixed_count = 0
    unresolved = []

    for aid, atitle, yr, url in affected_albums:
        page_name = url.split("/wiki/")[-1] if "/wiki/" in url else atitle
        page_name = urllib.parse.unquote(page_name)
        print(f"\nProcessing Album {aid}: {atitle} ({yr}) -> {page_name}")

        wt = fetch_wikitext(page_name)
        if not wt:
            # Fallback attempt with film suffix
            if not page_name.endswith("_(film)") and not page_name.endswith("_film)"):
                wt = fetch_wikitext(f"{page_name}_(film)")
            if not wt and not page_name.endswith(f"_({yr}_film)"):
                wt = fetch_wikitext(f"{page_name}_({yr}_film)")

        if not wt:
            print(f"  ❌ Could not retrieve wikitext for {atitle}")
            unresolved.append((aid, atitle, yr, "Fetch failed"))
            continue

        extracted = parse_tracks_from_wikitext(wt)
        if not extracted:
            print(f"  ❌ Could not parse tracks from wikitext for {atitle}")
            unresolved.append((aid, atitle, yr, "Parse failed"))
            time.sleep(0.8)
            continue

        print(f"  ✅ Extracted {len(extracted)} tracks from Wikipedia:")
        for t in extracted[:3]:
            print(f"     Trk {t[0]}: \"{t[1]}\" | Singers: \"{t[2]}\" | Duration: {t[3]}")

        # Update database
        # Fetch existing tracks for this album
        existing_tracks = c.execute("SELECT id, track_number FROM tracks WHERE album_id = ? ORDER BY track_number, id", (aid,)).fetchall()

        if len(existing_tracks) == len(extracted):
            # 1-to-1 update
            for old_trk, new_trk in zip(existing_tracks, extracted):
                trk_id = old_trk[0]
                t_num, title, singers, dur = new_trk
                c.execute("""
                    UPDATE tracks 
                    SET track_number = ?, title = ?, singers = ?, duration = ?
                    WHERE id = ?
                """, (t_num, title, singers, dur, trk_id))
        else:
            # Delete corrupted tracks and re-insert clean tracks
            # Preserve evidence_tier if any
            sample_evidence = c.execute("SELECT evidence_tier, historical_evidence_score FROM tracks WHERE album_id = ? LIMIT 1", (aid,)).fetchone()
            e_tier = sample_evidence[0] if sample_evidence else None
            h_score = sample_evidence[1] if sample_evidence else 0

            c.execute("DELETE FROM tracks WHERE album_id = ?", (aid,))
            for new_trk in extracted:
                t_num, title, singers, dur = new_trk
                c.execute("""
                    INSERT INTO tracks (album_id, track_number, title, singers, duration, track_type, evidence_tier, historical_evidence_score)
                    VALUES (?, ?, ?, ?, ?, 'song', ?, ?)
                """, (aid, t_num, title, singers, dur, e_tier, h_score))

        conn.commit()
        fixed_count += 1
        time.sleep(0.8)

    print(f"\n==========================================")
    print(f"Fix completed: {fixed_count} / {len(affected_albums)} albums successfully updated.")
    if unresolved:
        print(f"Unresolved albums ({len(unresolved)}):")
        for u in unresolved:
            print(f"  - {u[0]} | {u[1]} ({u[2]}): {u[3]}")
    
    # Final sanity check
    remaining_shifted = c.execute("""
        SELECT count(*) FROM tracks
        WHERE (singers GLOB '[0-9]:[0-9][0-9]' 
           OR singers GLOB '[0-9][0-9]:[0-9][0-9]'
           OR title GLOB '[0-9]:[0-9][0-9]' 
           OR title GLOB '[0-9][0-9]:[0-9][0-9]')
           AND album_id != 6194;
    """).fetchone()[0]
    print(f"Remaining shifted tracks in database: {remaining_shifted}")
    conn.close()

if __name__ == "__main__":
    main()
