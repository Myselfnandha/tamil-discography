#!/usr/bin/env python3
"""
resolve_missing_tracks.py - Post-Import Audit & Missing Track Resolver for Spotify.

Audits transferred Spotify playlists against source CSV discography files,
identifies missing or failed tracks, performs multi-strategy search on Spotify,
and adds missing songs directly to the target playlists on Spotify using the
high-performance SpotifyNativeClient (200 OK, zero rate limits).
"""

import os
import sys
import time
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from spotify_native_client import SpotifyNativeClient, clean_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_DIR = BASE_DIR / "playlists" / "spotify_exports" / "csv"
RESOLVED_LOG = DATA_DIR / "resolved_tracks.json"
UNRESOLVED_LOG = DATA_DIR / "unresolved_tracks.json"


def audit_and_resolve(client: SpotifyNativeClient, target_playlist: Optional[str] = None):
    print("=" * 80)
    print(" 🔍 SPOTIFY PLAYLIST AUDIT & MISSING TRACK RESOLVER (NATIVE)")
    print("=" * 80)

    # 1. Map all local CSV files by Playlist Name
    all_csvs = sorted(list(CSV_DIR.glob("*.csv")))
    all_csvs = [f for f in all_csvs if not f.name.startswith("bulk_")]
    
    # Exclude parent files if chunked parts exist
    chunked_stems = {f.stem.rsplit('_part', 1)[0] for f in all_csvs if '_part' in f.stem}
    all_csvs = [f for f in all_csvs if f.stem not in chunked_stems]

    playlist_csv_map: Dict[str, List[Path]] = {}
    for csv_file in all_csvs:
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                first_row = next(reader)
                p_name = first_row.get("Playlist Name", "").strip()
                if p_name:
                    playlist_csv_map.setdefault(p_name, []).append(csv_file)
        except Exception:
            pass

    print(f"📊 Found {len(playlist_csv_map)} distinct local playlists across {len(all_csvs)} chunk files.")

    # 2. Fetch Spotify playlists grouped by clean name
    spotify_playlists = client.get_all_playlists()

    targets = sorted(list(playlist_csv_map.keys()))
    if target_playlist:
        targets = [t for t in targets if clean_text(target_playlist) in clean_text(t)]
        if not targets:
            print(f"❌ Playlist '{target_playlist}' not found locally.")
            return

    resolved_total = 0
    unresolved_total = 0
    resolved_history = []
    unresolved_history = []

    print(f"\n🚀 Starting Audit across {len(targets)} playlists...\n")

    for idx, p_name in enumerate(targets, 1):
        clean_p = clean_text(p_name)
        containers = spotify_playlists.get(clean_p, [])
        if not containers:
            print(f"[{idx}/{len(targets)}] ⚠️ Playlist '{p_name}' not found on Spotify. Skipping.")
            continue

        master_container = containers[0]
        p_uri = master_container["uri"]
        orig_name = master_container["name"]
        print(f"[{idx}/{len(targets)}] 🎵 Auditing: '{orig_name}' ({len(containers)} container(s))...")

        # Combine all tracks across all containers with this name
        current_tracks = []
        for c in containers:
            c_tracks = client.get_playlist_tracks(c["uri"])
            current_tracks.extend(c_tracks)

        current_set = {clean_text(t["name"]) for t in current_tracks}
        print(f"   Currently on Spotify: {len(current_tracks)} tracks total across {len(containers)} chunk(s)")

        # Read source tracks from local CSVs
        source_tracks = []
        for csv_file in playlist_csv_map[p_name]:
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        title = row.get("Track Name", "").strip()
                        artist = row.get("Artist Name", "").strip()
                        album = row.get("Album Name", "").strip()
                        if title:
                            source_tracks.append({"title": title, "artist": artist, "album": album})
            except Exception:
                pass

        # Identify missing tracks
        missing_candidates = []
        for t in source_tracks:
            ct = clean_text(t["title"])
            if ct and ct not in current_set:
                missing_candidates.append(t)

        if not missing_candidates:
            print(f"   ✅ 100% Complete! All {len(source_tracks)} source tracks are present in Spotify.")
            continue

        print(f"   ⚠️ Found {len(missing_candidates)} missing/unmatched tracks. Resolving via Spotify Search...")

        found_uris = []
        for mt in missing_candidates:
            uri = client.search_track(mt["title"], mt["artist"])
            if uri:
                found_uris.append(uri)
                resolved_total += 1
                resolved_history.append({"playlist": orig_name, "title": mt["title"], "uri": uri})
                print(f"      ✨ Found: '{mt['title']}' -> {uri}")
            else:
                unresolved_total += 1
                unresolved_history.append({"playlist": orig_name, "title": mt["title"], "artist": mt["artist"]})

        if found_uris:
            ok = client.add_tracks_to_playlist(p_uri, found_uris)
            if ok:
                print(f"   🎉 Added {len(found_uris)} resolved tracks to playlist '{orig_name}'!")
            else:
                print(f"   ❌ Failed to add tracks to playlist '{orig_name}'.")

    # Save audit logs
    try:
        with open(RESOLVED_LOG, "w", encoding="utf-8") as f:
            json.dump(resolved_history, f, indent=2)
        with open(UNRESOLVED_LOG, "w", encoding="utf-8") as f:
            json.dump(unresolved_history, f, indent=2)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print(f" 🏁 AUDIT COMPLETE! Total Resolved & Added: {resolved_total} | Truly Unavailable: {unresolved_total}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Audit Spotify playlists and resolve missing tracks.")
    parser.add_argument("--playlist", type=str, default=None, help="Specific playlist to audit")
    parser.add_argument("--all", action="store_true", default=False, help="Audit all playlists")
    args = parser.parse_args()

    client = SpotifyNativeClient()
    try:
        audit_and_resolve(client, target_playlist=args.playlist)
    finally:
        client.close()


if __name__ == "__main__":
    main()
