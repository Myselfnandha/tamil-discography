#!/usr/bin/env python3
"""
songmirror_importer.py - Self-Hosted, Unlimited Open-Source Spotify Playlist Importer.

Powered by SongMirror (Docker container on http://127.0.0.1:8888).
- 100% Free & Self-Hosted: No TuneMyMusic paywalls, no 500-track limits.
- Uses Spotify's internal web player API authenticated via your 'sp_dc' cookie.
- No Spotify Developer App or Spotify Premium subscription required.
- Full playlists supported in 1 single shot (even 2,000+ tracks!).
- Tracks matching progress and live playlist creation with full resume support.
"""

import sys
import time
import json
import argparse
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "playlists" / "spotify_exports" / "csv"
PROGRESS_FILE = BASE_DIR / "data" / "songmirror_progress.json"
SONGMIRROR_URL = "http://127.0.0.1:8888"


def check_songmirror() -> bool:
    """Verifies that the SongMirror container is running and Spotify is connected."""
    try:
        r = requests.get(f"{SONGMIRROR_URL}/health", timeout=5)
        if r.status_code != 200:
            return False
        
        accs = requests.get(f"{SONGMIRROR_URL}/api/accounts", timeout=20).json()
        return any(a.get("provider") == "spotify" and a.get("state") == "connected" for a in accs)
    except Exception as e:
        print(f"⚠️ Health check exception: {e}")
        return False


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {"completed": {}, "failed": {}}


def save_progress(progress: dict):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def import_csv_to_spotify(csv_path: Path, playlist_name: str = None) -> tuple:
    """Uploads a CSV to SongMirror, runs track matching, and creates the Spotify playlist."""
    clean_name = playlist_name or csv_path.stem.replace("_", " ").title()
    print(f"\n🎵 [SongMirror] Importing: '{clean_name}' ({csv_path.name})...")

    # Check if a matching job already exists on SongMirror
    existing_jobs = requests.get(f"{SONGMIRROR_URL}/api/imports").json().get("jobs", [])
    matching_job = next((j for j in existing_jobs if j.get("source_name") == csv_path.stem or j.get("destination_name") == clean_name), None)

    if matching_job:
        job_id = matching_job["id"]
        total_tracks = matching_job.get("total_tracks", 0)
        status = matching_job.get("status")
        dest_id = matching_job.get("destination_playlist_id")
        print(f"   Found existing job ({job_id}) with status '{status}' for '{clean_name}'.")

        if status == "done" and dest_id:
            print(f"   🎉 Playlist already completed on Spotify: https://open.spotify.com/playlist/{dest_id}")
            return True, dest_id
    else:
        # 1. Upload CSV to SongMirror
        with open(csv_path, "rb") as f:
            files = {"file": (csv_path.name, f, "text/csv")}
            data = {
                "destination_account": "profile_default_spotify",
                "destination_mode": "create",
                "name": clean_name,
                "public": "false"
            }
            res = requests.post(f"{SONGMIRROR_URL}/api/imports/file", files=files, data=data)

        if res.status_code != 201:
            print(f"❌ Failed to parse file on SongMirror: {res.text}")
            return False, None

        job = res.json()
        job_id = job["id"]
        total_tracks = job.get("total_tracks", 0)
        print(f"   Parsed {total_tracks} tracks from CSV. Job ID: {job_id}")

        # 2. Trigger Track Matching
        m_res = requests.post(f"{SONGMIRROR_URL}/api/imports/{job_id}/match")
        if m_res.status_code != 202:
            print(f"❌ Failed to initiate track matching: {m_res.text}")
            return False, None

    # Monitor track matching if still in progress
    cur_poll = requests.get(f"{SONGMIRROR_URL}/api/imports/{job_id}").json().get("job", {})
    if cur_poll.get("status") in ["parsing", "matching"]:
        print("   🔍 Matching tracks against Spotify catalog (ISRC + RapidFuzz)...")
        last_matched = -1
        while True:
            time.sleep(3)
            poll = requests.get(f"{SONGMIRROR_URL}/api/imports/{job_id}").json()
            cur_job = poll.get("job", {})
            status = cur_job.get("status")
            matched = cur_job.get("matched_tracks", 0)

            if matched != last_matched:
                print(f"      Matched: {matched}/{total_tracks} tracks...")
                last_matched = matched

            if status in ["ready", "matched", "ready_to_create"]:
                print(f"   ✅ Matching complete! ({matched}/{total_tracks} matched)")
                break
            elif status in ["error", "failed"]:
                print(f"   ❌ Matching failed: {cur_job.get('error')}")
                return False, None

    # 3. Create Playlist & Insert Tracks
    print(f"   🚀 Creating Spotify playlist '{clean_name}' and adding tracks...")
    c_res = requests.post(f"{SONGMIRROR_URL}/api/imports/{job_id}/create")
    if c_res.status_code != 202:
        print(f"❌ Failed to trigger playlist creation: {c_res.text}")
        return False, None

    last_added = -1
    dest_id = None
    while True:
        time.sleep(3)
        poll = requests.get(f"{SONGMIRROR_URL}/api/imports/{job_id}").json()
        cur_job = poll.get("job", {})
        status = cur_job.get("status")
        added = cur_job.get("tracks_added", 0)
        dest_id = cur_job.get("destination_playlist_id") or dest_id

        if added != last_added:
            print(f"      Added: {added} tracks to Spotify...")
            last_added = added

        if status == "done":
            print(f"   🎉 SUCCESS! Playlist created on Spotify.")
            print(f"   🔗 Spotify Playlist URL: https://open.spotify.com/playlist/{dest_id}")
            return True, dest_id
        elif status in ["error", "failed"]:
            print(f"   ❌ Playlist creation failed: {cur_job.get('error')}")
            return False, None


