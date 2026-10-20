#!/usr/bin/env python3
"""
export_spotify.py - High-Performance Spotify Playlist Import Generator.

Generates universal import-ready files (CSV, M3U8, TXT) from the standalone
SQLite playlist databases under /home/nandha/play/playlists.

Features:
- Standard CSV formatted for 1-click import into Soundiiz, TuneMyMusic, and Spotlistr.
- Extended M3U8 formatted for Spotify Desktop local playback and media players.
- Clean TXT tracklist for fast copy-pasting into web matchers (e.g. Spotlistr.com).
- Auto-chunking for playlists exceeding Spotify's hard limit of 10,000 tracks.
- Zero Spotify Developer API or Premium account restrictions.
"""

import os
import sys
import csv
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists"
EXPORTS_DIR = PLAYLISTS_DIR / "spotify_exports"

CSV_DIR = EXPORTS_DIR / "csv"
M3U_DIR = EXPORTS_DIR / "m3u8"
TXT_DIR = EXPORTS_DIR / "txt"

# Spotify hard limit per playlist is 10,000 tracks
SPOTIFY_PLAYLIST_HARD_LIMIT = 10000

# Top 32 Curated Signature Playlists
CURATED_SLUGS = [
    # Top 20 Artist Hits
    "ar_rahman_hits",
    "ilaiyaraaja_hits",
    "anirudh_hits",
    "harris_jayaraj_hits",
    "yuvan_shankar_raja_hits",
    "deva_hits",
    "vidyasagar_hits",
    "santhosh_narayanan_hits",
    "gv_prakash_hits",
    "d_imman_hits",
    "ms_viswanathan_hits",
    "kv_mahadevan_hits",
    "spb_hits",
    "kj_yesudas_hits",
    "hariharan_hits",
    "shankar_mahadevan_hits",
    "sid_sriram_hits",
    "s_janaki_hits",
    "ks_chithra_hits",
    "shreya_ghoshal_hits",
    # Top 12 Categorical & Signature Collections
    "all_time_hits",
    "love_duets",
    "romantic_duets",
    "tamil_melody",
    "gaana",
    "kuthu_dance",
    "mass_hero_bgm",
    "tamil_instrumental_bgm",
    "old_is_gold",
    "2000s_hits",
    "90s_classics",
    "latest_releases",
]


def discover_playlist_dbs() -> Dict[str, Path]:
    """Scan and index all standalone .db files under playlists/."""
    dbs = {}
    if not PLAYLISTS_DIR.exists():
        return dbs
    for p in sorted(PLAYLISTS_DIR.rglob("*.db")):
        slug = p.stem
        dbs[slug] = p
    return dbs


def parse_duration_to_seconds(dur_str: str) -> int:
    """Convert mm:ss or hh:mm:ss string to integer seconds."""
    if not dur_str:
        return -1
    parts = str(dur_str).strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return -1


