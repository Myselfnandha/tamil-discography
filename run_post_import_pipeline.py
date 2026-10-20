#!/usr/bin/env python3
"""
run_post_import_pipeline.py - Master Orchestrator for 100% Free Spotify Library Optimization.

Executes Option B (Fast-Track):
1. Stage 1: Merge Duplicate Playlist Containers (416 -> 136 clean master playlists)
2. Stage 2: Audit & Resolve Missing Tracks (Cross-references CSVs, searches and adds missing tracks)
3. Stage 3: Strict Movie-Original Deduplication (Keeps authentic earliest film OSTs, drops secondary)
4. Stage 4: Intelligent Category Reclassification & Routing (Routes misfiled tracks)

Powered by SpotifyNativeClient (Pathfinder GraphQL engine: 200 OK, zero rate limits).
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

from spotify_native_client import SpotifyNativeClient
from merge_duplicate_playlists import run_merge
from resolve_missing_tracks import audit_and_resolve
from strict_deduplicate_spotify import run_strict_deduplication
from reclassify_and_route import audit_and_reclassify_tracks

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_FILE = DATA_DIR / "post_import_pipeline_summary.json"


def main():
    start_time = time.time()
    print("=" * 80)
    print(" 🚀 SPOTIFY POST-IMPORT OPTIMIZATION PIPELINE (FAST-TRACK OPTION B)")
    print(f" Started At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    summary = {
        "start_time": datetime.now().isoformat(),
        "stages": {},
        "status": "RUNNING"
    }

    client = SpotifyNativeClient()

    try:
        # =========================================================================
        # STAGE 1: MERGE DUPLICATE PLAYLIST CONTAINERS
        # =========================================================================
        print("\n" + "#" * 80)
        print(" [STAGE 1/4] MERGING DUPLICATE PLAYLIST CONTAINERS")
        print("#" * 80)
        s1_start = time.time()
        try:
            run_merge(execute=True, client=client)
            summary["stages"]["stage_1_merge"] = {
                "status": "SUCCESS",
                "duration_seconds": round(time.time() - s1_start, 2)
            }
        except Exception as e:
            print(f"❌ Error during Stage 1: {e}")
            summary["stages"]["stage_1_merge"] = {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": round(time.time() - s1_start, 2)
            }

        # =========================================================================
        # STAGE 2: RESOLVE MISSING TRACKS
        # =========================================================================
        print("\n" + "#" * 80)
        print(" [STAGE 2/4] AUDITING & RESOLVING MISSING TRACKS")
        print("#" * 80)
        s2_start = time.time()
        try:
            audit_and_resolve(client=client)
            summary["stages"]["stage_2_resolve"] = {
                "status": "SUCCESS",
                "duration_seconds": round(time.time() - s2_start, 2)
            }
        except Exception as e:
            print(f"❌ Error during Stage 2: {e}")
            summary["stages"]["stage_2_resolve"] = {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": round(time.time() - s2_start, 2)
            }

        # =========================================================================
        # STAGE 3: STRICT MOVIE-ORIGINAL DEDUPLICATION
        # =========================================================================
        print("\n" + "#" * 80)
        print(" [STAGE 3/4] STRICT MOVIE-ORIGINAL DEDUPLICATION")
        print("#" * 80)
        s3_start = time.time()
        try:
            run_strict_deduplication(client=client, execute=True)
            summary["stages"]["stage_3_deduplication"] = {
                "status": "SUCCESS",
                "duration_seconds": round(time.time() - s3_start, 2)
            }
        except Exception as e:
            print(f"❌ Error during Stage 3: {e}")
            summary["stages"]["stage_3_deduplication"] = {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": round(time.time() - s3_start, 2)
            }

        # =========================================================================
        # STAGE 4: CATEGORY RECLASSIFICATION & ROUTING
        # =========================================================================
        print("\n" + "#" * 80)
        print(" [STAGE 4/4] CATEGORY RECLASSIFICATION & ROUTING")
        print("#" * 80)
        s4_start = time.time()
        try:
            audit_and_reclassify_tracks(client=client, execute=True)
            summary["stages"]["stage_4_reclassification"] = {
                "status": "SUCCESS",
                "duration_seconds": round(time.time() - s4_start, 2)
            }
        except Exception as e:
            print(f"❌ Error during Stage 4: {e}")
            summary["stages"]["stage_4_reclassification"] = {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": round(time.time() - s4_start, 2)
            }

        total_elapsed = round(time.time() - start_time, 2)
        summary["total_duration_seconds"] = total_elapsed
        summary["end_time"] = datetime.now().isoformat()
        summary["status"] = "COMPLETED"

        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 80)
        print(f" 🏆 ALL 4 PIPELINE STAGES COMPLETED IN {total_elapsed} SECONDS ({round(total_elapsed / 60, 1)} min)!")
        print(f" 📁 Pipeline summary saved to: {SUMMARY_FILE}")
        print("=" * 80)

    finally:
        client.close()


if __name__ == "__main__":
    main()
