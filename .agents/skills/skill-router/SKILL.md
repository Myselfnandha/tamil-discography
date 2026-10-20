---
name: skill-router
description: Dynamic router: discover and load instructions from the 1,450+ offline skills library.
---

# Skill Router (Dynamic On-Demand Skill Loader)

This skill enables Antigravity to dynamically access the offline library of **1,450+ specialized skills** located in `.agents/plugins/antigravity-awesome-skills/skills/` without consuming permanent context window tokens.

---

## When to Use

Activate this workflow whenever the user request involves:
- A specific framework or library (e.g. Next.js, Django, Flutter, Vue, Svelte, Tailwind, PyTorch, GraphQL, Prisma)
- Infrastructure or DevOps (e.g. Kubernetes, Terraform, AWS, Docker, Nginx, CI/CD)
- Database patterns (e.g. PostgreSQL, Redis, MongoDB, Supabase, ClickHouse)
- Specialized domains (e.g. Web3, game development, bioinformatics, machine learning, audio/video processing)
- Any tool or niche technology not covered by the default core workspace skills.

---

## Discovery & Execution Protocol

### Step 1: Search the Offline Library
When a specific technology or pattern is mentioned, find the matching skill using either method:

1. **Fast Index Search:**
   Use `grep_search` on `.agents/skills_index.json` (or `.agents/data/skills_index.json`) with the technology keyword:
   ```json
   {
     "Query": "\"name\": \"<keyword>\"",
     "SearchPath": "<workspace-root>/.agents/skills_index.json"
   }
   ```

2. **Direct Folder Match:**
   Use `list_dir` or check the skill folder directly in:
   `<workspace-root>/.agents/plugins/antigravity-awesome-skills/skills/`

### Step 2: Read the Skill Instructions
Once the matching skill directory is located, read its primary instruction file using `view_file`:
```
<workspace-root>/.agents/plugins/antigravity-awesome-skills/skills/<skill-name>/SKILL.md
```

### Step 3: Announce and Apply
Inform the user that the specialized skill has been dynamically loaded:

```markdown
🤖 **Dynamically loaded skill `@[<skill-name>]` from offline library...**
```

Apply the best practices, constraints, and architecture guidelines defined in the loaded `SKILL.md` to fulfill the user's task.
