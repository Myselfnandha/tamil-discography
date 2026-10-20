# Codebase Context: play
> Auto-generated on 2026-10-15 18:04:32. 183 files, ~8,872,919 tokens.

## Directory Overview

### `./` (16 files)
- `.env` — Text file: 3 lines
- `.spotify_tokens.json` — JSON data
- `build_playlists.py` — database operations, CLI tool; functions: init_playlist_db, clean_meta_text, load_all_discography_tracks, matches_rules +1 more
- `db.py` — database operations; functions: get_connection, init_db, insert_album_with_tracks, update_checkpoint +2 more
- `enrich_multisource.py` — database operations, HTTP client, CLI tool; functions: normalize_title, match_score, clean_album_title, format_duration +8 more
- `enrich_with_ytmusic.py` — database operations, CLI tool; functions: is_junk_album_title, init_checkpoint_table, clean_title_for_matching, match_score +3 more
- `export.py` — functions: export_year_to_json, export_summary_index
- `export_spotify.py` — CLI tool; functions: discover_playlist_dbs, parse_duration_to_seconds, fetch_playlist_data, export_single_playlist +1 more
- `fetcher.py` — HTTP client; functions: clean_wiki, api_get, fetch_annual_filmography, is_date_or_header +3 more
- `find_duplicates.py` — database operations, CLI tool; functions: is_junk_title, scan_discography_duplicates, scan_playlist_duplicates, print_audit_report +1 more
- `ingest_missing_years.py` — database operations; functions: ingest_years
- `pipeline.log` — ------------------------------------------------------------------------------ (388 lines)
- ... and 4 more files

### `data/` (68 files)
- `data/1960.json` — JSON data
- `data/1961.json` — JSON data
- `data/1962.json` — JSON data
- `data/1963.json` — JSON data
- `data/1964.json` — JSON data
- `data/1965.json` — JSON data
- `data/1966.json` — JSON data
- `data/1967.json` — JSON data
- `data/1968.json` — JSON data
- `data/1969.json` — JSON data
- `data/1970.json` — JSON data
- `data/1971.json` — JSON data
- ... and 56 more files

### `playlists/` (99 files)
- `playlists/spotify_exports/csv/2000s_hits.csv` — CSV file: 6030 lines
- `playlists/spotify_exports/csv/90s_classics.csv` — CSV file: 2178 lines
- `playlists/spotify_exports/csv/all_time_hits.csv` — CSV file: 7852 lines
- `playlists/spotify_exports/csv/anirudh_hits.csv` — CSV file: 299 lines
- `playlists/spotify_exports/csv/ar_rahman_hits.csv` — CSV file: 1984 lines
- `playlists/spotify_exports/csv/d_imman_hits.csv` — CSV file: 30 lines
- `playlists/spotify_exports/csv/deva_hits.csv` — CSV file: 202 lines
- `playlists/spotify_exports/csv/gaana.csv` — CSV file: 4951 lines
- `playlists/spotify_exports/csv/gv_prakash_hits.csv` — CSV file: 43 lines
- `playlists/spotify_exports/csv/hariharan_hits.csv` — CSV file: 12 lines
- `playlists/spotify_exports/csv/harris_jayaraj_hits.csv` — CSV file: 140 lines
- `playlists/spotify_exports/csv/ilaiyaraaja_hits.csv` — CSV file: 101 lines
- ... and 87 more files

