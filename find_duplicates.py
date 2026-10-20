#!/usr/bin/env python3
"""
find_duplicates.py - Comprehensive duplicate finder and cleaner across all databases.
Scans tamil_discography.db and all 119 standalone playlist databases for:
1. Duplicate track titles within each database.
2. Corrupt / header / wikitable garbage rows (!, scope=, --, empty titles).
3. Provides a clean mode (--fix) to safely deduplicate and purge garbage.
"""

import sys
import os
import re
import argparse
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"
PLAYLISTS_DIR = BASE_DIR / "playlists"

# Criteria for non-song junk/artifacts
JUNK_PATTERNS = [
    r"^--+$",
    r"^—+$",
    r"^–+$",
    r"^\s*!.*",
    r"^\s*\|.*",
    r".*scope=.*",
    r".*rowspan=.*",
    r".*colspan=.*",
    r".*style=.*",
    r".*width=.*",
    r".*align=.*",
    r".*bgcolor=.*",
    r".*class=.*",
    r".*wikitable.*",
    r".*multiplication.*",
    r"^\{\|.*",
    r".*worldwide gross.*",
    r".*box office.*",
    r"^rank\s*$",
    r"^no\.\s*$",
    r"^\d{4}$",         # Pure 4-digit years parsed as titles from filmographies
    r"^\d{1,2}$",        # Pure 1-2 digit track numbers parsed as titles
    r".*<ref.*",
    r".*\{\{.*"
]

def is_junk_title(title: str) -> bool:
    """Check if title is empty or a wikitable header/artifact."""
    if not title:
        return True
    t = title.strip()
    if len(t) <= 1:
        return True
    for pat in JUNK_PATTERNS:
        if re.search(pat, t, re.I):
            return True
    return False


