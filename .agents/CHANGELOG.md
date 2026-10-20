# ZeroGravity OS Changelog

## 1.2.3 (2026-10-19)

### Performance & Token Economy Overhaul (~80% Prompt Token Reduction)
- **Eliminated Scratch Artifact Bloat (-9,520 tokens/turn)**:
  - Purged 224 accumulated temporary git clones from the brain scratch directory.
  - Reduced conversation artifact registry headers from 224 down to 0 scratch files.
- **Rule Deduplication & Deconfliction (-1,698 tokens/turn)**:
  - Deconflicted global rules (`~/.gemini/config/rules/`) with workspace rules (`.agents/rules/`).
  - Removed duplicate copies of `core.md`, `effort.md`, and `codebase_context.md` from global rules.
  - Preserved only universal `auto_codebase_context.md` globally, allowing Antigravity to inject workspace rules exactly once per turn.
- **Plugin Skill Restructuring (-3,638 tokens/turn)**:
  - Migrated 31 plugin skills from `.agents/plugins/*/skills/` directly into `.agents/skills/`.
  - Completely eliminated Antigravity's redundant `<plugins>` double-advertising block while preserving full skill functionality.
- **Progressive Disclosure Frontmatter Compaction (-2,535 tokens/turn)**:
  - Compacted `description:` across all 47 skills to high-signal 1-sentence triggers (60-100 characters).
  - Reduced `<skills>` block from 21,402 chars to 11,263 chars.
- **Knowledge Item (KI) Pruning (-600 tokens/turn)**:
  - Pruned stale, non-existent workspace KIs from `~/.gemini/antigravity-ide/knowledge/`.
  - Fixed relative metadata file references in `ki_injector.py` to target `.agents/codebase_summary.md`.

## 1.2.2 (2026-10-19)

### Features & Google Research Harness² Integration
- **Harness² Recursive Agent Harnessing (arXiv:2610.14224)**:
  - Full integration of Google Research's Harness² framework ("Recursive Agent Harnessing for an Open World").
  - Formally defined and instrumented the **8 editable harness components (`c1..c8`)** for Antigravity & ZeroGravity OS:
    - `c1` System Prompt (`AGENTS.md`)
    - `c2` Guardrails & Rules (`.agents/rules/`)
    - `c3` Memory (`.agents/memory/`)
    - `c4` Tool Guidance (`.agents/mcp_config.json`, `mcp-registry/`)
    - `c5` Subagents (`.agents/plugins/agent-skills/agents/`)
    - `c6` Skills (`.agents/skills/`, `.agents/plugins/*/skills/`)
    - `c7` Scripts (`.agents/scripts/`)
    - `c8` Plugins & Hooks (`.agents/hooks/`, `hooks.json`, `.agents/plugins/`)
- **Propose-Probe-Compose (PPC) Engine (`.agents/scripts/harness.py`)**:
  - Implements contrastive candidate harness proposals across Invariant (`INV`) and Domain (`DOM`) dimensions.
  - Generates behavioral contrast without requiring external ground-truth feedback.
  - Automatically synthesizes non-conflicting winning edits with omitted-is-inherited diff semantics.
- **Experience Ledger (`.agents/memory/harness_ledger.json`)**:
  - Tracks task-level rollouts, proposal counts, adopted harnesses, and lessons learned.
  - Connects task-level recursion with persistent harnessing-level meta-reflection.
- **CLI & Workflow Integration**:
  - Added `/harness` slash command workflow (`.agents/workflows/harness.md`).
  - Added dedicated Harness² skill (`.agents/skills/harness/SKILL.md`).
  - Integrated `zg harness` and `npx @nandhaalagesan/zerogravity harness` commands (`status`, `inspect`, `validate`, `propose`, `ledger`).
  - Updated `bin/cli.js` syncFolders to include `plugins/` across multi-workspace sync.
- **Surface Validation & Census**:
  - Added surface invariants validation and component budget checks.
  - Added unit test coverage in `tests/test_all.py` (CLI help, schema validation, smoke tests).

## 1.2.1 (2026-10-19)

