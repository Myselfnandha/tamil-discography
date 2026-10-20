#!/usr/bin/env python3
"""
organize_spotify_folders.py - Automated Spotify Playlist Folder Organizer.

Organizes Spotify playlists into folders matching the local discography hierarchy:
  1. Activity
  2. Artist
  3. Era
  4. Genre
  5. Mood
  6. Relationship
  7. Tamil

Uses native rootlist delta MOV operations with session authentication (200 OK).
"""

import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from spotify_native_client import SpotifyNativeClient, clean_text, HASH_LIBRARY

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists"

FOLDER_DEFINITIONS = {
    "activity": {
        "display_name": "Activity",
        "start_group": "spotify:start-group:61e622ebf620faa8",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:61e622ebf620faa8"
    },
    "artist": {
        "display_name": "Artist",
        "start_group": "spotify:start-group:83f7f5a695a6b6e2",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:83f7f5a695a6b6e2"
    },
    "era": {
        "display_name": "Era",
        "start_group": "spotify:start-group:158bb47d62f7967b",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:158bb47d62f7967b"
    },
    "genre": {
        "display_name": "Genre",
        "start_group": "spotify:start-group:5a5c7ded84fbb97a",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:5a5c7ded84fbb97a"
    },
    "mood": {
        "display_name": "Mood",
        "start_group": "spotify:start-group:af8ea7d8f3fef67b",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:af8ea7d8f3fef67b"
    },
    "relationship": {
        "display_name": "Relationship",
        "start_group": "spotify:start-group:c2bbf19ec524bf2b",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:c2bbf19ec524bf2b"
    },
    "tamil": {
        "display_name": "Tamil",
        "start_group": "spotify:start-group:7b9c9710e62981c9",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:7b9c9710e62981c9"
    },
    "year": {
        "display_name": "Year",
        "start_group": "spotify:start-group:7581063132455cbe",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:7581063132455cbe"
    },
    "indie": {
        "display_name": "Indie",
        "start_group": "spotify:start-group:859025b00671d970",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:859025b00671d970"
    },
    "year_complete": {
        "display_name": "Year - Complete",
        "start_group": "spotify:start-group:2effe1b0a46ff274",
        "folder_uri": "spotify:user:mqvns86lexwty9zusrxifajb4:folder:2effe1b0a46ff274"
    }
}


def load_category_db_names() -> Dict[str, Dict[str, str]]:
    """Loads all local .db playlist names grouped by category."""
    cat_playlists = {}
    for cat_slug in FOLDER_DEFINITIONS.keys():
        p = PLAYLISTS_DIR / cat_slug
        if not p.exists():
            continue
        cat_playlists[cat_slug] = {}
        for db_file in p.glob("*.db"):
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            try:
                info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
                name = info.get("name", db_file.stem)
            except Exception:
                name = db_file.stem
            finally:
                conn.close()
            cat_playlists[cat_slug][clean_text(name)] = name
    return cat_playlists


def move_playlists_to_folder(client: SpotifyNativeClient, playlist_uris: List[str], folder_start_group: str) -> bool:
    """Executes native MOV operation to place playlist URIs into the target folder."""
    if not playlist_uris:
        return True

    payload = {
        "deltas": [
            {
                "ops": [
                    {
                        "kind": "MOV",
                        "mov": {
                            "items": [{"uri": u, "attributes": {}} for u in playlist_uris],
                            "addAfterItem": {
                                "uri": folder_start_group,
                                "attributes": {}
                            }
                        }
                    }
                ],
                "info": {
                    "source": {
                        "client": "WEBPLAYER"
                    }
                }
            }
        ]
    }

    res = client._page.evaluate('''(args) => {
        return fetch('https://spclient.wg.spotify.com/playlist/v2/user/mqvns86lexwty9zusrxifajb4/rootlist/changes', {
            method: 'POST',
            headers: {
                ...args.headers,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(args.payload)
        }).then(async r => ({ status: r.status, text: await r.text() }))
          .catch(e => ({ status: 500, error: e.toString() }));
    }''', {"headers": client._headers, "payload": payload})

    status = res.get("status")
    return status == 200


