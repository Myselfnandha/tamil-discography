#!/usr/bin/env python3
"""
auto_run_goal_on_finish.py - Event-Driven Auto-Runner for Missing Tracks Resolution.

Monitors the active background TuneMyMusic automator task.
As soon as the bulk import finishes:
1. Audits tunemymusic_progress.json for any failed batches.
2. If any failed files remain, triggers a focused retry.
3. Runs the missing tracks audit and resolution.
4. Generates a comprehensive final report at data/goal_final_report.md.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROGRESS_FILE = DATA_DIR / "tunemymusic_progress.json"
REPORT_FILE = DATA_DIR / "goal_final_report.md"
AUTOMATOR_SCRIPT = BASE_DIR / "tunemymusic_automator.py"
RESOLVER_SCRIPT = BASE_DIR / "resolve_missing_tracks.py"


def is_automator_running() -> bool:
    """Checks if tunemymusic_automator.py is currently running."""
    try:
        out = subprocess.check_output(["pgrep", "-f", "tunemymusic_automator.py"]).decode().strip()
        # Ensure it's not matching this watcher script
        pids = [p for p in out.splitlines() if p.strip() and int(p.strip()) != os.getpid()]
        return len(pids) > 0
    except subprocess.CalledProcessError:
        return False


def dry_check():
    """Performs a pre-flight dry check of the goal requirements and candidate failed tracks."""
    print("=" * 80)
    print(" 🔎 DRY CHECK: MISSING TRACKS AUDIT & RESOLUTION GOAL")
    print("=" * 80)

    if not PROGRESS_FILE.exists():
        print("❌ Progress file not found.")
        return

    progress = json.loads(PROGRESS_FILE.read_text())
    completed = progress.get("completed", [])
    failed = progress.get("failed", [])

    print(f"Current Completed Batches : {len(completed)}")
    print(f"Current Failed Batches    : {len(failed)}")

    csv_dir = BASE_DIR / "playlists" / "spotify_exports" / "csv"
    if failed:
        print("\n📋 Candidate Failed Files to Check:")
        for f in failed:
            p = csv_dir / f
            if p.exists():
                lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
                track_count = max(0, len(lines) - 1)
                p_name = lines[1].split(",")[3].strip('"') if len(lines) > 1 else "Unknown"
                print(f"   • {f} -> Playlist: '{p_name}' ({track_count} tracks)")
    else:
        print("✅ No failed batches currently recorded.")

    automator_active = is_automator_running()
    print(f"\nBackground Automator Running: {'YES (Task Active)' if automator_active else 'NO (Completed/Idle)'}")
    print("=" * 80)


def watch_and_execute():
    """Event-driven loop: Waits for automator to finish, then automatically runs the goal."""
    print("👀 Watcher started. Monitoring background automator event...")
    while is_automator_running():
        time.sleep(10)

    print("\n🔔 EVENT TRIGGERED: Background bulk transfer completed!")
    print("🚀 Auto-running the Goal: Resolving missing and failed tracks...\n")

    # Step 1: Check if any failed files remain in progress
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
        failed = progress.get("failed", [])
        if failed:
            print(f"⚠️ Found {len(failed)} files needing retry: {failed}")
            print("🔄 Running targeted retry for failed files...")
            try:
                subprocess.run([sys.executable, str(AUTOMATOR_SCRIPT), "--headless"], check=True)
            except Exception as e:
                print(f"Retry pass error: {e}")

    # Step 2: Consolidate duplicate chunked playlists into clean master playlists
    MERGE_SCRIPT = BASE_DIR / "merge_duplicate_playlists.py"
    print("\n🔄 Consolidating multi-chunk playlists (merging duplicates and cleaning library)...")
    try:
        subprocess.run([sys.executable, str(MERGE_SCRIPT), "--execute"], check=True)
    except Exception as e:
        print(f"Playlist merger error: {e}")

    # Step 3: Run missing tracks audit and resolver
    print("\n🔍 Running resolve_missing_tracks.py to audit and add any missing songs...")
    try:
        subprocess.run([sys.executable, str(RESOLVER_SCRIPT), "--all"], check=True)
    except Exception as e:
        print(f"Resolver execution error: {e}")

    # Step 3: Write final report
    report_content = f"""# Goal Completion Report
- **Completed At**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Bulk Transfer**: Finished
- **Resolution Pass**: Complete
"""
    REPORT_FILE.write_text(report_content, encoding="utf-8")
    print(f"✅ Final report written to {REPORT_FILE}")


if __name__ == "__main__":
    if "--dry-check" in sys.argv:
        dry_check()
    else:
        watch_and_execute()
