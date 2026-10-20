#!/usr/bin/env python3
"""
export.py - OCD JSON exporter for Tamil Discography.
Dumps structured annual JSON files to data/<YYYY>.json and updates summary index.
"""

import json
import os
import datetime
from pathlib import Path
from db import get_connection, get_albums_by_year

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def export_year_to_json(year, output_dir=DATA_DIR):
    """Export complete albums and tracks for a single year into OCD JSON format."""
    os.makedirs(output_dir, exist_ok=True)
    albums = get_albums_by_year(year)
    
    total_tracks = sum(len(a.get('tracks', [])) for a in albums)
    
    payload = {
        "year": int(year),
        "total_albums": len(albums),
        "total_tracks": total_tracks,
        "exported_at": datetime.datetime.utcnow().isoformat() + "Z",
        "albums": albums
    }
    
    out_file = os.path.join(output_dir, f"{year}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    return out_file, len(albums), total_tracks

def export_summary_index(output_dir=DATA_DIR):
    """Export global discography summary index across all completed years."""
    os.makedirs(output_dir, exist_ok=True)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT year, status, albums_count, tracks_count, last_updated 
            FROM checkpoints 
            ORDER BY year ASC
        """)
        checkpoints = [dict(r) for r in cur.fetchall()]
        
        cur.execute("SELECT COUNT(*) AS total_albums FROM albums;")
        total_albums = cur.fetchone()['total_albums']
        
        cur.execute("SELECT COUNT(*) AS total_tracks FROM tracks;")
        total_tracks = cur.fetchone()['total_tracks']
        
    summary = {
        "total_years_indexed": len(checkpoints),
        "total_albums": total_albums,
        "total_tracks": total_tracks,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "years": checkpoints
    }
    
    out_file = os.path.join(output_dir, "discography_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    return out_file

if __name__ == "__main__":
    import sys
    yr = int(sys.argv[1]) if len(sys.argv) > 1 else 1960
    f, albs, trks = export_year_to_json(yr)
    print(f"Exported Year {yr} -> {f} ({albs} albums, {trks} tracks)")
