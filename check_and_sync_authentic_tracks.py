#!/usr/bin/env python3
"""
check_and_sync_authentic_tracks.py - Verify presence of authentic vintage tracks on Spotify
and sync them if missing.
"""

import sys
from spotify_native_client import SpotifyNativeClient, clean_text

OLD_IS_GOLD_URI = "spotify:playlist:2xhQNTJwc3C4tRP45WNEkP"
ILAIYARAAJA_CLASSICS_URI = "spotify:playlist:1tZJeDPr8VJFYDWmzaIDeA"

KEY_AUTHENTIC_VINTAGE_TRACKS = [
    {"title": "Vikram Vikram", "movie": "Vikram", "year": 1986, "artist": "Kamal Haasan, S. Janaki, Ilaiyaraaja"},
    {"title": "Penn Maaney", "movie": "Naan Sigappu Manithan", "year": 1985, "artist": "S. P. Balasubrahmanyam, S. Janaki, Ilaiyaraaja"},
    {"title": "Kanmaniye Pesu", "movie": "Kaakki Sattai", "year": 1985, "artist": "S. P. Balasubrahmanyam, S. Janaki, Ilaiyaraaja"},
    {"title": "Namma Singaari Saraku", "movie": "Kaakki Sattai", "year": 1985, "artist": "S. P. Balasubrahmanyam, Ilaiyaraaja"},
    {"title": "Ammaa Ammaa", "movie": "Maaveeran", "year": 1986, "artist": "Malaysia Vasudevan, Ilaiyaraaja"},
    {"title": "Namma Ooru Singari", "movie": "Ninaithale Inikkum", "year": 1979, "artist": "S. P. Balasubrahmanyam, M. S. Viswanathan"}
]

def main():
    client = SpotifyNativeClient()
    print("=" * 80, flush=True)
    print(" 🔍 VERIFYING AUTHENTIC VINTAGE TRACKS IN SPOTIFY CONTAINERS", flush=True)
    print("=" * 80, flush=True)

    tracks = client.get_playlist_tracks(OLD_IS_GOLD_URI)
    track_names = {clean_text(t["name"]): t for t in tracks}
    print(f"Total tracks in Spotify 'Old Is Gold': {len(tracks)}", flush=True)

    missing_tracks_to_add = []

    for item in KEY_AUTHENTIC_VINTAGE_TRACKS:
        t_clean = clean_text(item["title"])
        match = None
        for name_clean, t in track_names.items():
            if t_clean in name_clean:
                match = t
                break

        if match:
            print(f"  ✅ Verified in Old Is Gold: '{match['name']}' ({match['artists']})", flush=True)
        else:
            print(f"  🔍 Missing in Old Is Gold: '{item['title']}' ({item['movie']} - {item['year']}), searching Spotify...", flush=True)
            uri = client.search_track(item["title"], item["artist"])
            if uri:
                print(f"     Found Spotify track: {uri}", flush=True)
                missing_tracks_to_add.append(uri)
            else:
                print(f"     ⚠️ Not found on Spotify search.", flush=True)

    if missing_tracks_to_add:
        print(f"\nAdding {len(missing_tracks_to_add)} missing authentic tracks to 'Old Is Gold' on Spotify...", flush=True)
        success = client.add_tracks_to_playlist(OLD_IS_GOLD_URI, missing_tracks_to_add)
        if success:
            print(f"✅ Successfully synced {len(missing_tracks_to_add)} authentic vintage tracks to Spotify!", flush=True)
        else:
            print("❌ Failed to add tracks to Spotify.", flush=True)
    else:
        print("\n✨ All key authentic vintage tracks are already verified in 'Old Is Gold' on Spotify!", flush=True)

    client.close()

if __name__ == "__main__":
    main()
