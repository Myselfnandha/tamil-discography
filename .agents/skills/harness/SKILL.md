---
name: harness
description: Recursive agent self-harnessing (c1..c8) via Propose-Probe-Compose and experience ledgers.
---

# Harness²: Recursive Agent Harnessing

> Based on Google Research's *Harness²: Recursive Agent Harnessing for an Open World* (arXiv:2610.14224).

A **harness** is the complete computational and context environment around a foundation model that enables it to act as an agent: prompts, rules, memory, tools, skills, subagents, deterministic scripts, and lifecycle hooks.
**Harnessing** is the recursive process of optimizing that system to maximize task success and minimize token friction without modifying model weights.

---

## 🧭 The 8 Editable Harness Components (`c1..c8`)

| Component | Identifier | Path | Optimization Levers |
|---|---|---|---|
| **c1: System Prompt** | `system_prompt` | `AGENTS.md` | Core persona, execution principles, tool guidance seeds |
| **c2: Guardrails** | `guardrails` | `.agents/rules/` | Invariant fences, safety gates (`core.md`, `effort.md`, `codebase_context.md`) |
| **c3: Memory** | `memory` | `.agents/memory/` | Durable invariants (`decisions.md`), failure immunization (`gotchas.md`, `anti_patterns.json`) |
| **c4: Tool Guidance** | `tool_guidance` | `.agents/mcp_config.json` | MCP servers, interface contracts, parameter documentation |
| **c5: Subagents** | `subagents` | `.agents/plugins/agent-skills/agents/` | Persona specialists running in isolated sub-contexts |
| **c6: Skills** | `skills` | `.agents/skills/` | On-demand procedural workflows, domain guides, checklists |
| **c7: Scripts** | `scripts` | `.agents/scripts/` | Deterministic Python/Bash tools (`analyze.py`, `harness.py`, `learn.py`) |
| **c8: Plugins & Hooks** | `plugins_hooks` | `.agents/hooks/` + `.agents/plugins/` | Lifecycle interceptors (`validate-tool-call.mjs`, `antigravity-doctor.mjs`) |

---

## ⚡ When to Trigger Recursive Harnessing

Activate recursive harnessing when:
1. **Repeated Task Friction**: Agent hits repetitive retry loops, tool errors, or unexpected test regressions.
2. **Novel Domain Encounter**: The task requires unfamiliar frameworks, APIs, or specialized validation techniques.
3. **High Blast Radius Tasks**: Production migrations, multi-repo refactoring, or zero-tolerance compliance operations.
4. **Autonomous Run-Until-Done (`/goal`)**: When operating unattended across complex multi-step objectives.

---

## 🔄 The Propose-Probe-Compose (PPC) Protocol

```
           [ Initial Harness ]
                   │
                   ▼
       ┌──────────────────────┐
       │     1. PROPOSE       │
       │  Invariant + Domain  │
       └──────────┬───────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  Probe Candidate 1   Probe Candidate 2
  (Invariant edit)    (Domain edit)
        │                   │
        └─────────┬─────────┘
                  ▼
       ┌──────────────────────┐
       │     2. PROBE         │
       │ Behavioral Contrast  │
       │ (No Ground Truth)    │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │     3. COMPOSE       │
       │ Refined Synthesis    │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ 4. META-REFLECT &    │
       │ PERSIST TO LEDGER    │
       └──────────────────────┘
```

### Step 1: Propose (Contrastive Generation)
Separate mutations into:
- **Invariant Edits (`INV`)**: Structural enhancements that benefit all tasks (stricter pre-flight checks, atomic diff constraints, defensive logging).
- **Domain Edits (`DOM`)**: Contextual adaptations specific to the current domain (loading specialized skills, activating custom scripts).

Run:
```bash
python3 .agents/scripts/harness.py propose --task "<task_description>" --dim mixed
```

### Step 2: Probe (Behavioral Contrast)
Test candidate harness configurations against the problem. Contrast trajectories without requiring human or ground-truth feedback:
- Which candidate avoided syntax regressions?
- Which candidate produced cleaner, faster execution?
- Did any candidate trigger unexpected side-effects?

### Step 3: Compose
Synthesize the winning elements from both candidates into the active harness. Changes follow the **omitted-is-inherited** contract: only explicitly modified components change.

### Step 4: Reflect & Record (Experience Ledger)
Record the refinement cycle, adopted harness configuration, and key lessons in `.agents/memory/harness_ledger.json`:
```bash
python3 .agents/scripts/harness.py ledger summary
python3 .agents/scripts/auto_evolve.py capture --type coding_pattern --title "Harness Refinement: <Pattern>" --content "<Lesson>"
```

---

## 🛠️ CLI Reference

```bash
# Check status and health across all 8 components
python3 .agents/scripts/harness.py status

# Inspect a specific component (e.g. c2 rules or c6 skills)
python3 .agents/scripts/harness.py inspect c2

# Verify all components satisfy surface compilation & invariants
python3 .agents/scripts/harness.py validate

# Generate contrastive PPC proposals for a task
python3 .agents/scripts/harness.py propose --task "Refactor auth middleware to use OAuth2" --record

# View history of adopted harnesses and lessons in experience ledger
python3 .agents/scripts/harness.py ledger summary
python3 .agents/scripts/harness.py ledger list
```
