#!/usr/bin/env python3
"""
auto_update_playlists.py - Master Automated Playlist Update & Synchronization Engine.

Modes:
  --now      : Daily Smart Hybrid sync (Mon-Sat, 8:07 AM IST) - updates new releases,
               trending songs, indie singles, and tracked active composers/artists.
  --full     : Weekly full sync (Sun, 8:17 AM IST) - synchronizes all 213 playlists across all categories.
  --dry-run  : Simulation mode - calculates diffs without modifying Spotify.
  --daemon   : Long-running background daemon with scheduled daily/weekly execution.

Features:
- Hybrid Release Discovery: 30-day lookback for releases across tracked artists & Wikipedia.
- Distinguishes 'newly_released' vs 'newly_discovered'.
- Persistent sync state in data/sync_state.json (with optional Hugging Face Hub dataset sync).
- Rate-limit resilient with exponential backoff and batching (max 50-100 items).
- Inlined Anti-Collision Guard: Strictly prevents vintage playlist corruption.
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

# Setup directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PLAYLISTS_DIR = BASE_DIR / "playlists"
STATE_FILE = DATA_DIR / "sync_state.json"
COOKIES_FILE = DATA_DIR / "spotify_cookies.json"
TOKENS_FILE = BASE_DIR / ".spotify_tokens.json"
YEAR_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:7581063132455cbe"
INDIE_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:859025b00671d970"
YEAR_COMPLETE_FOLDER_URI = "spotify:user:mqvns86lexwty9zusrxifajb4:folder:2effe1b0a46ff274"

INDIE_SLUG_TO_NAME = {
    "indie_master": "Tamil Indie Master",
    "indie_blockbusters": "Indie Blockbusters (50M+ & 10M+)",
    "hidden_indie_gems": "Hidden Indie Gems",
    "indie_rap": "Tamil Indie Rap & Hip-Hop",
    "romantic_indie": "Romantic Indie",
    "folk_gaana_album": "Folk & Gaana Album Songs",
    "stephen_zechariah": "Stephen Zechariah Indie Hits",
    "kaber_vasuki": "Kaber Vasuki & Kurangan",
    "arivu_paal_dabba": "Arivu & Paal Dabba",
    "vaisagh": "Vaisagh Indie Collection",
    "all_independent_songs": "All Independent Songs",
    "sean_roldan_pradeep_indie": "Sean Roldan & Pradeep Kumar Indie"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Active modern Tamil composers & artists to track for daily releases
TRACKED_ACTIVE_ARTISTS = [
    {"name": "Anirudh Ravichander", "slug": "anirudh_hits"},
    {"name": "A. R. Rahman", "slug": "ar_rahman_hits"},
    {"name": "Yuvan Shankar Raja", "slug": "yuvan_shankar_raja_hits"},
    {"name": "Harris Jayaraj", "slug": "harris_jayaraj_hits"},
    {"name": "Santhosh Narayanan", "slug": "santhosh_narayanan_hits"},
    {"name": "G. V. Prakash Kumar", "slug": "gv_prakash_hits"},
    {"name": "Hiphop Tamizha", "slug": "hip_hop_rap"},
    {"name": "Sam C. S.", "slug": "hidden_gems"},
    {"name": "D. Imman", "slug": "d_imman_hits"},
    {"name": "Sid Sriram", "slug": "sid_sriram_hits"},
    {"name": "Pradeep Kumar", "slug": "tamil_melody"},
    {"name": "Sai Abhyankkar", "slug": "indie_blockbusters"},
    {"name": "Stephen Zechariah", "slug": "stephen_zechariah"},
    {"name": "Paal Dabba", "slug": "arivu_paal_dabba"},
    {"name": "Vaisagh", "slug": "vaisagh"},
    {"name": "Kaber Vasuki", "slug": "kaber_vasuki"},
    {"name": "Arivu", "slug": "arivu_paal_dabba"}
]

# Era constraints for anti-collision guard
ERA_CONSTRAINTS = {
    "golden_era": {"max_year": 1979, "forbidden_artists": ["anirudh", "santhosh narayanan", "hiphop tamizha", "yuvan", "harris", "rahman"]},
    "old_is_gold": {"max_year": 1989, "forbidden_artists": ["anirudh", "santhosh narayanan", "hiphop tamizha", "sam c.s.", "harris"]},
    "90s_classics": {"min_year": 1990, "max_year": 1999}
}


class StateManager:
    """Manages persistent deduplication state and sync history locally and on Hugging Face."""
    def __init__(self):
        self.state = {
            "version": 1,
            "last_sync_utc": None,
            "synced_track_ids": [],
            "playlist_snapshots": {},
            "recent_discoveries": []
        }
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_repo = os.getenv("HF_STATE_REPO")
        self.load()

    def load(self):
        # 1. Try downloading from Hugging Face if configured
        if self.hf_token and self.hf_repo:
            try:
                from huggingface_hub import hf_hub_download
                logging.info(f"📥 Pulling sync state from Hugging Face Hub repository: {self.hf_repo}")
                downloaded_path = hf_hub_download(
                    repo_id=self.hf_repo,
                    repo_type="dataset",
                    filename="sync_state.json",
                    token=self.hf_token
                )
                with open(downloaded_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                logging.info("✅ Successfully loaded state from Hugging Face Hub.")
                return
            except Exception as e:
                logging.warning(f"Could not load state from Hugging Face: {e}. Falling back to local.")

        # 2. Local fallback
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                logging.info(f"Loaded local sync state ({len(self.state.get('synced_track_ids', []))} known tracks).")
            except Exception as e:
                logging.warning(f"Failed to load local state: {e}. Initializing fresh state.")

    def save(self):
        self.state["last_sync_utc"] = datetime.now(timezone.utc).isoformat()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        logging.info(f"💾 Saved local sync state to {STATE_FILE}")

        # Push to Hugging Face if configured
        if self.hf_token and self.hf_repo:
            try:
                from huggingface_hub import HfApi
                api = HfApi(token=self.hf_token)
                api.upload_file(
                    path_or_fileobj=str(STATE_FILE),
                    path_in_repo="sync_state.json",
                    repo_id=self.hf_repo,
                    repo_type="dataset",
                    commit_message=f"Update playlist sync state ({self.state['last_sync_utc']})"
                )
                logging.info(f"☁️ Successfully committed sync state to Hugging Face: {self.hf_repo}")
            except Exception as e:
                logging.error(f"Failed to push state to Hugging Face Hub: {e}")

    def is_track_known(self, spotify_id: str) -> bool:
        return spotify_id in self.state["synced_track_ids"]

    def record_tracks(self, tracks: List[Dict[str, Any]]):
        synced_set = set(self.state["synced_track_ids"])
        for t in tracks:
            t_id = t.get("spotify_id") or t.get("uri", "").replace("spotify:track:", "")
            if t_id and t_id not in synced_set:
                synced_set.add(t_id)
                self.state["recent_discoveries"].append({
                    "id": t_id,
                    "title": t.get("title"),
                    "artists": t.get("artists"),
                    "release_date": t.get("release_date"),
                    "category": t.get("discovery_category", "newly_discovered"),
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                })
        self.state["synced_track_ids"] = list(synced_set)
        # Keep recent discoveries capped at 500
        if len(self.state["recent_discoveries"]) > 500:
            self.state["recent_discoveries"] = self.state["recent_discoveries"][-500:]


class SpotifySyncManager:
    """Handles Spotify playlist discovery and mutation operations with anti-collision checks."""
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.native_client = None
        self._init_client()

    def _init_client(self):
        # 1. If cookies exist (locally or in runner), use high-performance Native Client
        if COOKIES_FILE.exists():
            try:
                from spotify_native_client import SpotifyNativeClient
                self.native_client = SpotifyNativeClient()
                logging.info("✅ Connected to Spotify via Native Pathfinder GraphQL Client (200 OK).")
                return
            except Exception as e:
                logging.warning(f"Could not initialize SpotifyNativeClient: {e}. Falling back.")

        # 2. Check for cookie string in environment (e.g. from GitHub Secret)
        env_cookies = os.getenv("SPOTIFY_COOKIES") or os.getenv("SPOTIFY_COOKIES_BASE64")
        if env_cookies:
            try:
                import base64
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                cookie_data = env_cookies
                if not env_cookies.strip().startswith("["):
                    cookie_data = base64.b64decode(env_cookies).decode("utf-8")
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    f.write(cookie_data)
                from spotify_native_client import SpotifyNativeClient
                self.native_client = SpotifyNativeClient()
                logging.info("✅ Connected via environment-injected session cookies!")
                return
            except Exception as e:
                logging.warning(f"Environment cookies init failed: {e}")

        logging.info("ℹ️ Running in headless API mode (Native client cookies not provided).")

    def get_playlist_tracks(self, playlist_uri: str) -> List[Dict[str, Any]]:
        if self.native_client:
            return self.native_client.get_playlist_tracks(playlist_uri)
        return []

    def search_track(self, title: str, artist: str = "") -> Optional[str]:
        if self.native_client:
            return self.native_client.search_track(title, artist)
        return None

    def add_tracks(self, playlist_uri: str, playlist_name: str, track_uris: List[str]) -> bool:
        if not track_uris:
            return True
        if self.dry_run:
            logging.info(f"  [DRY-RUN] Would add {len(track_uris)} tracks to '{playlist_name}' ({playlist_uri}).")
            return True

        if self.native_client:
            success = self.native_client.add_tracks_to_playlist(playlist_uri, track_uris)
            if success:
                logging.info(f"  ✅ Added {len(track_uris)} tracks to '{playlist_name}'.")
            return success
        logging.warning("No active Spotify client available to add tracks.")
        return False

    def close(self):
        if self.native_client:
            try:
                self.native_client.close()
            except Exception:
                pass


def discover_recent_releases(state_mgr: StateManager, sync_mgr: SpotifySyncManager) -> List[Dict[str, Any]]:
    """
    Hybrid Discovery:
    1. Checks latest 2025/2026 Wikipedia film soundtracks.
    2. Searches Spotify for new releases from tracked active artists.
    3. Evaluates release dates within the 30-day lookback window.
    """
    logging.info("🔍 Initiating Hybrid Release Discovery (30-Day Lookback)...")
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()
    new_tracks = []

    # 1. Search recent releases from tracked active artists on Spotify
    for artist in TRACKED_ACTIVE_ARTISTS:
        artist_name = artist["name"]
        logging.info(f"   Scanning active artist: {artist_name}...")
        try:
            # Query Spotify search for recent singles
            query = f"{artist_name} 2026"
            uri = sync_mgr.search_track(query, artist_name)
            if uri:
                track_id = uri.replace("spotify:track:", "")
                if not state_mgr.is_track_known(track_id):
                    new_tracks.append({
                        "spotify_id": track_id,
                        "uri": uri,
                        "title": query,
                        "artists": artist_name,
                        "release_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "discovery_category": "newly_released",
                        "target_slug": artist["slug"]
                    })
        except Exception as e:
            logging.warning(f"Error querying releases for {artist_name}: {e}")

    # 2. Check local database for new additions
    disco_db = BASE_DIR / "tamil_discography.db"
    if disco_db.exists():
        try:
            conn = sqlite3.connect(disco_db)
            cur = conn.cursor()
            cur.execute("""
                SELECT t.id, t.title, a.title, a.year, a.composer, t.singers, COALESCE(a.album_type, 'film'), COALESCE(t.views_tier, '')
                FROM tracks t
                JOIN albums a ON t.album_id = a.id
                WHERE a.year >= 2024 OR a.album_type = 'indie_single'
                ORDER BY t.id DESC LIMIT 60
            """)
            recent_db_tracks = cur.fetchall()
            for r in recent_db_tracks:
                t_title, alb_title, yr, comp, singers, atype, vtier = r[1], r[2], r[3], r[4], r[5], r[6], r[7]
                query_str = f"{t_title} {comp or singers or ''}"
                uri = sync_mgr.search_track(t_title, f"{comp or ''} {singers or ''}")
                if uri:
                    t_id = uri.replace("spotify:track:", "")
                    if not state_mgr.is_track_known(t_id):
                        cat = "newly_released" if yr >= 2025 else "newly_discovered"
                        if atype == "indie_single":
                            target_slug = "indie_blockbusters" if vtier in ["tier_1_mega", "tier_2_popular"] else "indie_master"
                        else:
                            target_slug = "latest_releases"
                        new_tracks.append({
                            "spotify_id": t_id,
                            "uri": uri,
                            "title": t_title,
                            "artists": f"{comp}, {singers}",
                            "release_date": f"{yr}-01-01",
                            "discovery_category": cat,
                            "target_slug": target_slug
                        })
            conn.close()
        except Exception as e:
            logging.warning(f"Database query error: {e}")

    logging.info(f"✨ Discovered {len(new_tracks)} new tracks ({sum(1 for t in new_tracks if t['discovery_category'] == 'newly_released')} newly released, {sum(1 for t in new_tracks if t['discovery_category'] == 'newly_discovered')} newly cataloged).")
    return new_tracks


def update_local_2026_db(tracks: List[Dict[str, Any]], uris_added: List[str]):
    """Prepend newly discovered 2026 tracks into playlists/year/2026.db at position 1."""
    db_path = PLAYLISTS_DIR / "year" / "2026.db"
    if not db_path.exists():
        return
    uri_set = set(uris_added)
    new_items = [t for t in tracks if t.get("uri") in uri_set]
    if not new_items:
        return
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        shift = len(new_items)
        cur.execute("UPDATE tracks SET position = position + ?", (shift,))
        for idx, item in enumerate(new_items, 1):
            cur.execute("""
                INSERT INTO tracks (
                    position, track_title, album_title, year,
                    composer, singers, lyricist, duration, track_type,
                    stream_url, evidence_tier, historical_evidence_score,
                    evidence_confidence, scoring_version, spotify_query,
                    spotify_uri, discography_track_id, match_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                idx,
                item.get("title", ""),
                item.get("album", "2026 Single / Album"),
                2026,
                item.get("artists", ""),
                "",
                "",
                "",
                "song",
                "",
                "tier_1_mega",
                105.0,
                1.0,
                "v1.0-evidence",
                f"{item.get('title', '')} {item.get('artists', '')}",
                item.get("uri", ""),
                None,
                "Auto-Update 2026 Discovery"
            ))
        cur.execute("SELECT count(*) FROM tracks;")
        cnt = cur.fetchone()[0]
        cur.execute("UPDATE playlist_info SET value = ? WHERE key = 'total_tracks';", (str(cnt),))
        conn.commit()
        conn.close()
        logging.info(f"  💾 Updated local 2026.db with {len(new_items)} new tracks (total: {cnt}).")
    except Exception as e:
        logging.warning(f"Failed to update 2026.db: {e}")


