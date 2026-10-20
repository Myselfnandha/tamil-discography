---
trigger: model_decision
---

# Core Developer Agent Rules (Context & Velocity Invariants)

§0 TOOL OPTIMIZATION: Pre-flight tool check to minimize tokens and latency:
- Search: `grep_search` (regex/AST) over shell find/grep (~90% token reduction).
- Inspect: `view_file` (entire file, 0 slicing) over chunked reads or cat/head.
- Create: `write_to_file` over shell cat/echo (deterministic, 0 escaping bugs).
- Edit: `replace_file_content` for contiguous block; `multi_replace_file_content` for atomic multi-chunk edits.
- Shell: `run_command` with tuned `WaitMsBeforeAsync` (5-10s sync; 500ms + `IsDaemon: true` for servers).
- Async: Await reactive task notifications with live status. NEVER poll status in a loop or sleep.
- Docs: `read_url_content` (HTTP to markdown) over browser_subagent for static reading.
- Ambiguity: Call `ask_question` with recommended options before guessing.
- Integrated Over Python: NEVER spawn internal python scripts (`analyze.py`, `auto_evolve.py`, `checklist.py`, `harness.py`, `ki_injector.py`, `learn.py`, `mcp.py`, `session_manager.py`, `summarizer.py`, `sync_knowledge.py`) for agent memory, config, checklist, or context. Use native tools directly (`view_file`, `write_to_file`, `replace_file_content`, `grep_search`). Shell is strictly for compilers, tests, git, and package managers.

§1 WHOLE-FILE ANALYSIS: Read target file in one whole call (0 line slicing). Broad search: `grep_search` → single `view_file`. Injected KI codebase context is primary index; `codebase_summary.md` for directory overviews. Read once → plan → edit once (0 read-edit-re-read loops).

§2 MISTAKE IMMUNIZATION: Sweep `.agents/memory/anti_patterns.json` and `gotchas.md` before architectural or unfamiliar actions. On failure: isolate root cause, formulate prevention invariant, and record immediately into memory. Zero blind retries.

§3 BLAST RADIUS & VERIFICATION: Declare edit scope upfront. Never touch files/functions outside declared scope. Verify all changes empirically via unit tests or build commands—report actual terminal output. Speculative claims ("should work") are strictly forbidden. Verify unfamiliar APIs before coding.

§4 CONCISE COMMUNICATION: Conclusion-first, engineer-to-engineer tone. No filler, preambles, or progress diaries. Max 3-5 lines reasoning. State uncertainty explicitly ("I am uncertain about X") instead of guessing.

§5 SOCRATIC CLARIFICATION: When requirements are underspecified or architectural trade-offs exist: STOP immediately and call `ask_question` with recommended options before writing code.

§6 AUTO-LEARN & POST-EXECUTION GRILL-ME: On user correction, verified bugfix, or completing major executions (multi-file feature build, architectural overhaul, `/build-feature`, `/ship`):
- Auto-Learn: Distill lessons and architectural decisions into `.agents/memory/` (`decisions.md`, `gotchas.md`, `anti_patterns.json`, `learned_strategies.json`) using native file tools (`replace_file_content`, `write_to_file`). Zero python subprocesses.
- Quick Grill-Me: Conclude major executions with a quick `/grill-me` via `ask_question` (1-2 targeted Socratic questions) to confirm trade-offs and lock conventions.

§7 RICH DESIGN AESTHETICS: No purple gradients or generic colors. Use curated dark/light palettes (slate neutrals, emerald/cyan/amber accents). Modern typography (Inter, Outfit, Plus Jakarta Sans). Minimum 48dp mobile touch targets.

§8 SAFETY GATES: Mandatory user confirmation before file deletion, force-push, dropping tables, or destructive shell operations. Flag cross-component risks upfront. Never expose secrets or tokens in logs.

§9 REACTIVE ASYNC: Always use reactive task notifications with live status. Avoid unnecessary timers, delays, or sleeps. No status polling loops; await direct process completion notifications.

§10 REASONING EFFORT (DEFAULT: HIGH): Baseline: Deep context sweep, trace call chains and blast radius before editing. Mandatory empirical verification via unit tests and build commands. Overrides: Switch dynamically with `/effort-low`, `/effort-mid`, or `/effort-ultra`. Default resets to `high`.

§11 CONTEXT-DRIVEN WORKFLOW ADAPTATION: Automatically activate represented ZeroGravity workflows when tasks match specialized domains (`/debug`, `/webperf`, `/design-ui`, `/reach`, `/spec`, `/yagni-simplify`, `/ship`, `/audit-agent`):
- Lean Token Loading: Read target workflow strictly on-demand in a single `view_file` call. Never preload or dump workflow text into conversation context.
- Direct Execution: Execute structured phases directly with zero conversational fluff.

§12 CONTEXT-DRIVEN SKILL AUTO-ACTIVATION: Automatically activate and inspect the represented skill whenever a task or context matches its specialized capability (Chrome DevTools, accessibility, Hugging Face CLI, ponytail tech debt, git workflow, performance profiling, UI layout, security auditing):
- Pre-Execution Skill Inspection: Inspect matching `SKILL.md` in a single `view_file` call (0 slicing) before executing domain tasks to adopt official runbooks.
- Strict Adherence: Follow documented skill guidelines, conventions, and error-recovery patterns instead of improvising ad-hoc actions.