---
description: Recursive Agent Harnessing (Harness²) — optimize the 8 components (prompts, rules, memory, tools, subagents, skills, scripts, hooks) using Propose-Probe-Compose recursion.
---

# /harness — Recursive Agent Harnessing (Harness²)

You are now in **RECURSIVE HARNESSING MODE** (Google Research Harness², arXiv:2610.14224).
Your objective is to recursively analyze, contrast, and refine the 8 harness components around the model to maximize execution capability without modifying model weights.

## Target / Friction Scope
$ARGUMENTS

---

## The 8 Harness Components (`c1..c8`)

| Component | Identifier | Location | Role |
|---|---|---|---|
| **c1** | System Prompt | `AGENTS.md` | Core agent persona and root instructions |
| **c2** | Guardrails | `.agents/rules/*.md` | Safety gates, invariants, effort levels (`core.md`, `effort.md`) |
| **c3** | Memory | `.agents/memory/` | Persistent decisions, gotchas, anti-patterns, learned strategies |
| **c4** | Tool Guidance | `.agents/mcp_config.json` | MCP tools, contracts, and parameter routing |
| **c5** | Subagents | `.agents/plugins/agent-skills/agents/` | Delegated specialist roles running in isolated contexts |
| **c6** | Skills | `.agents/skills/` | On-demand procedural workflows and domain playbooks |
| **c7** | Scripts | `.agents/scripts/` | Deterministic CLI utilities (`analyze.py`, `harness.py`, `auto_evolve.py`) |
| **c8** | Plugins & Hooks | `.agents/hooks/` + `.agents/plugins/` | Lifecycle interceptors, pre/post tool hooks, and extensions |

---

## 4-Step Recursive Harnessing Pipeline

### 1. Census & Surface Audit
Run the harness surface inspection to check file health, character budgets, and invariants:
```bash
python3 .agents/scripts/harness.py status
python3 .agents/scripts/harness.py validate
```

### 2. Propose (Contrastive Candidate Generation)
Generate targeted edits across two complementary dimensions:
- **Invariant Edits (`INV`)**: Cross-task safety, pre-flight verification, blast-radius fences, error recovery.
- **Domain Edits (`DOM`)**: Task-specific skills, library playbooks, schema validators, custom scripts.

Generate candidate proposals:
```bash
python3 .agents/scripts/harness.py propose --task "$ARGUMENTS" --dim mixed
```

### 3. Probe (Behavioral Contrast)
Evaluate candidate harness modifications against target task trajectories without needing ground-truth feedback:
- Contrast error patterns and observation loops.
- Identify which component mutation broke failure loops or accelerated convergence.

### 4. Compose & Reflect (Harnessing-Level Recursion)
- **Compose**: Combine non-conflicting winning edits into the active `.agents/` environment.
- **Reflect & Record**: Commit lessons, adopted harness components, and anti-patterns to persistent memory:
```bash
python3 .agents/scripts/harness.py ledger summary
python3 .agents/scripts/auto_evolve.py capture --type coding_pattern --title "Harness: <Pattern>" --content "<Lesson>"
```
