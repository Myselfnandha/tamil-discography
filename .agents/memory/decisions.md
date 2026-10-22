# Architecture Decisions & Invariants

This document records durable architectural decisions, system invariants, and interface contracts for this project.

---

## Active Invariants

### 1. Dual-Layer Codebase Analysis Engine
- **Decision**: Codebase freshness is checked via `analyze.py --check --auto-heal --inject-ki` at the start of every session.
- **Rationale**: Prevents stale context without blocking user conversations, storing SQLite cache in `.agents/cache/codebase.db`.

### 2. Multi-Tier Security & Verification Gates
- **Decision**: All modified files and business logic must pass AAA unit test standards and Skylos SAST / AI hallucination verification.
- **Rationale**: Eliminates phantom imports, hallucinated package versions, and insecure sinks before commit.

### 3. Native MCP Server Protocol
- **Decision**: External tool integrations use the official Model Context Protocol (MCP) in `.agents/mcp_config.json`.

### 4. Standalone Annual Playlists & Spotify Year Container
- **Decision**: Annual playlists for 1960 through 2026 exist as 63 standalone SQLite databases in `playlists/year/{year}.db` and are mapped to Spotify containers under a dedicated `Year` folder (`spotify:user:mqvns86lexwty9zusrxifajb4:folder:7581063132455cbe`).
- **Rationale**: Provides strict year isolation (`track.year == YYYY`, 0 cross-year leakage) while enabling both local offline playback and cloud streaming.

### 5. Current Year (2026) Live Dynamic Invariant
- **Decision**: Active release year `2026` is continuously updated via `auto_update_playlists.py` with Newest-First (Position 0 / Prepend) ordering.
- **Rationale**: Listeners opening `2026` immediately hear the freshest weekly singles and movie soundtrack releases at the top.

### 6. Tamil Independent & YouTube Album Songs Engine & Zero-Collision Invariant
- **Decision**: Non-film, independent, and YouTube album music is cataloged in `tamil_discography.db` with `album_type = 'indie_single'`, `views_tier`, `views_count`, and `stream_url`. 11 dedicated playlist databases are generated in `playlists/indie/` and synchronized to Spotify under a dedicated `Indie` folder container (`spotify:user:mqvns86lexwty9zusrxifajb4:folder:859025b00671d970`).
- **Rationale**: Strict schema segregation (`album_type == 'indie_single'` vs `'film'`) guarantees zero collision with vintage/era cinema playlists, while multi-factor view tiering ensures viral hits (50M+) and underground cult gems (Kaber Vasuki, Stephen Zechariah, Paal Dabba) receive curated spotlighting.

### 7. Independent Historical Evidence Authority & Deterministic Ranking Ladder
- **Decision**: Annual playlist ranking is strictly governed by defensible historical evidence ($E = \text{milestone} + \text{award} + \text{label\_legacy} + \text{airplay} + \text{cultural\_impact}$) and deterministic tie-breakers (`tier ASC`, `evidence_score DESC`, `soundtrack_legacy_score DESC`, `track_number ASC`, `discography_track_id ASC`). Third-party API listenership metrics are eliminated from ranking authority to guarantee full compliance with Spotify Feb 2026 Developer Policy and YouTube analytics derived-metric regulations. Evidence provenance is stored in `track_evidence` with explicit attribution methods, and unresearched tracks default strictly to `NULL` (never `0.0`).
- **Rationale**: Ensures reproducible, tamper-proof, multi-tier listening experiences from #1 historical mega hits down to archive B-sides, while eliminating platform policy deprecation risks.

### 8. Systemd User Scheduling Architecture & Cross-Database Spotify URI Cache Preservation
- **Decision**: Automated playlist synchronization is executed via Arch Linux native `systemd --user` timers (`tamil-playlist-sync.timer` daily at 08:07 IST, `tamil-playlist-full-sync.timer` Sundays at 08:17 IST). Any rebuild of local playlist databases (`build_playlists.py`) must pre-harvest and preserve resolved Spotify track URIs across all local SQLite databases to prevent loss of match state or redundant API search calls.
- **Rationale**: Replaces missing `crontab` binaries with native systemd user services, ensures persistent journal logging, and maintains 100% Spotify URI match continuity during catalog regeneration.

### 9. Multi-Scope Metadata Isolation & Wikipedia Column Shift Rectification
- **Decision**: Playlist rule matching (`matches_rules()`) strictly decouples metadata scopes into:
  1) `song_scope` (`t_title` + `raga`) for Moods, Activities, Relationships, and song-level Genres (Devotional, Pop, Rock, Lofi, Phonk, Sad Melody, Kuthu Dance, Folk Village).
  2) `film_scope` (`t_title` + `a_title` + `raga`) for title tracks and mass themes.
  3) `music_scope` (`t_title` + `a_title` + `composer` + `singers` + `raga`) for general music searches.
  Under no circumstances may `{cast}`, `{director}`, or `{label}` be searched for mood, genre, activity, or relationship playlists.
  Furthermore, 56 shifted Wikipedia soundtrack tables in `tamil_discography.db` (where `title` held singers and `singers` held durations) were fully repaired using custom polite wikitext extraction.
- **Rationale**: Eliminates systemic leakage where actor cast names (e.g. comedian Thambi Ramaiah matching `family`, Ravi Krishna matching `devotional`), directors (Arun Vaseegaran matching `romance`), or production labels (Sri Surya Movies matching `energetic`) contaminated non-related song playlists.

