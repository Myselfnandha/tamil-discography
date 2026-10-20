#!/usr/bin/env python3
"""
fetcher.py - Optimized, resilient metadata extractor for Tamil cinema (1960-2026).
Makes a single HTTP call per film to parse soundtrack tables and wikitext.
Complies strictly with Wikimedia API rate limits and backoff policies.
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import re
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

USER_AGENT = "TamilDiscographyCataloger/1.0 (https://github.com/nandha/tamil-music; contact: nandha@localhost) python-urllib/3.10"

def clean_wiki(s):
    """Strip wiki markup, citations, templates, and extraneous formatting."""
    if not s:
        return ""
    # Remove citations <ref>...</ref> and <ref.../>
    s = re.sub(r'<ref.*?>.*?</ref>', '', s, flags=re.DOTALL)
    s = re.sub(r'<ref.*?/>', '', s)
    # Remove HTML tags
    s = re.sub(r'<[^>]+>', '', s)
    # Replace links [[Page|Label]] -> Label, [[Page]] -> Page
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', s)
    # Remove bold/italic markers
    s = re.sub(r"'''+|''+", '', s)
    # Remove templates {{...}}
    s = re.sub(r'\{\{.*?\}\}', '', s)
    # Strip rowspan / colspan declarations
    s = re.sub(r'rowspan\s*=\s*\"?\d+\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'colspan\s*=\s*\"?\d+\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'style\s*=\s*\"?[^\"]*\"?\s*\|', '', s, flags=re.I)
    s = re.sub(r'align\s*=\s*\"?[^\"]*\"?\s*\|', '', s, flags=re.I)
    s = s.strip(' "\'\t\r\n')
    if s.startswith('|'):
        s = s.lstrip('| \t\r\n')
    return s.strip(' "\'\t\r\n')

def api_get(params, retries=5, base_delay=2.5):
    """Fetch from Wikipedia API with automatic 429 detection and exponential backoff."""
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=headers)
    
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After")
                wait_sec = float(retry_after) if retry_after else (base_delay * (1.8 ** attempt))
                logging.warning(f"HTTP 429 (Rate limit). Backing off {wait_sec:.1f}s before retry {attempt + 1}/{retries}...")
                time.sleep(wait_sec)
            else:
                logging.warning(f"HTTP Error {e.code} for URL: {url[:70]}...")
                time.sleep(1.0)
        except Exception as e:
            if attempt == retries - 1:
                logging.warning(f"Network error after {retries} attempts: {e}")
                return None
            time.sleep(1.0)
    return None

def fetch_annual_filmography(year):
    """
    Fetch all Tamil films released in a given year from Wikipedia's annual list.
    """
    page_name = f"List_of_Tamil_films_of_{year}"
    data = api_get({
        "action": "parse",
        "page": page_name,
        "redirects": "1",
        "format": "json",
        "prop": "wikitext"
    })
    
    if not data or "error" in data:
        logging.error(f"Could not load filmography for year {year}")
        return []

MONTHS = {'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
          'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'}

def is_date_or_header(s):
    s_clean = re.sub(r'<[^>]+>', '', s).strip(' \'\t\r\n|\"!').lower()
    if not s_clean:
        return True
    if not re.search(r'[a-zA-Z0-9]', s_clean):
        return True
    if s_clean in MONTHS or s_clean.startswith('jan') or s_clean.startswith('feb') or s_clean.startswith('mar'):
        return True
    if re.match(r'^\d{1,2}$', s_clean):
        return True
    if any(k in s_clean for k in ['opening', 'title', 'director', 'cast', 'producer', 'music', 'gross', 'rank']):
        return True
    if 'style=' in s_clean or 'rowspan=' in s_clean or 'colspan=' in s_clean or 'align=' in s_clean or 'valign=' in s_clean:
        parts = s.split('|')
        val = parts[-1].strip(' \'\t\r\n|\"!')
        return is_date_or_header(val)
    return False

def fetch_annual_filmography(year):
    """
    Fetch all Tamil films released in a given year from Wikipedia's annual list.
    Handles dynamic column offsets caused by opening month and date rowspans.
    """
    page_name = f"List_of_Tamil_films_of_{year}"
    data = api_get({
        "action": "parse",
        "page": page_name,
        "redirects": "1",
        "format": "json",
        "prop": "wikitext"
    })
    
    if not data or "error" in data:
        logging.error(f"Could not load filmography for year {year}")
        return []

    wt = data["parse"]["wikitext"]["*"]
    tables = re.findall(r'\{\|(?:[^\n]*?wikitable[^\n]*?)(.*?)\|\}', wt, re.DOTALL | re.I)
    films = []
    
    for tbl in tables:
        # Skip pure box office or non-film tables
        tbl_preview = tbl[:400].lower()
        if not any(k in tbl_preview for k in ['director', 'cast', 'producer', 'music']):
            continue
            
        rows = tbl.split('|-')
        for r in rows[1:]:
            m = re.search(r'^\s*\|', r, re.MULTILINE)
            if not m:
                continue
            r_clean = r[m.start():]
            cells = [c.strip() for c in re.split(r'\|\||\n\|', r_clean.strip()) if c.strip() and not c.strip().startswith('class=')]
            if not cells:
                continue
                
            film_idx = -1
            for idx, c in enumerate(cells):
                if not is_date_or_header(c):
                    film_idx = idx
                    break
                    
            if film_idx == -1:
                continue
                
            raw_title = cells[film_idx]
            link_m = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', raw_title)
            if link_m:
                wiki_page = link_m.group(1).strip()
                title = link_m.group(2).strip() if link_m.group(2) else wiki_page
            else:
                wiki_page = clean_wiki(raw_title)
                title = wiki_page
                
            title = clean_wiki(title)
            if not title or is_date_or_header(title) or len(title) > 100:
                continue
                
            rem_cells = cells[film_idx + 1:]
            director = clean_wiki(rem_cells[0]) if len(rem_cells) > 0 else ""
            cast = clean_wiki(rem_cells[1]) if len(rem_cells) > 1 else ""
            producer = clean_wiki(rem_cells[2]) if len(rem_cells) > 2 else ""
            composer = clean_wiki(rem_cells[3]) if len(rem_cells) > 3 else ""
            
            films.append({
                "year": int(year),
                "title": title,
                "wiki_page": wiki_page,
                "director": director,
                "producer": producer,
                "composer": composer,
                "cast": cast,
                "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_page.replace(' ', '_'))}"
            })
        
    logging.info(f"Year {year}: Loaded {len(films)} registered films.")
    return films

def extract_tracks_from_wikitext(wt):
    """Parse track listing or wikitable from an article's wikitext."""
    tracks = []
    
    # Isolate Soundtrack / Songs section if possible
    soundtrack_match = re.search(r'==\s*(?:soundtrack|music|songs|track\s*listing)\s*==.*?(?:==|\Z)', wt, re.I | re.DOTALL)
    scope_wt = soundtrack_match.group(0) if soundtrack_match else wt

    # Strategy 1: {{Track listing}} template
    if "{{track listing" in scope_wt.lower() or "{{tracklist" in scope_wt.lower():
        for i in range(1, 40):
            tm = re.search(rf'\|\s*title{i}\s*=\s*([^|\n}}]+)', scope_wt, re.I)
            if not tm:
                break
            t_title = clean_wiki(tm.group(1))
            em = re.search(rf'\|\s*(?:extra|singer|singers){i}\s*=\s*([^|\n}}]+)', scope_wt, re.I)
            singers = clean_wiki(em.group(1)) if em else ""
            lm = re.search(rf'\|\s*(?:lyrics|lyricist){i}\s*=\s*([^|\n}}]+)', scope_wt, re.I)
            lyrics = clean_wiki(lm.group(1)) if lm else ""
            dm = re.search(rf'\|\s*(?:length|duration){i}\s*=\s*([^|\n}}]+)', scope_wt, re.I)
            length = clean_wiki(dm.group(1)) if dm else ""
            nm = re.search(rf'\|\s*note{i}\s*=\s*([^|\n}}]+)', scope_wt, re.I)
            raga = clean_wiki(nm.group(1)) if nm else ""
            
            tracks.append({
                "track_number": i,
                "title": t_title,
                "singers": singers,
                "lyricist": lyrics,
                "duration": length,
                "raga": raga
            })
        if tracks:
            return tracks

    # Strategy 2: Wikitable inside soundtrack section
    table_match = re.search(r'\{\|\s*class\s*=\s*\"?[^\"]*wikitable[^\"]*\"?(.*?)\|\}', scope_wt, re.DOTALL | re.I)
    if table_match:
        table_content = table_match.group(1)
        raw_rows = table_content.split('|-')
        
        headers = []
        data_rows_start = 1
        for r_idx, r in enumerate(raw_rows):
            if '!' in r or any(k in r.lower() for k in ['song', 'title', 'singers', 'length']):
                r_content = r
                if '!' in r_content:
                    r_content = r_content[r_content.index('!'):]
                elif '\n|' in r_content:
                    r_content = r_content[r_content.index('\n|'):]
                h_cells = [clean_wiki(h).lower() for h in re.split(r'!!|\n!|\|\||\n\|', r_content.strip()) if clean_wiki(h).strip()]
                h_cells = [h.lstrip('!| ').strip() for h in h_cells if h.lstrip('!| ').strip()]
                if any(any(k in h for k in ['song', 'title', 'track', 'singer', 'artist', 'length', 'duration']) for h in h_cells):
                    headers = h_cells
                    data_rows_start = r_idx + 1
                    break

        col_map = {'track_no': -1, 'title': -1, 'singers': -1, 'lyrics': -1, 'duration': -1}
        for idx, h in enumerate(headers):
            if any(k in h for k in ['s.no', 'no.', 'no ', 'number', '#', 's. no', 's.no.']) and col_map['track_no'] == -1:
                col_map['track_no'] = idx
            elif any(k in h for k in ['song', 'title', 'track']) and col_map['title'] == -1:
                col_map['title'] = idx
            elif any(k in h for k in ['singer', 'artist', 'playback']):
                col_map['singers'] = idx
            elif any(k in h for k in ['lyric', 'words']):
                col_map['lyrics'] = idx
            elif any(k in h for k in ['length', 'duration', 'time']):
                col_map['duration'] = idx

        if col_map['title'] == -1:
            if col_map['track_no'] == 0:
                col_map['title'] = 1
                col_map['singers'] = 2
                col_map['lyrics'] = 3
                col_map['duration'] = 4
            else:
                col_map['title'] = 0
                col_map['singers'] = 1
                col_map['lyrics'] = 2
                col_map['duration'] = 3

        valid_cols = [v for v in col_map.values() if v >= 0]
        total_cols = max(valid_cols) + 1 if valid_cols else 4
        active_spans = {}
        t_num = 1

        for r in raw_rows[data_rows_start:]:
            phys_cells = [c.strip() for c in re.split(r'\|\||\n\|', r.strip()) if c.strip() and not c.strip().startswith('class=')]
            if not phys_cells:
                continue

            logical_cells = []
            phys_idx = 0
            for log_col in range(total_cols):
                if log_col in active_spans and active_spans[log_col]['remaining'] > 0:
                    logical_cells.append(active_spans[log_col]['val'])
                    active_spans[log_col]['remaining'] -= 1
                elif phys_idx < len(phys_cells):
                    cell = phys_cells[phys_idx]
                    phys_idx += 1
                    span_m = re.match(r'rowspan\s*=\s*\"?(\d+)\"?\s*\|\s*(.*)', cell, re.I | re.DOTALL)
                    if span_m:
                        cnt = int(span_m.group(1))
                        val = clean_wiki(span_m.group(2))
                        active_spans[log_col] = {'val': val, 'remaining': cnt - 1}
                        logical_cells.append(val)
                    else:
                        logical_cells.append(clean_wiki(cell))
                else:
                    logical_cells.append('')

            t_title = logical_cells[col_map['title']] if 0 <= col_map['title'] < len(logical_cells) else ''
            t_singers = logical_cells[col_map['singers']] if 0 <= col_map['singers'] < len(logical_cells) else ''
            t_lyrics = logical_cells[col_map['lyrics']] if 0 <= col_map['lyrics'] < len(logical_cells) else ''
            t_duration = logical_cells[col_map['duration']] if 0 <= col_map['duration'] < len(logical_cells) else ''

            # If title is pure digits or starts with '!', shift
            if re.match(r'^\d{1,2}$', t_title.strip()) and t_singers:
                t_title = t_singers
                t_singers = t_lyrics

            t_title = t_title.lstrip('| \"\'').strip(' \"\'')
            if t_title and not t_title.startswith('!') and len(t_title) > 1 and not t_title.lower().startswith('song title'):
                tracks.append({
                    'track_number': t_num,
                    'title': t_title,
                    'singers': t_singers,
                    'lyricist': t_lyrics,
                    'duration': t_duration,
                    'raga': ''
                })
                t_num += 1

    return tracks

def fetch_soundtrack_tracks(wiki_page):
    """
    Fetch entire article in ONE request and extract soundtrack tracks.
    """
    data = api_get({
        "action": "parse",
        "page": wiki_page,
        "redirects": "1",
        "format": "json",
        "prop": "wikitext"
    })
    
    if not data or "error" in data:
        return []
        
    wt = data["parse"]["wikitext"]["*"]
    return extract_tracks_from_wikitext(wt)

if __name__ == "__main__":
    t = fetch_soundtrack_tracks("Mannathi Mannan")
    print(f"Mannathi Mannan: {len(t)} tracks")
    k = fetch_soundtrack_tracks("Kalathur Kannamma")
    print(f"Kalathur Kannamma: {len(k)} tracks")
