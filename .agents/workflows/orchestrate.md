---
description: Coordinate multiple agents for complex tasks. Use for multi-perspective analysis, comprehensive reviews, or tasks requiring different domain expertise.
---

# Multi-Agent Orchestration

You are now in **ORCHESTRATION MODE**. Your task: coordinate specialized agents to solve this complex problem.

## Task to Orchestrate
$ARGUMENTS

---

## Orchestration Philosophy

Leverage specialized personas and subagents when a problem benefits from separate perspectives (e.g. independent review, research, or browser testing). Use direct execution when a single focused plan is faster and lower-risk.

### Persona & Tool Matrix

| Domain | Recommended Persona / Tool | Method |
|---|---|---|
| **Deep Research / Survey** | `agy-researcher` | Fast parallel survey via AGY CLI |
| **Independent Code Review** | `agy-reviewer` | Objective second-opinion code & diff audit |
| **Delegated Implementation**| `agy-implementer` | Scoped code creation & refinement |
| **Browser Testing / E2E** | `browser_subagent` | Live browser automation & visual checks |
| **Core Supercoder Feature**| `/build-feature` | 5-stage feature pipeline (Blueprint → CodeCrush → Tests) |
| **Design & UI Components** | `react-components` / `design-ui` | ReUI component blocks & curated themes |
| **Mistake Immunization** | `learn.py` / `memory` | Sweep anti-patterns & update gotchas |

---

## 2-Phase Orchestration Pipeline

### PHASE 1: BLUEPRINT & RECONNAISSANCE
1. **Reconnaissance**: Read codebase index (`.agents/codebase_summary.md` or KI).
2. **Clarification**: If trade-offs exist, use `ask_question` before executing.
3. **Task Scope**: Define exact blast radius and files to be touched.

### PHASE 2: IMPLEMENTATION & VERIFICATION
1. **Code Execution**: Apply changes using single atomic edits (`multi_replace_file_content` / `write_to_file`).
2. **Empirical Verification**: Run tests (`npm test`, `pytest`, `cargo test`) and verify checklist natively using integrated tools.
3. **Sync Memory**: Record any discovered gotchas or patterns into `.agents/memory/`.

---

## Verification & Completion

Run project test suites (`npm test`, `cargo test`, `pytest`) and inspect codebase status natively with integrated tools. Report actual terminal outputs and verified outcomes directly to the user.