def get_folder_contents(client: SpotifyNativeClient, folder_uri: str) -> List[Dict[str, str]]:
    """Fetches all items currently inside a Spotify folder."""
    vars_ = {
        "filters": [],
        "order": None,
        "textFilter": "",
        "features": ["LIKED_SONGS", "YOUR_EPISODES_V2"],
        "limit": 100,
        "offset": 0,
        "flatten": False,
        "expandedFolders": [],
        "folderUri": folder_uri
    }
    data = client._query("libraryV3", HASH_LIBRARY, vars_)
    items = data.get("data", {}).get("me", {}).get("libraryV3", {}).get("items", [])
    result = []
    for it in items:
        d = it.get("item", {}).get("data", {})
        if d.get("uri") and d.get("name"):
            result.append({"name": d["name"], "uri": d["uri"]})
    return result


def main():
    print("=" * 80)
    print(" 📁 NATIVE SPOTIFY PLAYLIST FOLDER ORGANIZER")
    print("=" * 80)

    cat_db_map = load_category_db_names()
    for cat, dbs in cat_db_map.items():
        print(f"  Indexed category '{cat}': {len(dbs)} playlists")

    client = SpotifyNativeClient()

    try:
        # 1. Fetch all Spotify playlists
        print("\n🔍 Scanning all Spotify playlists in library...")
        all_spotify = client.get_all_playlists()
        print(f"Total playlists found on Spotify: {sum(len(v) for v in all_spotify.values())}")

        total_moved = 0

        # 2. Process each category
        for cat_slug, defn in FOLDER_DEFINITIONS.items():
            cat_name = defn["display_name"]
            folder_start = defn["start_group"]
            folder_uri = defn["folder_uri"]
            local_names = cat_db_map.get(cat_slug, {})

            print(f"\n📂 Processing Category: [{cat_name}] ({len(local_names)} expected)")

            # Check what's already inside this folder
            existing_in_folder = get_folder_contents(client, folder_uri)
            existing_uris = {item["uri"] for item in existing_in_folder}
            print(f"   Currently inside folder: {len(existing_in_folder)} playlists")

            # Find matching Spotify playlists for this category
            to_move_uris = []
            for clean_sp_name, containers in all_spotify.items():
                is_match = False
                if clean_sp_name in local_names:
                    is_match = True
                else:
                    for l_clean in local_names.keys():
                        if l_clean == clean_sp_name or (len(l_clean) > 4 and l_clean in clean_sp_name):
                            is_match = True
                            break

                if is_match:
                    for c in containers:
                        if c["uri"] not in existing_uris and c["uri"] not in to_move_uris:
                            to_move_uris.append(c["uri"])
                            print(f"   ➕ Queued to move: '{c['name']}' ({c['uri']})")

            if to_move_uris:
                print(f"   🚀 Moving {len(to_move_uris)} playlists into '{cat_name}' folder...")
                ok = move_playlists_to_folder(client, to_move_uris, folder_start)
                if ok:
                    print(f"   ✅ Successfully moved {len(to_move_uris)} playlists into '{cat_name}'!")
                    total_moved += len(to_move_uris)
                else:
                    print(f"   ❌ Failed to move playlists into '{cat_name}'.")
            else:
                print(f"   ✨ All matching playlists already inside '{cat_name}' folder!")

            time.sleep(0.5)

        # 3. Final Verification Audit
        print("\n" + "=" * 80)
        print(" 📊 FINAL FOLDER AUDIT VERIFICATION")
        print("=" * 80)

        total_in_folders = 0
        summary_report = {}
        for cat_slug, defn in FOLDER_DEFINITIONS.items():
            cat_name = defn["display_name"]
            folder_uri = defn["folder_uri"]
            contents = get_folder_contents(client, folder_uri)
            total_in_folders += len(contents)
            summary_report[cat_name] = [item["name"] for item in contents]
            print(f"  📁 {cat_name:15}: {len(contents):2d} playlists")

        print("-" * 80)
        print(f" 🎉 Total Playlists inside Category Folders: {total_in_folders}")
        print(f" 📦 Newly Organized in this run: {total_moved}")
        print("=" * 80)

        # Save audit report
        with open(BASE_DIR / "data" / "folder_organization_report.json", "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2)
        print("💾 Saved folder organization report to data/folder_organization_report.json")

    finally:
        client.close()


if __name__ == "__main__":
    main()
