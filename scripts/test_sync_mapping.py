#!/usr/bin/env python3
"""
Test mapping and verify that all 214 local databases cleanly map to Spotify containers.
"""
import sqlite3
import re
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from spotify_native_client import SpotifyNativeClient, clean_text
from organize_spotify_folders import FOLDER_DEFINITIONS, get_folder_contents
PLAYLISTS_DIR = BASE_DIR / "playlists"

def main():
    client = SpotifyNativeClient()
    
    print("=" * 80)
    print("🔍 VERIFYING PLAYLIST CONTAINER MAPPINGS ACROSS ALL 9 CATEGORIES")
    print("=" * 80)
    
    total_local = 0
    total_matched = 0
    missing_list = []
    
    for cat_slug, defn in FOLDER_DEFINITIONS.items():
        if cat_slug == "year_complete":
            continue
            
        cat_dir = PLAYLISTS_DIR / cat_slug
        if not cat_dir.exists():
            continue
            
        dbs = sorted(cat_dir.glob("*.db"))
        sp_items = get_folder_contents(client, defn["folder_uri"])
        
        # Build lookup maps
        sp_map = {}
        for it in sp_items:
            sp_map[clean_text(it["name"])] = it["uri"]
            # Also keep exact lower
            sp_map[it["name"].lower().strip()] = it["uri"]
            
        cat_matched = 0
        for db in dbs:
            total_local += 1
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            try:
                info = dict(cur.execute("SELECT key, value FROM playlist_info;").fetchall())
                name = info.get("name", db.stem)
            except Exception:
                name = db.stem
            conn.close()
            
            c_name = clean_text(name)
            c_stem = clean_text(db.stem)
            
            matched_uri = None
            if c_name in sp_map:
                matched_uri = sp_map[c_name]
            elif name.lower().strip() in sp_map:
                matched_uri = sp_map[name.lower().strip()]
            elif c_stem in sp_map:
                matched_uri = sp_map[c_stem]
            else:
                # Fuzzy or partial
                for sp_n, u in sp_map.items():
                    if c_name in sp_n or sp_n in c_name:
                        matched_uri = u
                        break
                        
            if matched_uri:
                cat_matched += 1
                total_matched += 1
            else:
                missing_list.append((cat_slug, name, db.name))
                
        print(f"📁 {defn['display_name']:15}: {cat_matched:2d} / {len(dbs):2d} matched")
        
    print("-" * 80)
    print(f"Total: {total_matched} / {total_local} matched")
    if missing_list:
        print(f"\nMissing containers ({len(missing_list)}):")
        for cat, name, filename in missing_list:
            print(f"  [{cat}] '{name}' ({filename})")
            
    client.close()

if __name__ == "__main__":
    main()
