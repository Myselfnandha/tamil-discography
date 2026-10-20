---
description: Dynamic On-Demand MCP Server Manager. List catalog servers, enable on-demand, disable, or sync to IDEs.
---

# /mcp - On-Demand MCP Server Manager

Manage and toggle the 12 verified production Model Context Protocol (MCP) servers with zero background overhead, or search the extended 2,600+ server ecosystem catalog.

---

## Quick Commands

```bash
# List all cataloged servers, grouped by tier (zero-config vs bring-your-key)
zg mcp list

# Enable server(s) on demand (prompts for API keys if needed)
zg mcp enable <name> [name2...]

# Disable server(s)
zg mcp disable <name> [name2...]

# Show currently enabled servers
zg mcp status

# Search extended 2,600+ catalog
grep -i "<service>" .agents/skills/mcp/data/mcp_catalog.json
```

---

## 12 Verified Production Servers

| Name | Category | Tier |
|:---|:---|:---|
| `context7` | Documentation | Bring-Your-Key |
| `shadcn` | Frontend | Zero-Config |
| `magic` | Frontend | Bring-Your-Key |
| `github` | VCS | Bring-Your-Key |
| `playwright` | Testing | Zero-Config |
| `supabase` | Database | Bring-Your-Key |
| `sentry` | Observability | Bring-Your-Key |
| `neon` | Database | Bring-Your-Key |
| `chrome-devtools` | Browser | Zero-Config |
| `serena` | Code Intelligence | Zero-Config |
| `docker-gateway` | Containers | Zero-Config |
| `reui` | Frontend | Zero-Config |

---

## Extended 2,600+ Server Catalog

When a task requires a specialized server outside the 12 verified core:
- Catalog dataset: [mcp_catalog.json](../skills/mcp/data/mcp_catalog.json)
- Catalog guide: [INDEX.md](../skills/mcp/data/INDEX.md)
- Search: `grep -i "<name>" .agents/skills/mcp/data/mcp_catalog.json`
- Ephemeral execution: `python .agents/scripts/mcp.py run <name> -- <task-cmd>`

---

## Agent Operating Standard
When an MCP tool is needed during a task, the agent will:
1. Scan for required tools and matching MCP servers in the 12 core servers or extended catalog.
2. Ask the user for permission to enable the required servers using `zg mcp enable <name>`.
3. If the server is in the `bring-your-key` tier, the agent will assist the user in providing the necessary configuration.
4. Execute the tool calls as needed.
