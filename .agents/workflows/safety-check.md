---
description: "Check for dangerous operations, force pushes, and leaked secrets."
---

# /safety-check — Safety Gate Protocol

$ARGUMENTS

## Purpose
Prevent data loss, broken git histories, and security leaks before major operations.

## Safety Checkpoints

### 1. Mandatory User Confirmation
Always prompt the user via `ask_question` before:
- Deleting files or project directories.
- Force pushing (`git push -f`) or rewriting git branch history.
- Dropping database tables or executing irreversible schema migrations.
- Running destructive shell commands (`rm -rf`, kill signals).

### 2. Secret Protection
- Never expose API tokens, private keys, or passwords in terminal outputs or commit logs.
- Confirm that sensitive config files (`.env`, credentials) are excluded in `.gitignore`.

### 3. Safe Fallback
- Make a git branch or commit snapshot before performing high-risk refactors.
