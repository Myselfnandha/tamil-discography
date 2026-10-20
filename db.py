#!/usr/bin/env python3
"""
db.py - SQLite storage engine for Tamil Discography (1960-2026).
Supports WAL mode, foreign keys, transaction safety, and resume checkpoints.
"""

import sqlite3
import os
from pathlib import Path

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tamil_discography.db")

def get_connection(db_path=DEFAULT_DB_PATH):
    """Create a thread-safe connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    """Initialize schema tables and indexes."""
    with get_connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            title TEXT NOT NULL,
            director TEXT,
            producer TEXT,
            composer TEXT,
            cast TEXT,
            source_url TEXT,
            album_type TEXT DEFAULT 'film',
            label TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, title, composer)
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_id INTEGER NOT NULL,
            track_number INTEGER,
            title TEXT NOT NULL,
            singers TEXT,
            lyricist TEXT,
            raga TEXT,
            duration TEXT,
            stream_url TEXT,
            track_type TEXT DEFAULT 'song',
            views_count INTEGER DEFAULT 0,
            views_tier TEXT DEFAULT '',
            historical_evidence_score REAL DEFAULT NULL,
            evidence_tier TEXT DEFAULT NULL,
            evidence_confidence REAL DEFAULT NULL,
            scoring_version TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS track_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL,
            evidence_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            points REAL NOT NULL,
            source_url TEXT,
            publication_date TEXT,
            verification_date TEXT,
            confidence REAL NOT NULL,
            attribution_method TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            year INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            albums_count INTEGER DEFAULT 0,
            tracks_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_albums_year ON albums(year);
        CREATE INDEX IF NOT EXISTS idx_albums_title ON albums(title);
        CREATE INDEX IF NOT EXISTS idx_albums_composer ON albums(composer);
        CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
        CREATE INDEX IF NOT EXISTS idx_tracks_singers ON tracks(singers);
        """)
    # Run repeatable migration for existing or newly created databases
    migrate_evidence_schema(db_path)

def migrate_evidence_schema(db_path=DEFAULT_DB_PATH):
    """Repeatable migration checking existing columns before applying ALTER TABLE."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        # Inspect columns in tracks
        existing_cols = {row['name'] for row in cur.execute("PRAGMA table_info(tracks)").fetchall()}
        
        columns_to_add = [
            ("historical_evidence_score", "REAL DEFAULT NULL"),
            ("evidence_tier", "TEXT DEFAULT NULL"),
            ("evidence_confidence", "REAL DEFAULT NULL"),
            ("scoring_version", "TEXT DEFAULT NULL"),
        ]
        
        for col_name, col_def in columns_to_add:
            if col_name not in existing_cols:
                cur.execute(f"ALTER TABLE tracks ADD COLUMN {col_name} {col_def};")
                
        # Ensure track_evidence table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS track_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                points REAL NOT NULL,
                source_url TEXT,
                publication_date TEXT,
                verification_date TEXT,
                confidence REAL NOT NULL,
                attribution_method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
            );
        """)
        
        # Ensure indexes exist
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tracks_hist_evidence ON tracks(historical_evidence_score, evidence_tier);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_evidence_track_id ON track_evidence(track_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_evidence_type ON track_evidence(evidence_type);")

def insert_album_with_tracks(album_dict, tracks_list, db_path=DEFAULT_DB_PATH):
    """Insert or update an album and its associated tracks."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        
        # Check if album already exists
        cur.execute("""
            SELECT id FROM albums 
            WHERE year = ? AND title = ? AND composer = ?
        """, (album_dict['year'], album_dict['title'], album_dict.get('composer', '')))
        
        row = cur.fetchone()
        if row:
            album_id = row['id']
            # Update metadata
            cur.execute("""
                UPDATE albums 
                SET director = ?, producer = ?, cast = ?, source_url = ?
                WHERE id = ?
            """, (album_dict.get('director', ''), album_dict.get('producer', ''),
                  album_dict.get('cast', ''), album_dict.get('source_url', ''), album_id))
            # Clear old tracks for re-insertion
            cur.execute("DELETE FROM tracks WHERE album_id = ?", (album_id,))
        else:
            cur.execute("""
                INSERT INTO albums (year, title, director, producer, composer, cast, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (album_dict['year'], album_dict['title'], album_dict.get('director', ''),
                  album_dict.get('producer', ''), album_dict.get('composer', ''),
                  album_dict.get('cast', ''), album_dict.get('source_url', '')))
            album_id = cur.lastrowid

        for t in tracks_list:
            cur.execute("""
                INSERT INTO tracks (album_id, track_number, title, singers, lyricist, raga, duration, stream_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (album_id, t.get('track_number'), t['title'], t.get('singers', ''),
                  t.get('lyricist', ''), t.get('raga', ''), t.get('duration', ''),
                  t.get('stream_url', '')))

        return album_id

def update_checkpoint(year, status, albums_count=0, tracks_count=0, db_path=DEFAULT_DB_PATH):
    """Record year ingestion progress."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO checkpoints (year, status, albums_count, tracks_count, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(year) DO UPDATE SET
                status = excluded.status,
                albums_count = excluded.albums_count,
                tracks_count = excluded.tracks_count,
                last_updated = CURRENT_TIMESTAMP
        """, (year, status, albums_count, tracks_count))

def get_checkpoint(year, db_path=DEFAULT_DB_PATH):
    """Retrieve checkpoint for a given year."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM checkpoints WHERE year = ?", (year,))
        row = cur.fetchone()
        return dict(row) if row else None

def get_albums_by_year(year, db_path=DEFAULT_DB_PATH):
    """Fetch complete album list with nested tracks for a given year."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM albums WHERE year = ? ORDER BY title ASC", (year,))
        albums = [dict(r) for r in cur.fetchall()]
        
        for alb in albums:
            cur.execute("""
                SELECT track_number, title, singers, lyricist, raga, duration, stream_url 
                FROM tracks 
                WHERE album_id = ? 
                ORDER BY track_number ASC, id ASC
            """, (alb['id'],))
            alb['tracks'] = [dict(t) for t in cur.fetchall()]
            
        return albums

def insert_track_evidence(
    track_id: int,
    evidence_type: str,
    subject: str,
    points: float,
    source_url: str = "",
    publication_date: str = "",
    verification_date: str = "",
    confidence: float = 1.0,
    attribution_method: str = "direct_track_award",
    db_path=DEFAULT_DB_PATH
) -> int:
    """Insert an evidence record with strict provenance."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO track_evidence (
                track_id, evidence_type, subject, points, source_url,
                publication_date, verification_date, confidence, attribution_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            track_id, evidence_type, subject, points, source_url,
            publication_date, verification_date, confidence, attribution_method
        ))
        return cur.lastrowid

def get_track_evidence(track_id: int, db_path=DEFAULT_DB_PATH):
    """Retrieve all provenance records for a given track."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM track_evidence WHERE track_id = ? ORDER BY points DESC, id ASC", (track_id,))
        return [dict(r) for r in cur.fetchall()]

def update_track_evidence_score(
    track_id: int,
    score: float,
    tier: str,
    confidence: float,
    scoring_version: str,
    db_path=DEFAULT_DB_PATH
):
    """Update track-level summary evidence score and tier."""
    with get_connection(db_path) as conn:
        conn.execute("""
            UPDATE tracks
            SET historical_evidence_score = ?,
                evidence_tier = ?,
                evidence_confidence = ?,
                scoring_version = ?
            WHERE id = ?
        """, (score, tier, confidence, scoring_version, track_id))

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)
