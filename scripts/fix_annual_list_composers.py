#!/usr/bin/env python3
"""
Fix Album Composers and Cast from Wikipedia Annual Film Lists.
Parses List_of_Tamil_films_of_{year} tables for years where individual film pages
do not exist (or are redlinks), correctly mapping Music -> composer and Cast -> cast.
"""

import sqlite3
import urllib.request
import urllib.parse
import json
import re
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tamil_discography.db"

HEADERS = {
    "User-Agent": "TamilDiscographyBot/2.0 (https://github.com/Myselfnandha/tamil-discography; contact: discography@example.com)"
}

FAMOUS_ACTORS_REGEX = (
    r'\b(jaishankar|gemini|gemini\s*ganesan|sivaji|sivaji\s*ganesan|mgr|m\.?\s*g\.?\s*r|'
    r'rajinikanth|kamal|kamal\s*haasan|vijayakanth|sathyaraj|prabhu|karthik|mohan|'
    r'muralis|pandiarajan|bhagyaraj|radhika|radha|ambika|revathi|khushbu|gautami|'
    r'ramya\s*krishnan|meena|roja|simran|jyothika|nayanthara|trisha|senthil|'
    r'goundamani|janagaraj|vadivelu|vivek|vinu\s*chakravarthy|poornam\s*viswanathan|'
    r'charlie|charle|manorama|vadivukkarasi|sukumari|jaya\s*bharathi|jayabharathi|'
    r'nizhalgal\s*ravi|vijayakumar|nasser|raghuvaran|delhi\s*ganesh|manivannan|'
    r'cho|major\s*sundarrajan|thengai\s*srinivasan|pushpalatha|cid\s*sakunthala|'
    r'k\.?\s*r\.?\s*vijaya|padmini|vanisri|sowcar\s*janaki|ravichandran|kanchana|'
    r'r\.?\s*muthuraman|vennira\s*aadai\s*nirmala|jayalalitha|jayalalithaa)\b'
)

def clean_wiki_meta(s):
    if not s:
        return ""
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.DOTALL)
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'\{\{(?:[uU]bl|[uU]nbulleted list|[hH]list)\|(.*?)\}\}', lambda m: m.group(1).replace('|', ', '), s, flags=re.DOTALL)
    s = re.sub(r'\{\{(?:[fF]latlist|[pP]lainlist)\|(.*?)\}\}', lambda m: m.group(1).replace('*', ', '), s, flags=re.DOTALL)
    s = re.sub(r'\{\{[a-zA-Z0-9_\s]*\|?', '', s)
    s = s.replace('}}', '').replace('{{', '')
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', s)
    s = re.sub(r'<br\s*/?>', ', ', s)
    s = s.replace("'''", "").replace("''", "").replace('"', '').replace('&amp;', '&')
    items = [x.strip() for x in re.split(r'[,*\n\r]+', s) if x.strip()]
    return ', '.join(items)

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

def norm_title(t):
    if not t:
        return ""
    t = re.sub(r'\(.*?\)', '', t)
    return re.sub(r'[^a-z0-9]', '', t.lower())

def extract_films_from_annual_page(wt):
    """
    Extracts all film records from annual list wikitext.
    Returns list of dicts: [{'title': ..., 'music': ..., 'cast': ...}]
    """
    results = []
    tables = re.findall(r'\{\| class=\"[^\"]*wikitable[^\"]*\".*?\n\|\}', wt, re.DOTALL)
    if not tables:
        tables = re.findall(r'\{\|.*?\n\|\}', wt, re.DOTALL)

    for tbl in tables:
        rows = re.split(r'\n\|-+', tbl)
        headers = []
        for r in rows:
            if '!' in r:
                h_parts = [clean_wiki_meta(h).lower() for h in re.split(r'!!|(?<!^)!', r) if clean_wiki_meta(h).strip()]
                if any('music' in h or 'title' in h for h in h_parts):
                    headers = h_parts
                    break

        t_col, m_col, c_col = -1, -1, -1
        for idx, h in enumerate(headers):
            if 'title' in h and t_col == -1:
                t_col = idx
            elif any(k in h for k in ['music', 'score', 'composer']) and m_col == -1:
                m_col = idx
            elif any(k in h for k in ['cast', 'starring']) and c_col == -1:
                c_col = idx

        if t_col != -1 and m_col != -1:
            for r in rows:
                if '!' in r or '{|' in r:
                    continue
                cells = [clean_wiki_meta(c) for c in re.split(r'\n\||(?<!^)\|\|', r) if clean_wiki_meta(c).strip() and not c.startswith('}')]
                if len(cells) == 5 and t_col == 1 and m_col == 4 and c_col == 5:
                    r_title = cells[0]
                    r_music = cells[3]
                    r_cast = cells[4]
                    if r_title and r_music and r_title != '---':
                        results.append({
                            'title': r_title,
                            'music': r_music,
                            'cast': r_cast
                        })
                elif len(cells) > max(t_col, m_col):
                    r_title = cells[t_col]
                    r_music = cells[m_col]
                    r_cast = cells[c_col] if (c_col != -1 and len(cells) > c_col) else ""
                    if r_title and r_music and r_title != '---':
                        results.append({
                            'title': r_title,
                            'music': r_music,
                            'cast': r_cast
                        })
    return results

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    total_updated = 0

    for yr in range(1970, 1990):
        print(f"\nProcessing annual list for {yr}...")
        wt = fetch_wikitext(f"List_of_Tamil_films_of_{yr}")
        if not wt:
            print(f"  ❌ Could not fetch List_of_Tamil_films_of_{yr}")
            continue

        films = extract_films_from_annual_page(wt)
        print(f"  Found {len(films)} films in {yr} tables.")

        c.execute('SELECT id, title, composer, "cast" FROM albums WHERE year = ?', (yr,))
        db_albums = c.fetchall()

        year_updated = 0
        for f in films:
            f_norm = norm_title(f['title'])
            if not f_norm:
                continue

            for aid, atitle, acomp, acast in db_albums:
                if norm_title(atitle) == f_norm:
                    c_str = str(acomp).strip()
                    needs_update = False
                    # Check if composer has actor names or multiple commas
                    if re.search(FAMOUS_ACTORS_REGEX, c_str, re.I):
                        needs_update = True
                    elif ',' in c_str and len(c_str.split(',')) >= 2 and not any(k in c_str.lower() for k in ['music', 'brothers', 'duo']):
                        needs_update = True
                    elif any(k in c_str.lower() for k in ['films', 'pictures', 'productions', 'combines', 'studios', 'movies']):
                        needs_update = True
                    elif not c_str or c_str.lower() == 'unknown':
                        needs_update = True

                    if needs_update and f['music']:
                        new_cast = f['cast'] if f['cast'] else acast
                        c.execute('UPDATE albums SET composer = ?, "cast" = ? WHERE id = ?', (f['music'], new_cast, aid))
                        print(f"  ✅ [ID {aid}] {atitle} ({yr}) -> Composer: \"{f['music']}\" | Cast: \"{new_cast[:40]}...\"")
                        year_updated += 1
                        total_updated += 1
                        break

        conn.commit()
        print(f"  Updated {year_updated} albums for {yr}.")

    conn.close()
    print(f"\n==========================================")
    print(f"Annual list repair complete: {total_updated} albums updated.")

if __name__ == "__main__":
    main()
