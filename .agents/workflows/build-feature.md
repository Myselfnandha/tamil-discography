---
description: Autonomous 5-stage feature building pipeline: Memory Sweep → Blueprint → CodeCrush → AAA Test → Sync. Invoke with /build-feature.
---

# Autonomous 5-Stage Feature Pipeline

The Feature Pipeline provides an end-to-end framework for autonomous, high-velocity, high-reliability software engineering.

---

## Operating Protocol: The 5 Stages

### 1. Memory & Context Sweep
Before modifying or creating files:
1. Read `.agents/memory/decisions.md` to honor past architectural commitments and invariants.
2. Read `.agents/memory/gotchas.md` to avoid known platform bugs, tricky edge cases, and circular dependencies.
3. Check the active goal state in `.agents/memory/goals.md`.
4. **Pre-Execution Tool Optimization**: Select integrated tools (`grep_search`, whole-file `view_file`, `multi_replace_file_content`, tuned `run_command`). Never spawn internal Python scripts.

### 2. Architecture & Seam Design
- Design interface boundaries before writing implementation logic.
- Ensure modules hide internal complexity behind clean, minimal public interfaces.
- Identify and isolate external dependencies (I/O, database, network) behind testable seams.

### 3. CodeCrushing Implementation
- Write clean, idiomatically typed code across any target stack (TypeScript, Python, Rust, Go, Dart/Flutter, SQL).
- Avoid premature abstractions while strictly adhering to DRY where repetition causes maintenance debt.
- Handle error edge cases explicitly with typed errors or result types.

### 4. AAA Testing & Verification Gate
- Every business logic module requires tests structured as:
  - **Arrange**: Set up mocks, inputs, and state.
  - **Act**: Execute the unit under test.
  - **Assert**: Verify outputs, state mutations, and mock invocations.
- Run project test suites and linters to verify behavior and type safety.

### 5. Memory Tree Synchronization & Auto-Learn / Quick Grill-Me
- **Auto-run `/learn`**: Record durable learnings and invariants directly into `.agents/memory/` using integrated tools:
  - New invariants $\rightarrow$ `decisions.md` (via `replace_file_content`)
  - Fixed quirks/workarounds $\rightarrow$ `gotchas.md` and `anti_patterns.json` (via `replace_file_content`)
  - Completed milestones $\rightarrow$ `goals.md` (via `replace_file_content`)
  - Captured strategies $\rightarrow$ append directly to `learned_strategies.json` (via `replace_file_content`, no Python subprocesses)
- **Quick Grill-Me**: Conclude the execution with a quick `/grill-me` via `ask_question` (1-2 targeted Socratic questions) to verify alignment, confirm architectural choices, and lock in user conventions.

---

## Slash Command Usage

| Command | Action |
|:---|:---|
| `/build-feature <task>` | Execute full 5-stage engineering pipeline for the requested task. |
| `/build-feature architect <feature>` | Produce architectural blueprint and interface definitions only. |
| `/build-feature code <plan>` | High-velocity implementation of an existing plan. |
| `/build-feature test <target>` | Generate AAA test suite and run verification gates. |
| `/build-feature sync-memory` | Sweep codebase and synchronize active state into `.agents/memory/`. |
