# SPEC-year-multi-tier-popularity.md: Evidence-Based Multi-Tier Annual Playlists Engine (1960–2026)

## 1. Overview & Objective
This specification defines the architecture, data schemas, deterministic historical scoring algorithms, and safe synchronization workflows for organizing all Tamil annual playlists (1960–2026) into strictly prioritized, multi-tier listening experiences.

Ranking authority is derived exclusively from **independently sourced historical and cultural evidence** (theatrical longevity milestones, awards, label catalog stature, airplay recurrence, and cultural impact), completely eliminating dependency on volatile or policy-restricted third-party API metrics.

---

## 2. Core Architectural Invariants

### 2.1 Scope & Calendar Inventory
- **Calendar Span**: 1960–2026 inclusive is **67 years**.
- **Active Workspace Inventory**: Currently **63 active years** populated in `tamil_discography.db`.
- **Catalog Repair Isolation**: Years `1990`, `1991`, `1993`, and `1995` contain 0 tracks due to corrupted Wikipedia HTML scrapes (`rowspan="1"` in `data/*.json`). These four years are tracked in a dedicated repair pipeline and will not block or corrupt the 63 verified active databases.
- **Dynamic Inventory Manifest**: Audits must discover database files dynamically from the filesystem rather than asserting a hardcoded database count.

### 2.2 Independent Evidence Authority (Zero API Policy Risk)
- **Spotify February 2026 Policy Alignment**: Spotify has removed track popularity from Development Mode responses and strictly prohibits creating derived listenership metrics.
- **YouTube June/September 2026 Policy Alignment**: YouTube restrictions prevent combining API analytics into cross-platform derived metrics.
- **Invariant**: `historical_evidence_score` is the sole ranking authority. Permitted platform observations (Spotify URIs, YouTube stream URLs) are stored in separate, isolated columns for playback matching only, with independent retention rules.

### 2.3 Strict Nullability (No Zero Defaults)
- Missing or unresearched evidence is stored as `NULL` (never `0.0`).
- Unranked tracks carry `evidence_tier = NULL`, strictly distinct from verified `tier_4_archive` tracks.

---

## 3. Data Schema Specifications

### 3.1 Master Catalog Schema Migration (`tamil_discography.db`)
Repeatable migration checks existing columns before applying `ALTER TABLE`:

```sql
-- Track-level evidence summary columns
ALTER TABLE tracks ADD COLUMN historical_evidence_score REAL DEFAULT NULL;
ALTER TABLE tracks ADD COLUMN evidence_tier TEXT DEFAULT NULL;
ALTER TABLE tracks ADD COLUMN evidence_confidence REAL DEFAULT NULL;
ALTER TABLE tracks ADD COLUMN scoring_version TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_tracks_hist_evidence 
ON tracks(historical_evidence_score, evidence_tier);

-- Separate Evidence Provenance Table
CREATE TABLE IF NOT EXISTS track_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,         -- box_office_milestone, national_award, state_award, filmfare_award, label_flagship, airplay_recurrence, cultural_impact
    subject TEXT NOT NULL,               -- track, album, film, artist
    points REAL NOT NULL,
    source_url TEXT,
    publication_date TEXT,
    verification_date TEXT,
    confidence REAL NOT NULL,            -- 0.0 to 1.0
    attribution_method TEXT NOT NULL,    -- direct_track_award, film_milestone_inheritance, flagship_soundtrack_inheritance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_track_id ON track_evidence(track_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON track_evidence(evidence_type);
```

