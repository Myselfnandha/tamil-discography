---
description: "Pick the most token-efficient tool for searching, editing, and running commands."
---

# /tools — Tool Optimization Guide

$ARGUMENTS

## Purpose
Select the fastest native tool for the task to minimize token usage and latency.

## Tool Selection Matrix

| Goal | Best Tool | Why |
|:---|:---|:---|
| **Find code / symbols** | `grep_search` | Uses fast ripgrep AST regex; 90% fewer tokens than shell find/grep |
| **Inspect a file** | `view_file` | Reads the whole file in 1 call with zero line slicing |
| **Create a new file** | `write_to_file` | Reliable atomic creation with no shell escaping issues |
| **Edit existing code** | `replace_file_content` | Precision in-place replacement of target code block |
| **Multi-chunk edits** | `multi_replace_file_content`| Applies multiple non-contiguous edits in a single file |
| **Run tests / builds** | `run_command` | Direct shell execution with timed sync/async control |
| **Read web docs** | `read_url_content` | Converts public HTTP pages directly to clean markdown |
| **Ask clarification** | `ask_question` | Interactive Socratic modal with recommended options |

## Golden Directives
1. Never spawn background Python analyzer scripts for memory, rules, or checklists. Use native IDE tools directly.
2. Read a target file completely once, plan your change, and apply it in a single edit.