def fetch_playlist_data(db_path: Path) -> Dict[str, Any]:
    """Read metadata and tracks from a single playlist database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT key, value FROM playlist_info;")
    info = {r["key"]: r["value"] for r in cur.fetchall()}

    cur.execute("""
        SELECT 
            position,
            track_title,
            album_title,
            year,
            composer,
            singers,
            lyricist,
            duration,
            track_type,
            spotify_query
        FROM tracks 
        ORDER BY position ASC;
    """)
    tracks = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "slug": info.get("slug", db_path.stem),
        "name": info.get("name", db_path.stem),
        "category": info.get("category", db_path.parent.name.upper()),
        "emoji": info.get("emoji", "🎵"),
        "description": info.get("description", ""),
        "tracks": tracks
    }


def export_single_playlist(pl_data: Dict[str, Any], max_chunk: int = SPOTIFY_PLAYLIST_HARD_LIMIT) -> List[Dict[str, str]]:
    """Export a playlist into CSV, M3U8, and TXT with auto-chunking for >10k tracks."""
    slug = pl_data["slug"]
    name = pl_data["name"]
    emoji = pl_data["emoji"]
    tracks = pl_data["tracks"]
    total = len(tracks)

    if total == 0:
        return []

    # Chunk tracks if exceeding Spotify's hard limit
    chunks = []
    if total > max_chunk:
        for i in range(0, total, max_chunk):
            part_num = (i // max_chunk) + 1
            total_parts = (total + max_chunk - 1) // max_chunk
            chunk_slug = f"{slug}_part{part_num}"
            chunk_name = f"{name} (Part {part_num} of {total_parts})"
            chunks.append((chunk_slug, chunk_name, tracks[i:i + max_chunk]))
    else:
        chunks.append((slug, name, tracks))

    generated_files = []

    for chunk_slug, chunk_name, chunk_tracks in chunks:
        # 1. Generate CSV (Soundiiz / TuneMyMusic optimized with Playlist Name)
        csv_file = CSV_DIR / f"{chunk_slug}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Universal Soundiiz / TuneMyMusic recognized headers
            writer.writerow([
                "Track Name",
                "Artist Name",
                "Album Name",
                "Playlist Name",
                "Year",
                "Duration",
                "Track Type",
                "Spotify Search Query"
            ])
            for t in chunk_tracks:
                artist = t.get("singers") or t.get("composer") or "Various Artists"
                writer.writerow([
                    t.get("track_title", ""),
                    artist,
                    t.get("album_title", ""),
                    name,  # Keep clean original playlist name so all chunks merge into one playlist
                    t.get("year") or "",
                    t.get("duration", ""),
                    t.get("track_type", "song"),
                    t.get("spotify_query", "")
                ])

        # 2. Generate Extended M3U8 (Spotify Desktop local / VLC / Media Players)
        m3u_file = M3U_DIR / f"{chunk_slug}.m3u8"
        with open(m3u_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:{chunk_name}\n")
            f.write(f"#DESCRIPTION:{pl_data.get('description', '')}\n\n")
            for t in chunk_tracks:
                dur_secs = parse_duration_to_seconds(t.get("duration", ""))
                artist = t.get("singers") or t.get("composer") or "Various Artists"
                title = t.get("track_title", "")
                album = t.get("album_title", "")
                yr = t.get("year") or ""
                f.write(f"#EXTINF:{dur_secs},{artist} - {title}\n")
                f.write(f"#ALBUM:{album} ({yr})\n")
                f.write(f"#SPOTIFY_QUERY:{t.get('spotify_query', '')}\n")
                f.write(f"{artist} - {title}.mp3\n\n")

        # 3. Generate Plain Text (Spotlistr / Text Matcher copy-paste)
        txt_file = TXT_DIR / f"{chunk_slug}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            for t in chunk_tracks:
                artist = t.get("singers") or t.get("composer") or "Various Artists"
                title = t.get("track_title", "")
                album = t.get("album_title", "")
                f.write(f"{title} - {artist} ({album})\n")

        generated_files.append({
            "chunk_slug": chunk_slug,
            "chunk_name": chunk_name,
            "track_count": len(chunk_tracks),
            "csv": str(csv_file),
            "m3u8": str(m3u_file),
            "txt": str(txt_file)
        })

    return generated_files


def generate_master_bulk_csv(selected_slugs: List[str], dbs: Dict[str, Path], bulk_filename: str):
    """Generate a single master bulk CSV containing all playlists grouped by Playlist Name."""
    bulk_dir = EXPORTS_DIR / "bulk"
    bulk_dir.mkdir(parents=True, exist_ok=True)
    bulk_path = bulk_dir / bulk_filename

    total_bulk_tracks = 0
    with open(bulk_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Track Name",
            "Artist Name",
            "Album Name",
            "Playlist Name",
            "Year",
            "Duration",
            "Track Type"
        ])

        for slug in selected_slugs:
            if slug not in dbs:
                continue
            pl_data = fetch_playlist_data(dbs[slug])
            pl_name = pl_data["name"]
            for t in pl_data["tracks"]:
                artist = t.get("singers") or t.get("composer") or "Various Artists"
                writer.writerow([
                    t.get("track_title", ""),
                    artist,
                    t.get("album_title", ""),
                    pl_name,
                    t.get("year") or "",
                    t.get("duration", ""),
                    t.get("track_type", "song")
                ])
                total_bulk_tracks += 1

    return bulk_path, total_bulk_tracks


def run_export(mode: str = "curated", target_slug: str = None, target_cat: str = None, max_tracks: int = SPOTIFY_PLAYLIST_HARD_LIMIT):
    """Execute playlist export according to specified criteria."""
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    M3U_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    dbs = discover_playlist_dbs()
    if not dbs:
        print(f"Error: No playlist databases found in {PLAYLISTS_DIR}!")
        return

    # Determine which playlists to export
    selected_slugs = []
    if target_slug:
        if target_slug in dbs:
            selected_slugs = [target_slug]
        else:
            matches = [s for s in dbs if target_slug.lower() in s.lower()]
            if matches:
                selected_slugs = matches
            else:
                print(f"Error: Playlist slug '{target_slug}' not found.")
                return
    elif target_cat:
        for s, path in dbs.items():
            if target_cat.lower() in path.parent.name.lower():
                selected_slugs.append(s)
        if not selected_slugs:
            print(f"Error: No playlists found in category matching '{target_cat}'.")
            return
    elif mode == "curated":
        for s in CURATED_SLUGS:
            if s in dbs:
                selected_slugs.append(s)
    elif mode == "all":
        selected_slugs = list(dbs.keys())

    print("=" * 80)
    print(" 🚀 SPOTIFY PLAYLIST IMPORT BUNDLE GENERATOR")
    print("=" * 80)
    print(f"Mode               : {mode.upper()}")
    print(f"Playlists Selected : {len(selected_slugs)}")
    print(f"Target Directory   : {EXPORTS_DIR}")
    print(f"Hard Limit Chunk   : {max_tracks:,} songs / playlist")
    print("-" * 80)

    total_exported_tracks = 0
    total_files_generated = 0

    for idx, s in enumerate(selected_slugs, 1):
        db_path = dbs[s]
        pl_data = fetch_playlist_data(db_path)
        chunks = export_single_playlist(pl_data, max_chunk=max_tracks)
        
        for c in chunks:
            total_exported_tracks += c["track_count"]
            total_files_generated += 3  # CSV, M3U8, TXT
            print(f" [{idx:03d}/{len(selected_slugs)}] {pl_data['emoji']} {c['chunk_name']:<42} -> {c['track_count']:>5} songs")

    # Generate Master Bulk CSV for 1-Click Multi-Playlist creation
    bulk_file, bulk_count = generate_master_bulk_csv(selected_slugs, dbs, f"bulk_{mode}_playlists.csv")

    print("=" * 80)
    print(" ✅ SPOTIFY IMPORT BUNDLES GENERATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Total Playlists Handled : {len(selected_slugs)}")
    print(f"Total Tracks Exported   : {total_exported_tracks:,}")
    print(f"Total Files Created     : {total_files_generated + 1} (CSV, M3U8, TXT + Master Bulk CSV)")
    print(f"Master Bulk CSV         : {bulk_file} ({bulk_count:,} tracks)")
    print(f"CSV Directory           : {CSV_DIR}")
    print(f"M3U8 Directory          : {M3U_DIR}")
    print(f"TXT Directory           : {TXT_DIR}")
    print("-" * 80)
    print(" 💡 HOW TO GENERATE BULK PLAYLISTS ON SPOTIFY (1-CLICK):")
    print(f"  1. Visit https://tunemymusic.com -> Click 'Upload File'")
    print(f"  2. Select the Master Bulk CSV: {bulk_file.name} (from playlists/spotify_exports/bulk/)")
    print(f"  3. In the field mapping screen:")
    print(f"     - Song name field      : 'Track Name'")
    print(f"     - Artist name field    : 'Artist Name'")
    print(f"     - Separate playlists by: 'Playlist Name'  <-- (This creates ALL playlists in bulk!)")
    print(f"  4. Destination: 'Spotify' -> Click Start Transfer!")
    print(f"     TuneMyMusic will create every single playlist on your Spotify in one single pass!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Tamil Discography playlists to Spotify import bundles.")
    parser.add_argument("--curated", action="store_true", default=False, help="Export curated top 32 signature playlists (default)")
    parser.add_argument("--all", action="store_true", default=False, help="Export all 139 playlist databases")
    parser.add_argument("--slug", type=str, default=None, help="Export a specific playlist by slug (e.g. anirudh_hits, love_duets)")
    parser.add_argument("--category", type=str, default=None, help="Export all playlists in a specific category (e.g. artist, mood, tamil)")
    parser.add_argument("--max-tracks", type=int, default=SPOTIFY_PLAYLIST_HARD_LIMIT, help="Max tracks per playlist before auto-chunking (default: 10000)")

    args = parser.parse_args()

    # Determine mode
    if args.all:
        mode = "all"
    elif args.slug:
        mode = "slug"
    elif args.category:
        mode = "category"
    else:
        mode = "curated"

    run_export(mode=mode, target_slug=args.slug, target_cat=args.category, max_tracks=args.max_tracks)
