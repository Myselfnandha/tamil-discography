---
name: compress-tokens
description: Ultra-compressed caveman communication mode; reduces token usage ~75%.
---

# Compress Tokens (Caveman Mode & Context Compressor)

This skill activates ultra-terse, high-density technical communication to save token bandwidth and context window space. It also provides an automated memory file compressor utility.

---

## Communication Modes

| Mode | Trigger | Behavior |
|:---|:---|:---|
| **Lite** | `/caveman lite` | Removes hedging, pleasantries, and meta-commentary. Clean, direct prose. |
| **Full** | `/caveman full` (Default) | Drops filler articles, terse sentence fragments, code-first. Maximum density. |
| **Ultra** | `/caveman ultra` | Extreme compression, abbreviations, ASCII arrows (`->`), technical shorthand. |
| **Off** | `/caveman off` | Restores standard detailed communication. |

---

## Memory File Compression CLI

To compress a verbose context file (e.g. `CLAUDE.md`, `AGENTS.md`, or architecture notes):

```bash
python .agents/skills/compress-tokens/scripts/cli.py <filepath>
```

### What It Does:
1. Backs up `<filepath>` to `<filepath>.original.md`.
2. Strips fluff, redundant boilerplate, and non-actionable descriptions while preserving all code blocks, tables, and invariants.
3. Reduces token weight by ~45% without losing semantic meaning.
