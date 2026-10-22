---
description: "Verify code changes with unit tests, linters, and build checks."
---

# /verify — Verification Gate Protocol

$ARGUMENTS

## Purpose
Ensure all changes work with real terminal proof before committing or reporting completion.

## Verification Checklist

### 1. Scope Discipline
- Declare the exact files and functions to modify.
- Never edit unrelated files or clean up orthogonal code.

### 2. Empirical Proof
- Execute real unit tests or build commands via `run_command`.
- Read actual exit codes and terminal output.
- Never rely on speculative statements ("it should work").

### 3. AAA Testing Structure
Structure unit tests with 3 clear steps:
- **Arrange**: Set up inputs, mocks, and expected outcomes.
- **Act**: Call the function or widget under test.
- **Assert**: Validate outputs, state mutations, and mock calls.

### 4. Build & Contract Health
- Run linters, type-checkers, or compilers (e.g., `flutter test`, `pytest`, `npm test`).
- Ensure all automated checks exit with code 0.
