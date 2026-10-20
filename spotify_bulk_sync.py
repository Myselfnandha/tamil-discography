#!/usr/bin/env python3
"""
spotify_bulk_sync.py - Direct Automated Spotify Bulk Playlist Creator & Synchronizer.

Creates standalone playlists directly on your personal Spotify account and adds
matched songs in batches of 100 using your browser Spotify access token.

Features:
- Validates your Spotify token against /v1/me.
- Automatic playlist creation with custom descriptions.
- High-accuracy track matching on Spotify.
- Local SQLite caching of Spotify URIs to avoid redundant searches and rate limits.
- Supports --curated (top 32), --all (135), or --slug <name>.
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
PLAYLISTS_DIR = BASE_DIR / "playlists"
DISCO_DB = BASE_DIR / "tamil_discography.db"

# Spotify API base
SPOTIFY_API = "https://api.spotify.com/v1"

# Curated Top 32 Playlists
CURATED_SLUGS = [
    "ar_rahman_hits", "ilaiyaraaja_hits", "anirudh_hits", "harris_jayaraj_hits",
    "yuvan_shankar_raja_hits", "deva_hits", "vidyasagar_hits", "santhosh_narayanan_hits",
    "gv_prakash_hits", "d_imman_hits", "ms_viswanathan_hits", "kv_mahadevan_hits",
    "spb_hits", "kj_yesudas_hits", "hariharan_hits", "shankar_mahadevan_hits",
    "sid_sriram_hits", "s_janaki_hits", "ks_chithra_hits", "shreya_ghoshal_hits",
    "all_time_hits", "love_duets", "romantic_duets", "tamil_melody",
    "gaana", "kuthu_dance", "mass_hero_bgm", "tamil_instrumental_bgm",
    "old_is_gold", "2000s_hits", "90s_classics", "latest_releases"
]


class SpotifyClient:
    def __init__(self, token: str):
        self.token = token.strip().strip('"\'')
        self.user = self._verify_token()

    def _request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> Optional[dict]:
        url = f"{SPOTIFY_API}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        body = json.dumps(data).encode("utf-8") if data else None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = resp.read().decode("utf-8")
                    return json.loads(resp_data) if resp_data else {}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", 3))
                    print(f"    ⏳ Spotify rate limit reached. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                elif e.code == 401:
                    raise RuntimeError("Spotify access token is expired or invalid (HTTP 401).")
                else:
                    err_msg = e.read().decode("utf-8")
                    print(f"    ⚠️ Spotify API Error ({e.code}) on {endpoint}: {err_msg}")
                    return None
            except Exception as e:
                print(f"    ⚠️ Request error: {e}")
                time.sleep(1)
        return None

    def _verify_token(self) -> dict:
        data = self._request("GET", "/me")
        if not data or "id" not in data:
            raise RuntimeError(
                "Could not authenticate with Spotify.\n"
                "Please make sure you provided a valid Spotify Bearer token (starts with 'BQ...').\n"
                "Tip: In Spotify Web Player (open.spotify.com), open Console (F12) and run:\n"
                "(await (await fetch('/get_access_token?reason=transport&productType=web_player')).json()).accessToken"
            )
        return data

    def get_existing_playlists(self) -> Dict[str, str]:
        """Fetch user's existing playlists to avoid creating duplicates."""
        existing = {}
        offset = 0
        while True:
            res = self._request("GET", "/me/playlists", params={"limit": 50, "offset": offset})
            if not res or "items" not in res:
                break
            for item in res["items"]:
                if item and "name" in item:
                    existing[item["name"].lower().strip()] = item["id"]
            if not res.get("next"):
                break
            offset += 50
        return existing

    def create_playlist(self, name: str, description: str, public: bool = False) -> Optional[str]:
        """Create a new playlist for the user."""
        res = self._request("POST", "/me/playlists", data={
            "name": name,
            "description": description[:300],
            "public": public
        })
        if not res or "id" not in res:
            res = self._request("POST", f"/users/{self.user['id']}/playlists", data={
                "name": name,
                "description": description[:300],
                "public": public
            })
        return res.get("id") if res else None

    def search_track(self, title: str, artist: str, query_hint: str = None) -> Optional[str]:
        """Search Spotify for a track and return its Spotify URI."""
        clean_title = title.split("(")[0].split("-")[0].strip()
        clean_artist = artist.split(",")[0].strip() if artist else ""

        # 1. Try precomputed query hint if available
        if query_hint and query_hint.strip():
            res = self._request("GET", "/search", params={"q": query_hint.strip(), "type": "track", "limit": 1})
            items = res.get("tracks", {}).get("items", []) if res else []
            if items:
                return items[0]["uri"]

        # 2. Try specific track + artist query
        q = f'track:"{clean_title}"'
        if clean_artist and clean_artist.lower() not in ("various artists", "unknown"):
            q += f' artist:"{clean_artist}"'

        res = self._request("GET", "/search", params={"q": q, "type": "track", "limit": 1})
        items = res.get("tracks", {}).get("items", []) if res else []
        if items:
            return items[0]["uri"]

        # 3. Fallback to broad text search
        fallback_q = f"{clean_title} {clean_artist}".strip()
        res = self._request("GET", "/search", params={"q": fallback_q, "type": "track", "limit": 1})
        items = res.get("tracks", {}).get("items", []) if res else []
        if items:
            return items[0]["uri"]

        # 4. Fallback to title only
        if clean_title:
            res = self._request("GET", "/search", params={"q": clean_title, "type": "track", "limit": 1})
            items = res.get("tracks", {}).get("items", []) if res else []
            if items:
                return items[0]["uri"]

        return None

    def add_tracks_to_playlist(self, playlist_id: str, uris: List[str]):
        """Add tracks to playlist in chunks of 100."""
        for i in range(0, len(uris), 100):
            batch = uris[i:i + 100]
            self._request("POST", f"/playlists/{playlist_id}/tracks", data={"uris": batch})