### 3.2 Playlist Database `tracks` Schema (`playlists/year/{year}.db`)
```sql
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position INTEGER NOT NULL,                   -- Strictly monotonic: 1, 2, ... N
    track_title TEXT NOT NULL,
    album_title TEXT NOT NULL,
    year INTEGER NOT NULL,
    composer TEXT,
    singers TEXT,
    lyricist TEXT,
    duration TEXT,
    track_type TEXT DEFAULT 'song',
    stream_url TEXT DEFAULT NULL,
    evidence_tier TEXT DEFAULT NULL,             -- tier_1_mega, tier_2_popular, tier_3_cult, tier_4_archive
    historical_evidence_score REAL DEFAULT NULL,
    evidence_confidence REAL DEFAULT NULL,
    scoring_version TEXT DEFAULT NULL,
    spotify_query TEXT,
    spotify_uri TEXT DEFAULT '',
    discography_track_id INTEGER,
    match_reason TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracks_pos ON tracks(position);
CREATE INDEX IF NOT EXISTS idx_tracks_tier ON tracks(evidence_tier);
CREATE INDEX IF NOT EXISTS idx_tracks_year ON tracks(year);
```

---

## 4. Authoritative Scoring Rubric & Deterministic Contract

### 4.1 Single Unified Scoring Formula
$$\text{Score} = \text{milestone} + \text{award} + \text{label\_legacy} + \text{airplay} + \text{cultural\_impact}$$

| Factor | Evidence Requirement | Points | Deduplication Rule |
|---|---|:---:|---|
| **Theatrical Milestone** (`milestone`) | Verified Silver Jubilee (175 days / 25 weeks) or 100-day blockbuster run from film trade ledgers | +35 | Max 1 milestone per film; inherited by album tracks |
| **Documented Award** (`award`) | National Film Award, Tamil Nadu State Film Award, or Filmfare Award for Best Music / Best Song / Best Singer | +25 | Direct song award = full points (+25); album award = +15 |
| **Label Flagship Catalog** (`label_legacy`) | Flagship platinum LP/cassette release on premier label (HMV/Saregama, Echo, Pyramid, Sony, Think Music) | +20 | Max 1 label tier score per soundtrack |
| **Airplay Recurrence** (`airplay`) | Verified multi-decade radio recurrence (All India Radio / Ceylon / Suryan FM / Radio Mirchi top recurrers) | +15 | Single award per track |
| **Cultural Impact** (`cultural_impact`) | Landmark anthem status (frequently re-recorded, referenced, or cultural touchstone) | +10 | Documented evidence required |

*Invariant*: No track may earn duplicate points for multiple citations of the same single achievement.

### 4.2 Deterministic Tie-Breaker Ladder
When two tracks share the exact same `historical_evidence_score`:
1. **Soundtrack Legacy Score Descending**: Sum of all evidence points for the parent album.
2. **Original Track Sequence Ascending**: Track 1 of original LP/cassette release precedes Track 2, 3, etc.
3. **Database Primary Key Ascending**: `discography_track_id ASC` (guarantees 100% reproducible ordering).

*Invariant*: Subjective composer seniority is prohibited; composer achievements must be recorded as documented evidence.

### 4.3 Evidence-Qualified Tier Assignment
Tier placement is strictly governed by evidence score thresholds. Target quotas are guidelines, NOT rigid constraints:

| Tier Identifier | Display Name | Threshold Criteria | Target Guideline |
|---|---|---|---|
| `tier_1_mega` | **Mega Blockbuster Hits** | Score $\ge 50.0$ AND Confidence $\ge 0.8$ | ~15 – 25 tracks |
| `tier_2_popular` | **Popular Chartbusters** | Score $\ge 30.0$ and $< 50.0$ | ~25 – 35 tracks |
| `tier_3_cult` | **Cult Gems & Fan Favorites** | Score $\ge 15.0$ and $< 30.0$ | ~40 – 60 tracks |
| `tier_4_archive` | **Archive & Film B-Sides** | Score $< 15.0$ (verified researched) | Remainder |
| `NULL` | **Unranked / Unresearched** | No evidence collected yet | 0 after Phase 3 |

*Invariant*: If only 12 songs in a vintage year meet the $\ge 50.0$ threshold, Tier 1 contains exactly 12 songs. Low-confidence songs are never artificially promoted.

---

## 5. Pilot Specifications (1985 Vintage & 2024 Modern)

