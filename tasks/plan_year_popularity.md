# Implementation Plan: Multi-Tier Annual Popularity Engine

## High-Level Architecture
1. **Schema Migration**: Add `spotify_popularity INTEGER DEFAULT 0` and `popularity_score REAL DEFAULT 0.0` to `tracks` in `tamil_discography.db` and playlist database schemas.
2. **Data & Scoring Engine (`populate_year_popularity.py`)**:
   - Queries Spotify track popularity (0–100) via `SpotifyNativeClient` / Spotify search.
   - Harvests YouTube view metrics via `ytmusicapi` for top soundtracks of each year.
   - Applies Era Calibration (1960–1989 $\times 3.0$, 1990–2009 $\times 1.8$, 2010–2026 $\times 1.0$) and relative annual percentiles to ensure top 15–25 blockbusters per year are assigned `tier_1_mega`.
   - Caches results to `data/year_popularity_cache.json`.
3. **Database Re-Generation (`build_playlists.py`)**:
   - Re-generates `playlists/year/*.db` sorted by `popularity_score DESC, views_count DESC, id ASC`.
   - Position 1 is guaranteed to be the #1 most-listened track of that year.
4. **Deep Verification (`verify_all_playlists.py`)**:
   - Verifies 0 errors across all 213 databases.
   - Validates that position 1 in `1995.db` is an authentic blockbuster (e.g. *Baasha*, *Muthu*, *Bombay*, *Rangeela*, *Aasai*) and position 1 in `2024.db` is a mega viral anthem (e.g. *Katchi Sera*, *Aasa Kooda*, *Whistle Podu*, *Matta*, *Spark*, *Ta Takkara*).
5. **Spotify Sync Deployment (`sync_annual_playlists_to_spotify.py`)**:
   - Pilot sync for `1995` and `2024` into the `Year` folder.
   - Batch deployment across all 63 years.