### Features & Multi-Workspace Background Auto-Sync
- **Central Workspaces Registry (`~/.gemini/config/workspaces.json`)**:
  - Automatically records and tracks all active projects where ZeroGravity (`.agents/`) is installed across the system.
  - Auto-discovers workspaces dynamically from Antigravity IDE knowledge context (`~/.gemini/antigravity-ide/knowledge/`) and filesystem scans.
- **Push Mode Synchronization (`bin/cli.js`)**:
  - Whenever `npx @nandhaalagesan/zerogravity update` or `zg update` runs, it automatically synchronizes the update across all other registered workspaces on the machine in the background.
  - Supports explicit multi-project updates via `-A` / `--all-workspaces`.
  - Always safely preserves each project's `.agents/memory/` (decisions, gotchas, goals) and `.agents/mcp_config.json`.
  - Added self-overwrite protection preventing development repository from modifying itself during sync.
- **Pull Mode & Silent Self-Healing (`scripts/analyze.py`)**:
  - Automatically executes on conversation start via `auto_codebase_context.md`.
  - Detects if the workspace's `.agents/` is older than `~/.gemini/config/VERSION` and silently self-syncs in ~20ms without blocking.
  - Includes a non-blocking background npm freshness check (cached every 12h) to detect new releases and trigger background updates.

## 1.2.0 (2026-10-19)

### Features & Addy Osmani Agent-Skills Integration
- **Full Plugin Suite (`.agents/plugins/agent-skills/`)**: Integrated Addy Osmani's complete production-grade software engineering skill suite:
  - **25 Specialized Skills**: `api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`, `code-review-and-quality`, `code-simplification`, `constraint-driven-development`, `context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`, `doubt-driven-development`, `frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`, `interview-me`, `observability-and-instrumentation`, `performance-optimization`, `planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`, `source-driven-development`, `spec-driven-development`, `test-driven-development`, `using-agent-skills`.
  - **4 Subagent Roles**: `code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`.
  - **7 Reference Checklists**: Accessibility, Definition of Done, Observability, Orchestration Patterns, Performance, Security, and Testing Patterns.
- **Dedicated Slash Workflows**:
  - `/spec`: Requirements gathering, constraint identification, user stories, and acceptance criteria.
  - `/review`: 5-axis code review across correctness, design, performance, security, and testability.
  - `/webperf`: Web performance audit, Core Web Vitals (LCP/INP/CLS), bundle optimization, and rendering efficiency.
  - `/ship`: Multi-specialist pre-launch review, smoke testing, migration verification, and Go/No-Go decision.
- **CLI & Sync Automation**: Updated `bin/cli.js` with intelligent plugin synchronization preserving user custom plugins while updating built-in plugins (`agent-skills`, `ponytail`) locally and globally in `~/.gemini/config/plugins/`.
- **Skills Registry Indexing**: Re-indexed registry to 46 total skills in `skills_index.json`.

## 1.1.9 (2026-10-19)

### Features & Agent-Reach Integration
- **Agent Reach Skill (`skills/agent-reach/`)**: Integrated universal internet capability router supporting 16 platforms (Twitter/X, Reddit, Facebook, Instagram, YouTube, GitHub, Bilibili, XiaoHongShu, LinkedIn, Boss直聘, V2EX, Xueqiu, RSS, Exa web search, Jina Reader).
- **`/reach` & `/agent-reach` Slash Workflows**: Added dedicated workflows for autonomous internet search, transcript extraction, and cross-platform multi-source synthesis.
- **Skills Registry Indexing**: Re-indexed 21 skills in `skills_index.json`.
- **Global Synchronization**: Synchronized `agent-reach` skill and `/reach` workflows directly to `~/.gemini/config/` for universal access across all workspaces.

## 1.1.8 (2026-10-18)

### Enhancements & Global Rules Auto-Sync
- **Universal Global Rules Sync**: Updated CLI (`bin/cli.js`) and installer (`pack.sh`) to always synchronize core rules (`core.md`, `effort.md`) and all 23 slash workflows directly into `~/.gemini/config/` on any install or update. This guarantees baseline reasoning invariants apply across all workspaces (e.g. Pocket, new projects).
- **Clean Global Overwrites**: Removed legacy `.bak` directory creation during global installation.

