#!/usr/bin/env python3
import sys
import time
from pathlib import Path
from spotify_native_client import SpotifyNativeClient, HASH_LIBRARY

def rename_folder():
    client = SpotifyNativeClient()
    page = client._page

    print("Navigating to Spotify Web Player...")
    page.goto("https://open.spotify.com", timeout=30000)
    page.wait_for_timeout(3000)

    folder_id = "859025b00671d970"
    folder_uri = f"spotify:user:mqvns86lexwty9zusrxifajb4:folder:{folder_id}"

    # Search for text 'New Folder'
    loc = page.get_by_text("New Folder", exact=True).first
    print("Finding 'New Folder' locator...")
    if loc.count() > 0:
        print("Clicking right button on target folder...")
        loc.click(button="right", force=True)
        page.wait_for_timeout(1000)

        # Click Rename
        rename_item = page.locator("button:has-text('Rename'), li:has-text('Rename'), span:has-text('Rename')").first
        if rename_item.count() > 0:
            print("Clicking Rename...")
            rename_item.click(force=True)
            page.wait_for_timeout(800)

            # Type 'Indie'
            inp = page.locator("input").first
            if inp.count() > 0:
                inp.fill("Indie")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                print("Pressed Enter with 'Indie'")

    # Verify via libraryV3
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
        if folder_id in d.get('uri', ''):
            print("Verified folder in libraryV3:", d)

    client.close()

if __name__ == "__main__":
    rename_folder()
