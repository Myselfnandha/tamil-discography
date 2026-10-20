# Specification: Annual Playlists (1960–2026)

**Spec ID:** `SPEC-annual-playlists`  
**Status:** In Review (Gated Phase 1)  
**Author:** Antigravity / ZeroGravity OS  
**Effort Level:** Ultra (`⚡ Effort: ultra`)  
**Date:** 2026-10-19  

---

## 1. Objective & User Story

### 1.1 Objective
Design, generate, verify, and synchronize dedicated annual Tamil soundtrack playlists for every year from 1960 through 2026 (spanning 67 years). Each year will exist as an autonomous, indexed SQLite database in `playlists/year/{year}.db` and as a synchronized Spotify playlist contained within a dedicated `Year` folder in the user's Spotify library.

### 1.2 User Story
- **As a Tamil music enthusiast and archivist**, I want a dedicated playlist for every individual release year from 1960 to 2026.
- **So that** I can explore the exact evolution of Tamil cinema and music year-by-year, experience the signature soundscape of any given year (from vintage M.S. Viswanathan / K.V. Mahadevan era to Ilaiyaraaja's 80s peak, A.R. Rahman's 90s revolution, 2000s Harris/Yuvan era, and modern Anirudh/Santhosh chartbusters), and stream them seamlessly locally or on Spotify without track collision or cross-year pollution.

---

## 2. Capability Map (Phase 0 Scope Breakdown)

| Module ID | Responsibility | Depends On | Output Artifacts |
|---|---|---|---|
| `annual-db-generator` | Query `tamil_discography.db`, apply year clamping (`year == YYYY`), generate SQLite schema, and write `playlists/year/{year}.db` | `tamil_discography.db` | 63–67 SQLite databases in `playlists/year/` |
| `annual-verifier` | Audit year clamping (`track.year == db.year`), assert 0 collided modern tracks in vintage years, assert 0 empty databases | `annual-db-generator` | Audit test assertions in `verify_all_playlists.py` |
| `annual-spotify-folder` | Provision a top-level `Year` folder container in Spotify rootlist using native GraphQL delta operations | Spotify session cookies | Spotify rootlist folder `Year` (`spotify:user:...:folder:...`) |
| `annual-spotify-sync` | Create/sync annual playlists to Spotify in batches of 50–100 tracks, write persistent state to `sync_state.json` | `annual-db-generator`, `annual-spotify-folder` | Spotify playlist URIs in `data/sync_state.json` |
| `annual-pipeline-integration` | Incorporate `year` into `build_playlists.py`, `auto_update_playlists.py`, and GitHub Actions workflow | `annual-db-generator`, `annual-spotify-sync` | Unified scheduled sync across all 206 playlists |

**Build Order:**  
`annual-db-generator` ──→ `annual-verifier` ──→ `annual-spotify-folder` ──→ `annual-spotify-sync` ──→ `annual-pipeline-integration`

---

## 3. Assumptions

1. **Year Clamping & Isolation:** Unlike thematic playlists (`Mood`, `Activity`) which rely on keyword regexes, an annual playlist `playlists/year/{YYYY}.db` has one strict filtering invariant: `a.year == YYYY` (100% strict equality; zero fuzzy year matching).
2. **Track Eligibility:** Includes all tracks belonging to films released in year `YYYY` where `track_title` is valid and non-empty. Instrumental film OST tracks / score tracks are preserved with `track_type = 'instrumental'` or `'song'`.
3. **Database Schema Parity:** Each annual database conforms exactly to the existing `playlist_info` and `tracks` schema used by the 139 existing category databases, ensuring 100% compatibility with `query.py`, `export.py`, `auto_update_playlists.py`, and third-party players (e.g. PowerAMP / offline DSP exporters).
4. **Spotify Folder Hierarchy:** Spotify playlists will be grouped under a dedicated top-level folder named `Year` (folder ID provisioned via Spotify Web GraphQL rootlist API), alongside the existing 7 folders (`Activity`, `Artist`, `Era`, `Genre`, `Mood`, `Relationship`, `Tamil`).
5. **Missing Wikipedia Scrape Years (1990, 1991, 1993, 1995):** Currently `tamil_discography.db` contains 63 active years with tracks. Years 1990, 1991, 1993, and 1995 had malformed Wikipedia wikitables during original scraping. The generator will generate databases for all active years in `tamil_discography.db` and leave a clear hook to populate missing years when wikitables are re-scraped.