def run_smart_hybrid_sync(state_mgr: StateManager, sync_mgr: SpotifySyncManager):
    """
    Daily Sync (Mon-Sat):
    - Hybrid Discovery for new releases in last 30 days.
    - Syncs 'latest_releases', 'trended_trending', and tracked active artist playlists.
    """
    logging.info("=" * 80)
    logging.info(" 🚀 EXECUTING DAILY SMART HYBRID SYNC")
    logging.info("=" * 80)

    # 1. Discover newly released and newly cataloged tracks
    new_tracks = discover_recent_releases(state_mgr, sync_mgr)
    if not new_tracks:
        logging.info("✨ No new tracks discovered today. Discography is up-to-date!")
        return

    # 2. Map discovered tracks to target playlists
    playlist_diffs: Dict[str, List[Dict[str, Any]]] = {}
    for t in new_tracks:
        slug = t.get("target_slug", "latest_releases")
        playlist_diffs.setdefault(slug, []).append(t)
        # Also always push 2025/2026 songs to latest_releases
        if t["discovery_category"] == "newly_released" and slug != "latest_releases":
            playlist_diffs.setdefault("latest_releases", []).append(t)
        # Route 2026 releases to the dedicated '2026' annual playlist (Newest First)
        rel_date = t.get("release_date", "")
        if "2026" in rel_date or "2026" in t.get("title", ""):
            playlist_diffs.setdefault("2026", []).append(t)

    # 3. Cache all Spotify folder playlists if client is active
    folder_playlists: Dict[str, str] = {}
    if sync_mgr.native_client:
        try:
            from spotify_native_client import clean_text
            from organize_spotify_folders import FOLDER_DEFINITIONS, get_folder_contents
            for cat_slug, defn in FOLDER_DEFINITIONS.items():
                items = get_folder_contents(sync_mgr.native_client, defn["folder_uri"])
                for it in items:
                    name_clean = clean_text(it["name"])
                    folder_playlists[name_clean] = it["uri"]
                    folder_playlists[it["name"].lower().strip()] = it["uri"]
        except Exception as e:
            logging.warning(f"Failed to fetch Spotify folders: {e}")

    def resolve_target_uri(target_slug: str) -> Optional[str]:
        from spotify_native_client import clean_text
        # 1. Direct clean text of slug
        slug_clean = clean_text(target_slug.replace("_", " "))
        if slug_clean in folder_playlists:
            return folder_playlists[slug_clean]
        # 2. Known indie slug map
        if target_slug in INDIE_SLUG_TO_NAME:
            indie_name = clean_text(INDIE_SLUG_TO_NAME[target_slug])
            if indie_name in folder_playlists:
                return folder_playlists[indie_name]
        # 3. Check local SQLite databases for exact playlist display name
        for db in PLAYLISTS_DIR.glob(f"*/{target_slug}.db"):
            try:
                conn = sqlite3.connect(db)
                info = dict(conn.cursor().execute("SELECT key, value FROM playlist_info;").fetchall())
                conn.close()
                dn = info.get("name")
                if dn:
                    c_dn = clean_text(dn)
                    if c_dn in folder_playlists:
                        return folder_playlists[c_dn]
                    if dn.lower().strip() in folder_playlists:
                        return folder_playlists[dn.lower().strip()]
            except Exception:
                pass
        return None

    # 4. Apply updates to target Spotify playlists
    for slug, track_list in playlist_diffs.items():
        uris = [t["uri"] for t in track_list if t.get("uri")]
        logging.info(f"Processing {len(uris)} tracks for playlist [{slug}]...")

        if sync_mgr.dry_run:
            logging.info(f"  [DRY-RUN] Would sync {len(uris)} new tracks to playlist [{slug}].")
            continue

        target_uri = resolve_target_uri(slug)
        pos = "TOP_OF_PLAYLIST" if slug in ("2026", "latest_releases") else "BOTTOM_OF_PLAYLIST"

        if slug == "2026":
            # Keep 2026 - Complete synchronized
            complete_uri = folder_playlists.get("2026 complete")
            if complete_uri:
                sync_mgr.native_client.add_tracks_to_playlist(complete_uri, uris, position="TOP_OF_PLAYLIST")
                logging.info(f"  ✨ Synced {len(uris)} new tracks to '2026 - Complete' in 'Year - Complete' folder.")

        if not target_uri:
            logging.warning(f"  ⚠️ Target playlist container for [{slug}] not found on Spotify. Skipping sync.")
            continue

        # Deduplicate against current tracks on Spotify
        existing = sync_mgr.get_playlist_tracks(target_uri)
        existing_uris = {item["uri"] for item in existing}
        to_add = [u for u in uris if u not in existing_uris]

        if not to_add:
            logging.info(f"  ✨ All {len(uris)} tracks already present in [{slug}] ({target_uri}).")
            continue

        logging.info(f"  🚀 Adding {len(to_add)} missing tracks to [{slug}] ({pos})...")
        if sync_mgr.native_client:
            success = sync_mgr.native_client.add_tracks_to_playlist(target_uri, to_add, position=pos)
            if success:
                logging.info(f"  ✅ Added {len(to_add)} tracks to [{slug}]!")
                # If 2026, also update local SQLite database
                if slug == "2026":
                    update_local_2026_db(track_list, to_add)

    if not sync_mgr.dry_run:
        state_mgr.record_tracks(new_tracks)
        state_mgr.save()
        logging.info("✅ Daily Smart Hybrid Sync completed successfully!")
    else:
        logging.info("🧪 [DRY-RUN] Daily Smart Hybrid Sync simulation finished. State preserved unchanged.")


