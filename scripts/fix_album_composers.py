#!/usr/bin/env python3
"""
Fix Album Composers and Cast in tamil_discography.db.
Audits and repairs albums where Wikipedia annual film list scrapers
shifted actor cast lists into albums.composer and producer into albums.cast.
Extracts true composer and starring cast from Wikipedia {{Infobox film}}.
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

def extract_infobox_meta(wt):
    if not wt:
        return '', ''
    m = re.search(r'\|\s*(?:music|music_by|songs)\s*=\s*(.*?)(?=\n\|\s*[a-z_]+\s*=|\n\}\})', wt, re.DOTALL | re.I)
    if not m:
        m = re.search(r'\|\s*score\s*=\s*(.*?)(?=\n\|\s*[a-z_]+\s*=|\n\}\})', wt, re.DOTALL | re.I)
    s = re.search(r'\|\s*starring\s*=\s*(.*?)(?=\n\|\s*[a-z_]+\s*=|\n\}\})', wt, re.DOTALL | re.I)
    music = clean_wiki_meta(m.group(1)) if m else ''
    starring = clean_wiki_meta(s.group(1)) if s else ''
    return music, starring

def get_affected_albums(c):
    c.execute('SELECT id, title, year, director, composer, "cast", source_url FROM albums WHERE id != 6194')
    rows = c.fetchall()
    affected = []
    for aid, title, yr, director, comp, cast, url in rows:
        c_str = str(comp).strip()
        # Detect if composer has multiple actors or comma-separated cast lists
        if re.search(FAMOUS_ACTORS_REGEX, c_str, re.I) and (',' in c_str or len(c_str.split()) >= 4):
            affected.append((aid, title, yr, c_str, str(cast).strip(), url))
        elif ',' in c_str and len(c_str.split(',')) >= 4 and not re.search(r'\b(music|composer|duo|brothers|orchestra)\b', c_str, re.I):
            affected.append((aid, title, yr, c_str, str(cast).strip(), url))
    return sorted(affected, key=lambda x: (x[2] or 0, x[1]))

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    affected = get_affected_albums(c)
    print(f"=== Found {len(affected)} albums with cast in composer column ===")

    fixed_count = 0
    unresolved = []

    for aid, atitle, yr, old_comp, old_cast, url in affected:
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
            time.sleep(0.4)
            continue

        music, starring = extract_infobox_meta(wt)
        if not music:
            print(f"  ❌ Infobox music not found for {atitle}")
            unresolved.append((aid, atitle, yr, "No infobox music"))
            time.sleep(0.12)
            continue

        print(f"  ✅ Extracted True Composer: \"{music}\" | Cast: \"{starring[:45]}...\"")
        
        # Update database
        if starring:
            c.execute('UPDATE albums SET composer = ?, "cast" = ? WHERE id = ?', (music, starring, aid))
        else:
            c.execute('UPDATE albums SET composer = ? WHERE id = ?', (music, aid))

        conn.commit()
        fixed_count += 1
        time.sleep(0.12)

    print(f"\n==========================================")
    print(f"Album repair completed: {fixed_count} / {len(affected)} albums successfully updated.")
    if unresolved:
        print(f"Unresolved albums ({len(unresolved)}):")
        for u in unresolved[:20]:
            print(f"  - {u[0]} | {u[1]} ({u[2]}): {u[3]}")

    conn.close()

if __name__ == "__main__":
    main()
