#!/usr/bin/env python3
"""
SQLite State Cache Database for analyze.py.

Provides high-performance, atomic caching of file metadata, mtimes, hashes,
heuristic summaries, and formatted markdown sections. Replaces slow regex-parsing
of multi-megabyte markdown files with sub-millisecond SQLite lookups.

Zero external dependencies. Uses only Python stdlib.
"""

import os
import sqlite3
import hashlib
from datetime import datetime, timezone


def compute_file_hash(filepath, chunk_size=65536):
    """Compute SHA-256 hash of a file efficiently."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


class CodebaseCacheDB:
    """Manages SQLite cache for codebase analysis metadata."""

    def __init__(self, db_path):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize the database connection and schema with WAL mode."""
        self.conn = sqlite3.connect(self.db_path, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            # Enable WAL mode for high concurrency and fast writes
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
            self.conn.execute("PRAGMA temp_store=MEMORY;")
            self.conn.execute("PRAGMA mmap_size=268435456;")  # 256MB mmap

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    rel_path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    file_size INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    section_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_cache_mtime 
                ON file_cache (rel_path, mtime);
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_file(self, rel_path):
        """Get cached record for a file path."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM file_cache WHERE rel_path = ?", (rel_path,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_cached(self):
        """Get all cached files as a dict of rel_path -> dict."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM file_cache")
        return {row['rel_path']: dict(row) for row in cursor.fetchall()}

    def upsert_file(self, rel_path, mtime, file_size, content_hash, token_count, summary, section_text):
        """Insert or update a file record atomically."""
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO file_cache (rel_path, mtime, file_size, content_hash, token_count, summary, section_text, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rel_path) DO UPDATE SET
                    mtime = excluded.mtime,
                    file_size = excluded.file_size,
                    content_hash = excluded.content_hash,
                    token_count = excluded.token_count,
                    summary = excluded.summary,
                    section_text = excluded.section_text,
                    updated_at = excluded.updated_at;
            """, (rel_path, mtime, file_size, content_hash, token_count, summary, section_text, now))

    def update_mtime_only(self, rel_path, new_mtime):
        """Update just the mtime for a file whose content hash is unchanged."""
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute("""
                UPDATE file_cache 
                SET mtime = ?, updated_at = ? 
                WHERE rel_path = ?;
            """, (new_mtime, now, rel_path))

    def delete_missing(self, current_rel_paths):
        """Remove cached entries for files that no longer exist on disk."""
        all_cached = set(self.get_all_cached().keys())
        missing = all_cached - set(current_rel_paths)
        if missing:
            with self.conn:
                self.conn.executemany(
                    "DELETE FROM file_cache WHERE rel_path = ?",
                    [(path,) for path in missing]
                )
        return len(missing)

    def set_meta(self, key, value):
        """Set a metadata key-value pair."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO meta (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (key, str(value)))

    def get_meta(self, key, default=None):
        """Get a metadata value by key."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

    def count(self):
        """Get total number of cached files."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM file_cache")
        row = cursor.fetchone()
        return row['total'] if row else 0