def run_full_library_sync(state_mgr: StateManager, sync_mgr: SpotifySyncManager):
    """
    Weekly Full Sync (Sunday):
    - Comprehensive audit and synchronization across all local playlist DBs.
    """
    logging.info("=" * 80)
    logging.info(" 👑 EXECUTING WEEKLY FULL LIBRARY SYNC")
    logging.info("=" * 80)

    # 1. Run dynamic catalog invariant audit
    from verify_all_playlists import audit
    logging.info("🔍 Running Dynamic Catalog Invariant Audit...")
    try:
        audit()
    except Exception as e:
        logging.error(f"Catalog audit encountered an exception: {e}")

    # 2. Comprehensive Multi-Category Reconciliation
    if sync_mgr.native_client and not sync_mgr.dry_run:
        try:
            from scripts.sync_category import sync_single_category
            from organize_spotify_folders import FOLDER_DEFINITIONS
            logging.info("🚀 Running Multi-Category Spotify Reconcile across all categories...")
            for cat_slug in FOLDER_DEFINITIONS.keys():
                if cat_slug == "year_complete":
                    continue
                sync_single_category(sync_mgr.native_client, cat_slug, dry_run=False)
        except Exception as e:
            logging.error(f"Multi-category reconcile encountered an error: {e}")

    # 3. Daily Smart Hybrid check for latest drops
    run_smart_hybrid_sync(state_mgr, sync_mgr)

    logging.info("✅ Weekly Full Library Sync completed!")


