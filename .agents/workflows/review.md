---
description: Conduct a 5-axis code quality review (correctness, readability, architecture, security, performance). Invoke with /review.
---

# /review — 5-Axis Code Review & Health Audit

You are now in **CODE REVIEW MODE**. Your goal is to evaluate staged changes or recent commits to improve code health and catch defects before merge.

## Review Scope
$ARGUMENTS

---

## 5 Review Axes

| Axis | What to Check | Failure Trigger |
|---|---|---|
| **1. Correctness** | Does it match spec? Edge cases handled? Off-by-one errors? Adequate tests? | Bugs, missing validation, untested branches |
| **2. Readability** | Intention-revealing names? Straightforward flow? No clever tricks? | Cryptic naming, deep nesting (>3 levels), dead code |
| **3. Architecture** | Adheres to module seams? Low coupling? Right abstraction level? | Leaky abstractions, circular imports, god classes |
| **4. Security** | Inputs sanitized? Secrets protected? Auth/Authz gates enforced? | Injection vectors, plain-text credentials, unescaped output |
| **5. Performance** | No N+1 queries? Unbounded memory loops? Expensive re-renders? | Linear/quadratic scale traps, missing indexes, memory leaks |

---

## Review Output Format

Categorize all findings strictly:
- **[CRITICAL]**: Must fix before merge (broken logic, security vulnerability, data loss risk).
- **[REQUIRED]**: Defect or invariant violation that must be addressed.
- **[OPTIONAL]**: Architecture or performance improvement opportunity.
- **[NIT]**: Naming or stylistic suggestion.

Always provide exact clickable file links and line references (`[file.ext:L10-L15](file:///path/to/file#L10-L15)`).
