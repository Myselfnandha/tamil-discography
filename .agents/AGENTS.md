# ZeroGravity OS (AGENTS.md)

Autonomous Supercoding Engine. 5-stage pipeline (on `/build-feature`): Memory Sweep→Blueprint→CodeCrush→AAA Test→Sync.
On any major execution complete: automatically run `/learn` distillation to memory followed by a quick `/grill-me` alignment.
Anti-patterns inlined in `.agents/rules/core.md`. Memory files (decisions/gotchas/goals) read on-demand via `/build-feature` or `/learn`.

## Tooling
- MCPs: zero-default, on-demand (`npx @nandhaalagesan/zerogravity mcp enable <name>` or `zg mcp enable <name>`). 12 verified servers + 2,600+ searchable catalog.
- CLI: `npx @nandhaalagesan/zerogravity` / `zg` (install|update|mcp|harness)
- Harness²: Recursive agent harnessing engine (arXiv:2610.14224) optimizing c1..c8 via Propose-Probe-Compose (`/harness` or `zg harness`)
- Slash: /build-feature /harness /spec /review /webperf /ship /reach /agent-reach /mcp /effort-low /effort-mid /effort-high /effort-ultra /brainstorm /create /debug /test /deploy /enhance /design-ui /codebase-design /domain-model /orchestrate /focus /humanize-text /compress-tokens /skill /yagni-simplify /audit-agent /react-components
- Built-ins: /plan (Native interactive planning mode), /goal (Autonomous run-until-done), /grill-me (Socratic plan alignment), /schedule, /learn

