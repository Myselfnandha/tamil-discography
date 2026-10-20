# Technical Implementation Plan: Tamil Independent & YouTube Album Songs Engine

**Feature:** Tamil Indie & YouTube Album Songs Engine  
**Spec Document:** [`SPEC-tamil-indie.md`](file:///home/nandha/play/SPEC-tamil-indie.md)  
**Effort:** `⚡ Effort: ultra`  

---

## Architecture & Dependency Graph

```
YouTube / YouTube Music (ytmusicapi) + Curated Seed Catalog (300+ songs)
                         │
                         ▼
[Task 1: Schema Extension in tamil_discography.db]
  - Add 'album_type' column to albums (default: 'film')
  - Add 'views_tier', 'label' to albums / tracks
                         │
                         ▼
[Task 2: Seed Ingestion & Autonomous Scraper (ingest_indie_songs.py)]
  - Curate & ingest 300+ viral hits and cult favorites
  - Integrate ytmusicapi artist and channel scraper
  - Write records to tamil_discography.db with stream_url & spotify_uri
                         │
                         ▼
[Task 3: Taxonomy Extension & Local DB Generation (build_playlists.py)]
  - Add TAXONOMY["indie"] with 11 playlists (Master, Blockbusters, Hidden Gems, Rap, Melodies, Folk, 5 Artist Spotlights)
  - Generate 11 standalone databases in playlists/indie/*.db
                         │
                         ▼
[Task 4: Audit & Invariant Verification (verify_all_playlists.py)]
  - Audit all 213 databases (139 taxonomy + 63 annual + 11 indie = 213 total)
  - Assert 0 schema errors and valid track counts
                         │
                         ▼
[Task 5: Spotify 'Indie' Folder Container Provisioning]
  - Create 'Indie' folder container in Spotify rootlist via native Web UI
  - Register folder URI in organize_spotify_folders.py
                         │
                         ▼
[Task 6: Spotify Sync Engine (sync_indie_playlists_to_spotify.py)]
  - Create and synchronize all 11 indie playlists inside the 'Indie' folder
  - Batch add tracks (50/batch) and update data/sync_state.json
                         │
                         ▼
[Task 7: Pipeline Hook in auto_update_playlists.py]
  - Hook daily discovery of new indie releases into auto_update_playlists.py
```

---

## 11 Indie Playlists Definition

1. `indie_master` - 🌟 Tamil Independent Master Collection (All non-film tracks)
2. `indie_blockbusters` - 🔥 Tamil Indie Blockbusters (10M+ views / mega hits)
3. `hidden_indie_gems` - 💎 Hidden Indie Gems (Under 5M views / cult & alternative)
4. `indie_rap` - 🎤 Tamil Indie Rap & Street Hip-Hop (Arivu, Paal Dabba, Asal Kolaar, ADK)
5. `romantic_indie` - 🌹 Romantic Indie Melodies (Stephen Zechariah & acoustic love singles)
6. `folk_gaana_album` - 🪘 Folk & Gaana Album Songs (Rural folk & Chennai street singles)
7. `stephen_zechariah` - 🎙️ Stephen Zechariah Collection (Singapore/Malaysia & Indian hits)
8. `kaber_vasuki` - 🎸 Kaber Vasuki Collection (Philosophical indie poetry & cult tracks)
9. `arivu_paal_dabba` - ⚡ Arivu & Paal Dabba Spotlight (Street conscious rap)
10. `vaisagh` - 🕺 Vaisagh Viral Hits (Pop & modern youth anthems)
11. `sean_roldan_pradeep_indie` - 🎼 Sean Roldan & Pradeep Kumar Indie (Acoustic masterworks)
