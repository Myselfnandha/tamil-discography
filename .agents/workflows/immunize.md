---
description: "Check known anti-patterns and record lessons learned from bugs."
---

# /immunize — Mistake Immunization & Memory Protocol

$ARGUMENTS

## Purpose
Prevent recurring mistakes by checking known anti-patterns before coding, and recording new invariants when bugs are resolved.

## Operating Protocol

### 1. Pre-Action Check (Sweep Before Coding)
Before taking unfamiliar architectural actions:
1. Inspect `.agents/memory/anti_patterns.json` for known traps.
2. Inspect `.agents/memory/gotchas.md` for platform and tool quirks.
3. Inspect `.agents/memory/decisions.md` to uphold past architectural commitments.

### 2. Post-Fix Learning (Auto-Distillation)
When a bug, test failure, or correction occurs:
1. **Identify Root Cause**: Determine exactly why the error occurred.
2. **Formulate Invariant**: Write a single clear rule to prevent the issue.
3. **Persist Directly**:
   - Traps -> append to `anti_patterns.json`
   - Platform gotchas -> append to `gotchas.md`
   - Architecture decisions -> append to `decisions.md`
4. Use native `replace_file_content` to write directly. Zero subprocess scripts.