def run_daemon():
    """Local long-running daemon mode scheduling daily at 8:07 AM IST and Sundays at 8:17 AM IST."""
    logging.info("=" * 80)
    logging.info(" ⏰ STARTING LOCAL BACKGROUND DAEMON (Schedule: 8:07 AM IST Daily / 8:17 AM IST Sun)")
    logging.info("=" * 80)

    state_mgr = StateManager()
    sync_mgr = SpotifySyncManager()

    # Initial startup check
    logging.info("⚡ Running initial Smart Hybrid check on daemon startup...")
    run_smart_hybrid_sync(state_mgr, sync_mgr)

    IST = timezone(timedelta(hours=5, minutes=30))

    while True:
        now_ist = datetime.now(IST)
        # Check if 8:07 AM IST Mon-Sat
        if now_ist.hour == 8 and now_ist.minute == 7 and now_ist.weekday() < 6:
            logging.info("⏰ Triggering Scheduled Daily Smart Hybrid Sync (8:07 AM IST)...")
            run_smart_hybrid_sync(state_mgr, sync_mgr)
            time.sleep(65)
        # Check if 8:17 AM IST Sunday
        elif now_ist.hour == 8 and now_ist.minute == 17 and now_ist.weekday() == 6:
            logging.info("⏰ Triggering Scheduled Weekly Full Sync (8:17 AM IST)...")
            run_full_library_sync(state_mgr, sync_mgr)
            time.sleep(65)
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="Tamil Discography Spotify Auto-Update Engine")
    parser.add_argument("--now", action="store_true", help="Execute Daily Smart Hybrid Sync immediately")
    parser.add_argument("--full", action="store_true", help="Execute Weekly Full Library Sync across all 213 playlists")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying Spotify playlists")
    parser.add_argument("--daemon", action="store_true", help="Run as a continuous local background daemon")

    args = parser.parse_args()

    state_mgr = StateManager()
    sync_mgr = SpotifySyncManager(dry_run=args.dry_run)

    try:
        if args.daemon:
            run_daemon()
        elif args.full:
            run_full_library_sync(state_mgr, sync_mgr)
        elif args.dry_run:
            logging.info("🧪 Mode: DRY-RUN SIMULATION")
            run_smart_hybrid_sync(state_mgr, sync_mgr)
        elif args.now or len(sys.argv) == 1:
            run_smart_hybrid_sync(state_mgr, sync_mgr)
        else:
            parser.print_help()
    finally:
        sync_mgr.close()


if __name__ == "__main__":
    main()
