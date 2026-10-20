---
description: Spec before code — define what to build, PRD requirements, and architecture constraints. Invoke with /spec.
---

# /spec — Spec-Driven Development

You are now in **SPECIFICATION MODE**. Your objective is to establish an unambiguous, testable specification before writing code. Code without a spec is guessing.

## Feature / Change to Specify
$ARGUMENTS

---

## The 4-Phase Gated Workflow

### PHASE 0: CAPABILITY MAP (If multi-capability)
If the request bundles multiple capabilities, map modules, dependency directions, and build order before detailing any single spec.

### PHASE 1: REQUIREMENTS INTERROGATION
Ask clarifying questions on:
1. **Objective & Target Users**: Why build this? Who uses it?
2. **Core Capabilities & Acceptance Criteria**: What exact behaviors must succeed?
3. **Tech Stack & Seams**: What libraries, patterns, and modules are touched?
4. **Known Boundaries**: What is strictly out-of-scope?

### PHASE 2: STRUCTURED SPEC GENERATION
Draft `SPEC.md` covering:
- **Objective & Scope**: Core goal and non-goals.
- **Interface & Data Contracts**: Schemas, API signatures, and type definitions.
- **Testing Strategy**: Unit, integration, and failure modes to verify.
- **Blast Radius**: Explicit list of files created or modified.

### PHASE 3: USER VALIDATION GATE
Present the proposed specification and request approval before moving to implementation (`/build-feature` or `/plan`).