---

## 4. Tech Stack & Dependencies

- **Language:** Python 3.10+ (Standard Library: `sqlite3`, `pathlib`, `json`, `re`, `argparse`, `datetime`)
- **Database:** SQLite 3 (WAL mode, synchronous=NORMAL, indexed on `position`, `track_title`, `year`)
- **API Client:** `SpotifyNativeClient` (TLS session, SHA256 persisted queries, batch track additions)
- **External Dependencies:** `requests`, `urllib3` (declared in `requirements.txt`)
- **No Heavy Frameworks:** Pure Python + SQLite (zero bloat, zero native binary dependencies)

---

## 5. Commands

```bash
# 1. Build only the annual playlists (generates playlists/year/*.db)
python3 build_playlists.py --section year

# 2. Build entire discography library (all 7 existing categories + year = ~206 databases)
python3 build_playlists.py

# 3. Audit and verify all playlist databases (asserts 100% year clamp integrity)
python3 verify_all_playlists.py

# 4. Provision Spotify 'Year' folder container
python3 organize_spotify_folders.py --create-folder "Year"

# 5. Dry-run synchronization of annual playlists to Spotify
python3 auto_update_playlists.py --section year --dry-run

# 6. Execute live sync of annual playlists to Spotify (batching 50-100 tracks)
python3 auto_update_playlists.py --section year --live
```

---

## 6. Project Structure

```
/home/nandha/play/
├── build_playlists.py               # Extended with TAXONOMY["year"] and year generator
├── verify_all_playlists.py          # Extended with annual clamping integrity assertions
├── organize_spotify_folders.py      # Extended with "year" in FOLDER_DEFINITIONS
├── auto_update_playlists.py         # Extended with annual sync & weekly audit
├── tamil_discography.db             # Source SQLite catalog (33,288+ indexed tracks)
├── docs/
│   └── spec/
│       └── SPEC-annual-playlists.md # This specification document
├── data/
│   ├── sync_state.json              # Persistent sync state (contains playlist URIs)
│   └── annual_summary.json          # Manifest of all generated annual databases
└── playlists/
    ├── activity/                    # Existing 10 databases
    ├── artist/                      # Existing 60 databases
    ├── era/                         # Existing 10 databases
    ├── genre/                       # Existing 15 databases
    ├── mood/                        # Existing 19 databases
    ├── relationship/                # Existing 10 databases
    ├── tamil/                       # Existing 15 databases
    └── year/                        # [NEW] 63–67 annual databases (1960.db ... 2026.db)
        ├── 1960.db
        ├── 1961.db
        ├── ...
        ├── 2024.db
        ├── 2025.db
        └── 2026.db
```

---

## 7. Schema & Code Style

### 7.1 SQLite Schema for `playlists/year/{year}.db`

```sql
CREATE TABLE IF NOT EXISTS playlist_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position INTEGER NOT NULL,
    track_title TEXT NOT NULL,
    album_title TEXT NOT NULL,
    year INTEGER NOT NULL,
    composer TEXT,
    singers TEXT,
    lyricist TEXT,
    duration TEXT,
    track_type TEXT DEFAULT 'song',
    spotify_query TEXT,
    spotify_uri TEXT DEFAULT '',
    discography_track_id INTEGER,
    match_reason TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracks_pos ON tracks(position);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(track_title);
CREATE INDEX IF NOT EXISTS idx_tracks_year ON tracks(year);
```

### 7.2 Python Generator Pattern
Consistent with `build_playlists.py`:

```python
def generate_annual_taxonomy(min_year: int = 1960, max_year: int = 2026) -> List[Dict[str, Any]]:
    """Generates annual taxonomy entries for each year in range."""
    annual_entries = []
    for yr in range(min_year, max_year + 1):
        annual_entries.append({
            "slug": str(yr),
            "name": f"📅 Tamil Songs {yr}",
            "category": "By Year",
            "emoji": "📅",
            "desc": f"Complete Tamil cinema soundtrack discography & essential hits of {yr}.",
            "rules": [
                {"type": "exact_year", "year": yr}
            ]
        })
    return annual_entries
```

---

## 8. Testing & Verification Strategy

