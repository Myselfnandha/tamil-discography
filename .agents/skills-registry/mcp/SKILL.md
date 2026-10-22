---
name: mcp
description: Search, enable, or disable on-demand MCP servers from 12 verified and 2,600+ catalog.
---

# Dynamic On-Demand MCP Manager & Ecosystem Catalog

> Zero active servers at startup. Preserve RAM, CPU, and context window by enabling MCP servers only when needed.

---

## ⚡ Architecture Overview

ZeroGravity OS uses a two-tier MCP architecture:

1. **Verified Core Registry (`.agents/mcp-registry/servers.json`)**:
   - 12 pre-configured, tested production MCP servers.
   - 6 Zero-Config (instant activation) + 6 Bring-Your-Key.
   - Directly managed via `python .agents/scripts/mcp.py` or `/mcp` in chat.

2. **Extended Ecosystem Catalog (`data/mcp_catalog.json`)**:
   - 2,600+ searchable community MCP servers covering databases, cloud providers, devtools, AI frameworks, and security tools.
   - Located at [mcp_catalog.json](./data/mcp_catalog.json) with index guide at [INDEX.md](./data/INDEX.md).

---

## 🔍 Searching the Extended Catalog

When a task requires a specialized tool or protocol not present in the 12 core servers:

### 1. Keyword Search
Search the catalog dataset for the desired service or protocol:

```bash
grep -i "<service-name>" .agents/skills/mcp/data/mcp_catalog.json
```

Or extract the package name, command, and description using Python:

```bash
python3 -c "
import json
with open('.agents/skills/mcp/data/mcp_catalog.json') as f:
    cat = json.load(f)
matches = [s for s in cat if '<keyword>' in json.dumps(s).lower()]
for m in matches[:5]:
    print(f'• {m.get(\"name\")}: {m.get(\"description\")} | Command: {m.get(\"command\", m.get(\"install\", \"\"))}')
"
```

### 2. Ephemeral Execution (Auto-Shutdown)
Run a catalog server ephemerally without permanently adding it to configuration:

```bash
python .agents/scripts/mcp.py run <server-name> -- <task-command>
```

---

## 🛠️ Managing Verified Core Servers

### Chat Commands
- `/mcp list`: View verified servers and active status.
- `/mcp enable <name>`: Enable one or more servers on-demand.
- `/mcp disable <name>`: Disable servers and free resources.
- `/mcp status`: Show currently active servers in `.agents/mcp_config.json`.
- `/mcp reset`: Deactivate all servers (return to zero-default clean slate).

### CLI Equivalent
```bash
zg mcp list
zg mcp enable playwright
zg mcp disable playwright
zg mcp reset
```

---

## 📋 Verified Server Matrix (`servers.json`)

| Server | Category | Tier | Description |
|:---|:---|:---|:---|
| `playwright` | Testing | Zero-Config | Browser automation & visual snapshots |
| `chrome-devtools` | Browser | Zero-Config | Chrome DOM inspection & Lighthouse audits |
| `serena` | Code Intel | Zero-Config | AST navigation & semantic refactoring |
| `docker-gateway` | Containers | Zero-Config | Docker container lifecycle & sandboxing |
| `shadcn` | Frontend | Zero-Config | Shadcn UI registry component discovery |
| `reui` | Frontend | Zero-Config | ReUI 1,105+ React components & blocks |
| `context7` | Documentation | Bring-Your-Key | Real-time library documentation resolver |
| `magic` | Frontend | Bring-Your-Key | 21st.dev Magic UI design inspiration |
| `github` | VCS | Bring-Your-Key | Issues, PRs & repo automation |
| `supabase` | Database | Bring-Your-Key | Database migrations & SQL execution |
| `neon` | Database | Bring-Your-Key | Serverless Postgres branching & queries |
| `sentry` | Observability | Bring-Your-Key | Error telemetry & crash diagnostics |