### 5.1 Vintage Era Pilot: 1985 (593 Tracks in Catalog)
*Autograph* (2004) and *Punnagai Mannan* (1986) are strictly excluded from 1985 test fixtures.
Verified 1985 Track-Level Assertions:
1. `Poove Poochoodava` (*Poove Poochoodava* - Track ID 41366, K.J. Yesudas, Ilaiyaraaja) -> Must rank in `tier_1_mega`
2. `Sangeetha Megam` (*Udaya Geetham* - Track ID 41503, S.P. Balasubrahmanyam, Ilaiyaraaja) -> Must rank in `tier_1_mega`
3. `Kanmaniye Pesu` (*Kaakki Sattai* - Track ID 49466, S.P. Balasubrahmanyam, S. Janaki) -> Must rank in `tier_1_mega`
4. `Namma Singaari Saraku` (*Kaakki Sattai* - Track ID 49467, S.P. Balasubrahmanyam) -> Must rank in `tier_1_mega`
5. `Poongaatru Thirumbuma` (*Muthal Mariyathai* - Track ID 41281, Malaysia Vasudevan, S. Janaki) -> Must rank in `tier_1_mega`
6. `Kuyile Kuyile Poonguyile` (*Aan Paavam* - Track ID 41033, Malaysia Vasudevan, K.S. Chithra) -> Must rank in `tier_1_mega`

### 5.2 Modern Era Pilot: 2024 (675 Tracks in Catalog)
Verified 2024 Track-Level Assertions:
1. `Katchi Sera` (*Sai Abhyankkar* - Track ID 49666, Think Music Indie) -> Must rank in `tier_1_mega`
2. `Aasa Kooda` (*Sai Abhyankkar* - Track ID 49667, Think Music Indie) -> Must rank in `tier_1_mega`
3. `Whistle Podu` (*The GOAT* - Yuvan Shankar Raja, Thalapathy Vijay) -> Must rank in `tier_1_mega`
4. `Matta` (*The GOAT* - Yuvan Shankar Raja, Shenbagaraj) -> Must rank in `tier_1_mega`
5. `Manasilaayo` (*Vettaiyan* - Anirudh Ravichander, Malaysia Vasudevan AI, Manju Warrier) -> Must rank in `tier_1_mega`

---

## 6. Execution Phasing & Gates

### Phase 0: Pre-Flight Backups & Scope Validation
- Create `tamil_discography.db.bak` and timestamped `playlists_backup/`.
- Dynamic manifest generated: count active databases in `playlists/`.
- Freeze scoring formula and tie-breaker contract.

### Phase 1: Schema Migrations & Evidence Engine
- Run repeatable migrations on `tamil_discography.db` (inspect before `ALTER`).
- Create `track_evidence` table with provenance attributes.
- Ingest verified historical records for 1985 and 2024.

### Phase 2: Pilot and Audit (1985 & 2024)
- Run `engine/historical_evidence.py --year 1985` and `--year 2024`.
- Re-generate `1985.db` and `2024.db`.
- Validate track-level fixtures and strict monotonic position order.
- Generate dry-run diff report; verify non-destructive rollback behavior.

### Phase 3: Spotify Sync Pilot
- Generate pre-sync diff report (`data/spotify_diff_1985.json`, `data/spotify_diff_2024.json`).
- Require explicit `--execute` confirmation.
- Sync ranked tracks into Spotify `Year` folder. Verify track 1 matches evidence leader.

### Phase 4: Full Catalog Expansion (10-Year Batches)
- Process in restartable batches:
  - Batch 1: 1960–1969
  - Batch 2: 1970–1979
  - Batch 3: 1980–1989
  - Batch 4: 1990–1999 (excluding un-repaired 1990, 1991, 1993, 1995)
  - Batch 5: 2000–2009
  - Batch 6: 2010–2019
  - Batch 7: 2020–2026
- Run `PRAGMA integrity_check` on all databases after each batch.

### Phase 5: Dynamic Catalog Audit & Pipeline Update
- Update `verify_all_playlists.py` with dynamic database discovery and integrity validation.
- Hook into `auto_update_playlists.py` with pre-sync diff generation.