### 8.1 Automated Test Suites in `verify_all_playlists.py`
1. **Year Clamping Invariant:**
   - For every database `playlists/year/{yr}.db`, run `SELECT DISTINCT year FROM tracks`.
   - Assert `len(years) == 1` and `years[0] == yr`. (Zero cross-year leakage).
2. **Schema & Primary Key Integrity:**
   - Assert `tracks` table exists, `playlist_info` contains keys (`slug`, `name`, `category`, `total_tracks`).
   - Assert `total_tracks == (SELECT COUNT(*) FROM tracks)`.
3. **De-duplication Check:**
   - Assert `(track_title, album_title)` is strictly unique within each year database.
4. **Collision & Anachronism Audit:**
   - Assert that no known modern collision tracks (`Pathala Pathala`, `Scene Ah Scene Ah`, etc.) appear in databases where `year < 2000`.

---

## 9. Boundaries

### 9.1 Always Do
- **Always** verify database write integrity with `verify_all_playlists.py` before initiating any Spotify sync.
- **Always** use WAL mode (`PRAGMA journal_mode = WAL;`) for clean concurrency.
- **Always** clamp tracks strictly to `year == YYYY` (no leakage).
- **Always** batch Spotify track addition operations to max 50–100 tracks per call with rate-limit backoff.

### 9.2 Ask First
- **Ask first** before wiping or recreating any existing Spotify folders.
- **Ask first** before executing a live sync that creates 60+ new public playlists on Spotify.

### 9.3 Never Do
- **Never** modify `tamil_discography.db` destructively without a backup.
- **Never** allow songs from other years into an annual database.
- **Never** exceed Spotify rate limits or ignore 429 Retry-After headers.
- **Never** commit authentication credentials or Spotify cookie values to git.

---

## 10. Success Criteria (Testable & Empirical)

- [ ] Directory `playlists/year/` contains standalone `.db` files for all active years in `tamil_discography.db` (63 databases spanning 1960 to 2026).
- [ ] Each database contains a valid `playlist_info` table and `tracks` table with correct indices.
- [ ] 100% of tracks in `playlists/year/{YYYY}.db` satisfy `track.year == YYYY` (0 errors reported by `verify_all_playlists.py`).
- [ ] Total number of local playlist databases in repository expands from 139 to 202+ databases.
- [ ] Command `python3 build_playlists.py --section year` runs to completion in under 30 seconds.
- [ ] Spotify folder container structure is defined and ready for safe batched synchronization.

---

## 11. Approved Decisions & Configuration

1. **Playlist Naming:**
   - Name format: `{year}` (e.g., `1960`, `1995`, `2024`, `2026`).
   - Clean, numeric title for playlists locally and on Spotify.

2. **Rollout & Sync Scope:**
   - **Immediate Full Sync:** Generate all 63 local `.db` files, provision the `Year` folder container in Spotify rootlist, and synchronize all 63 annual playlists to Spotify with batch track additions (50–100 tracks per batch).

3. **Missing Scrape Years (1990, 1991, 1993, 1995):**
   - Generate databases for the 63 active years in `tamil_discography.db` now.
   - A dedicated Wikipedia scraper repair script will follow to populate the 4 missing years up to 67 years.

---

## 12. Current Year (2026) Dynamic Lifecycle & Ordering

Unlike historical closed years (1960–2025), the active release year (`2026`) is a **live, continuously evolving playlist**:

1. **Daily Smart Hybrid Integration:**
   - Hooked into `auto_update_playlists.py`.
   - Every newly dropped 2026 single or movie track discovered via daily Spotify/Wikipedia scans is automatically routed to both `latest_releases` and the dedicated `2026` playlist.

2. **Track Ordering Invariant (Newest First):**
   - New 2026 tracks are prepended at the top (`position = 0` / newest first) on Spotify and in `2026.db`.
   - When listeners open `2026`, the freshest releases from this week appear right at the top.

3. **Dual State Cataloging:**
   - All 1,186 cataloged 2026 tracks from `tamil_discography.db` are preserved in local `playlists/year/2026.db` with clean metadata.
   - Streamable tracks with resolved Spotify URIs are pushed to Spotify; announced/unreleased tracks have their URIs resolved automatically as soon as they drop on Spotify during daily sync runs.


