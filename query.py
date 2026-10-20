#!/usr/bin/env python3
"""
query.py - Headless CLI search and inspection tool for Tamil Discography (1960-2026).
Allows instant searching by year, album, composer, singer, or lyricist.
"""

import sys
import argparse
import sqlite3
from db import get_connection, DEFAULT_DB_PATH

def show_stats():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM albums;")
        total_albums = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) AS total FROM tracks;")
        total_tracks = cur.fetchone()['total']
        
        cur.execute("SELECT MIN(year) as min_yr, MAX(year) as max_yr FROM albums;")
        row = cur.fetchone()
        min_yr, max_yr = row['min_yr'], row['max_yr']
        
        cur.execute("SELECT year, albums_count, tracks_count, status FROM checkpoints ORDER BY year ASC;")
        years = cur.fetchall()

    print("\n" + "="*50)
    print(" 🎵 TAMIL DISCOGRAPHY DATABASE STATISTICS")
    print("="*50)
    print(f"Total Albums Indexed : {total_albums}")
    print(f"Total Tracks Indexed : {total_tracks}")
    print(f"Year Span            : {min_yr or 'None'} – {max_yr or 'None'}")
    print("\nIndexed Years Breakdown:")
    for y in years:
        print(f"  • Year {y['year']}: {y['albums_count']} albums | {y['tracks_count']} tracks [{y['status']}]")
    print("="*50 + "\n")

def list_year(year):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, composer, director, cast 
            FROM albums 
            WHERE year = ? 
            ORDER BY title ASC;
        """, (year,))
        albums = cur.fetchall()

        if not albums:
            print(f"\nNo albums found in database for year {year}. Run 'python runner.py --year {year}' first.\n")
            return

        print(f"\n" + "="*70)
        print(f" 📀 TAMIL FILMS & ALBUMS OF {year} ({len(albums)} Total)")
        print("="*70)
        for idx, a in enumerate(albums, 1):
            cur.execute("SELECT COUNT(*) as t_count FROM tracks WHERE album_id = ?;", (a['id'],))
            t_count = cur.fetchone()['t_count']
            
            comp = a['composer'] or 'Unknown'
            dir_name = a['director'] or 'Unknown'
            print(f"{idx:02d}. {a['title']}")
            print(f"    Composer: {comp} | Director: {dir_name} | Tracks: {t_count}")
            if a['cast']:
                print(f"    Cast: {a['cast'][:70]}...")
            print("-" * 70)

def inspect_album(query):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM albums 
            WHERE title LIKE ? OR source_url LIKE ?
            ORDER BY year ASC;
        """, (f"%{query}%", f"%{query}%"))
        albums = cur.fetchall()

        if not albums:
            print(f"\nNo album found matching '{query}'.\n")
            return

        for a in albums:
            print("\n" + "="*70)
            print(f" 🎬 ALBUM: {a['title']} ({a['year']})")
            print("="*70)
            print(f"Composer : {a['composer']}")
            print(f"Director : {a['director']}")
            print(f"Producer : {a['producer']}")
            print(f"Cast     : {a['cast']}")
            print(f"Source   : {a['source_url']}")
            print("\n--- OCD TRACKLIST ---")
            
            cur.execute("""
                SELECT track_number, title, singers, lyricist, duration, raga 
                FROM tracks 
                WHERE album_id = ? 
                ORDER BY track_number ASC, id ASC;
            """, (a['id'],))
            tracks = cur.fetchall()
            
            if not tracks:
                print("  (No soundtrack tracks recorded on Wikipedia for this film)")
            else:
                for t in tracks:
                    dur = f"[{t['duration']}]" if t['duration'] else ""
                    raga = f" (Raagam: {t['raga']})" if t['raga'] else ""
                    print(f"  {t['track_number']:02d}. {t['title']} {dur}{raga}")
                    if t['singers']:
                        print(f"      Singers : {t['singers']}")
                    if t['lyricist']:
                        print(f"      Lyrics  : {t['lyricist']}")
            print("="*70)

def search_tracks(query):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.title AS track_title, t.singers, t.lyricist, t.duration,
                   a.title AS album_title, a.year, a.composer
            FROM tracks t
            JOIN albums a ON t.album_id = a.id
            WHERE t.title LIKE ? OR t.singers LIKE ? OR t.lyricist LIKE ?
            ORDER BY a.year ASC, a.title ASC
            LIMIT 50;
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        results = cur.fetchall()

        print(f"\n--- Search results for '{query}' ({len(results)} matches) ---")
        for r in results:
            dur = f"[{r['duration']}]" if r['duration'] else ""
            print(f"• {r['track_title']} {dur}")
            print(f"  Album: {r['album_title']} ({r['year']}) | Composer: {r['composer']}")
            print(f"  Singers: {r['singers']} | Lyricist: {r['lyricist']}\n")

def main():
    parser = argparse.ArgumentParser(description="Query Tamil Discography Database")
    parser.add_argument("--stats", action="store_true", help="Show database overview and stats")
    parser.add_argument("--year", type=int, help="List all albums released in this year")
    parser.add_argument("--album", type=str, help="Search and view full tracklist for an album")
    parser.add_argument("--search", type=str, help="Search for songs, singers, or lyricists")
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.year:
        list_year(args.year)
    elif args.album:
        inspect_album(args.album)
    elif args.search:
        search_tracks(args.search)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
