#!/usr/bin/env python3
"""
verify_remediation.py - Deep Forensic Audit of Discography & Playlists
Checks for:
1. Shifted columns (durations in title/singers/lyricist).
2. Famous singers as track titles.
3. Actor cast lists in composer fields.
4. Mood integrity (no party/kuthu in sad/breakup, no kuthu/fight in calm/peaceful/sleeping).
5. Indie database hash integrity.
"""

import sqlite3
import hashlib
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DISCO_DB = BASE_DIR / "tamil_discography.db"
PLAYLISTS_DIR = BASE_DIR / "playlists"
INDIE_DB = PLAYLISTS_DIR / "indie" / "all_independent_songs.db"
EXPECTED_INDIE_HASH = "630f3d362ed3305cccd492994e62d9d42ef3a99066e6339658843c1e6cf0ce6a"

FAMOUS_ACTORS_REGEX = (
    r'\b(jaishankar|gemini\s*ganesan|sivaji\s*ganesan|rajinikanth|kamal\s*haasan|'
    r'vijayakanth|sathyaraj|radhika|vadivelu|goundamani|janagaraj)\b'
)

def check_indie_hash():
    with open(INDIE_DB, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()
    assert h == EXPECTED_INDIE_HASH, f"Indie hash mismatch: {h} != {EXPECTED_INDIE_HASH}"
    print(f"✅ Indie Hash Verified: {h}")

def audit_discography():
    print("\n--- Auditing tamil_discography.db ---")
    conn = sqlite3.connect(DISCO_DB)
    c = conn.cursor()

    # 1. Check for durations in text columns (excluding genuine film 3:33)
    c.execute("SELECT count(*) FROM tracks WHERE (title GLOB '[0-9]:[0-9][0-9]*' AND id != 39682) OR singers GLOB '[0-9]:[0-9][0-9]*' OR lyricist GLOB '[0-9]:[0-9][0-9]*'")
    dur_count = c.fetchone()[0]
    print(f"  Duration strings in title/singers/lyricist: {dur_count}")
    assert dur_count == 0, f"Found {dur_count} duration strings in metadata columns!"

    # 2. Check for famous singers in track titles
    c.execute("SELECT count(*) FROM tracks WHERE lower(title) in ('s. p. balasubrahmanyam', 's. janaki', 'k. s. chithra', 'k. j. yesudas', 'p. susheela', 'malaysia vasudevan')")
    singer_title_count = c.fetchone()[0]
    print(f"  Famous singers as track titles: {singer_title_count}")
    assert singer_title_count == 0, f"Found {singer_title_count} singer titles!"

    # 3. Check for actor cast lists in albums.composer
    c.execute("SELECT id, title, composer FROM albums WHERE id != 8426") # 8426 is Kannil Theriyum Kathaikal (5 composers)
    rows = c.fetchall()
    cast_in_comp = []
    for aid, atitle, comp in rows:
        c_str = str(comp).strip()
        if re.search(FAMOUS_ACTORS_REGEX, c_str, re.I) and (',' in c_str or len(c_str.split()) >= 4):
            cast_in_comp.append((aid, atitle, comp))
    print(f"  Actor cast in albums.composer: {len(cast_in_comp)}")
    assert len(cast_in_comp) == 0, f"Found {len(cast_in_comp)} albums with actor casts in composer!"

    conn.close()

def audit_playlists():
    print("\n--- Auditing Playlists ---")
    dbs = list(PLAYLISTS_DIR.glob("**/*.db"))
    print(f"  Found {len(dbs)} playlist databases.")
    assert len(dbs) == 214, f"Expected 214 playlist databases, found {len(dbs)}"

    # Check sensitive emotional playlists for bad leaks
    sad_dbs = [PLAYLISTS_DIR / "mood" / "sad.db", PLAYLISTS_DIR / "relationship" / "breakup.db", PLAYLISTS_DIR / "tamil" / "sad_melody.db"]
    for sdb in sad_dbs:
        if sdb.exists():
            conn = sqlite3.connect(sdb)
            conn.create_function('regexp', 2, lambda pat, item: bool(re.search(pat, item, re.I)) if item else False)
            c = conn.cursor()
            c.execute(r"SELECT track_title FROM tracks WHERE lower(track_title) REGEXP '\b(party|dance|kuthu|kondattam|celebration|jolly|rowdy)\b'")
            leaks = c.fetchall()
            print(f"  Party/Kuthu leaks in {sdb.name}: {len(leaks)}")
            assert len(leaks) == 0, f"Found party/kuthu leaks in {sdb.name}: {leaks}"
            conn.close()

    calm_dbs = [PLAYLISTS_DIR / "mood" / "peaceful.db", PLAYLISTS_DIR / "mood" / "calm.db", PLAYLISTS_DIR / "activity" / "sleeping.db"]
    for cdb in calm_dbs:
        if cdb.exists():
            conn = sqlite3.connect(cdb)
            conn.create_function('regexp', 2, lambda pat, item: bool(re.search(pat, item, re.I)) if item else False)
            c = conn.cursor()
            c.execute(r"SELECT track_title FROM tracks WHERE lower(track_title) REGEXP '\b(kuthu|danga|verithanam|badass|fight|action|rowdy|item|sarakku|neruppu|thee|adra)\b'")
            leaks = c.fetchall()
            print(f"  Aggressive/Fight leaks in {cdb.name}: {len(leaks)}")
            assert len(leaks) == 0, f"Found aggressive leaks in {cdb.name}: {leaks}"
            conn.close()

    print("✅ All playlist semantic checks passed with 0 errors!")

def main():
    check_indie_hash()
    audit_discography()
    audit_playlists()
    print("\n==============================================")
    print(" 🌟 ALL AUDITS & INVARIANTS PERFECTLY VERIFIED! ")
    print("==============================================")

if __name__ == "__main__":
    main()