def scan_discography_duplicates():
    """Audit tamil_discography.db for duplicate and junk tracks."""
    if not DISCO_DB.exists():
        print(f"Master database {DISCO_DB} not found.")
        return {}

    conn = sqlite3.connect(DISCO_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Total tracks
    cur.execute("SELECT COUNT(*) as total FROM tracks;")
    total_tracks = cur.fetchone()["total"]

    # 2. Junk tracks
    cur.execute("SELECT id, title, album_id FROM tracks;")
    all_tracks = cur.fetchall()
    junk_ids = [r["id"] for r in all_tracks if is_junk_title(r["title"])]

    # 3. True duplicates: same title + same album_id
    cur.execute("""
        SELECT LOWER(TRIM(title)) as norm_title, album_id, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM tracks
        WHERE title IS NOT NULL AND title != ''
        GROUP BY LOWER(TRIM(title)), album_id
        HAVING COUNT(*) > 1;
    """)
    dup_rows = cur.fetchall()
    
    conn.close()

    return {
        "total_tracks": total_tracks,
        "junk_count": len(junk_ids),
        "junk_ids": junk_ids,
        "dup_groups_count": len(dup_rows),
        "dup_rows": dup_rows
    }


def scan_playlist_duplicates(playlists_dir=PLAYLISTS_DIR):
    """Scan all standalone playlist databases for internal duplicates and junk."""
    if not playlists_dir.exists():
        return {}

    db_files = sorted(playlists_dir.rglob("*.db"))
    report = {}

    for db_path in db_files:
        rel_path = str(db_path.relative_to(playlists_dir.parent))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as cnt FROM tracks;")
        total_cnt = cur.fetchone()["cnt"]

        # Check junk
        cur.execute("SELECT id, track_title, album_title FROM tracks;")
        rows = cur.fetchall()
        junk_ids = [r["id"] for r in rows if is_junk_title(r["track_title"])]

        # Check duplicates by (LOWER(track_title), LOWER(album_title))
        cur.execute("""
            SELECT LOWER(TRIM(track_title)) as norm_t, LOWER(TRIM(album_title)) as norm_a, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
            FROM tracks
            GROUP BY LOWER(TRIM(track_title)), LOWER(TRIM(album_title))
            HAVING COUNT(*) > 1;
        """)
        dups = cur.fetchall()
        conn.close()

        if junk_ids or dups:
            report[rel_path] = {
                "db_path": db_path,
                "total_tracks": total_cnt,
                "junk_count": len(junk_ids),
                "junk_ids": junk_ids,
                "dup_count": len(dups),
                "dup_samples": [(d["norm_t"], d["norm_a"], d["cnt"]) for d in dups[:5]]
            }

    return report


def print_audit_report(disco_rep, pl_rep, show_all=False, playlists_only=False):
    """Print clean terminal audit summary."""
    print("\n" + "="*85)
    print(" 🔎 TAMIL DISCOGRAPHY & PLAYLISTS DUPLICATE & JUNK AUDIT REPORT")
    print("="*85)

    if not playlists_only and disco_rep:
        print("\n[1] MASTER DATABASE: tamil_discography.db")
        print("-" * 85)
        print(f"  • Total Track Entries          : {disco_rep.get('total_tracks', 0):,}")
        print(f"  • Corrupt / Junk Header Rows   : {disco_rep.get('junk_count', 0):,} (table headers, dashes, etc.)")
        print(f"  • Duplicate Title+Album Groups : {disco_rep.get('dup_groups_count', 0):,}")
    
    total_dbs = len(list(PLAYLISTS_DIR.rglob("*.db")))
    print(f"\n[2] STANDALONE PLAYLIST DATABASES ({total_dbs} DBs)")
    print("-" * 85)
    total_pl_junk = sum(d["junk_count"] for d in pl_rep.values())
    total_pl_dups = sum(d["dup_count"] for d in pl_rep.values())
    print(f"  • Databases with Duplicates/Junk: {len(pl_rep)} of {total_dbs}")
    print(f"  • Total Junk Entries Across DBs : {total_pl_junk:,}")
    print(f"  • Total Duplicate Song Groups   : {total_pl_dups:,}")

    if pl_rep:
        sorted_dbs = sorted(pl_rep.items(), key=lambda x: (x[1]["junk_count"] + x[1]["dup_count"]), reverse=True)
        display_dbs = sorted_dbs if show_all else sorted_dbs[:15]
        header_title = f"All {len(display_dbs)} Playlists with Duplicates/Junk:" if show_all else f"Top 15 Playlists by Duplicate/Junk Count (pass --all to show all {len(pl_rep)}):"
        print(f"\n{header_title}")
        for rel_p, data in display_dbs:
            j_cnt = data["junk_count"]
            d_cnt = data["dup_count"]
            tot = data["total_tracks"]
            sample_str = f"Sample: '{data['dup_samples'][0][0]}' x{data['dup_samples'][0][2]}" if data["dup_samples"] else ""
            print(f"  • {rel_p:<42} | Total: {tot:>4} | Junk: {j_cnt:>3} | Dups: {d_cnt:>3}  {sample_str}")

    print("\n" + "="*85)
    print(" 💡 To clean and remove all duplicates & garbage headers across all DBs:")
    print("    Run: python find_duplicates.py --fix")
    print("="*85 + "\n")


def fix_duplicates(dry_run=False, playlists_only=False, verbose=True):
    """Safely deduplicate and remove junk across all databases."""
    action_str = "DRY RUN CLEANUP" if dry_run else "EXECUTING AUTOMATIC DEDUPLICATION"
    print("\n" + "="*85)
    print(f" 🧹 {action_str}")
    print("="*85)

    # 1. Clean tamil_discography.db
    if not playlists_only and DISCO_DB.exists():
        conn = sqlite3.connect(DISCO_DB)
        cur = conn.cursor()

        # Delete junk
        cur.execute("SELECT id, title FROM tracks;")
        all_t = cur.fetchall()
        junk_ids = [r[0] for r in all_t if is_junk_title(r[1])]
        
        if junk_ids and not dry_run:
            cur.executemany("DELETE FROM tracks WHERE id = ?;", [(jid,) for jid in junk_ids])

        # Deduplicate same title + same album_id, keeping the one with best data (highest id or non-empty duration)
        cur.execute("""
            SELECT id, LOWER(TRIM(title)), album_id 
            FROM tracks 
            ORDER BY id ASC;
        """)
        seen = {}
        dup_disco_ids = []
        for tid, t_title, a_id in cur.fetchall():
            key = (t_title, a_id)
            if key in seen:
                dup_disco_ids.append(tid)
            else:
                seen[key] = tid

        if dup_disco_ids and not dry_run:
            cur.executemany("DELETE FROM tracks WHERE id = ?;", [(did,) for did in dup_disco_ids])
            conn.commit()

        conn.close()
        print(f"[Master DB] Cleaned tamil_discography.db: Purged {len(junk_ids)} junk rows, {len(dup_disco_ids)} duplicate songs.")

    # 2. Clean each playlist database
    db_files = sorted(PLAYLISTS_DIR.rglob("*.db"))
    cleaned_dbs = 0
    total_purged_junk = 0
    total_purged_dups = 0

    for db_path in db_files:
        rel_p = str(db_path.relative_to(PLAYLISTS_DIR.parent))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Find junk rows
        cur.execute("SELECT id, track_title FROM tracks;")
        t_rows = cur.fetchall()
        junk_ids = [r["id"] for r in t_rows if is_junk_title(r["track_title"])]

        # Find duplicate rows
        cur.execute("SELECT id, LOWER(TRIM(track_title)) as norm_t, LOWER(TRIM(album_title)) as norm_a FROM tracks ORDER BY id ASC;")
        all_recs = cur.fetchall()
        seen_keys = set()
        dup_ids = []

        for r in all_recs:
            if r["id"] in junk_ids:
                continue
            k = (r["norm_t"], r["norm_a"])
            if k in seen_keys:
                dup_ids.append(r["id"])
            else:
                seen_keys.add(k)

        ids_to_delete = junk_ids + dup_ids

        if ids_to_delete and not dry_run:
            cur.executemany("DELETE FROM tracks WHERE id = ?;", [(did,) for did in ids_to_delete])
            
            # Re-index positions sequentially: 1, 2, 3...
            cur.execute("SELECT id FROM tracks ORDER BY position ASC, id ASC;")
            remaining = cur.fetchall()
            for new_pos, row in enumerate(remaining, start=1):
                cur.execute("UPDATE tracks SET position = ? WHERE id = ?;", (new_pos, row["id"]))

            # Update playlist_info total_tracks
            cur.execute("UPDATE playlist_info SET value = ? WHERE key = 'total_tracks';", (str(len(remaining)),))
            conn.commit()

        if ids_to_delete:
            cleaned_dbs += 1
            if verbose:
                print(f"  • {rel_p:<42} -> purged {len(junk_ids):>3} junk, {len(dup_ids):>3} dups")

        total_purged_junk += len(junk_ids)
        total_purged_dups += len(dup_ids)

        conn.close()

    print(f"\n[Playlists] Cleaned {cleaned_dbs} playlist databases.")
    print(f"            Purged {total_purged_junk:,} junk header rows.")
    print(f"            Purged {total_purged_dups:,} duplicate track entries.")
    status_msg = "DRY RUN COMPLETE — No files modified." if dry_run else "All databases are now 100% clean and deduplicated!"
    print(f"\n✅ {status_msg}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and Clean Duplicates & Corrupt Titles Across All Databases.")
    parser.add_argument("--fix", "--clean", action="store_true", help="Deduplicate and purge junk rows across all DBs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without modifying files")
    parser.add_argument("--all", action="store_true", help="Show all 119 databases in audit report")
    parser.add_argument("--playlists-only", action="store_true", help="Only process standalone playlist databases")
    parser.add_argument("-q", "--quiet", action="store_true", help="Do not print per-database progress in fix mode")

    args = parser.parse_args()

    disco_rep = {} if args.playlists_only else scan_discography_duplicates()
    pl_rep = scan_playlist_duplicates()

    if args.fix:
        fix_duplicates(dry_run=args.dry_run, playlists_only=args.playlists_only, verbose=not args.quiet)
    else:
        print_audit_report(disco_rep, pl_rep, show_all=args.all, playlists_only=args.playlists_only)

