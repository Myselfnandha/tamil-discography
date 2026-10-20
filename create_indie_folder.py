#!/usr/bin/env python3
"""
create_indie_folder.py - Creates and registers the 'Indie' folder container on Spotify.
"""

import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from spotify_native_client import SpotifyNativeClient, HASH_LIBRARY

def create_indie_folder():
    client = SpotifyNativeClient()
    page = client._page

    print("Navigating to Spotify Web Player...")
    page.goto("https://open.spotify.com", timeout=30000)
    page.wait_for_timeout(3000)

    # 1. First check if 'Indie' folder already exists
    vars_ = {
        'filters': [],
        'order': None,
        'textFilter': '',
        'features': ['LIKED_SONGS', 'YOUR_EPISODES_V2'],
        'limit': 100,
        'offset': 0,
        'flatten': False,
        'expandedFolders': [],
        'folderUri': None
    }
    data = client._query('libraryV3', HASH_LIBRARY, vars_)
    items = data.get('data', {}).get('me', {}).get('libraryV3', {}).get('items', [])
    for it in items:
        d = it.get('item', {}).get('data', {})
        name = d.get('name', '')
        uri = d.get('uri', '')
        if 'folder' in uri and name.lower() == 'indie':
            print(f"✅ 'Indie' folder already exists: {name} -> {uri}")
            folder_id = uri.split("folder:")[-1]
            print(f"FOLDER_URI: {uri}")
            print(f"START_GROUP: spotify:start-group:{folder_id}")
            client.close()
            return uri, f"spotify:start-group:{folder_id}"

    # 2. Click create button
    btn = page.query_selector('button[aria-label="Create"]')
    if not btn:
        print("Create button not found!")
        client.close()
        return None, None

    print("Clicking Create button...")
    btn.click()
    page.wait_for_timeout(1000)

    # Find the Folder menu item
    folder_menu_item = page.query_selector('li:has-text("Folder"), button:has-text("Folder")')
    if not folder_menu_item:
        print("Folder menu item not found!")
        client.close()
        return None, None

    print("Clicking 'Folder' menu item...")
    folder_menu_item.click()
    page.wait_for_timeout(3000)

    # 3. Query library to get created folder URI
    data = client._query('libraryV3', HASH_LIBRARY, vars_)
    items = data.get('data', {}).get('me', {}).get('libraryV3', {}).get('items', [])
    created_folder = None
    for it in items:
        d = it.get('item', {}).get('data', {})
        name = d.get('name', '')
        uri = d.get('uri', '')
        if 'folder' in uri:
            if name in ['New Folder', 'Indie']:
                created_folder = d
                break

    if not created_folder:
        print("❌ Created folder not found in library items!")
        client.close()
        return None, None

    folder_uri = created_folder['uri']
    folder_id = folder_uri.split("folder:")[-1]
    start_group = f"spotify:start-group:{folder_id}"
    print(f"Found created folder: '{created_folder.get('name')}' -> {folder_uri}")

    # 4. Rename to 'Indie' if named 'New Folder'
    if created_folder.get('name') == 'New Folder':
        print(f"Renaming folder '{created_folder['name']}' to 'Indie'...")
        folder_elem = page.query_selector("li:has-text('New Folder'), div:has-text('New Folder')")
        if folder_elem:
            folder_elem.click(button="right")
            page.wait_for_timeout(800)
            rename_opt = page.query_selector("li:has-text('Rename'), button:has-text('Rename')")
            if rename_opt:
                rename_opt.click()
                page.wait_for_timeout(500)
                input_elem = page.query_selector("input")
                if input_elem:
                    input_elem.fill("Indie")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1500)
                    print("✅ Successfully renamed folder to 'Indie'!")

    client.close()
    print(f"\nResult:")
    print(f"  folder_uri: {folder_uri}")
    print(f"  start_group: {start_group}")
    return folder_uri, start_group

if __name__ == "__main__":
    create_indie_folder()
