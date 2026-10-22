#!/usr/bin/env python3
"""
Fix Shifted Column Albums in tamil_discography.db.
Audits and repairs tracks where Wikipedia table scrapers shifted singer names
into title and durations into singers/lyricist.
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

FAMOUS_SINGERS_REGEX = (
    r'\b(spb|s\.?\s*p\.?\s*b|balasubrahmanyam|chithra|k\.?\s*s\.?\s*chithra|'
    r'janaki|s\.?\s*janaki|yesudas|k\.?\s*j\.?\s*yesudas|susheela|p\.?\s*susheela|'
    r'soundararajan|t\.?\s*m\.?\s*soundararajan|tms|t\.?\s*l\.?\s*maharajan|'
    r'mano|hariharan|unni\s*krishnan|unnikrishnan|shankar\s*mahadevan|tippu|'
    r'karthik|harish\s*raghavendra|harini|swarnalatha|sujatha|anuradha\s*sriram|'
    r'malgudi\s*subha|malathy|vasundhara|madhu\s*balakrishnan|sirkazhi|seerkazhi|'
    r'sirgazhi|jamuna\s*rani|jikki|p\.?\s*leela|m\.?\s*l\.?\s*vasanthakumari|'
    r'shreya\s*ghoshal|sadhana\s*sargam|chinmayi|vijay\s*yesudas|naresh\s*iyer|'
    r'sid\s*sriram|pradeep\s*kumar|dhee|jonita|anthony\s*daasan|malaysia\s*vasudevan|'
    r'deepan\s*chakravarthy|s\.?\s*n\.?\s*surendar|gangai\s*amaran|jency|sailaja|'
    r's\.?\s*p\.?\s*sailaja|bambaye\s*jayashri|bombay\s*jayashri|nithyasree|srinivas|vasudevan|'
    r'haricharan|bhavatharini)\b'
)

def clean_wiki(s):
    if not s:
        return ""
    # Strip table formatting attributes
    s = re.sub(r'rowspan\s*=\s*\"?\d+\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'colspan\s*=\s*\"?\d+\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'style\s*=\s*\"[^\"]*\"\s*\|', '', s, flags=re.I)
    s = re.sub(r'style\s*=\s*\'[^\']*\'\s*\|', '', s, flags=re.I)
    s = re.sub(r'align\s*=\s*\"?[a-zA-Z]+\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'valign\s*=\s*\"?[a-zA-Z]+\"?\s*\|', '', s, flags=re.I)
    # Strip wiki links
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', s)
    # Unpack lang templates before stripping
    s = re.sub(r'\{\{lang\|[^|}]+\|([^|}]*?)(?:\|[^}]*)?\}\}', r'\1', s, flags=re.I)
    # Strip references and templates
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.DOTALL)
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'\{\{[^}]+\}\}', '', s)
    # HTML entities and line breaks
    s = s.replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'").replace('&nbsp;', ' ')
    s = re.sub(r'<br\s*/?>', ', ', s)
    s = s.replace("'''", "").replace("''", "").replace('"', '').strip()
    # Leading and trailing punctuation
    s = re.sub(r'^[,\-–—\s]+|[,\-–—\s]+$', '', s)
    return s.strip()

def fetch_wikitext(page_name):
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
    if not wt:
        return []

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
                y_m = re.search(r'\|\s*lyrics' + str(num) + r'\s*=\s*([^|\n]+)', content, re.I)
                title = clean_wiki(t_m.group(1)) if t_m else ''
                singers = clean_wiki(s_m.group(1)) if s_m else ''
                length = clean_wiki(l_m.group(1)) if l_m else ''
                lyr = clean_wiki(y_m.group(1)) if y_m else ''
                if title and not re.match(r'^\d{1,2}:\d{2}$', title):
                    curr_tracks.append((num, title, singers, lyr, length))
            if len(curr_tracks) >= 2:
                return curr_tracks

    # Strategy 2: Check for wikitables
    tables = re.findall(r'\{\|\s*class=\"wikitable.*?\n(.*?)\|\}', wt, re.DOTALL)
    for table in tables:
        rows = [r.strip() for r in table.split('|-') if r.strip()]
        if len(rows) <= 1:
            continue

        header_line = rows[0]
        headers = []
        for line in header_line.split('\n'):
            line = line.strip()
            if line.startswith('!'):
                line = line[1:].strip()
                for part in line.split('!!'):
                    headers.append(part.strip().lower())

        col_roles = {}
        has_song_or_title = any(re.search(r'\b(song|title|track\s*title)\b', h) for h in headers)
        for i, h in enumerate(headers):
            if re.search(r'\b(no\.?|#|track\s*no|track\s*number|sl\.?\s*no\.?)\b', h):
                col_roles['track_num'] = i
            elif h.strip() in ['track', 'tr']:
                if has_song_or_title:
                    col_roles['track_num'] = i
                else:
                    col_roles['title'] = i
            elif re.search(r'\b(song|title|track\s*title)\b', h):
                col_roles['title'] = i
            elif re.search(r'(singer|artist|performed|vocal)', h):
                col_roles['singers'] = i
            elif re.search(r'(lyric|writer)', h):
                col_roles['lyricist'] = i
            elif re.search(r'(length|duration|time)', h):
                col_roles['duration'] = i

        if 'title' not in col_roles and not any(k in col_roles for k in ['singers', 'duration']):
            continue

        curr_tracks = []
        last_singers = ''
        last_lyr = ''
        for idx, dr in enumerate(rows[1:], 1):
            cells = []
            for line in dr.split('\n'):
                line = line.strip()
                if line.startswith(('|', '!')):
                    line = re.sub(r'^[|!]\s*(?:scope\s*=\s*\"?[a-zA-Z]+\"?\s*\|)?', '', line).strip()
                if not line:
                    continue
                for p in line.split('||'):
                    cells.append(clean_wiki(p))

            if not cells:
                continue

            dur = ''
            t_num = idx
            title = ''
            singers = ''
            lyr = ''

            # If row has only 1 cell and rowspan from previous row is active
            if len(cells) == 1 and (last_singers or last_lyr):
                title = cells[0]
                singers = last_singers
                lyr = last_lyr
            else:
                # Detect duration pattern in any cell
                for c in cells:
                    if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', c):
                        dur = c
                        break

                if 'title' in col_roles and col_roles['title'] < len(cells):
                    title = cells[col_roles['title']]
                    if 'track_num' in col_roles and col_roles['track_num'] < len(cells):
                        try:
                            t_num = int(re.sub(r'\D', '', cells[col_roles['track_num']])) or idx
                        except:
                            t_num = idx
                    if 'singers' in col_roles and col_roles['singers'] < len(cells):
                        singers = cells[col_roles['singers']]
                    if 'lyricist' in col_roles and col_roles['lyricist'] < len(cells):
                        lyr = cells[col_roles['lyricist']]
                    if 'duration' in col_roles and col_roles['duration'] < len(cells) and not dur:
                        dur = cells[col_roles['duration']]
                else:
                    row_cells = list(cells)
                    if re.match(r'^\d+$', row_cells[0]):
                        t_num = int(row_cells[0])
                        row_cells = row_cells[1:]

                    if row_cells:
                        title = row_cells[0]
                    if len(row_cells) > 1 and row_cells[1] != dur:
                        singers = row_cells[1]
                    if len(row_cells) > 2 and row_cells[2] != dur:
                        lyr = row_cells[2]

            # Re-check misplaced durations
            if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', lyr):
                dur = lyr
                lyr = ''
            if re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', singers):
                dur = singers
                singers = ''

            # Auto-swap if singer ended up in title and singers has actual title
            if re.match(FAMOUS_SINGERS_REGEX, title.strip(), re.I) and not re.match(FAMOUS_SINGERS_REGEX, singers.strip(), re.I) and singers:
                title, singers = singers, title

            if singers:
                last_singers = singers
            if lyr:
                last_lyr = lyr

            if title and not re.match(r'^\d{1,2}:\d{2}$', title):
                curr_tracks.append((t_num, title, singers, lyr, dur))

        if len(curr_tracks) >= 2:
            return curr_tracks

    return []

def get_affected_albums(c):
    # 1. Check duration in wrong columns
    cur_dur = c.execute("""
        SELECT DISTINCT a.id, a.title, a.year, a.source_url
        FROM tracks t
        JOIN albums a ON a.id = t.album_id
        WHERE a.id != 6194
          AND (
              t.singers GLOB '[0-9]:[0-9][0-9]' 
           OR t.singers GLOB '[0-9][0-9]:[0-9][0-9]'
           OR t.title GLOB '[0-9]:[0-9][0-9]' 
           OR t.title GLOB '[0-9][0-9]:[0-9][0-9]'
           OR t.lyricist GLOB '[0-9]:[0-9][0-9]'
           OR t.lyricist GLOB '[0-9][0-9]:[0-9][0-9]'
          )
    """).fetchall()

    # 2. Check singer names in title
    c.execute("""
        SELECT t.album_id, a.title, a.year, a.source_url, t.title
        FROM tracks t
        JOIN albums a ON a.id = t.album_id
        WHERE a.id != 6194
    """)
    singer_title_albums = set()
    for aid, atitle, ayear, aurl, ttitle in c.fetchall():
        t_str = str(ttitle).strip()
        if re.match(FAMOUS_SINGERS_REGEX, t_str, re.I):
            singer_title_albums.add((aid, atitle, ayear, aurl))

    all_affected = sorted(list(set(cur_dur).union(singer_title_albums)), key=lambda x: (x[2] or 0, x[1]))
    return all_affected

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    affected_albums = get_affected_albums(c)
    print(f"=== Found {len(affected_albums)} affected albums to audit/repair in {DB_PATH.name} ===")

    fixed_count = 0
    unresolved = []

    for aid, atitle, yr, url in affected_albums:
        page_name = url.split("/wiki/")[-1] if (url and "/wiki/" in url) else atitle
        page_name = urllib.parse.unquote(page_name)
        print(f"\nProcessing Album {aid}: {atitle} ({yr}) -> {page_name}")

        wt = fetch_wikitext(page_name)
        if not wt:
            if not page_name.endswith("_(film)") and not page_name.endswith("_film)"):
                wt = fetch_wikitext(f"{page_name}_(film)")
            if not wt and not page_name.endswith(f"_({yr}_film)"):
                wt = fetch_wikitext(f"{page_name}_({yr}_film)")

        if not wt:
            print(f"  ❌ Could not retrieve wikitext for {atitle}")
            unresolved.append((aid, atitle, yr, "Fetch failed"))
            time.sleep(0.5)
            continue

        extracted = parse_tracks_from_wikitext(wt)
        if not extracted:
            print(f"  ❌ Could not parse tracks from wikitext for {atitle}")
            unresolved.append((aid, atitle, yr, "Parse failed"))
            time.sleep(0.5)
            continue

        print(f"  ✅ Extracted {len(extracted)} tracks from Wikipedia:")
        for t in extracted[:3]:
            print(f"     Trk {t[0]}: \"{t[1]}\" | Singers: \"{t[2]}\" | Duration: {t[4]}")

        # Update database
        existing_tracks = c.execute("SELECT id, track_number FROM tracks WHERE album_id = ? ORDER BY track_number, id", (aid,)).fetchall()

        if len(existing_tracks) == len(extracted):
            for old_trk, new_trk in zip(existing_tracks, extracted):
                trk_id = old_trk[0]
                t_num, title, singers, lyr, dur = new_trk
                c.execute("""
                    UPDATE tracks 
                    SET track_number = ?, title = ?, singers = ?, lyricist = ?, duration = ?
                    WHERE id = ?
                """, (t_num, title, singers, lyr, dur, trk_id))
        else:
            sample_evidence = c.execute("SELECT evidence_tier, historical_evidence_score FROM tracks WHERE album_id = ? LIMIT 1", (aid,)).fetchone()
            e_tier = sample_evidence[0] if sample_evidence else None
            h_score = sample_evidence[1] if sample_evidence else 0

            c.execute("DELETE FROM tracks WHERE album_id = ?", (aid,))
            for new_trk in extracted:
                t_num, title, singers, lyr, dur = new_trk
                c.execute("""
                    INSERT INTO tracks (album_id, track_number, title, singers, lyricist, duration, track_type, evidence_tier, historical_evidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, 'song', ?, ?)
                """, (aid, t_num, title, singers, lyr, dur, e_tier, h_score))

        conn.commit()
        fixed_count += 1
        time.sleep(0.5)

    print(f"\n==========================================")
    print(f"Fix completed: {fixed_count} / {len(affected_albums)} albums successfully updated.")
    if unresolved:
        print(f"Unresolved albums ({len(unresolved)}):")
        for u in unresolved[:20]:
            print(f"  - {u[0]} | {u[1]} ({u[2]}): {u[3]}")
    
    conn.close()

if __name__ == "__main__":
    main()

