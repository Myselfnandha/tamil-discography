---
description: "Interview and grill user interactively to resolve design decisions before building."
---

# /grill-me — Interactive Design & Build Interview

Progressively interview the user to unpack requirements, explore trade-offs, and lock in architecture before writing any code. Unifies intent extraction, idea refinement, specification, and constraint definition.

## Invoked Skills (On-Demand)
- **`interview-me`**: Progressive, one-at-a-time intent extraction with attached hypotheses and confidence scoring.
- **`idea-refine`**: Explore design branches, evaluate trade-offs, and clarify edge cases.
- **`spec-driven-development`**: Convert agreed design decisions into concrete contracts and acceptance criteria.
- **`constraint-driven-development`**: Bind limits (tech stack, performance, scope boundaries, out-of-scope non-goals).
- **`planning-and-task-breakdown`**: Sequence atomic implementation phases for `/build-feature` or `/create`.

## Execution Protocol

1. **Codebase Exploration First**:
   - If a question can be answered by searching the codebase or existing docs, inspect it first. Do not ask what can be discovered.

2. **One-at-a-Time Socratic Questions (`ask_question`)**:
   - Formulate one targeted question at a time using the `ask_question` tool.
   - Attach your hypothesis (`GUESS: ...`) with clear rationale.
   - Present concrete selectable choices plus user write-in.

3. **Listen for "Want" vs. "Convention"**:
   - Probe buzzwords ("scalable", "modern", "clean architecture") to find real operational requirements.
   - Establish explicit "Out of scope" boundaries.

4. **Confirm Statement of Intent**:
   - Summarize confirmed decisions: Outcome, Target User, Success Criteria, Constraints, and Out of Scope.
   - Require explicit user confirmation before proceeding.

5. **Handoff to Build**:
   - Hand off directly to `/build-feature`, `/create`, or `/plan`.