def get_playlist_tracks(db_path: Path) -> tuple[dict, list]:
    """Read metadata and tracks from a playlist database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT key, value FROM playlist_info;")
    info = {r["key"]: r["value"] for r in cur.fetchall()}

    cur.execute("""
        SELECT id, track_title, album_title, year, composer, singers, spotify_uri, spotify_query
        FROM tracks 
        ORDER BY position ASC;
    """)
    tracks = [dict(r) for r in cur.fetchall()]
    conn.close()
    return info, tracks


def update_cached_uri(db_path: Path, track_id: int, uri: str):
    """Save resolved Spotify URI in local playlist database for future instant reuse."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE tracks SET spotify_uri = ? WHERE id = ?;", (uri, track_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def list_available_playlists():
    """Print all available playlists grouped by category."""
    print("=" * 75)
    print(" 📂 AVAILABLE PLAYLISTS IN /home/nandha/play/playlists")
    print("=" * 75)
    categories = {}
    for p in sorted(PLAYLISTS_DIR.rglob("*.db")):
        cat = p.parent.name
        if cat not in categories:
            categories[cat] = []
        info, tracks = get_playlist_tracks(p)
        categories[cat].append((p.stem, info.get("name", p.stem), len(tracks), info.get("emoji", "🎵")))

    total_all = 0
    for cat, pls in sorted(categories.items()):
        cat_total = sum(t[2] for t in pls)
        total_all += cat_total
        print(f"\n📁 Category: {cat.upper()} ({len(pls)} playlists, {cat_total:,} songs)")
        print("-" * 75)
        for slug, name, count, emoji in pls:
            print(f"  {emoji} {slug:<34} : {name:<30} ({count:>4} songs)")

    print("\n" + "=" * 75)
    print(f" TOTAL: {sum(len(pls) for pls in categories.values())} Playlists | {total_all:,} Songs across all collections")
    print("=" * 75 + "\n")


def run_sync_from_csv(client: SpotifyClient, csv_path: Path, max_tracks: int = 10000):
    """Import directly from an exported CSV file."""
    import csv
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        return

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        print("❌ Error: CSV file is empty.")
        return

    pl_name = rows[0].get("Playlist Name") or csv_path.stem.replace("_", " ").title()
    desc = f"Imported from {csv_path.name} via Tamil Discography"

    existing_playlists = client.get_existing_playlists()
    pl_id = existing_playlists.get(pl_name.lower().strip())
    if pl_id:
        print(f"ℹ️ Found existing playlist on Spotify: {pl_name} (ID: {pl_id})")
    else:
        pl_id = client.create_playlist(pl_name, desc, public=False)
        print(f"✨ Created playlist on Spotify: {pl_name} (ID: {pl_id})")

    matched_uris = []
    tracks_to_process = rows[:max_tracks]
    print(f"🔍 Searching and matching {len(tracks_to_process)} tracks on Spotify...")

    for idx, r in enumerate(tracks_to_process, 1):
        title = r.get("Track Name", "")
        artist = r.get("Artist Name", "")
        query_hint = r.get("Spotify Search Query", "")

        uri = client.search_track(title, artist, query_hint=query_hint)
        if uri:
            matched_uris.append(uri)
        time.sleep(0.04)
        if idx % 25 == 0 or idx == len(tracks_to_process):
            print(f"   [{idx}/{len(tracks_to_process)}] Matched: {len(matched_uris)} tracks...", end="\r", flush=True)

    print(f"\n🎯 Matched {len(matched_uris)}/{len(tracks_to_process)} tracks.")
    if matched_uris:
        client.add_tracks_to_playlist(pl_id, matched_uris)
        print(f"✅ Successfully added {len(matched_uris)} songs to '{pl_name}'!")


def run_sync(token: str, mode: str = "curated", target_slug: str = None, target_cat: str = None, max_per_playlist: int = 10000):
    print("=" * 75)
    print(" 🚀 SPOTIFY BULK PLAYLIST AUTOMATION (100% FREE)")
    print("=" * 75)

    client = SpotifyClient(token)
    user_name = client.user.get("display_name") or client.user.get("id")
    print(f" Connected to Spotify Account : {user_name} (ID: {client.user['id']})")
    print(f" Sync Mode                    : {mode.upper()}")
    print(f" Max Tracks Per Playlist      : {max_per_playlist:,}")
    print("-" * 75)

    # Discover databases
    dbs = {}
    for p in sorted(PLAYLISTS_DIR.rglob("*.db")):
        dbs[p.stem] = p

    # Select playlists
    if target_slug:
        selected = [target_slug] if target_slug in dbs else [s for s in dbs if target_slug.lower() in s.lower()]
    elif target_cat:
        selected = [s for s, p in dbs.items() if target_cat.lower() in p.parent.name.lower()]
    elif mode == "all":
        selected = list(dbs.keys())
    else:
        selected = [s for s in CURATED_SLUGS if s in dbs]

    if not selected:
        print("❌ No matching playlists found.")
        return

    print(f" Total Playlists to Sync      : {len(selected)}\n")

    # Fetch existing playlists to avoid duplicates
    existing_playlists = client.get_existing_playlists()

    for idx, slug in enumerate(selected, 1):
        db_path = dbs[slug]
        info, tracks = get_playlist_tracks(db_path)
        pl_name = info.get("name", slug)
        emoji = info.get("emoji", "🎵")
        desc = info.get("description", f"Tamil Discography collection: {pl_name}")

        print(f"[{idx:02d}/{len(selected)}] {emoji} {pl_name} ({len(tracks)} local tracks)...")

        # Check if already on Spotify
        key = pl_name.lower().strip()
        pl_id = existing_playlists.get(key)
        if pl_id:
            print(f"    ℹ️ Found existing playlist on Spotify (ID: {pl_id})")
        else:
            pl_id = client.create_playlist(pl_name, desc, public=False)
            if not pl_id:
                print("    ❌ Failed to create playlist on Spotify. Skipping.")
                continue
            existing_playlists[key] = pl_id
            print(f"    ✨ Created playlist on Spotify (ID: {pl_id})")

        # Resolve tracks
        matched_uris = []
        tracks_to_process = tracks[:max_per_playlist]
        newly_cached = 0
        
        for t_idx, t in enumerate(tracks_to_process, 1):
            uri = t.get("spotify_uri")
            if uri and uri.startswith("spotify:track:"):
                matched_uris.append(uri)
                continue

            # Search on Spotify using spotify_query hint + fallbacks
            t_name = t.get("track_title", "")
            artist = t.get("singers") or t.get("composer") or ""
            q_hint = t.get("spotify_query") or ""
            uri = client.search_track(t_name, artist, query_hint=q_hint)

            if uri:
                matched_uris.append(uri)
                update_cached_uri(db_path, t["id"], uri)
                newly_cached += 1

            time.sleep(0.04)
            if t_idx % 20 == 0 or t_idx == len(tracks_to_process):
                print(f"    🔍 Searching [{t_idx}/{len(tracks_to_process)}] (Matched: {len(matched_uris)})...", end="\r", flush=True)

        print(f"    🎯 Matched {len(matched_uris)}/{len(tracks_to_process)} tracks on Spotify (New cached: {newly_cached})")

        # Add to playlist
        if matched_uris:
            client.add_tracks_to_playlist(pl_id, matched_uris)
            print(f"    ✅ Added {len(matched_uris)} songs to '{pl_name}'")
        else:
            print("    ⚠️ No tracks matched for this playlist.")
        print()

    print("=" * 75)
    print(" 🎉 ALL SELECTED PLAYLISTS ARE SYNCED TO YOUR SPOTIFY ACCOUNT!")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Bulk create and sync Tamil Discography playlists on Spotify without premium fees.")
    parser.add_argument("--token", type=str, default=None, help="Spotify Bearer access token (starts with 'BQ...')")
    parser.add_argument("--curated", action="store_true", default=False, help="Sync top 32 curated playlists (default)")
    parser.add_argument("--all", action="store_true", default=False, help="Sync all 139 playlists")
    parser.add_argument("--category", type=str, default=None, help="Sync all playlists in a category (e.g. artist, mood, tamil, era, genre)")
    parser.add_argument("--slug", type=str, default=None, help="Sync a specific playlist by slug (e.g. anirudh_hits, love, 90s_classics)")
    parser.add_argument("--csv", type=str, default=None, help="Import directly from an exported CSV file")
    parser.add_argument("--max", type=int, default=10000, help="Max tracks per playlist to sync (default: 10,000 - Spotify hard limit)")
    parser.add_argument("--list", action="store_true", default=False, help="List all available playlists and categories")

    args = parser.parse_args()

    if args.list:
        list_available_playlists()
        sys.exit(0)

    token = args.token
    tok_file = BASE_DIR / ".spotify_tokens.json"

    if token:
        # Save token for future reuse
        try:
            tok_data = {"access_token": token.strip().strip('"\''), "updated_at": time.time()}
            tok_file.write_text(json.dumps(tok_data, indent=2))
        except Exception:
            pass
    else:
        # Check if stored in .spotify_tokens.json
        if tok_file.exists():
            try:
                data = json.loads(tok_file.read_text())
                token = data.get("access_token")
            except Exception:
                pass

    if not token:
        print("\n❌ Error: Spotify access token is required.")
        print("Usage: python3 spotify_bulk_sync.py --token \"BQ...\"\n")
        print("💡 How to get your Spotify Access Token in 10 seconds (100% Free, No Premium needed):")
        print("  1. Open https://open.spotify.com in your browser (Chrome/Firefox/Brave/Edge).")
        print("  2. Press F12 (Inspect) -> Click the 'Console' tab.")
        print("  3. Paste this command and hit Enter:")
        print("     (await (await fetch('/get_access_token?reason=transport&productType=web_player')).json()).accessToken")
        print("  4. Copy the quoted string (starts with 'BQ...') and run:")
        print("     python3 spotify_bulk_sync.py --token \"<PASTE_TOKEN_HERE>\" --slug <slug>\n")
        sys.exit(1)

    if args.csv:
        try:
            client = SpotifyClient(token)
            run_sync_from_csv(client, Path(args.csv), max_tracks=args.max)
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            sys.exit(1)
        return

    mode = "all" if args.all else ("category" if args.category else ("slug" if args.slug else "curated"))
    try:
        run_sync(token, mode=mode, target_slug=args.slug, target_cat=args.category, max_per_playlist=args.max)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

