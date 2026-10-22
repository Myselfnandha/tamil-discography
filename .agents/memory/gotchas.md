# 🛡️ ZeroGravity OS: Anti-Patterns Matrix & Known Gotchas

This document serves as the **Persistent Anti-Patterns Matrix** for OpenHuman and ZeroGravity OS.
Before taking any architectural, coding, or tooling action, the agent must sweep this matrix (Stage 1) to immunize itself against known failure modes.

---

## 📊 Anti-Patterns & Invariant Prevention Matrix

| ID | ⚠️ Mistake / Anti-Pattern | 🔍 Root Cause & Triggers | 🛡️ Invariant Prevention Strategy |
| :--- | :--- | :--- | :--- |
| **AP-001** | **Unchecked npx execution polluting JSON-RPC stdout with colored notices and ANSI escape sequences** | npx in modern npm writes colored notices to stdout when not silenced, breaking JSON-RPC parsing (invalid character '\x1b') | Always wrap Node-based MCP servers using mcp-npx with NO_COLOR=1, npm_config_loglevel=silent, and --silent flag |
| **AP-002** | **Sentry MCP server falling back to interactive OAuth device code flow and hanging** | @sentry/mcp-server defaults to interactive device code login if --access-token or SENTRY_ACCESS_TOKEN is omitted | Pass --access-token ${SENTRY_AUTH_TOKEN} explicitly in CLI arguments and provide environment fallback |
| **AP-003** | **Codebase indexer scanning self-extracting archive payload and inflating codebase database to 40MB+** | Scanning binary payloads or packed archive files in analyze.py treats binary blobs as source text | Exclude *.tar.gz, *.tar.xz, install.sh, and dist/ in codebase indexing routines |
| **AP-004** | **Leaving MCP servers running permanently in background consuming CPU and RAM** | Static mcp_config.json with default background servers creates memory bloat and port collisions | Zero-Default profile: start with empty mcpServers ({}), enable dynamically on-demand, and auto-close upon task completion |
| **AP-005** | **Agent looping over view_file sequentially to understand an entire folder codebase** | Sequential view_file calls waste context tokens and cause high latency | Execute analyze.py --check --auto-heal --inject-ki and read the consolidated codebase_summary.md in a single read |
| **AP-006** | **Refactoring code outside the user's requested scope** | Agent interprets adjacent code as needing improvement or unsolicited optimization. | Blast Radius Lock: Declare edit scope upfront; only edit within declared scope; flag out-of-scope issues as follow-up recommendations. |
| **AP-007** | **Claiming success without running verification commands** | Token-pressure or speed bias leads agent to skip test runs and pattern-match 'this looks right' or use speculative language. | Evidence Gate: Always run tests or re-read files, report actual terminal output, never say 'should work'. |
| **AP-008** | **Editing files based on stale cached memory instead of current on-disk state** | Files read early in long sessions get modified externally or by background tasks while agent remembers old lines. | Freshness Gate: Re-read target file if >5 tool calls since last read; run git status before multi-file edits. |
| **AP-009** | **Using invented library functions that don't exist in installed packages** | LLM hallucination on fast-moving libraries or niche frameworks where training memory contains plausible APIs. | Hallucination Guard: Verify every unfamiliar API symbol via tool inspection, REPL check, or docs before using. |
| **AP-010** | **Substring collisions in title audits flagging genuine vintage tracks** | Checking `WHERE title LIKE '%Yelelo%'` falsely flagged the authentic 1988 song 'Aathukulle Yelelo' (Senthoora Poove) as modern collided song 'Yelelo'. | Exact/Word-Boundary Verification: Check exact title equality or word boundaries rather than generic substring matches. |
| **AP-011** | **Multi-instance IDE sprawl exhausting RAM and causing Linux system lag** | Opening multiple independent IDE windows duplicates Electron renderers, extension hosts, and language servers, exhausting RAM and triggering slow disk swap | Use `ide-open` to consolidate projects into a single `.code-workspace` sharing 1 renderer, 1 extension host, and expand ZRAM to 12GB |
| **AP-012** | **Invalid pseudo/syntax mixing in Playwright CSS selector strings** | Combining Playwright selector extensions like `text='...'` inside comma-separated CSS selectors causes Playwright parser errors | Use `page.get_by_text(...)` or valid `:has-text(...)` pseudo-classes instead of raw `text=` inside CSS lists |
| **AP-013** | **Third-party API derived metric policy violations** | Spotify Feb 2026 Developer Migration removes track popularity in Dev Mode; Spotify and YouTube policies forbid creating cross-platform derived listenership metrics | Independent Historical Evidence Authority: Rank purely on independently documented box-office, award, label legacy, airplay, and cultural impact evidence. |
| **AP-014** | **Zero-default ambiguity penalizing unresearched tracks** | Using `DEFAULT 0.0` or `DEFAULT 'tier_4_archive'` causes unindexed tracks to appear as confirmed failures or archive cuts | Strict Nullability: Use `NULL` for missing evidence and unranked tracks; distinguish unresearched from verified archive cuts. |
| **AP-015** | **Static inventory assertions in evolving catalogs** | Hardcoding total database count (e.g. 213) in audits causes false passes or failures when catalog repairs add/remove databases | Dynamic Inventory Discovery: Discover database files dynamically, record a manifest (`data/catalog_inventory_manifest.json`), and audit against discovered counts. |
| **AP-016** | **Premature Playwright interaction on unhydrated heavy SPAs** | Heavy SPAs (Spotify Web Player) stream background assets, causing page.goto to time out on 'load' or selectors to fail on unhydrated DOM | Use `wait_until='domcontentloaded'`, generous timeouts (45s), and explicitly wait for key hydration anchors (`button[aria-label="Create"]`, `button:has-text("Name & details")`) before clicking. |
| **AP-017** | **Single-track pre-release duplicates polluting annual playlists** | Multi-release streaming entries (singles, promos, full album drops) create duplicate tracks with differing titles or credits | Normalize `(track_title, album_title)` and retain only the highest-evidence version during playlist generation. |
| **AP-018** | **Artist attribution cross-role and substring pollution** | Searching unanchored regexes against combined `{cast, director, composer, singers}` strings caused Prabhu Deva in cast or Shivam Mahadevan in singers to match composer Deva, and actor Rahman to match A. R. Rahman | Strictly scope queries by credit role (`role="composer"` checks only composer), enforce word boundaries (`\b`), and apply negative lookaheads/exclusions for colliding substrings. |
| **AP-019** | **Unscoped searchable metadata string polluting mood/genre/relationship playlists** | Concatenating cast, director, and label into a single searchable string caused comedy actor Thambi Ramaiah to trigger 'family', Ravi Krishna to trigger 'devotional', and Sri Surya Movies to trigger 'energetic' | Scope Isolation: Decouple search scopes into `song_scope` (`t_title` + `raga`) for emotions/themes, `film_scope` for mass themes, and `music_scope` for music credits. Never search actor cast, directors, or studio labels for mood or genre. |
| **AP-020** | **Wikitable column shifts when Track and Song headers co-exist** | When Wikipedia table headers contained both '! Track !! Song !! Singer(s)', scraper matched 'Track' as title candidate, popping col 0 and shifting song title into singers and duration into lyricist. | Role Disambiguation: If a header has 'song' or 'title', 'track' is mapped strictly to track_num. Access row cells by absolute column index without slicing. |
| **AP-021** | **Wikipedia annual list tables column order variance shifting cast into albums.composer** | Wikipedia annual film lists (1970–1989) have 5 columns: 'Title \| Director \| Production \| Music \| Cast'. Naive scrapers mapped column 4 (Cast) to composer and column 2 to cast, polluting composer with actor cast lists. | Dynamic Table Header Inspection: Parse wikitext headers per year; detect omitted Date columns; extract true composer from Infobox film and annual list Music column. |
| **AP-022** | **Unanchored sub-word matching and missing negative emotional filters in playlist taxonomy** | Unanchored regexes (e.g. 'danga') matched inside unrelated words (e.g. 'Bandangala' -> relations), and missing negative filters allowed party/kuthu tracks into sad/breakup playlists. | Strict Word Boundaries & Negative Emotional Gates: Enforce word boundaries `\b` for all keywords; strictly exclude party/dance/kuthu from sad/breakup, and aggressive/fight themes from calm/peaceful/sleeping. |



