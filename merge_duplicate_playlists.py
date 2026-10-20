#!/usr/bin/env python3
"""
merge_duplicate_playlists.py - Spotify Duplicate Playlist Merger & Deduplicator.

Consolidates multi-chunk Spotify playlists that share the exact same name
(e.g., multiple "Old Is Gold", "Personal Favorites", "2000s Hits" playlists created by chunked imports)
into a single master playlist per title, and deletes the redundant duplicate containers.
Powered by SpotifyNativeClient (200 OK, zero rate limits).
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from spotify_native_client import SpotifyNativeClient, clean_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "merged_playlists_log.json"


def run_merge(execute: bool = False, target_name: Optional[str] = None, client: Optional[SpotifyNativeClient] = None):
    print("=" * 80)
    print(" 🔄 SPOTIFY PLAYLIST MERGER & DEDUPLICATOR (NATIVE)")
    print(f" Mode: {'⚡ EXECUTE (Merging & Deleting duplicates)' if execute else '🔎 DRY RUN (Inspection only)'}")
    print("=" * 80)

    should_close = False
    if client is None:
        client = SpotifyNativeClient()
        should_close = True
    try:
        grouped = client.get_all_playlists()

        duplicate_groups = {k: v for k, v in grouped.items() if len(v) > 1}

        if target_name:
            cn = clean_text(target_name)
            duplicate_groups = {k: v for k, v in duplicate_groups.items() if cn in k}

        print(f"\n📊 Summary: Found {len(duplicate_groups)} playlist titles with duplicate chunks.\n")

        if not duplicate_groups:
            print("🎉 No duplicate playlists found!")
            return

        total_chunks_to_remove = sum(len(v) - 1 for v in duplicate_groups.values())
        print(f"Total redundant playlist containers to merge & clean: {total_chunks_to_remove}\n")

        merge_log = []

        for idx, (clean_n, pl_list) in enumerate(duplicate_groups.items(), 1):
            orig_name = pl_list[0]["name"]
            print(f"[{idx}/{len(duplicate_groups)}] 📁 '{orig_name}' ({len(pl_list)} duplicate parts):")
            for i, p in enumerate(pl_list, 1):
                print(f"      Part {i}: URI {p['uri']}")

            if not execute:
                continue

            try:
                # Designate first container as master
                master = pl_list[0]
                duplicates = pl_list[1:]

                print(f"   👉 Master Destination: {master['uri']}")

                # Fetch existing track URIs in master
                master_tracks = client.get_playlist_tracks(master["uri"])
                master_uris = {t["uri"] for t in master_tracks}
                print(f"      Current Master tracks: {len(master_uris)}")

                for dup in duplicates:
                    dup_tracks = client.get_playlist_tracks(dup["uri"])
                    dup_uris = [t["uri"] for t in dup_tracks]
                    new_uris = [u for u in dup_uris if u not in master_uris]

                    if new_uris:
                        print(f"      ➕ Adding {len(new_uris)} songs from duplicate container to Master...")
                        ok_add = client.add_tracks_to_playlist(master["uri"], new_uris)
                        if ok_add:
                            master_uris.update(new_uris)
                        else:
                            print(f"      ❌ Failed to append tracks from {dup['uri']}. Skipping deletion.")
                            continue

                    # Delete redundant container
                    print(f"      🗑️ Removing duplicate playlist container {dup['uri']}...")
                    try:
                        ok_del = client.delete_playlist(dup["uri"])
                        if ok_del:
                            merge_log.append({
                                "playlist_name": orig_name,
                                "master_uri": master["uri"],
                                "deleted_uri": dup["uri"],
                                "tracks_merged": len(new_uris)
                            })
                        else:
                            print(f"      ⚠️ Failed to delete container {dup['uri']}, continuing...")
                    except Exception as del_err:
                        print(f"      ⚠️ Exception deleting {dup['uri']}: {del_err}, continuing...")

                print(f"   ✅ Cleaned up '{orig_name}'! Consolidated into single master.\n")
            except Exception as group_err:
                print(f"   ⚠️ Error consolidating '{orig_name}': {group_err}. Continuing to next playlist.\n")

        if execute:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(merge_log, f, indent=2)
            print(f"🎉 Merge Complete! Audit log saved to {LOG_FILE}")
        else:
            print("\n💡 Run with --execute to merge all tracks into master playlists and delete duplicate entries:")
            print("   python3 merge_duplicate_playlists.py --execute")
    finally:
        if should_close:
            client.close()


def main():
    parser = argparse.ArgumentParser(description="Merge duplicate Spotify playlists created from chunked CSV uploads.")
    parser.add_argument("--execute", action="store_true", default=False, help="Perform the actual merge and deletion")
    parser.add_argument("--name", type=str, default=None, help="Filter by specific playlist name")
    args = parser.parse_args()

    run_merge(execute=args.execute, target_name=args.name)


if __name__ == "__main__":
    main()
