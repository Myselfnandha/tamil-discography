#!/usr/bin/env python3
"""
audit_and_clean_spotify_collisions.py - Audit and purge scraper collisions from live Spotify playlists.

Scans:
1. Era Folder playlists (Golden Era, Old Is Gold, 90s Classics)
2. Tamil Folder playlists (Ilaiyaraaja Classics, etc.)
3. Artist Folder playlists (Ilaiyaraaja, MSV, KVM, Deva, etc.)

Detects and purges:
- Modern songs collided into vintage playlists (e.g. "Pathala Pathala", "Scene Ah Scene Ah", "Yelelo", "Kurumba", "Iragai Poley", etc.)
- Any track with release year or artist violating era boundaries.
- Reports complete inventory of purged collided tracks.
"""

import sys
import time
import json
import sqlite3
from pathlib import Path
from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import get_folder_contents, FOLDER_DEFINITIONS

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists"

# Collided modern songs that should NEVER appear in vintage playlists
COLLISION_TRACK_TITLES = {
    "pathala pathala", "scene ah scene ah", "yelelo", "kurumba", "iragai poley",
    "idhuvum kadandhu pogum", "aaru padai", "prabalamagavey", "kandaa vara sollunga",
    "thattaan thattaan", "yen aalu manjanathi", "uttradheenga yeppov", "kannula kaasa kattappa"
}

# Modern artists who should NEVER appear in Golden Era or Old Is Gold
MODERN_ARTISTS_PRE_1990 = [
    "anirudh", "santhosh narayanan", "hiphop tamizha", "sam c.s.", "justin prabhakaran",
    "sid sriram", "pradeep kumar", "sean roldan", "leon james", "ghibran", "d. imman"
]

def audit_and_clean():
    client = SpotifyNativeClient()
    print("=" * 80)
    print(" 🧹 SPOTIFY LIVE PLAYLIST SCRAPER COLLISION AUDITOR & REMEDIATOR")
    print("=" * 80)

    # 1. Fetch playlists in Era, Tamil, and Artist folders
    folders_to_check = ["era", "tamil", "artist"]
    total_scanned = 0
    total_collided_purged = 0
    remediation_log = []

    for folder_key in folders_to_check:
        defn = FOLDER_DEFINITIONS[folder_key]
        print(f"\n📂 Inspecting Folder: [{defn['display_name']}]")
        playlists = get_folder_contents(client, defn["folder_uri"])
        print(f"   Found {len(playlists)} playlists in folder.")

        for p in playlists:
            p_name = p["name"]
            p_uri = p["uri"]
            clean_pname = clean_text(p_name)
            total_scanned += 1

            import re
            is_golden_era = "golden era" in clean_pname
            is_old_is_gold = "old is gold" in clean_pname
            is_90s = "90s" in clean_pname
            is_vintage_era = is_golden_era or is_old_is_gold
            is_ilaiyaraaja_classic = "ilaiyaraaja" in clean_pname
            is_msv = "viswanathan" in clean_pname
            is_kvm = "mahadevan" in clean_pname
            is_deva = bool(re.search(r'\bdeva\b', clean_pname))

            if not (is_vintage_era or is_90s or is_ilaiyaraaja_classic or is_msv or is_kvm or is_deva):
                continue

            print(f"   🎵 Scanning '{p_name}' ({p_uri})...", flush=True)
            # Fetch tracks
            tracks = client.get_playlist_tracks(p_uri)
            if not tracks:
                print(f"      (0 tracks found)", flush=True)
                continue

            uids_to_remove = []
            collided_details = []

            for t in tracks:
                t_name_clean = clean_text(t["name"])
                t_artists_clean = clean_text(t["artists"])
                t_year = t["year"]
                uid = t["uid"]

                reason = None

                # 1. Direct collided title match in vintage / classic playlists
                if (is_vintage_era or is_90s or is_ilaiyaraaja_classic or is_msv or is_kvm):
                    for ct in COLLISION_TRACK_TITLES:
                        if ct in t_name_clean:
                            reason = f"Collided Modern Title: '{t['name']}'"
                            break

                # 2. Modern artist in pre-1990 vintage playlists
                if not reason and is_vintage_era:
                    for ma in MODERN_ARTISTS_PRE_1990:
                        if ma in t_artists_clean:
                            reason = f"Modern Artist in Vintage Playlist: '{t['artists']}' ({t['name']})"
                            break

                # 3. Year violation in Golden Era (1960-1979)
                if not reason and is_golden_era and t_year != 2099 and t_year > 1980:
                    # Check if artist is also modern
                    if any(ma in t_artists_clean for ma in MODERN_ARTISTS_PRE_1990) or t_year >= 2000:
                        reason = f"Post-1980 track in Golden Era: '{t['name']}' ({t_year})"

                # 4. Year violation in Old Is Gold (1960-1989)
                if not reason and is_old_is_gold and t_year != 2099 and t_year > 1990:
                    if any(ma in t_artists_clean for ma in MODERN_ARTISTS_PRE_1990) or t_year >= 2000:
                        reason = f"Post-1990 track in Old Is Gold: '{t['name']}' ({t_year})"

                if reason:
                    uids_to_remove.append(uid)
                    collided_details.append({
                        "name": t["name"],
                        "artists": t["artists"],
                        "year": t_year,
                        "reason": reason
                    })

            if uids_to_remove:
                print(f"   ⚠️ Playlist '{p_name}': Found {len(uids_to_remove)} collided tracks!", flush=True)
                for cd in collided_details:
                    print(f"      - {cd['reason']} [{cd['artists']} - {cd['year']}]", flush=True)

                # Remove from Spotify
                success = client.remove_tracks_from_playlist(p_uri, uids_to_remove)
                if success:
                    print(f"      ✅ Successfully purged {len(uids_to_remove)} collided tracks from '{p_name}'.", flush=True)
                    total_collided_purged += len(uids_to_remove)
                    remediation_log.append({
                        "playlist": p_name,
                        "uri": p_uri,
                        "purged_count": len(uids_to_remove),
                        "details": collided_details
                    })
                else:
                    print(f"      ❌ Failed to purge collided tracks from '{p_name}'.", flush=True)
            else:
                print(f"      ✨ Clean! (0 collided tracks)", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(f" 🎉 AUDIT COMPLETE: Scanned targeted Spotify playlists.", flush=True)
    print(f" 🗑️ Total Collided Tracks Purged: {total_collided_purged}", flush=True)
    print("=" * 80, flush=True)

    # Save log
    log_path = BASE_DIR / "data" / "spotify_scraper_collision_cleanup.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(remediation_log, f, indent=2)
    print(f"Remediation log saved to {log_path}", flush=True)

    client.close()

if __name__ == "__main__":
    audit_and_clean()