## 1.1.7 (2026-10-17)

### Fixes & Clean Overwrite
- **Clean Workspace Overwrite**: Removed `.agents.bak.<timestamp>` folder creation when overriding `.agents/` via `npx @nandhaalagesan/zerogravity` or `install.sh`. Overwriting now cleanly replaces target workspace components without leaving backup clutter behind.
- **Zero-Binary Packaging**: Added automated `prepack` purge for bytecode and database caches, ensuring clean, quarantine-free npm package delivery.
- **CLI Output Cleanups**: Updated dry-run update messages to accurately reflect in-place updates.

## 1.1.6 (2026-10-17)

### Fixes & Clean Overwrite
- **Clean Workspace Overwrite**: Removed `.agents.bak.<timestamp>` folder creation when overriding `.agents/` via `npx @nandhaalagesan/zerogravity` or `install.sh`. Overwriting now cleanly replaces target workspace components without leaving backup clutter behind.
- **CLI Output Cleanups**: Updated dry-run update messages to accurately reflect in-place updates.

## 1.1.5 (2026-10-17)

### Highlights & Reasoning Effort Optimization
- **Default High Reasoning**: Set baseline model reasoning effort to `high` (Claude-style deep reasoning) in `rules/core.md` (§10) and `rules/effort.md`.
- **Restored Granular Effort Workflows**: Retained dedicated `/effort-low`, `/effort-mid`, `/effort-high` (default), and `/effort-ultra` workflows.
- **Removed Redundant Effort Entrypoint**: Pruned `.agents/workflows/effort.md` in favor of direct granular slash commands.

## 1.1.4 (2026-10-17)

### Highlights & Slim Optimization
- **File Count Reduced**: Down to 115 total package files (from 229+) and 516 KB installer.
- **Workflow & Rules Consolidation**: Merged all effort levels into unified `workflows/effort.md` and `rules/core.md` (§10).
- **Purged Obsolete Workflows & Manifests**: Deleted legacy `prd-workflow.md`, `teach-concept.md`, `spec-driven-dev.md`, and stale `manifest.json`.
- **Ecosystem & Redundancy Pruning**: Removed dead `DEPENDENCY_GRAPH.md`, unused ecosystem templates, and session scratch files.
- **MCP Catalog Isolated in Skill Data**: Moved 1.27 MB community catalog dataset into `skills/mcp/data/` leaving core `mcp-registry/servers.json` lean (5 KB, 12 verified servers).

## 1.1.3 (2026-10-15)

### Highlights & Major Optimization
- **Portability & Zero-Dependency Installation**: Bundled authoritative `AGENTS.md` directly into `.agents/` ensuring complete standalone functionality when copying `.agents/` to any new workspace.
- **Complete OpenHuman Purge**: Removed all legacy OpenHuman references across workflows, agents, scripts, templates, and memory; established pure 5-stage feature pipeline (`/build-feature`).
- **2,648+ MCP Server Catalog**: Deleted bloated `servers/` sources and compiled a lightweight, structured `mcp_catalog.json` indexing 2,648 MCP servers with runtime commands and zero background bloat.
- **Skills Renamed & Standardized**: Renamed skills to match slash workflows (`compress-tokens`, `humanize-text`, `audit-agent`, `react-components`); all skills verified with valid `SKILL.md` frontmatters.
- **Time & Context Economy Rules**: Strengthened `rules/core.md` with strict pre-flight tool selection (§0), whole-file analysis invariant (§1), and reactive async waiting with live status (§9).
- **Scripts & Schemas Pruned**: Removed obsolete Chinese documentation validators and non-mandatory schemas; enhanced `checklist.py` with multi-project fallback.

## 2026.8.31

### Added

