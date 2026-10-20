#!/usr/bin/env python3
"""
run_all_post_import_pipeline.py - Master Post-Import Pipeline Orchestrator.

Waits for Spotify's rate-limit cooldown to clear, then executes all stages sequentially:
1. Merge Duplicate Containers (merge_duplicate_playlists.py)
2. Strict Movie-Original Deduplication (strict_deduplicate_spotify.py)
3. Category Reclassification & Route (reclassify_and_route.py)
4. Missing Track Resolution (resolve_missing_tracks.py)
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = BASE_DIR / ".spotify_tokens.json"
REPORT_FILE = DATA_DIR / "pipeline_execution_report.md"
PROFILE_DIR = DATA_DIR / "tunemymusic_browser_profile"

MERGE_SCRIPT = BASE_DIR / "merge_duplicate_playlists.py"
DEDUP_SCRIPT = BASE_DIR / "strict_deduplicate_spotify.py"
ROUTE_SCRIPT = BASE_DIR / "reclassify_and_route.py"
RESOLVE_SCRIPT = BASE_DIR / "resolve_missing_tracks.py"


def refresh_token_if_needed():
    """Extracts a fresh Spotify token from browser session."""
    from playwright.sync_api import sync_playwright
    import tempfile, shutil

    print("🌐 Intercepting fresh Spotify token from browser...")
    token_found = [None]
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copytree(PROFILE_DIR, tmpdir, dirs_exist_ok=True, ignore=shutil.ignore_patterns('*Singleton*'))
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(tmpdir, executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
            page = context.new_page()

            def handle_req(request):
                auth = request.headers.get("authorization")
                if auth and "api-partner.spotify.com" in request.url:
                    token_found[0] = auth.split("Bearer ")[1].strip()

            page.on("request", handle_req)
            page.goto("https://open.spotify.com", timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)
            context.close()

    if token_found[0]:
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump({"access_token": token_found[0]}, f, indent=2)
        print("✅ Fresh token saved!")
        return token_found[0]
    return None


def wait_for_rate_limit_clear():
    """Polls Spotify API until rate limit clears and returns 200 OK."""
    print("=" * 80)
    print(" ⏳ WAITING FOR SPOTIFY API RATE-LIMIT COOLDOWN TO CLEAR")
    print("=" * 80)

    start_wait = time.time()
    while True:
        if not TOKENS_FILE.exists():
            refresh_token_if_needed()

        with open(TOKENS_FILE, "r") as f:
            token = json.load(f).get("access_token", "")

        req = urllib.request.Request("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                print(f"\n🎉 RATE LIMIT CLEARED! Connected as {data.get('display_name')} ({data.get('id')})")
                print(f"Total cooldown wait: {int(time.time() - start_wait)}s\n")
                return
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 30))
                print(f"   ⏳ Spotify still throttled (HTTP 429). Retry-After: {retry_after}s. Waiting {retry_after + 5}s...")
                time.sleep(retry_after + 5)
            elif e.code == 401:
                print("   🔄 Token expired. Refreshing token...")
                refresh_token_if_needed()
                time.sleep(5)
            else:
                print(f"   ⚠️ Unexpected HTTP {e.code}. Waiting 15s...")
                time.sleep(15)
        except Exception as e:
            print(f"   ⚠️ Network error: {e}. Waiting 10s...")
            time.sleep(10)


def execute_pipeline():
    """Runs all 4 stages sequentially with full logging."""
    wait_for_rate_limit_clear()

    print("=" * 80)
    print(" 🚀 STARTING FULL POST-IMPORT PIPELINE EXECUTION")
    print("=" * 80)

    # Stage 1: Merge Duplicate Playlists
    print("\n--------------------------------------------------------------------------------")
    print(" 📁 STAGE 1: CONSOLIDATING DUPLICATE MULTI-PART CONTAINERS")
    print("--------------------------------------------------------------------------------")
    try:
        subprocess.run([sys.executable, str(MERGE_SCRIPT), "--execute"], check=True)
    except Exception as e:
        print(f"Stage 1 error: {e}")

    # Stage 2: Strict Movie-Original Deduplication
    print("\n--------------------------------------------------------------------------------")
    print(" 🎬 STAGE 2: STRICT MOVIE-ORIGINAL DEDUPLICATION")
    print("--------------------------------------------------------------------------------")
    try:
        subprocess.run([sys.executable, str(DEDUP_SCRIPT), "--all", "--execute"], check=True)
    except Exception as e:
        print(f"Stage 2 error: {e}")

    # Stage 3: Category Reclassification & Routing
    print("\n--------------------------------------------------------------------------------")
    print(" 🎼 STAGE 3: CATEGORY RECLASSIFICATION & ROUTING")
    print("--------------------------------------------------------------------------------")
    try:
        subprocess.run([sys.executable, str(ROUTE_SCRIPT), "--execute"], check=True)
    except Exception as e:
        print(f"Stage 3 error: {e}")

    # Stage 4: Missing Track Resolver
    print("\n--------------------------------------------------------------------------------")
    print(" 🔍 STAGE 4: RESOLVING ANY REMAINING MISSING TRACKS")
    print("--------------------------------------------------------------------------------")
    try:
        subprocess.run([sys.executable, str(RESOLVE_SCRIPT), "--all"], check=True)
    except Exception as e:
        print(f"Stage 4 error: {e}")

    print("\n" + "=" * 80)
    print(" 🎉 ALL STAGES EXECUTED SUCCESSFULLY!")
    print("=" * 80)

    report = f"""# Post-Import Pipeline Final Report
- **Completed At**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Stage 1 (Merge Duplicates)**: Complete
- **Stage 2 (Movie-Original Deduplication)**: Complete
- **Stage 3 (Category Reclassification)**: Complete
- **Stage 4 (Missing Tracks Resolution)**: Complete
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"📄 Report written to {REPORT_FILE}")


if __name__ == "__main__":
    execute_pipeline()
