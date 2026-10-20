#!/usr/bin/env python3
"""
purge_duplicate_containers.py - Deletes Redundant Duplicate Playlist Containers via Spotify Web UI.

All tracks across all parts were already merged into the designated Master container.
This script purges the remaining empty/duplicate containers (e.g., redundant "Trended & Trending Songs"
parts 2..11) so each of the 136 playlists appears as a single clean master playlist in your Spotify Library.
"""

import sys
import time
import json
import argparse
from pathlib import Path
from spotify_native_client import SpotifyNativeClient, clean_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "purged_containers_log.json"


def main():
    print("=" * 80)
    print(" 🗑️ PURGE REDUNDANT DUPLICATE PLAYLIST CONTAINERS")
    print("=" * 80)

    client = SpotifyNativeClient()

    try:
        grouped = client.get_all_playlists()

        duplicate_groups = {k: v for k, v in grouped.items() if len(v) > 1}
        total_redundant = sum(len(v) - 1 for v in duplicate_groups.values())

        print(f"\n📊 Summary: Found {len(duplicate_groups)} titles with duplicate containers.")
        print(f"Total redundant containers to purge: {total_redundant}\n")

        if total_redundant == 0:
            print("🎉 No duplicate containers found! Your library is already 100% clean.")
            return

        deleted_records = []
        count = 0

        for group_idx, (clean_n, pl_list) in enumerate(duplicate_groups.items(), 1):
            master = pl_list[0]
            duplicates = pl_list[1:]
            name = master["name"]

            print(f"[{group_idx}/{len(duplicate_groups)}] 📁 '{name}' ({len(pl_list)} containers total):")
            print(f"   👑 Master: {master['uri']}")

            for dup_idx, dup in enumerate(duplicates, 1):
                count += 1
                print(f"   [{count}/{total_redundant}] 🗑️ Deleting duplicate container: {dup['uri']}...", end="", flush=True)
                ok = client.delete_playlist(dup["uri"])
                if ok:
                    print(" ✅ DELETED!")
                    deleted_records.append({
                        "name": name,
                        "master_uri": master["uri"],
                        "deleted_uri": dup["uri"]
                    })
                else:
                    print(" ⚠️ FAILED (Skipping)")

        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(deleted_records, f, indent=2)

        print("\n" + "=" * 80)
        print(f" 🏁 COMPLETED! Successfully purged {len(deleted_records)} redundant containers.")
        print(f" Audit log saved to: {LOG_FILE}")
        print("=" * 80)

    finally:
        client.close()


if __name__ == "__main__":
    main()