- Embedded mandatory `DESIGN.md` (Design Source-of-Truth) gate into `app-builder` orchestration pipeline, scaffolding structure, and Next.js templates.
- Added 2026 AI Application Pattern (Vercel AI SDK streaming, PostgreSQL pgvector, vector search, LLM API rate limiting) and SQL-first Drizzle ORM options in `tech-stack.md`.
- Added project type detection for AI/Chatbot applications and Game applications (`game-development` skill routing).
- Integrated automatic preview verification (`auto_preview.py`) into iterative enhancement and DevOps handoff.

### Changed

- Advanced toolkit version to `2026.8.31`.
- Bumped `app-builder` skill version to `1.1.0`.
- Standardized `globals.css` path to `src/app/globals.css` across Next.js templates.
- Fixed Express API template dependencies to include `@prisma/client` in dependencies and `prisma` as devDependency.
- Updated the `mcp-builder` skill for the stable MCP `2026-07-28` specification: stateless per-request metadata, `server/discover`, explicit state handles, extension negotiation, JSON Schema 2020-12, compatibility behavior, and migration guidance for deprecated features.
- Reworked the orchestrator and `parallel-agents` guidance around Antigravity-native agents and tasks while retaining best-effort portability for other runtimes.

### Security

- Added required safeguards for external `$ref` resolution, schema-validation resource limits, untrusted tool annotations, explicit consent, least privilege, secret handling, and execution isolation.
- Added explicit trust boundaries for repository content, MCP responses, tool annotations, web content, logs, and subagent outputs.
- Added finite agent, delegation-depth, turn/retry, timeout, cancellation, and no-progress controls to prevent recursive delegation and indefinite ReAct loops.


## 2026.7.26

### Added

- Antigravity runtime contract with six production integration phases.
- Native `PreToolUse` hook and destructive-command policy.
- Antigravity Doctor, MCP synchronization helper, plugin builder, schemas, and regression tests.
- Complete migration, production checklist, security, and operator documentation.

### Changed

- Toolkit version advanced from `2026.7.18` to `2026.7.26`.
- Google Antigravity is the primary production runtime; other Markdown-compatible tools are best-effort consumers.
- Component manifest now records Antigravity runtime metadata.
- Integrity lock now covers `antigravity.json`, `hooks.json`, and the complete `hooks/` runtime-tooling tree.
- Self-validation and Antigravity Doctor enforce synchronized root, CLI, web, and toolkit versions.

### Security

- High-confidence root/disk destructive commands are blocked before tool execution.
- Invalid or unknown hook payloads fail open with a warning to avoid runtime-wide lockout.
- MCP writes remain explicit, placeholder-blocked, conflict-aware, and backup-protected.
- Plugin artifacts are reviewable and contain no home-directory configuration or environment secrets.

### Compatibility

- Existing agent, skill, workflow, rule, and memory names remain compatible.
- The native safety hook is enabled by default and can be temporarily disabled for compatibility diagnosis.
- Plugin installation is optional; repository `.agents/` remains the project source of truth.

## 2026.7.18

### Added

- Strict SemVer metadata for all 20 agents, 47 skills, 13 workflows, and 6 rules.
- Machine-readable `manifest.json` with agent-to-skill and workflow dependencies.
- Deterministic `manifest.lock.json` with SHA-256 integrity hashes.
- Generated `DEPENDENCY_GRAPH.md` for workflow → agent → skill orchestration.
- JSON schemas for component metadata, manifest, lock, and memory topics.
- Standard memory topic files for user preferences, technical decisions, and feedback history.
- Registry and graph generation scripts with non-mutating `--check` modes.

### Changed

- Toolkit version advanced from `2026.7.12` to `2026.7.18`.
- Self-validation now checks component versions, workflow references, dependency compatibility, registry drift, lock integrity, graph drift, and memory contracts.
- CI now treats generated registry files as release artifacts that must remain synchronized.

### Compatibility

- Official runtime support remained Gemini CLI and Google Antigravity for that release.
- The component metadata and dependency format remain portable and avoid unnecessary platform coupling.

## 2026.7.12

- Release-safety upgrade, non-destructive CLI updates, rollback support, CI, dependency review, and hardened publishing.
