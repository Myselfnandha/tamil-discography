#!/usr/bin/env python3
"""
spotify_native_client.py - High-Performance Native Spotify GraphQL Client.
Bypasses public REST API 429 rate limits and 403 premium requirements by directly
executing official Spotify Web Player GraphQL Pathfinder operations with session cookies.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COOKIES_FILE = DATA_DIR / "spotify_cookies.json"

PATHFINDER_URL = "https://api-partner.spotify.com/pathfinder/v2/query"

HASH_LIBRARY = "390c78e5b951029bad359785e69b07b536a509c581cbcd0aded5e5067f187455"
HASH_PLAYLIST = "21ea11a6ac75a5f3e01fd365d29c18e0a4a8b7dc09f89bbb5d73910190c6acaf"
HASH_SEARCH = "f244254b94c0e824d458ac216e0f8406a73f2f69a9ff52831a2f78fa774ff6ce"
HASH_MUTATION = "b907ad6b088d5bf7680fa81198996d58398c2d55dfcdf59fcc959e0be98a418a"
HASH_LIBRARY_REMOVE = "896ebcb47815681340860d121cb5d494e157e2a78d3950385cd54e0393c67148"


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[\(\[\{].*?[\)\]\}]', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())


class SpotifyNativeClient:
    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._headers = {}
        self._init_browser()

    def _init_browser(self):
        if not COOKIES_FILE.exists():
            raise FileNotFoundError(f"Missing cookies file: {COOKIES_FILE}")

        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        pw_cookies = []
        for c in cookies:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", False)
            })

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self._context = self._browser.new_context()
        self._context.add_cookies(pw_cookies)
        self._page = self._context.new_page()

        def on_req(r):
            if "pathfinder" in r.url and r.headers.get("authorization") and not self._headers.get("authorization"):
                self._headers["authorization"] = r.headers["authorization"]
                if "client-token" in r.headers:
                    self._headers["client-token"] = r.headers["client-token"]

        self._page.on("request", on_req)
        self._page.goto("https://open.spotify.com", wait_until="domcontentloaded", timeout=45000)
        for _ in range(40):
            if self._headers.get("authorization"):
                break
            self._page.wait_for_timeout(500)

        if not self._headers.get("authorization"):
            try:
                self._page.goto("https://open.spotify.com/collection/playlists", wait_until="domcontentloaded", timeout=30000)
                for _ in range(30):
                    if self._headers.get("authorization"):
                        break
                    self._page.wait_for_timeout(500)
            except Exception:
                pass

        if not self._headers.get("authorization"):
            raise RuntimeError("Could not capture Spotify session authorization headers.")
        print("✅ Spotify Native Client connected! Session authenticated (200 OK).")

    def _refresh_headers(self):
        print("       🔄 Access token expired. Refreshing browser session headers...")
        self._headers.clear()
        try:
            self._page.reload(wait_until="domcontentloaded", timeout=30000)
        except Exception:
            self._page.goto("https://open.spotify.com/collection/playlists", wait_until="domcontentloaded", timeout=45000)
        self._page.wait_for_timeout(3000)
        if not self._headers.get("authorization"):
            self._page.goto("https://open.spotify.com", wait_until="domcontentloaded", timeout=45000)
            self._page.wait_for_timeout(3000)
        print("       ✅ Refreshed Spotify session headers!")

    def _query(self, operation_name: str, sha256_hash: str, variables: dict) -> dict:
        payload = {
            "operationName": operation_name,
            "variables": variables,
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": sha256_hash
                }
            }
        }
        for attempt in range(4):
            res = self._page.evaluate('''(args) => {
                return fetch('https://api-partner.spotify.com/pathfinder/v2/query', {
                    method: 'POST',
                    headers: {
                        ...args.headers,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(args.payload)
                }).then(async (r) => {
                    const text = await r.text();
                    let data = {};
                    try {
                        data = text ? JSON.parse(text) : {};
                    } catch(e) {
                        data = { raw: text };
                    }
                    return { status: r.status, data: data };
                }).catch(err => ({ status: 500, data: { error: err.toString() } }));
            }''', {"headers": self._headers, "payload": payload})

            status = res.get("status")
            if status == 401:
                self._refresh_headers()
                continue
            if status in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            if status not in (200, 204):
                raise RuntimeError(f"Pathfinder query '{operation_name}' failed with status {status}: {res.get('data')}")
            return res.get("data", {})
        raise RuntimeError(f"Pathfinder query '{operation_name}' failed after 4 retry attempts (last status: {status}).")

    def get_all_playlists(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns dict of {clean_name: [list of playlist dicts with 'name', 'uri', 'id']}."""
        grouped = {}
        offset = 0
        limit = 50

        print("📋 Scanning all Spotify playlists via native backend...")
        while True:
            vars_ = {
                "filters": ["Playlists"],
                "order": None,
                "textFilter": "",
                "offset": offset,
                "limit": limit
            }
            data = self._query("libraryV3", HASH_LIBRARY, vars_)
            items = data.get("data", {}).get("me", {}).get("libraryV3", {}).get("items", [])
            if not items:
                break

            for it in items:
                p = it.get("item", {}).get("data", {})
                uri = p.get("uri", "")
                name = p.get("name", "").strip()
                if "playlist:" in uri and name:
                    p_id = uri.split("playlist:")[1]
                    cn = clean_text(name)
                    grouped.setdefault(cn, []).append({
                        "name": name,
                        "uri": uri,
                        "id": p_id
                    })

            if len(items) < limit:
                break
            offset += limit

        total_containers = sum(len(v) for v in grouped.values())
        print(f"   Found {total_containers} playlist containers across {len(grouped)} unique titles.")
        return grouped

    def get_playlist_tracks(self, playlist_uri: str) -> List[Dict[str, Any]]:
        """Fetch all tracks for a playlist with 'uid', 'uri', 'name', 'artists', 'album', 'year'."""
        tracks = []
        offset = 0
        limit = 100

        while True:
            vars_ = {
                "uri": playlist_uri,
                "offset": offset,
                "limit": limit,
                "enableWatchFeedEntrypoint": True,
                "includeEpisodeContentRatingsV2": True
            }
            data = self._query("fetchPlaylist", HASH_PLAYLIST, vars_)
            p_v2 = (data.get("data") or {}).get("playlistV2") or {}
            content = p_v2.get("content") or {}
            items = content.get("items", [])
            if not items:
                break

            for it in items:
                t_data = it.get("itemV2", {}).get("data", {})
                t_uri = t_data.get("uri", "")
                t_name = t_data.get("name", "").strip()
                uid = it.get("uid", "")
                if t_uri and t_name:
                    artists = []
                    for a in t_data.get("artists", {}).get("items", []):
                        artists.append(a.get("profile", {}).get("name", ""))
                    
                    album_data = t_data.get("albumOfTrack", {})
                    album_name = album_data.get("name", "")
                    date_str = album_data.get("date", {}).get("isoString", "")
                    year = int(date_str[:4]) if date_str and date_str[:4].isdigit() else 2099

                    tracks.append({
                        "uid": uid,
                        "uri": t_uri,
                        "name": t_name,
                        "artists": ", ".join(artists),
                        "album": album_name,
                        "year": year
                    })

            total = content.get("totalCount", 0)
            if len(tracks) >= total or len(items) < limit:
                break
            offset += limit

        return tracks

    def search_track(self, title: str, artist: str = "") -> Optional[str]:
        """Search Spotify for a track and return the best matching Spotify track URI."""
        clean_t = clean_text(title)
        clean_a = clean_text(artist.split(",")[0].split("&")[0].split("/")[0].strip()) if artist else ""
        query = f"{clean_t} {clean_a}".strip()
        vars_ = {
            "query": query,
            "limit": 10,
            "numberOfTopResults": 10,
            "offset": 0,
            "includeAuthors": True,
            "includeAlbumPreReleases": False,
            "includeEpisodeContentRatingsV2": True
        }
        try:
            data = self._query("searchSuggestions", HASH_SEARCH, vars_)
            items = data.get("data", {}).get("searchV2", {}).get("topResultsV2", {}).get("itemsV2", [])
            for it in items:
                item_obj = it.get("item", {})
                if item_obj.get("__typename") == "TrackResponseWrapper":
                    d = item_obj.get("data", {})
                    uri = d.get("uri", "")
                    if uri.startswith("spotify:track:"):
                        return uri
        except Exception:
            pass
        return None

    def create_playlist(self, name: str, description: str = "", folder_start_group: Optional[str] = None) -> Optional[str]:
        """Creates a playlist directly via Spotify spclient API with name and description, and optionally files into a folder."""
        payload = {
            "ops": [
                {
                    "kind": "UPDATE_LIST_ATTRIBUTES",
                    "updateListAttributes": {
                        "newAttributes": {
                            "values": {
                                "name": name,
                                "description": description or ""
                            }
                        }
                    }
                }
            ]
        }
        try:
            res = self._page.evaluate('''(args) => {
                return fetch('https://spclient.wg.spotify.com/playlist/v2/playlist', {
                    method: 'POST',
                    headers: {
                        ...args.headers,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(args.payload)
                }).then(async r => {
                    const text = await r.text();
                    return { status: r.status, raw: text };
                }).catch(e => ({ status: 500, error: e.toString() }));
            }''', {"headers": self._headers, "payload": payload})

            if res.get("status") != 200:
                print(f"      ⚠️ spclient create_playlist failed: {res}")
                return None

            raw_text = res.get("raw", "")
            m = re.search(r'(spotify:playlist:[a-zA-Z0-9]+)', raw_text)
            if not m:
                print(f"      ⚠️ No playlist URI found in spclient response: {raw_text[:200]}")
                return None

            pl_uri = m.group(1)

            # File into rootlist / folder
            rootlist_item = {
                "uri": pl_uri,
                "attributes": {"timestamp": str(int(time.time() * 1000))}
            }
            add_op = {
                "kind": "ADD",
                "add": {
                    "items": [rootlist_item]
                }
            }
            if folder_start_group:
                add_op["add"]["addAfterItem"] = {
                    "uri": folder_start_group,
                    "attributes": {}
                }
            else:
                add_op["add"]["addFirst"] = True

            rootlist_payload = {
                "deltas": [
                    {
                        "ops": [add_op],
                        "info": {
                            "source": {
                                "client": "WEBPLAYER"
                            }
                        }
                    }
                ]
            }

            self._page.evaluate('''(args) => {
                return fetch('https://spclient.wg.spotify.com/playlist/v2/user/mqvns86lexwty9zusrxifajb4/rootlist/changes', {
                    method: 'POST',
                    headers: {
                        ...args.headers,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(args.payload)
                }).then(async r => ({ status: r.status })).catch(e => ({ status: 500 }));
            }''', {"headers": self._headers, "payload": rootlist_payload})

            return pl_uri
        except Exception as e:
            print(f"      ⚠️ Failed to create playlist '{name}': {e}")
            return None

    def add_tracks_to_playlist(self, playlist_uri: str, track_uris: List[str], position: str = "BOTTOM_OF_PLAYLIST") -> bool:
        """Add track URIs to a playlist in batches of 50. position can be 'BOTTOM_OF_PLAYLIST' or 'TOP_OF_PLAYLIST'."""
        if not track_uris:
            return True
        for i in range(0, len(track_uris), 50):
            batch = track_uris[i:i + 50]
            vars_ = {
                "playlistUri": playlist_uri,
                "playlistItemUris": batch,
                "newPosition": {
                    "moveType": position,
                    "fromUid": None
                },
                "interactionId": None
            }
            try:
                self._query("addToPlaylist", HASH_MUTATION, vars_)
            except Exception as e:
                print(f"      ⚠️ Add batch failed: {e}")
                return False
            time.sleep(0.2)
        return True

    def remove_tracks_from_playlist(self, playlist_uri: str, uids: List[str]) -> bool:
        """Remove tracks from a playlist by item UID in batches of 50."""
        if not uids:
            return True
        for i in range(0, len(uids), 50):
            batch = uids[i:i + 50]
            vars_ = {
                "playlistUri": playlist_uri,
                "uids": batch
            }
            try:
                self._query("removeFromPlaylist", HASH_MUTATION, vars_)
            except Exception as e:
                print(f"      ⚠️ Remove batch failed: {e}")
                return False
            time.sleep(0.2)
        return True

    def delete_playlist(self, playlist_uri: str) -> bool:
        """Permanently delete a playlist container via Web Player UI automation."""
        p_id = playlist_uri.split("playlist:")[-1]
        try:
            self._page.goto(f"https://open.spotify.com/playlist/{p_id}", wait_until="domcontentloaded", timeout=35000)
            try:
                more_btn = self._page.wait_for_selector("button[data-testid='more-button']", timeout=12000)
            except Exception:
                more_btn = None

            if more_btn:
                more_btn.click()
                self._page.wait_for_timeout(600)
                menu_items = self._page.query_selector_all("button[role='menuitem'], li[role='menuitem']")
                for m in menu_items:
                    txt = m.inner_text().strip().lower()
                    if any(w in txt for w in ["delete", "remove from your library", "remove from library"]):
                        m.click()
                        self._page.wait_for_timeout(600)
                        confirm_btn = self._page.query_selector("button:has-text('Delete'), button:has-text('Remove')")
                        if confirm_btn:
                            confirm_btn.click()
                            self._page.wait_for_timeout(1500)
                            return True
            return False
        except Exception as e:
            print(f"      ⚠️ UI Delete failed for {playlist_uri}: {e}")
            return False

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()


if __name__ == "__main__":
    client = SpotifyNativeClient()
    playlists = client.get_all_playlists()
    print(f"Total Unique Titles: {len(playlists)}")
    sample_key = next(iter(playlists))
    print(f"Sample: '{sample_key}' -> {len(playlists[sample_key])} container(s): {playlists[sample_key][0]}")
    sample_tracks = client.get_playlist_tracks(playlists[sample_key][0]["uri"])
    print(f"Tracks in '{sample_key}': {len(sample_tracks)}")
    client.close()
