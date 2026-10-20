# Technical Implementation Plan: Annual Playlists (1960–2026)

**Feature:** Standalone Annual Playlists (1960–2026)  
**Spec Document:** `SPEC-annual-playlists.md`  
**Effort:** `⚡ Effort: ultra`  

---

## Architecture & Dependency Graph

```
tamil_discography.db (33,288 tracks)
         │
         ▼
[Task 1: Taxonomy Extension in build_playlists.py]
  - Add TAXONOMY["year"] populated with 63 active years (1960–2026)
  - Configure rule type "exact_year" with clean naming: name="{year}"
         │
         ▼
[Task 2: Local Database Generation]
  - Run python3 build_playlists.py --section year
  - Output: 63 standalone SQLite databases in playlists/year/{year}.db
         │
         ▼
[Task 3: Clamping & Anachronism Verification]
  - Update verify_all_playlists.py with Year Clamping Invariant
  - Verify all 63 databases: track.year == db.year (100%), 0 collisions
         │
         ▼
[Task 4: Spotify Folder Container Provisioning]
  - Check / provision "Year" folder container in Spotify rootlist via GraphQL MOV
  - Register folder ID in organize_spotify_folders.py
         │
         ▼
[Task 5: Spotify Playlist Creation & Synchronization Engine]
  - Create annual playlists named "{year}" in Spotify under "Year" folder
  - Query & batch add matching tracks in batches of 50–100 per request
  - Store playlist URIs and track IDs in data/sync_state.json
         │
         ▼
[Task 6: Continuous Integration & Pipeline Integration]
  - Update auto_update_playlists.py full library sync (include playlists/year)
  - Run end-to-end verification and generate walkthrough artifact
```

---

## Risk Analysis & Mitigation

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| Cross-year track leakage (e.g. 2024 track in 1995.db) | Critical (data corruption) | Strict `exact_year` match checking `track['year'] == target_year`. Verification script will assert `SELECT DISTINCT year FROM tracks` has length 1. |
| Spotify Rate Limiting (429 Too Many Requests) | High (aborted sync) | Batch additions to 50–100 tracks per call with 1.0–2.0s sleep and exponential backoff retry. |
| Duplicate Spotify Playlists | Medium (clutter) | Check `sync_state.json` and Spotify rootlist before creating any playlist with name `{year}`. |
| High database file count | Low | 63 files totaling ~30MB in `playlists/year/`, fully supported by Linux/macOS/Windows filesystem. |

---

## Verification Checkpoints

1. **Local DB Checkpoint:** All 63 databases created in `playlists/year/`. Total count of playlists in `playlists/` is 139 + 63 = 202 databases.
2. **Integrity Checkpoint:** `python3 verify_all_playlists.py` returns 0 errors across all 202 databases.
3. **Spotify Container Checkpoint:** `Year` folder exists in Spotify rootlist.
4. **Spotify Sync Checkpoint:** Annual playlists created and populated with tracks. `data/sync_state.json` contains valid playlist URIs.
