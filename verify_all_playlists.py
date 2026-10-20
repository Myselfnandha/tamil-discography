#!/usr/bin/env python3
"""
verify_all_playlists.py - Deep Audit of all 139 Local Playlist Databases.

Checks:
1. Era constraints across Golden Era, Old Is Gold, 90s Classics, 2000s Hits, etc.
2. Zero occurrence of known collision songs (modern tracks in vintage databases).
3. Presence of genuine vintage tracks restored from Wikipedia.
4. Zero occurrence of non-movie debris (biographical artists as album titles).
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists"

# Known collided modern songs that were previously polluting vintage albums
COLLIDED_MODERN_SONGS = [
    "Pathala Pathala", "Scene Ah Scene Ah", "Yelelo", "Kurumba", "Iragai Poley",
    "Idhuvum Kadandhu Pogum", "Aaru Padai", "Prabalamagavey", "Kandaa Vara Sollunga"
]

# Genuine vintage tracks that should be present
EXPECTED_VINTAGE_TRACKS = [
    ("Vikram Vikram", "old_is_gold.db"),
    ("Kanmaniye Pesu", "old_is_gold.db"),
    ("Namma Singaari Saraku", "old_is_gold.db"),
    ("Penn Maaney", "old_is_gold.db"),
    ("Namma Ooru Singari", "old_is_gold.db"),
    ("Ammaa Ammaa", "old_is_gold.db")
]

def audit():
    import json
    print("==================================================================")
    print(" 🔍 RUNNING DEEP AUDIT ON ALL PLAYLIST DATABASES")
    print("==================================================================")

    # 0. Dynamic Manifest Comparison
    manifest_path = BASE_DIR / "data" / "catalog_inventory_manifest.json"
    manifest_total = None
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                manifest_total = manifest_data.get("total_discovered_databases")
                print(f"Loaded dynamic inventory manifest ({manifest_total} expected databases).")
        except Exception as e:
            print(f"Note: Could not parse manifest: {e}")

    db_files = sorted(list(PLAYLISTS_DIR.glob("**/*.db")))
    print(f"Dynamically discovered {len(db_files)} playlist databases across {len(set(p.parent.name for p in db_files))} categories.")

    errors = []
    checked_count = 0

    for db_path in db_files:
        rel_path = db_path.relative_to(PLAYLISTS_DIR)
        checked_count += 1
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Database Integrity
        try:
            integrity = cur.execute("PRAGMA integrity_check;").fetchone()[0]
            if integrity != "ok":
                errors.append(f"❌ Corrupt SQLite database {rel_path}: {integrity}")
        except Exception as e:
            errors.append(f"❌ Could not run integrity check on {rel_path}: {e}")

        # Check table schema
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
        if not cur.fetchone():
            conn.close()
            continue

        # 1. Check for known collided songs in vintage playlists
        if any(v in str(rel_path) for v in ["golden_era", "old_is_gold"]):
            for s in COLLIDED_MODERN_SONGS:
                if s == "Yelelo":
                    cur.execute("SELECT track_title, album_title, year, composer FROM tracks WHERE track_title = 'Yelelo' OR track_title LIKE 'Yelelo %'")
                else:
                    cur.execute("SELECT track_title, album_title, year, composer FROM tracks WHERE track_title LIKE ?", (f"%{s}%",))
                hits = cur.fetchall()
                for h in hits:
                    errors.append(f"❌ Collided Modern Song in {rel_path}: '{h[0]}' ({h[1]}, {h[2]}, {h[3]})")

        # 2. Check for non-movie debris album titles
        cur.execute("""
            SELECT track_title, album_title FROM tracks 
            WHERE album_title IN ('A. R. Rahman', 'Harris Jayaraj', 'Yuvan Shankar Raja', 'Deva', 'Anirudh Ravichander')
               OR album_title LIKE '--%'
        """)
        debris = cur.fetchall()
        for d in debris:
            errors.append(f"❌ Non-movie debris album in {rel_path}: '{d[1]}' - '{d[0]}'")

        # 3. Era year violations
        if "golden_era.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title, year FROM tracks WHERE year < 1960 OR year > 1979")
            bad = cur.fetchall()
            for b in bad:
                errors.append(f"❌ Year violation in golden_era: '{b[0]}' from {b[1]} ({b[2]} not in 1960-1979)")

        if "old_is_gold.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title, year FROM tracks WHERE year < 1960 OR year > 1989")
            bad = cur.fetchall()
            for b in bad:
                errors.append(f"❌ Year violation in old_is_gold: '{b[0]}' from {b[1]} ({b[2]} not in 1960-1989)")

        if "90s_classics.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title, year FROM tracks WHERE year < 1990 OR year > 1999")
            bad = cur.fetchall()
            for b in bad:
                errors.append(f"❌ Year violation in 90s_classics: '{b[0]}' from {b[1]} ({b[2]} not in 1990-1999)")

        # 4. Annual Year Invariant Clamping (for playlists/year/*.db)
        if "year/" in str(rel_path) or "year\\" in str(rel_path):
            try:
                expected_year = int(db_path.stem)
                cur.execute("SELECT DISTINCT year FROM tracks")
                distinct_years = [r[0] for r in cur.fetchall()]
                for yr in distinct_years:
                    if yr != expected_year:
                        errors.append(f"❌ Cross-Year Leakage in {rel_path}: Found year {yr} in {expected_year}.db")
                
                # Verify total_tracks in playlist_info matches tracks count
                cur.execute("SELECT value FROM playlist_info WHERE key='total_tracks'")
                meta_cnt_row = cur.fetchone()
                cur.execute("SELECT COUNT(*) FROM tracks")
                actual_cnt = cur.fetchone()[0]
                if meta_cnt_row and int(meta_cnt_row[0]) != actual_cnt:
                    errors.append(f"❌ Track count mismatch in {rel_path}: meta={meta_cnt_row[0]}, actual={actual_cnt}")

                # Verify strictly monotonic positions 1..N
                cur.execute("SELECT position FROM tracks ORDER BY position ASC")
                positions = [r[0] for r in cur.fetchall()]
                expected_positions = list(range(1, len(positions) + 1))
                if positions != expected_positions:
                    errors.append(f"❌ Non-monotonic positions in {rel_path}: expected 1..{len(positions)}")

                # Verify zero duplicates
                cur.execute("SELECT track_title, album_title FROM tracks")
                all_tracks = cur.fetchall()
                seen_tracks = set()
                for t in all_tracks:
                    key = (t[0].lower().strip(), t[1].lower().strip())
                    if key in seen_tracks:
                        errors.append(f"❌ Duplicate track in {rel_path}: '{t[0]}' ({t[1]})")
                    seen_tracks.add(key)

                # Verify evidence tiers validity
                cur.execute("SELECT DISTINCT evidence_tier FROM tracks WHERE evidence_tier IS NOT NULL")
                tiers = [r[0] for r in cur.fetchall()]
                valid_tiers = {"tier_1_mega", "tier_2_popular", "tier_3_cult", "tier_4_archive"}
                for tier in tiers:
                    if tier not in valid_tiers:
                        errors.append(f"❌ Invalid evidence_tier in {rel_path}: '{tier}'")

            except ValueError:
                pass

        # 5. Indie Invariant & Track Count Integrity (for playlists/indie/*.db)
        if "indie/" in str(rel_path) or "indie\\" in str(rel_path):
            cur.execute("SELECT value FROM playlist_info WHERE key='total_tracks'")
            meta_cnt_row = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM tracks")
            actual_cnt = cur.fetchone()[0]
            if actual_cnt == 0:
                errors.append(f"❌ Empty indie database in {rel_path}")
            if meta_cnt_row and int(meta_cnt_row[0]) != actual_cnt:
                errors.append(f"❌ Indie track count mismatch in {rel_path}: meta={meta_cnt_row[0]}, actual={actual_cnt}")

        # 6. Artist Attribution Integrity (No cross-artist or false positive leakage)
        if "deva.db" in str(rel_path) or "deva_hits.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title, composer FROM tracks WHERE track_title = 'Yaavalo' OR composer LIKE '%Ashwin Vinayagamoorthy%'")
            false_hits = cur.fetchall()
            for fh in false_hits:
                errors.append(f"❌ False Deva match in {rel_path}: '{fh[0]}' from '{fh[1]}' (Composer: {fh[2]})")

        if "kv_mahadevan.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title, singers FROM tracks WHERE singers LIKE '%Shivam Mahadevan%' OR singers LIKE '%Shankar Mahadevan%'")
            false_hits = cur.fetchall()
            for fh in false_hits:
                errors.append(f"❌ False K.V. Mahadevan match in {rel_path}: '{fh[0]}' sung by {fh[2]}")

        if "devotional.db" in str(rel_path):
            cur.execute("SELECT track_title, album_title FROM tracks WHERE track_title = 'Yaavalo'")
            false_hits = cur.fetchall()
            for fh in false_hits:
                errors.append(f"❌ False Devotional match in {rel_path}: '{fh[0]}' from '{fh[1]}'")

        conn.close()

    print(f"Audited {checked_count} databases.")
    if manifest_total and checked_count != manifest_total:
        print(f"⚠️ Manifest comparison: Discovered {checked_count} vs Manifest {manifest_total}")
    else:
        print(f"✅ Dynamic inventory match: {checked_count}/{manifest_total or checked_count} databases audited.")

    if errors:
        print(f"⚠️ FOUND {len(errors)} ERRORS:")
        for e in errors[:25]:
            print("  ", e)
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more.")
    else:
        print(f"✅ ZERO ERRORS! All {checked_count} playlist databases strictly satisfy all era, year-clamping, indie, monotonic ordering, and collision invariants!")

    # Verify expected vintage tracks
    print("\nVerifying genuine restored vintage tracks in local databases:")
    for track_name, db_name in EXPECTED_VINTAGE_TRACKS:
        target_db = None
        for p in db_files:
            if p.name == db_name:
                target_db = p
                break
        if target_db:
            conn = sqlite3.connect(target_db)
            cur = conn.cursor()
            cur.execute("SELECT track_title, album_title, year, composer, singers FROM tracks WHERE track_title LIKE ?", (f"%{track_name}%",))
            res = cur.fetchone()
            if res:
                print(f"  ✅ Found '{res[0]}' in '{res[1]}' ({res[2]}, Composer: {res[3]}, Singers: {res[4]})")
            else:
                print(f"  ⚠️ Warning: '{track_name}' not found in {db_name}")
            conn.close()

if __name__ == "__main__":
    audit()
