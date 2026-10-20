---
description: Branching gateway to search, explore, and activate specialized skills by category or name.
---

# /skill — Antigravity Skill Gateway

$ARGUMENTS

---

## Purpose
The `/skill` command provides an organized, branching gateway to Antigravity's library of 1,500+ specialized skills without cluttering the root `/` slash autocomplete menu.

---

## Usage

| Command | Action |
| :--- | :--- |
| `/skill` | Open interactive branching menu to browse skills by category. |
| `/skill <name>` | Immediately load and activate the specified skill (e.g., `/skill clean-code`). |
| `/skill list <category>` | List all available skills within a category. |

---

## Category Hierarchy

```text
/skill
├── 🎨 Frontend & UI
│   ├── frontend-design (Modern UI/UX principles, design systems, micro-interactions)
│   ├── react-nextjs-development (Next.js 14+ App Router, RSC, Tailwind)
│   └── mobile-design (Touch-first mobile design patterns)
├── ⚡ Backend & APIs
│   ├── fastapi-pro (High-performance async APIs, SQLAlchemy 2.0, Pydantic V2)
│   ├── clean-code (Robert C. Martin Clean Code engineering standards)
│   ├── database-design (Schema design, migrations, indexing, optimization)
│   └── typescript-expert (Advanced type-level programming, monorepos)
├── 🔒 Security & Audit
│   ├── security-auditor (DevSecOps, threat modeling, vulnerability audits)
│   └── vulnerability-scanner (SAST/DAST, dependency audits)
├── 🧪 Testing & Debugging
│   ├── test-driven-development (Red-Green-Refactor, test-first cycle)
│   ├── testing-patterns (Jest/Pytest patterns, factories, mocks)
│   └── debugging-strategies (Systematic root-cause diagnosis)
└── 🛠️ DevOps & Tools
    ├── git-advanced-workflows (Rebase, bisect, worktrees, conflict resolution)
    └── github-actions-templates (Production CI/CD pipelines)
```

---

## Execution Instructions for Agent

When the user invokes `/skill`:
1. **If an argument `<name>` is provided** (e.g. `/skill clean-code`):
   - Search `.agents/skills_index.json` or `.agents/plugins/` for `<name>`.
   - Read the corresponding `SKILL.md` file using `view_file`.
   - Announce activation: `🤖 Loaded and activated skill: @[<name>]` and apply its guidelines to the conversation.

2. **If NO argument is provided** (just `/skill`):
   - You must act as the **Unified Workflow Selector**.
   - Use the `ask_question` tool to present a branching menu. First, offer these categories:
     - 🏗️ Architecture & Design
     - ✨ Create & Enhance
     - 🐛 Debug & Triage
     - 🧪 Test & Deploy
     - 🧠 Planning & Management
     - 🎓 Meta & Education
   - After the user selects a category, use `list_dir` or `skills_index.json` to find the local skills in `.agents/skills/` that fit the category, and use `ask_question` again to let the user pick the specific workflow.
   - Once selected, use `view_file` to read its `SKILL.md` and announce activation: `🤖 Loaded workflow: @[<name>]`.
