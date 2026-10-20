#!/usr/bin/env python3
import time
from spotify_native_client import SpotifyNativeClient, HASH_LIBRARY

def rename_folder():
    client = SpotifyNativeClient()
    page = client._page

    print("Navigating to Spotify Web Player...")
    page.goto("https://open.spotify.com", timeout=30000)
    page.wait_for_timeout(4000)

    # Locate 'New Folder'
    loc = page.locator('text="New Folder"').first
    if loc.is_visible():
        print("Found visible 'New Folder'! Right-clicking...")
        loc.click(button="right")
        page.wait_for_timeout(1000)
        page.screenshot(path="data/context_menu_test.png")

        # Find Rename option
        rename_btn = page.locator('button:has-text("Rename"), li:has-text("Rename"), span:has-text("Rename")').first
        if rename_btn.is_visible():
            print("Found Rename button! Clicking...")
            rename_btn.click()
            page.wait_for_timeout(1000)

            inp = page.locator('input').first
            if inp.is_visible():
                print("Found rename input! Typing 'Year - Complete'...")
                inp.fill("Year - Complete")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                print("Successfully submitted rename!")
            else:
                print("Input not visible!")
        else:
            print("Rename button not visible in context menu!")
    else:
        print("'New Folder' not visible!")

    # Verify via library query
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
        if '2effe1b0a46ff274' in d.get('uri', ''):
            print("Current folder name in library:", d.get('name'))

    client.close()

if __name__ == "__main__":
    rename_folder()
