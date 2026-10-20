#!/usr/bin/env python3
"""
tunemymusic_automator.py - Automated Bulk TuneMyMusic Playlist Importer to Spotify.

Features:
- Splits playlists into <= 480 song chunks (under TuneMyMusic's 500-song free limit).
- Keeps the exact same playlist name in all chunks so Spotify merges them into ONE single playlist.
- Launches a persistent Chromium browser window on your Linux desktop.
- You connect Spotify ONCE; the persistent profile keeps you logged in across all files.
- Automatically loops through CSV chunks: uploads file, selects Spotify, starts transfer, and monitors completion.
- Tracks completed uploads in 'tunemymusic_progress.json' so you can pause and resume anytime.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, BrowserContext

BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "playlists" / "spotify_exports" / "csv"
PROFILE_DIR = BASE_DIR / "data" / "tunemymusic_browser_profile"
PROGRESS_FILE = BASE_DIR / "data" / "tunemymusic_progress.json"
CHROMIUM_EXEC = "/usr/bin/chromium"

TUNEMYMUSIC_URL = "https://www.tunemymusic.com/transfer?mode=spotify&UI2=false"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {"completed": [], "failed": []}


def save_progress(progress: dict):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


SPOTIFY_COOKIES_FILE = BASE_DIR / "data" / "spotify_cookies.json"


def load_cookies() -> list:
    if not SPOTIFY_COOKIES_FILE.exists():
        return []
    try:
        raw_cookies = json.loads(SPOTIFY_COOKIES_FILE.read_text())
        playwright_cookies = []
        for c in raw_cookies:
            cookie_obj = {
                'name': c['name'],
                'value': c['value'],
                'domain': c['domain'],
                'path': c.get('path', '/'),
                'secure': c.get('secure', False),
                'httpOnly': c.get('httpOnly', False)
            }
            same_site = c.get('sameSite')
            if same_site in ['lax', 'strict', 'none']:
                cookie_obj['sameSite'] = same_site.capitalize()
            playwright_cookies.append(cookie_obj)
        return playwright_cookies
    except Exception as e:
        print(f"⚠️ Failed to parse Spotify cookies: {e}")
        return []


def transfer_single_csv(page: Page, csv_path: Path, is_first: bool = False, timeout: int = 180) -> bool:
    """Uploads a single CSV to TuneMyMusic and initiates transfer to Spotify."""
    # 1-3. Open transfer page & upload CSV file with resilient retries
    uploaded = False
    for attempt in range(3):
        try:
            page.goto(TUNEMYMUSIC_URL, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            upload_source = page.locator("text='Upload file'").first
            upload_source.wait_for(state="visible", timeout=20000)
            upload_source.click()
            time.sleep(1.5)

            file_input = page.locator("input[type='file']")
            file_input.wait_for(state="attached", timeout=20000)
            file_input.set_input_files(str(csv_path))
            uploaded = True
            break
        except Exception as e:
            print(f"       ⚠️ Upload attempt {attempt + 1} failed ({e}). Retrying...")
            time.sleep(3)

    if not uploaded:
        print(f"       ❌ Failed to upload {csv_path.name} after 3 attempts.")
        return False
    time.sleep(1.5)

    # 4. Handle Field Mapping screen if present: Map Playlist Name column
    try:
        page.locator("select").first.wait_for(state="visible", timeout=4000)
        selects = page.locator('select').all()
        if len(selects) >= 3:
            try:
                selects[2].select_option(label='Playlist Name')
                time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass

    continue_btn = page.locator("button:has-text('Continue'), span:has-text('Continue'), div:has-text('Continue')").last
    try:
        if continue_btn.is_visible(timeout=6000):
            continue_btn.click()
            time.sleep(1.5)
    except Exception:
        pass

    # 5. In Partner Mode: Wait for and click "Transfer to Spotify" directly!
    # TuneMyMusic needs 5-15 seconds to parse and match 480 tracks before showing the button.
    transfer_started = False
    transfer_direct = page.locator("button:has-text('Transfer to Spotify'), button:has-text('Transfer Now')").first
    try:
        transfer_direct.wait_for(state="visible", timeout=30000)
        print("    👉 Starting direct Spotify partner transfer...")
        transfer_direct.click()
        transfer_started = True
    except Exception:
        pass

    if not transfer_started:
        # Check if an additional Continue or Next button is needed
        extra_cont = page.locator("button:has-text('Continue'), button:has-text('Select Destination')").last
        if extra_cont.is_visible(timeout=3000):
            extra_cont.click()
            time.sleep(1.5)
            try:
                transfer_direct.wait_for(state="visible", timeout=15000)
                print("    👉 Starting direct Spotify partner transfer (after step)...")
                transfer_direct.click()
                transfer_started = True
            except Exception:
                pass

    if not transfer_started:
        # Fallback to standard 4-step wizard
        choose_dest = page.locator("button:has-text('Choose Destination'), div:has-text('Choose Destination'), span:has-text('Choose Destination')").last
        if choose_dest.is_visible(timeout=5000):
            choose_dest.click()
            time.sleep(1.5)

        spotify_btn = page.locator("button[title='Spotify'], button[aria-label='Spotify'], button[name='Spotify']").first
        if spotify_btn.is_visible(timeout=10000):
            try:
                with page.expect_popup(timeout=4000) as popup_info:
                    spotify_btn.click()
                popup = popup_info.value
                popup.wait_for_load_state("domcontentloaded")
                time.sleep(1.5)
                popup.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll('button[data-testid="auth-accept"], button:has-text("Agree")'));
                    for (const b of btns) {
                        b.scrollIntoView();
                        b.click();
                    }
                }''')
                time.sleep(3)
            except Exception:
                pass

        time.sleep(2)
        start_transfer_btn = page.locator("button:has-text('Start Transfer')").first
        if start_transfer_btn.is_visible(timeout=15000):
            start_transfer_btn.click()
            transfer_started = True

    if not transfer_started:
        print("    ⚠️ Transfer button not ready or not found. Skipping file.")
        return False

    print("    ⏳ Transfer started! Monitoring progress...")

    # 6. Monitor progress until completion
    start_time = time.time()
    success = False
    last_status = ""
    while time.time() - start_time < timeout:
        page_text = page.locator("body").inner_text()
        
        # Print live progress if visible
        for line in page_text.splitlines():
            clean = line.strip()
            if "processed:" in clean.lower() and clean != last_status:
                print(f"       {clean}")
                last_status = clean

        if "Transfer Complete" in page_text or "Transfer completed" in page_text or "Open Your Library in Spotify" in page_text or "Summary" in page_text:
            print("    ✅ Transfer completed successfully!")
            success = True
            break
        elif "Error" in page_text and "Something went wrong" in page_text:
            print("    ❌ TuneMyMusic reported an error.")
            break
        time.sleep(2)

    return success


def run_automator(slug: str = None, curated: bool = False, all_playlists: bool = False, test: bool = False, headless: bool = False):
    print("=" * 80)
    print(" 🎵 TUNEMYMUSIC SPOTIFY AUTOMATED BULK IMPORTER")
    print("=" * 80)
    print(f"Browser Profile Directory : {PROFILE_DIR}")
    print(f"CSV Source Directory      : {CSV_DIR}")
    print(f"Headless Mode             : {headless}")
    print("-" * 80)

    if not CSV_DIR.exists():
        print(f"❌ Error: CSV directory {CSV_DIR} does not exist.")
        return

    all_csvs = sorted(list(CSV_DIR.glob("*.csv")))
    # Filter out bulk master CSVs
    all_csvs = [f for f in all_csvs if not f.name.startswith("bulk_")]

    # Critical: Filter out unchunked parent files if chunked parts exist
    # (e.g. keep 90s_classics_part*.csv, exclude the 2,172-song unchunked 90s_classics.csv)
    chunked_stems = {f.stem.rsplit('_part', 1)[0] for f in all_csvs if '_part' in f.stem}
    all_csvs = [f for f in all_csvs if f.stem not in chunked_stems]

    if test:
        targets = [f for f in all_csvs if "sid_sriram" in f.name][:1]
        if not targets:
            targets = all_csvs[:1]
    elif slug:
        targets = [f for f in all_csvs if slug.lower() in f.stem.lower()]
    elif curated:
        from export_spotify import CURATED_SLUGS
        targets = [f for f in all_csvs if any(s in f.stem.lower() for s in CURATED_SLUGS)]
    elif all_playlists:
        targets = all_csvs
    else:
        print("💡 Please specify which playlists to import:")
        print("   python3 tunemymusic_automator.py --test              (Test 1 small playlist)")
        print("   python3 tunemymusic_automator.py --slug 90s_classics (Import specific playlist)")
        print("   python3 tunemymusic_automator.py --curated           (Import top 32 collections)")
        print("   python3 tunemymusic_automator.py --all               (Import all 135 playlists)")
        return

    progress = load_progress()
    pending = [f for f in targets if f.name not in progress["completed"]]

    print(f"Total Selected Files : {len(targets)}")
    print(f"Already Completed    : {len(targets) - len(pending)}")
    print(f"Pending to Transfer  : {len(pending)}\n")

    if not pending:
        print("🎉 All selected files have already been completed!")
        return

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("🌐 Launching Chromium browser session...")
        context: BrowserContext = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            executable_path=CHROMIUM_EXEC,
            headless=headless,
            args=["--start-maximized", "--no-sandbox", "--disable-popup-blocking"],
            viewport=None
        )

        cookies = load_cookies()
        if cookies:
            context.add_cookies(cookies)

        page = context.pages[0] if context.pages else context.new_page()

        for idx, csv_file in enumerate(pending, 1):
            is_first = (idx == 1 and len(progress["completed"]) == 0)
            print(f"[{idx}/{len(pending)}] Queueing: {csv_file.name}")
            try:
                ok = transfer_single_csv(page, csv_file, is_first=is_first)
                if not ok:
                    print(f"    🔄 Retrying once for {csv_file.name}...")
                    time.sleep(2)
                    ok = transfer_single_csv(page, csv_file, is_first=False)

                if ok:
                    if csv_file.name not in progress["completed"]:
                        progress["completed"].append(csv_file.name)
                    if csv_file.name in progress["failed"]:
                        progress["failed"].remove(csv_file.name)
                    save_progress(progress)
                else:
                    if csv_file.name not in progress["failed"]:
                        progress["failed"].append(csv_file.name)
                    save_progress(progress)
            except Exception as e:
                print(f"    ⚠️ Exception during transfer of {csv_file.name}: {e}")
                if csv_file.name not in progress["failed"]:
                    progress["failed"].append(csv_file.name)
                save_progress(progress)

            time.sleep(2)

        context.close()
        print("\n" + "=" * 80)
        print(" 🎉 BATCH TRANSFER COMPLETED!")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Automate TuneMyMusic CSV playlist uploads to Spotify.")
    parser.add_argument("--test", action="store_true", default=False, help="Run a test transfer with 1 small playlist")
    parser.add_argument("--slug", type=str, default=None, help="Transfer a specific playlist slug (e.g. 90s_classics, anirudh_hits)")
    parser.add_argument("--curated", action="store_true", default=False, help="Transfer top 32 curated playlists")
    parser.add_argument("--all", action="store_true", default=False, help="Transfer all 135 playlists (~350 chunk files)")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser in headless mode (after first login)")

    args = parser.parse_args()
    run_automator(slug=args.slug, curated=args.curated, all_playlists=args.all, test=args.test, headless=args.headless)


if __name__ == "__main__":
    main()
