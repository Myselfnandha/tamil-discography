# Task List: Evidence-Based Multi-Tier Annual Playlists Engine (1960–2026)

- [x] Phase 0: Scope Validation, Pre-Flight Audit & Database Backups
  - Acceptance: Create timestamped backups of `tamil_discography.db` and `playlists/year/`; document 63 active vs 67 calendar scope with missing scrape analysis for 1990/1991/1993/1995.
  - Verify: Confirm backup directory exists, checksums verify, and schema baseline frozen.
  - Files: `tamil_discography.db.bak`, `playlists_backup/`

- [x] Phase 1: Build Evidence and Deterministic Ranking Engine
  - Acceptance: Schema migrated with `historical_evidence_score`, `evidence_tier`, `evidence_confidence`, `scoring_version`. Independent historical evidence rubric implemented without violating Spotify/YouTube API derived metric policies. Missing values set to `NULL` (never `0`).
  - Verify: PRAGMA table_info confirms columns and index; unit tests verify deterministic tie-breaker ladder.
  - Files: `engine/historical_evidence.py`, `tamil_discography.db`, `db.py`

- [x] Phase 2: Pilot and Audit (1985 Vintage & 2024 Modern)
  - Acceptance: Run evidence scoring on 1985 (593 tracks) and 2024 (675 tracks); pass track-level test fixtures (*Poove Poochoodava*, *Sangeetha Megam*, *Kanmaniye Pesu*, *Namma Singaari Saraku*, *Poongaatru Thirumbuma*, *Kuyile Kuyile Poonguyile* in 1985; *Katchi Sera*, *Aasa Kooda*, *Whistle Podu*, *Matta*, *Manasilaayo* in 2024). *Enna Satham Indha Neram* verified retained in 1986.
  - Verify: Generate dry-run diff report; verify rollback behavior and non-destructive replacement.
  - Files: `playlists/year/1985.db`, `playlists/year/2024.db`, `data/pilot_diff_report.json`

- [x] Phase 3: Pilot Spotify Synchronization & Verification Gate
  - Acceptance: Generate pre-sync diff report for 1985 and 2024; verify playlist contents inside Spotify `Year` folder in strictly ranked order.
  - Verify: Query Spotify native client to confirm track 1 matches evidence leader.
  - Files: `sync_annual_playlists_to_spotify.py`

- [x] Phase 4: Full Catalog Expansion in Restartable Batches (1960–2026)
  - Acceptance: Score and re-generate annual databases across all active years in 10-year restartable batches.
  - Verify: Run `PRAGMA integrity_check` on all databases; verify strictly monotonic ordering and duplicate-free tracks.
  - Files: `build_playlists.py`, `playlists/year/*.db`

- [x] Phase 5: Dynamic Whole-Catalog Audit & Master Automation Hook
  - Acceptance: `verify_all_playlists.py` dynamically discovers databases, saves inventory manifest (`data/catalog_inventory_manifest.json`), and validates schema consistency, duplicate prevention, and strict monotonic order with 0 errors. Update `auto_update_playlists.py` with diff safety gates. Isolated repair ticket for missing scrape years (1990, 1991, 1993, 1995).
  - Verify: `python3 verify_all_playlists.py` outputs 0 errors against discovered count; `python3 auto_update_playlists.py --full --dry-run` succeeds.
  - Files: `verify_all_playlists.py`, `auto_update_playlists.py`, `data/catalog_inventory_manifest.json`

---
### 🏁 Milestone Completed: Full Annual Catalog Synchronized to Spotify (63/63)
- All 63 annual playlist containers populated and filed inside Spotify `Year` folder.
- Native `spclient` creation architecture active and verified.
- 0 extraneous items inside `Year` folder container.
