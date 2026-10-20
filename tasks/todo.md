# Task List: Annual Playlists (1960–2026)

- [x] Task 1: Extend `build_playlists.py` with `year` Category & Strict Rule
  - Acceptance: `TAXONOMY["year"]` defines 63 entries (1960–2026 excluding missing years 1990, 1991, 1993, 1995) with clean title `{year}`, slug `{year}`, and strict `exact_year` rule matching.
  - Verify: `python3 -c "import build_playlists; print(len(build_playlists.TAXONOMY.get('year', [])))"` outputs `63`.
  - Files: `build_playlists.py`

- [x] Task 2: Generate All 63 Local Annual Playlist Databases
  - Acceptance: Directory `playlists/year/` exists and contains 63 SQLite `.db` files (`1960.db` ... `2026.db`) with populated `playlist_info` and `tracks` tables.
  - Verify: `ls playlists/year/*.db | wc -l` outputs `63`.
  - Files: `playlists/year/*.db`

- [x] Task 3: Implement Annual Invariant Verification in `verify_all_playlists.py`
  - Acceptance: `verify_all_playlists.py` inspects `playlists/year/*.db` and asserts `track.year == db.year` for 100% of tracks, reporting zero errors.
  - Verify: `python3 verify_all_playlists.py` reports 0 errors across all 202 databases.
  - Files: `verify_all_playlists.py`

- [x] Task 4: Provision Spotify `Year` Folder Container
  - Acceptance: Spotify rootlist contains a top-level folder named `Year`. Folder URI and `start_group` are mapped in `organize_spotify_folders.py`.
  - Verify: Query rootlist or execute folder verification script to confirm `Year` folder exists on Spotify.
  - Files: `organize_spotify_folders.py`

- [x] Task 5: Build Spotify Annual Playlist Creator & Sync Engine
  - Acceptance: Engine creates Spotify playlists named `{year}` inside the `Year` folder, matches & batch-adds track URIs, and updates `data/sync_state.json`.
  - Verify: Query Spotify playlist track counts and inspect `sync_state.json`.
  - Files: `sync_annual_playlists_to_spotify.py`, `data/sync_state.json`

- [x] Task 6: Integrate Annual Playlists into Automated Pipelines & Audit
  - Acceptance: `auto_update_playlists.py` recognizes `playlists/year/` during full library sync and updates documentation.
  - Verify: `python3 auto_update_playlists.py --full --dry-run` reports 202 total playlist databases.
  - Files: `auto_update_playlists.py`

