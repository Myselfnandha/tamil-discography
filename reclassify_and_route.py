#!/usr/bin/env python3
"""
reclassify_and_route.py - Intelligent Song-Level Category Classifier & Playlist Re-Router.

Audits high-impact theme playlists (Sad, Energetic, Hype, Inspiration, Chill)
to detect and relocate misconfigured tracks:
- Separates romantic duets and love songs erroneously filed under 'Sad' -> re-routes to 'Romantic Duets' / 'Love'.
- Separates soft acoustic/lullaby melodies erroneously filed under 'Energetic' / 'Hype' -> re-routes to 'Tamil Melody' / 'Chill'.
- Separates love duets from 'Inspiration' -> re-routes to 'Love'.

Powered by SpotifyNativeClient (200 OK, zero rate limits).
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

from spotify_native_client import SpotifyNativeClient, clean_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORT_FILE = DATA_DIR / "reclassification_report.json"

# Explicit grief / sorrow tokens that confirm a song IS genuinely sad
TRUE_SAD_TOKENS = {
    "sogam", "kanneer", "kannir", "pirivu", "maranam", "azhuvadhu", "vali", 
    "valikudhu", "thani", "thooram", "vidai", "theeyil", "azhugai", "thunbam",
    "parthen", "parthal", "maranthu", "theerkadha", "vilagi", "kanave"
}

# Explicit romance / love tokens that flag a song as LOVE / ROMANCE
ROMANCE_TOKENS = {
    "kadhal", "kaadhal", "anbe", "anbil", "uyire", "priya", "penne", "azhagi", 
    "unakkul", "kannazhaga", "vizhiyil", "malare", "vaseegara", "enrenrum", 
    "ennodu", "unale", "nenjukkul", "paarthu", "paravai", "sweet", "chellam",
    "kalyana", "roja", "un mela", "kadhaippoma", "bae", "un koodave", "kannaana",
    "innum", "adiye", "thalli pogathey", "maruvaarthai", "chellamma"
}

# Acoustic / gentle tokens that disqualify from Energetic/Hype
GENTLE_TOKENS = {
    "thalattu", "thaalattu", "aararo", "kanne", "urangu", "poovarasam", "thendral",
    "breeze", "kaatru", "mazhai", "nila", "nilavu", "poongatru", "chinna chinna",
    "vellai", "vidukathaiya", "thenral", "sendhoora", "malargale", "kannodu",
    "venmathi", "pesugiren", "kangal", "anbendra", "sangeetha"
}


def audit_and_reclassify_tracks(client: SpotifyNativeClient, execute: bool = False):
    print("=" * 80)
    print(" 🎼 INTELLIGENT CATEGORY AUDITOR & RECLASSIFIER (NATIVE)")
    print(f" Mode: {'⚡ EXECUTE (Moving tracks on Spotify)' if execute else '🔎 PREVIEW (Inspection only)'}")
    print("=" * 80)

    grouped = client.get_all_playlists()

    # Flat lookup mapping normalized clean name to primary container
    all_playlists = {clean_k: v[0] for clean_k, v in grouped.items()}

    def find_pl(pattern: str) -> Optional[Dict[str, str]]:
        for clean_n, pl in all_playlists.items():
            if re.search(pattern, clean_n, re.I):
                return pl
        return None

    sad_pl = find_pl(r"^(😢\s*)?sad$")
    energetic_pl = find_pl(r"^energetic$")
    hype_pl = find_pl(r"^(🔥\s*)?hype$")
    inspiration_pl = find_pl(r"^inspiration$")

    love_pl = find_pl(r"^(❤️\s*)?love$")
    romantic_duets_pl = find_pl(r"^romantic duets$") or find_pl(r"^love duets$") or love_pl
    chill_pl = find_pl(r"^(😎\s*)?chill$")
    melody_pl = find_pl(r"^tamil melody$") or chill_pl

    moves_plan = []

    # 1. Audit SAD Playlist
    if sad_pl:
        s_name = sad_pl["name"]
        s_uri = sad_pl["uri"]
        print(f"🔍 Auditing: '{s_name}' ({s_uri})...")
        tracks = client.get_playlist_tracks(s_uri)
        print(f"   Total tracks: {len(tracks)}")

        for t in tracks:
            title_lower = t["name"].lower()
            artists_str = t.get("artists", "").lower()
            
            has_grief = any(tok in title_lower for tok in TRUE_SAD_TOKENS)
            has_romance = any(tok in title_lower for tok in ROMANCE_TOKENS)
            is_duet = "," in artists_str or "&" in artists_str
            
            if (has_romance or (is_duet and "ninaithu" in title_lower)) and not has_grief:
                dest = romantic_duets_pl if is_duet else love_pl
                if dest:
                    moves_plan.append({
                        "track_name": t["name"],
                        "artists": t.get("artists", ""),
                        "uri": t["uri"],
                        "uid": t["uid"],
                        "source_name": s_name,
                        "source_uri": s_uri,
                        "dest_name": dest["name"],
                        "dest_uri": dest["uri"],
                        "reason": "Romantic theme/duet misclassified in Sad"
                    })

    # 2. Audit ENERGETIC & HYPE Playlists
    for fast_pl in [energetic_pl, hype_pl]:
        if not fast_pl:
            continue
        f_name = fast_pl["name"]
        f_uri = fast_pl["uri"]
        print(f"\n🔍 Auditing: '{f_name}' ({f_uri})...")
        tracks = client.get_playlist_tracks(f_uri)
        print(f"   Total tracks: {len(tracks)}")

        for t in tracks:
            title_lower = t["name"].lower()
            has_gentle = any(tok in title_lower for tok in GENTLE_TOKENS)
            if has_gentle:
                dest = melody_pl if melody_pl else chill_pl
                if dest:
                    moves_plan.append({
                        "track_name": t["name"],
                        "artists": t.get("artists", ""),
                        "uri": t["uri"],
                        "uid": t["uid"],
                        "source_name": f_name,
                        "source_uri": f_uri,
                        "dest_name": dest["name"],
                        "dest_uri": dest["uri"],
                        "reason": "Gentle acoustic/melody misclassified in Energetic/Hype"
                    })

    print(f"\n📊 Audit Complete: Identified {len(moves_plan)} misconfigured tracks to relocate.\n")

    for i, m in enumerate(moves_plan[:10], 1):
        print(f"[{i}] '{m['track_name']}' ({m['artists']})")
        print(f"     Move from: '{m['source_name']}' ──▶ '{m['dest_name']}'")
        print(f"     Reason: {m['reason']}")

    if execute and moves_plan:
        print(f"\n⚡ Executing relocations on Spotify...")
        # Group by (source_uri, dest_uri)
        route_batches: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
        for m in moves_plan:
            route_batches.setdefault((m["source_uri"], m["dest_uri"]), []).append(m)

        for (src_uri, dst_uri), batch in route_batches.items():
            uris_to_add = [m["uri"] for m in batch]
            uids_to_remove = [m["uid"] for m in batch]

            print(f"   ➕ Adding {len(uris_to_add)} tracks to destination: {dst_uri}...")
            client.add_tracks_to_playlist(dst_uri, uris_to_add)

            print(f"   🧹 Removing {len(uids_to_remove)} tracks from source: {src_uri}...")
            client.remove_tracks_from_playlist(src_uri, uids_to_remove)

        print("\n✅ Successfully relocated all misconfigured tracks!")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(moves_plan, f, indent=2)
    else:
        print("\n💡 Run with --execute to perform relocations on Spotify:")
        print("   python3 reclassify_and_route.py --execute")


def main():
    parser = argparse.ArgumentParser(description="Reclassify and route miscategorized tracks across Spotify playlists.")
    parser.add_argument("--execute", action="store_true", default=False, help="Perform the actual track relocations")
    args = parser.parse_args()

    client = SpotifyNativeClient()
    try:
        audit_and_reclassify_tracks(client, execute=args.execute)
    finally:
        client.close()


if __name__ == "__main__":
    main()