---

## 🛠️ Platform & Tooling Gotchas

### 1. Skylos SAST on Meta-Directories
- **Gotcha**: Scanning directories containing 1,450+ offline skill scripts causes slow traversal.
- **Rule**: Pass `--exclude .agents --exclude .agent --exclude venv` when running whole-project audits.

### 2. PEP 668 & Linux System Python Isolation
- **Gotcha**: Modern Linux distros (Arch, Debian 12+, Ubuntu 24+) block system-wide `pip install`.
- **Rule**: Provision isolated virtual environments under `~/.local/share/<tool>/venv` and symlink CLI entrypoints to `~/.local/bin/`.

### 3. NPM Remote Package Authorization (`EALLOWREMOTE`)
- **Gotcha**: npm v12+ defaults `allow-remote="none"`, failing to install git-based tarball dependencies.
- **Rule**: Configure `npm config set allow-remote all` during environment setup.

---

## 🔄 The 2-Way Immunization Protocol
1. **Pre-Action Check**: Before executing a tool call or creating a component, verify against this matrix.
2. **Post-Failure Distillation**: When a mistake, test failure, or user correction occurs:
   - Identify the exact root cause.
   - Formulate an Invariant Prevention Strategy.
   - Append to this matrix and `anti_patterns.json` via `zg learn add`.