def run_pipeline(slug: str = None, curated: bool = False, all_playlists: bool = False, test: bool = False):
    print("=" * 80)
    print(" 🪞 SONGMIRROR SELF-HOSTED SPOTIFY BULK IMPORTER")
    print("=" * 80)
    print(f"SongMirror Server : {SONGMIRROR_URL}")
    print(f"Web Dashboard     : http://localhost:8888")
    print("-" * 80)

    if not check_songmirror():
        print("❌ Error: SongMirror is not reachable or Spotify is not connected.")
        print("   Make sure Docker is running: cd /home/nandha/play/songmirror && docker compose up -d")
        return

    # For SongMirror, we use the FULL unchunked master CSV files (no 500 track limit!)
    all_csvs = sorted(list(CSV_DIR.glob("*.csv")))
    # Exclude partial chunk files and bulk combined files
    master_csvs = [f for f in all_csvs if not f.name.startswith("bulk_") and "_part" not in f.stem]

    if test:
        targets = [f for f in master_csvs if "sid_sriram" in f.name][:1]
        if not targets:
            targets = master_csvs[:1]
    elif slug:
        targets = [f for f in master_csvs if slug.lower() in f.stem.lower()]
    elif curated:
        from export_spotify import CURATED_SLUGS
        targets = [f for f in master_csvs if any(s in f.stem.lower() for s in CURATED_SLUGS)]
    elif all_playlists:
        targets = master_csvs
    else:
        print("💡 Usage:")
        print("   python3 songmirror_importer.py --test              (Test with 1 small playlist)")
        print("   python3 songmirror_importer.py --slug 90s_classics (Import specific full playlist)")
        print("   python3 songmirror_importer.py --curated           (Import top 32 curated collections)")
        print("   python3 songmirror_importer.py --all               (Import all 135 full playlists)")
        return

    progress = load_progress()
    pending = [f for f in targets if f.name not in progress["completed"]]

    print(f"Total Selected Playlists : {len(targets)}")
    print(f"Already Completed        : {len(targets) - len(pending)}")
    print(f"Pending to Transfer      : {len(pending)}\n")

    if not pending:
        print("🎉 All selected playlists have already been imported!")
        return

    for idx, csv_file in enumerate(pending, 1):
        print(f"[{idx}/{len(pending)}] Processing: {csv_file.name}")
        clean_name = csv_file.stem.replace("_", " ").title()
        try:
            ok, playlist_id = import_csv_to_spotify(csv_file, playlist_name=clean_name)
            if ok:
                progress["completed"][csv_file.name] = {
                    "playlist_name": clean_name,
                    "playlist_id": playlist_id,
                    "url": f"https://open.spotify.com/playlist/{playlist_id}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                save_progress(progress)
            else:
                progress["failed"][csv_file.name] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_progress(progress)
        except Exception as e:
            print(f"⚠️ Exception during import of {csv_file.name}: {e}")
            progress["failed"][csv_file.name] = str(e)
            save_progress(progress)

        time.sleep(2)

    print("\n" + "=" * 80)
    print(" 🎉 ALL BATCH IMPORTS COMPLETED VIA SONGMIRROR!")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="SongMirror automated Spotify playlist importer.")
    parser.add_argument("--test", action="store_true", default=False, help="Test with 1 playlist")
    parser.add_argument("--slug", type=str, default=None, help="Import a specific playlist slug (e.g. 90s_classics)")
    parser.add_argument("--curated", action="store_true", default=False, help="Import top 32 curated playlists")
    parser.add_argument("--all", action="store_true", default=False, help="Import all 135 playlists")

    args = parser.parse_args()
    run_pipeline(slug=args.slug, curated=args.curated, all_playlists=args.all, test=args.test)


if __name__ == "__main__":
    main()
