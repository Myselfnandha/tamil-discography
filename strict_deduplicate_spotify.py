#!/usr/bin/env python3
"""
strict_deduplicate_spotify.py - Strict Movie-Original Spotify Deduplicator.

Strictly deduplicates tracks in Spotify playlists by identifying duplicate titles,
alternate takes, remasters, compilations, and re-issues, preserving ONLY the authentic
original movie soundtrack version (earliest release year / original OST release).
Powered by SpotifyNativeClient (200 OK, zero rate limits).
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from spotify_native_client import SpotifyNativeClient, clean_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "deduplicated_tracks_log.json"


def clean_core_title(title: str) -> str:
    """
    Normalizes track title to its core melodic/film identity.
    Removes qualifiers like (From "..."), (Male Version), (Female), (Duet), (Sad), (Reprise), Remaster, etc.
    """
    if not title:
        return ""
    t = title.lower()

    # Remove (From "Movie") or From "Movie"
    t = re.sub(r'\(from\s+["\'].*?["\']\)', '', t)
    t = re.sub(r'from\s+["\'].*?["\']', '', t)
    # Remove common alternate qualifiers: (male), (female), (duet), (sad), (reprise), (bit), (version 1), etc.
    t = re.sub(r'\b(male|female|duet|sad|reprise|bit|theme|version\s*\d*|part\s*\d*|title\s*track)\b', '', t)
    # Remove parentheticals
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)
    # Normalize duplicate consecutive letters at word ends (e.g. 'ninaithuu' -> 'ninaithu')
    t = re.sub(r'(.)\1+$', r'\1', t.strip())
    # Strip non-alphanumeric
    t = re.sub(r'[^\w\s]', ' ', t)
    # Reduce whitespace
    tokens = t.split()
    return " ".join(tokens)


def score_track_originality(t: Dict[str, Any]) -> Tuple[int, int]:
    """
    Ranks tracks so the authentic movie original has the HIGHEST score.
    Higher score wins.
    Tuple: (year_priority, album_penalty)
    """
    year = t.get("year", 2099)
    # We prefer the EARLIEER release year (the original movie release, not a 2026 re-issue or compilation)
    year_score = -year  # e.g., -2004 > -2026

    # Album authenticity: penalty if album title contains words like 'part 2', 'remix', 'compilation', '&quot;'
    alb = t.get("album", "").lower()
    penalty = 0
    if any(w in alb for w in ["remix", "cover", "tribute", "lofi", "dj", "mashup", "reprise"]):
        penalty -= 100
    if "&quot;" in t.get("name", "") or "&amp;" in t.get("name", ""):
        penalty -= 50
    if "2" in alb and "vol" not in alb:
        penalty -= 20
    if "compilation" in alb or "best of" in alb or "hits" in alb:
        penalty -= 30

    return (year_score, penalty)


def deduplicate_playlist(client: SpotifyNativeClient, playlist_info: Dict[str, Any], execute: bool = False) -> Dict[str, Any]:
    p_uri = playlist_info["uri"]
    p_name = playlist_info["name"]
    print(f"\n🎵 Checking Playlist: '{p_name}' ({p_uri})...")

    tracks = client.get_playlist_tracks(p_uri)
    if not tracks:
        print("   Empty playlist.")
        return {"playlist": p_name, "removed": 0, "kept": 0}

    # Group by core title
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for t in tracks:
        core = clean_core_title(t["name"])
        if not core:
            core = t["name"].lower()
        groups.setdefault(core, []).append(t)

    to_remove_uids: List[str] = []
    removed_summary = []

    for core, t_list in groups.items():
        if len(t_list) > 1:
            # Sort by originality score descending (winner first)
            ranked = sorted(t_list, key=score_track_originality, reverse=True)
            original_winner = ranked[0]
            duplicates = ranked[1:]

            # Mark duplicates for removal by item UID
            for d in duplicates:
                to_remove_uids.append(d["uid"])
                removed_summary.append({
                    "winner": f"{original_winner['name']} [{original_winner.get('album', '')} ({original_winner.get('year', '')})]",
                    "removed": f"{d['name']} [{d.get('album', '')} ({d.get('year', '')})]"
                })

    # Also deduplicate any exact URI duplicates that might have slipped past core title
    seen_uris = set()
    exact_dup_uids = []
    for t in tracks:
        if t["uri"] in seen_uris and t["uid"] not in to_remove_uids:
            exact_dup_uids.append(t["uid"])
        else:
            seen_uris.add(t["uri"])

    all_uids_to_remove = to_remove_uids + exact_dup_uids
    # Ensure uniqueness
    all_uids_to_remove = list(dict.fromkeys(all_uids_to_remove))

    print(f"   📊 Total Tracks: {len(tracks)}")
    print(f"   🧹 Duplicate/Secondary Tracks to Purge: {len(all_uids_to_remove)}")
    print(f"   🎯 Authentic Movie Originals Kept: {len(tracks) - len(all_uids_to_remove)}")

    if removed_summary:
        print("   Sample Purges:")
        for s in removed_summary[:3]:
            print(f"      🗑️ [DROP] {s['removed']}")
            print(f"         └─▶ [KEEP ORIGINAL] {s['winner']}")

    if execute and all_uids_to_remove:
        print(f"   ⚡ Purging {len(all_uids_to_remove)} duplicate items from Spotify...")
        ok = client.remove_tracks_from_playlist(p_uri, all_uids_to_remove)
        if ok:
            print("   ✅ Successfully purged duplicates!")
        else:
            print("   ⚠️ Some items could not be removed.")

    return {
        "playlist": p_name,
        "uri": p_uri,
        "initial_total": len(tracks),
        "removed_count": len(all_uids_to_remove),
        "final_total": len(tracks) - len(all_uids_to_remove)
    }


def run_strict_deduplication(client: Optional[SpotifyNativeClient] = None, playlist: Optional[str] = None, execute: bool = False):
    print("=" * 80)
    print(" 🎬 STRICT MOVIE-ORIGINAL SPOTIFY DEDUPLICATOR (NATIVE)")
    print(f" Mode: {'⚡ EXECUTE (Permanently removing duplicates)' if execute else '🔎 DRY RUN (Inspection only)'}")
    print("=" * 80)

    should_close = False
    if client is None:
        client = SpotifyNativeClient()
        should_close = True

    try:
        grouped = client.get_all_playlists()

        all_flat = []
        for pl_list in grouped.values():
            all_flat.extend(pl_list)

        targets = all_flat
        if playlist:
            cn = clean_text(playlist)
            targets = [p for p in targets if cn in clean_text(p["name"])]
            if not targets:
                print(f"❌ Playlist '{playlist}' not found on Spotify.")
                return []

        print(f"🚀 Processing {len(targets)} playlist(s)...\n")

        reports = []
        for p in targets:
            rep = deduplicate_playlist(client, p, execute=execute)
            reports.append(rep)

        if execute:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(reports, f, indent=2)
            print(f"\n🎉 Deduplication complete! Audit report saved to {LOG_FILE}")
        else:
            print("\n💡 Run with --execute to perform deletions:")
            print("   python3 strict_deduplicate_spotify.py --all --execute")
        return reports
    finally:
        if should_close:
            client.close()


def main():
    parser = argparse.ArgumentParser(description="Strict Movie-Original Deduplication for Spotify Playlists.")
    parser.add_argument("--playlist", type=str, default=None, help="Specific playlist to deduplicate")
    parser.add_argument("--all", action="store_true", default=False, help="Deduplicate all playlists")
    parser.add_argument("--execute", action="store_true", default=False, help="Perform the actual deletions on Spotify")
    args = parser.parse_args()

    run_strict_deduplication(playlist=args.playlist, execute=args.execute)


if __name__ == "__main__":
    main()
