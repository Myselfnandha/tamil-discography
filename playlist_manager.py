#!/usr/bin/env python3
"""
playlist_manager.py - CLI tool to inspect, search, and manage all 73 individual playlist databases.
"""

import sys
import os
import argparse
import sqlite3
import json
from pathlib import Path

PLAYLISTS_DIR = Path(__file__).resolve().parent / "playlists"

def find_all_playlist_dbs():
    """Discover all .db files under playlists/ directory without collisions."""
    if not PLAYLISTS_DIR.exists():
        return {}
    
    dbs = {}
    for db_file in sorted(PLAYLISTS_DIR.rglob("*.db")):
        key = f"{db_file.parent.name}/{db_file.stem}"
        dbs[key] = db_file
    return dbs


def get_playlist_info(db_path: Path):
    """Retrieve playlist metadata and track count from a single DB file."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM playlist_info;")
        meta = {r["key"]: r["value"] for r in cur.fetchall()}
        
        cur.execute("SELECT COUNT(*) as cnt FROM tracks;")
        cnt = cur.fetchone()["cnt"]
        conn.close()
        meta["track_count"] = cnt
        return meta
    except Exception as e:
        return {"name": db_path.stem, "slug": db_path.stem, "track_count": 0, "error": str(e)}


def list_playlists(category_filter=None):
    """Display clean summary list of all 73 playlists."""
    dbs = find_all_playlist_dbs()
    if not dbs:
        print("\nNo playlist databases found in 'playlists/'. Run 'python build_playlists.py' first.\n")
        return

    print("\n" + "="*85)
    print(f" 🎵 TAMIL DISCOGRAPHY - {len(dbs)} STANDALONE PLAYLIST DATABASES")
    print("="*85)
    
    grouped = {}
    total_tracks_all = 0

    for slug, path in dbs.items():
        meta = get_playlist_info(path)
        cat = meta.get("category", path.parent.name.upper())
        if category_filter and category_filter.lower() not in cat.lower():
            continue
        grouped.setdefault(cat, []).append((meta, path))
        total_tracks_all += meta.get("track_count", 0)

    idx = 1
    for cat, items in grouped.items():
        print(f"\n📁 {cat.upper()} ({len(items)} Playlists)")
        print("-" * 85)
        for meta, path in items:
            emoji = meta.get("emoji", "🎶")
            name = meta.get("name", meta.get("slug"))
            slug = meta.get("slug")
            cnt = meta.get("track_count", 0)
            rel_file = path.relative_to(PLAYLISTS_DIR.parent)
            print(f"  {idx:02d}. {emoji} {name:<32} [{slug}] -> {cnt:>4} songs ({rel_file})")
            idx += 1

    print("\n" + "="*85)
    print(f"Total Playlists: {idx - 1} | Total Tracks Across All: {total_tracks_all:,}")
    print("="*85 + "\n")


def show_playlist(slug_or_name, limit=25):
    """Inspect tracks in a specific playlist database."""
    dbs = find_all_playlist_dbs()
    target_path = None

    for slug, path in dbs.items():
        if slug.lower() == slug_or_name.lower() or slug_or_name.lower() in slug.lower():
            target_path = path
            break

    if not target_path:
        print(f"\nPlaylist '{slug_or_name}' not found. Run 'python playlist_manager.py --list' to see slugs.\n")
        return

    meta = get_playlist_info(target_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT position, track_title, album_title, year, composer, singers, duration, match_reason FROM tracks ORDER BY position ASC LIMIT ?;", (limit,))
    tracks = cur.fetchall()
    conn.close()

    print("\n" + "="*85)
    print(f" {meta.get('emoji', '🎶')} {meta.get('name')} [{meta.get('slug')}]")
    print("="*85)
    print(f"Category    : {meta.get('category')}")
    print(f"Description : {meta.get('description')}")
    print(f"Database    : {target_path.relative_to(PLAYLISTS_DIR.parent)}")
    print(f"Total Songs : {meta.get('track_count')} (Showing first {min(limit, len(tracks))})")
    print("-" * 85)

    for t in tracks:
        pos = t["position"]
        title = t["track_title"]
        movie = t["album_title"]
        yr = t["year"] or "Unknown"
        comp = t["composer"] or "Unknown"
        singers = t["singers"] or "Unknown"
        dur = t["duration"] or ""
        dur_str = f" [{dur}]" if dur else ""
        print(f"{pos:03d}. {title} — {movie} ({yr}){dur_str}")
        print(f"     Composer: {comp[:35]} | Singers: {singers[:40]}")
        if t["match_reason"]:
            print(f"     Tag/Reason: {t['match_reason']}")
        print()

    print("="*85 + "\n")


def search_all_playlists(query, limit=20):
    """Search for a track, movie, or artist across all 73 playlist databases."""
    dbs = find_all_playlist_dbs()
    print(f"\n🔍 Searching across all 73 playlist databases for '{query}'...\n")
    
    matches = []
    for slug, path in dbs.items():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT track_title, album_title, year, composer, singers, position 
            FROM tracks 
            WHERE track_title LIKE ? OR album_title LIKE ? OR composer LIKE ? OR singers LIKE ?
            LIMIT 5;
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
        rows = cur.fetchall()
        for r in rows:
            matches.append((slug, dict(r)))
        conn.close()
        if len(matches) >= limit:
            break

    if not matches:
        print(f"No tracks found matching '{query}'.\n")
        return

    print("="*85)
    print(f" Found {len(matches)} matching entries:")
    print("="*85)
    for slug, r in matches[:limit]:
        print(f"[{slug}] #{r['position']} {r['track_title']} — {r['album_title']} ({r['year']})")
        print(f"       Composer: {r['composer']} | Singers: {r['singers']}")
    print("="*85 + "\n")


def export_playlist(slug_or_name, fmt="json"):
    """Export a playlist to JSON or M3U."""
    dbs = find_all_playlist_dbs()
    target_path = None
    for slug, path in dbs.items():
        if slug.lower() == slug_or_name.lower():
            target_path = path
            break

    if not target_path:
        print(f"Playlist '{slug_or_name}' not found.")
        return

    meta = get_playlist_info(target_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT position, track_title, album_title, year, composer, singers, duration, spotify_query FROM tracks ORDER BY position ASC;")
    tracks = [dict(r) for r in cur.fetchall()]
    conn.close()

    export_dir = target_path.parent / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "m3u":
        out_file = export_dir / f"{meta['slug']}.m3u"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#PLAYLIST:{meta.get('name')}\n")
            for t in tracks:
                f.write(f"#EXTINF:-1,{t['track_title']} - {t['album_title']} ({t['year']})\n")
                f.write(f"#SPOTIFY:{t['spotify_query']}\n\n")
    else:
        out_file = export_dir / f"{meta['slug']}.json"
        payload = {
            "playlist_info": meta,
            "tracks": tracks
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Exported {len(tracks)} tracks to: {out_file}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage 73 Individual Tamil Playlist SQLite Databases.")
    parser.add_argument("--list", action="store_true", help="List all 73 playlists grouped by category")
    parser.add_argument("--category", type=str, help="Filter list by category (e.g. mood, genre, activity)")
    parser.add_argument("--show", type=str, help="Show tracks inside a playlist by slug or name")
    parser.add_argument("--limit", type=int, default=25, help="Number of tracks to show (default: 25)")
    parser.add_argument("--search", type=str, help="Search for songs across all 73 databases")
    parser.add_argument("--export", type=str, help="Export a playlist by slug")
    parser.add_argument("--format", choices=["json", "m3u"], default="json", help="Export format (json or m3u)")

    args = parser.parse_args()

    if args.list or (len(sys.argv) == 1):
        list_playlists(args.category)
    elif args.show:
        show_playlist(args.show, args.limit)
    elif args.search:
        search_all_playlists(args.search)
    elif args.export:
        export_playlist(args.export, args.format)
    else:
        parser.print_help()
