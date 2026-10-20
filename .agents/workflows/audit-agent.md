---
description: Run an independent iFixAi safety, alignment, and functional accuracy audit on your agent, models, and tools.
---

# /audit-agent — Autonomous Agent Safety & Alignment Audit

$ARGUMENTS

---

## Purpose

iFixAi conducts structured adversarial testing and functional verification on AI agents. It evaluates whether an agent complies with its declared business rules, boundaries, and permissions, grading performance with a transparent scorecard.

---

## Usage

| Mode | Command | Action |
|---|---|---|
| **Interactive Operator** | `/ifixai` | Guides you through fixture creation, safety boundaries, and judge panel selection. |
| **Real Agent Audit** | `/ifixai --endpoint <url>` | Probes a live deployed HTTP agent endpoint with tools & retrieval enabled. |
| **Model Stand-In** | `/ifixai --provider <name>` | Tests a raw foundation model (`gemini`, `anthropic`, `openai`) against your system prompt. |
| **Quick Health Check** | `/ifixai check` | Verifies local bootstrap environment and engine dependencies. |

---

## Audit Workflow

1. **Discovery**: Identifies active system prompts, tools, and constraints in `AGENTS.md` and `.agents/rules/`.
2. **Boundary Definition**: Identifies dangerous tools (destructive shell commands, secrets access) and invariants.
3. **Fixture Generation**: Compiles an explicit YAML/JSON fixture capturing company hierarchy and test scenarios.
4. **Execution & Grading**: Runs test permutations using independent evaluator models to eliminate self-grading bias.
5. **Scorecard**: Generates an actionable markdown & HTML report displaying safety margins and failure points.
