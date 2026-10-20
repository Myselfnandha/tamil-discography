# Specification: Tamil Independent & YouTube Album Songs Engine

**Spec ID:** `SPEC-tamil-indie`  
**Status:** In Review (Gated Phase 1)  
**Author:** Antigravity / ZeroGravity OS  
**Effort Level:** Ultra (`⚡ Effort: ultra`)  
**Date:** 2026-10-20  

---

## 1. Objective & User Story

### 1.1 Objective
Expand the Tamil Discography ecosystem beyond film soundtracks by designing, ingesting, categorizing, and synchronizing non-film Tamil music: **YouTube independent album songs, viral chartbusters, deep indie cult classics, and underground gems**.

Each playlist will exist locally as an autonomous SQLite database in `playlists/indie/` and in Spotify under a dedicated top-level `Indie` folder container.

### 1.2 User Story
- **As a Tamil music enthusiast**, I want to discover and listen to the rich world of non-film Tamil music—from 100M+ viral YouTube hits (*Enjoy Enjaami*, *Katchi Sera*, *Aasa Kooda*, *Orasaadha*) to deeply poignant, unrecognized indie gems (Kaber Vasuki, Sean Roldan non-film, Stephen Zechariah, underground Tamil rap).
- **So that** I have a curated, auto-updating library of independent Tamil music that isn't confined to cinema soundtracks, complete with YouTube streaming links and Spotify playback.

---

## 2. Capability Map (Scope Breakdown)

| Module ID | Responsibility | Depends On | Output Artifacts |
|---|---|---|---|
| `indie-schema-extension` | Extend `tamil_discography.db` with `album_type` (`film` vs `indie_single`), view count, and YouTube stream URLs | `tamil_discography.db` | Schema migration in `db.py` / `tamil_discography.db` |
| `indie-seed-catalog` | Seed 300+ known viral hits, cult classics, and underground gems across major labels and indie pioneers | YouTube & Spotify metadata | `data/indie_seeds.json` |
| `indie-channel-scraper` | Autonomous YouTube / YouTube Music scraper (`ytmusicapi` & channel queries) for Think Indie, Sony South, Maajja, and indie artists | `ytmusicapi` | `ingest_indie_songs.py` |
| `indie-db-generator` | Generate standalone local SQLite databases in `playlists/indie/*.db` | `tamil_discography.db`, `build_playlists.py` | 10+ databases in `playlists/indie/` |
| `indie-spotify-folder` | Provision `Indie` folder container in Spotify rootlist | Spotify session | `organize_spotify_folders.py` mapping |
| `indie-spotify-sync` | Synchronize indie playlists to Spotify in batches with URI caching | `SpotifyNativeClient` | `sync_indie_playlists_to_spotify.py` |
| `indie-pipeline-hook` | Hook indie release discovery into `auto_update_playlists.py` daily/weekly runs | `auto_update_playlists.py` | Continuous discovery in background |

---

## 3. Assumptions & Locked Decisions

1. **Unified Storage in `tamil_discography.db`:**
   - Both film soundtracks and independent album songs reside in `tamil_discography.db`.
   - Distinct classification via `album_type`:
     - `'film'` (7,430 existing cinema albums)
     - `'indie_single'` (non-film album songs, independent singles, EPs)
2. **Multi-Factor Categorization (Views + Editorial Curation):**
   - **Tier 1 (Mega Hits):** 50M+ views (*Enjoy Enjaami*, *Katchi Sera*, *Aasa Kooda*, *Orasaadha*, *Kutty Pattas*, *Vaadi En Machinichi*)
   - **Tier 2 (Popular Blockbusters):** 10M–50M views (7UP Madras Gig, Think Indie hits, Divo viral singles)
   - **Tier 3 (Emerging / Mid-Tier):** 1M–10M views (Vaisagh, Paal Dabba, Asal Kolaar, Stephen Zechariah)
   - **Tier 4 (Deep Underground / Hidden Gems):** <1M views or cult/alternative favorites (Kaber Vasuki, Tenma, Sean Roldan acoustic, experimental Tamil rap)
3. **Playlist Structure in `playlists/indie/`:**
   - `indie_master.db`: Comprehensive collection of all non-film Tamil tracks.
   - `indie_blockbusters.db`: Mega hits & popular singles (10M+ views).
   - `hidden_indie_gems.db`: Underrated, cult, and unrecognized masterpieces.
   - `indie_rap.db`: Street hip-hop, Tamil conscious rap (Arivu, Paal Dabba, Asal Kolaar, ADK).
   - `romantic_indie.db`: Sweet independent melodies & duets (Stephen Zechariah, acoustic love songs).
   - `folk_gaana_album.db`: Village folk singles and Chennai street gaana album songs.
   - Artist Spotlights:
     - `stephen_zechariah.db`
     - `kaber_vasuki.db`
     - `arivu_paal_dabba.db`
     - `vaisagh.db`
     - `sean_roldan_pradeep_indie.db`
4. **Spotify Organization:**
   - Dedicated folder: `Indie` (`spotify:user:...:folder:...`).
   - All 11 indie playlists contained within this folder.

---

## 4. Tech Stack & Dependencies

- **Language:** Python 3.10+
- **Database:** SQLite 3 (WAL mode, synchronous=NORMAL)
- **YouTube Engine:** `ytmusicapi` (already installed and verified in repo)
- **Spotify Engine:** `SpotifyNativeClient` (browser session automation, Pathfinder GraphQL)
- **State & Caching:** `data/indie_seeds.json`, `data/sync_state.json`

---

## 5. Commands

```bash
# 1. Ingest pre-seeded catalog + scan YouTube indie channels
python3 ingest_indie_songs.py --seed --scan

# 2. Build local indie playlist databases (generates playlists/indie/*.db)
python3 build_playlists.py --section indie

# 3. Verify all databases (checks year, schema, and non-film invariants)
python3 verify_all_playlists.py

# 4. Provision Spotify 'Indie' folder container
python3 organize_spotify_folders.py --create-folder "Indie"

# 5. Sync indie playlists to Spotify
python3 sync_indie_playlists_to_spotify.py --all --limit 50
```

---

## 6. Success Criteria (Testable & Empirical)

- [ ] `tamil_discography.db` schema updated with `album_type` and index on `album_type`.
- [ ] At least 300+ verified Tamil independent album songs ingested with title, artist, composer, year, and YouTube URL.
- [ ] Directory `playlists/indie/` contains 11 standalone `.db` files with verified tracklists.
- [ ] Spotify rootlist contains a top-level `Indie` folder container.
- [ ] `verify_all_playlists.py` audits all databases (now 213 total databases) with 0 errors.
- [ ] `auto_update_playlists.py` seamlessly recognizes indie playlists.
