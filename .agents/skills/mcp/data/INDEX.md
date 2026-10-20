# Antigravity MCP Server Registry & Catalog

A curated index of production Model Context Protocol (MCP) servers integrated into ZeroGravity OS, backed by a searchable catalog of **2,600+ community MCP servers**.

---

## 1. Verified Core MCP Servers (`servers.json`)

Ready for zero-default, on-demand activation via `python .agents/scripts/mcp.py enable <name>`:

| Server Name | Recipe Guide | Runner Command | Required Credentials / Env | Category |
|:---|:---|:---|:---|:---|
| **github** | [github.md](./recipes/github.md) | `npx -y @modelcontextprotocol/server-github` | `${GITHUB_TOKEN}` | Git & DevOps |
| **playwright** | [playwright.md](./recipes/playwright.md) | `npx -y @playwright/mcp@latest` | — | Browser Automation & E2E |
| **supabase** | [supabase.md](./recipes/supabase.md) | `npx -y @supabase/mcp-server` | `${SUPABASE_ACCESS_TOKEN}`, `${SUPABASE_PROJECT_REF}` | Database & Backend |
| **sentry** | [sentry.md](./recipes/sentry.md) | `uvx sentry-mcp` | `${SENTRY_AUTH_TOKEN}`, `${SENTRY_ORG}` | Observability & Telemetry |
| **context7** | [context7.md](./recipes/context7.md) | `npx -y @upstash/context7-mcp` | `${UPSTASH_CONTEXT7_API_KEY}` | Vector Docs & Memory |
| **neon** | [neon.md](./recipes/neon.md) | `npx -y @neondatabase/mcp-server-neon` | `${NEON_API_KEY}` | Serverless Postgres |
| **chrome-devtools** | [chrome-devtools.md](./recipes/chrome-devtools.md) | `npx -y @chrome-devtools-mcp/server` | — | Performance & Web Debugging |
| **serena** | [serena.md](./recipes/serena.md) | `uvx serena-mcp` | — | Semantic Code Intelligence |
| **docker-gateway** | [docker-gateway.md](./recipes/docker-gateway.md) | `npx -y @docker/mcp-server` | Running Docker daemon | Containers & Infrastructure |
| **shadcn** | Core Tool | `npx shadcn@latest mcp` | — | Component Registry |
| **magic** | Core Tool | `npx -y @21st-dev/magic@latest` | `MAGIC_API_KEY` | UI Design & Magic Components |
| **ponytail** | Core Tool | `node ${AGENT_DIR}/plugins/ponytail/ponytail-mcp/index.js` | — | Lazy Senior Dev Mode |
| **reui** | Core Tool | `https://mcp.reui.io` | — | 1,105+ React Component Blocks |

---

## 2. Dynamic 2,600+ MCP Server Catalog (`mcp_catalog.json`)

The entire ecosystem catalog is indexed in `.agents/mcp-registry/mcp_catalog.json` with:
- **Server Name & GitHub/GitLab URL**
- **Category** (e.g. Database, Cloud, Developer Tools, AI, Security, Productivity)
- **Runtime Language** (Python, TypeScript, Go, Rust, C#, Java, etc.)
- **Install & Launch Command** (`npx`, `uvx`, `docker`, or custom CLI)

### Finding & Enabling an MCP from the Catalog

When an agent needs any tool or integration not currently in `servers.json`:
1. **Search the Catalog**:
   ```bash
   grep -i "<keyword>" .agents/mcp-registry/mcp_catalog.json
   ```
2. **Setup and Run on Demand**:
   The model can immediately extract the `install` command and configure it dynamically in `.agents/mcp_config.json` or run it ephemerally:
   ```bash
   python .agents/scripts/mcp.py run <server-name> -- <task-command>
   ```

---

## 3. How to Activate or Pass Credentials

When running commands that require authenticated MCP servers, provide tokens in your environment:

```bash
export GITHUB_TOKEN="ghp_..."
export SUPABASE_ACCESS_TOKEN="sbp_..."
export SUPABASE_PROJECT_REF="abcdef..."
export SENTRY_AUTH_TOKEN="sntrys_..."
export SENTRY_ORG="my-org"
export NEON_API_KEY="neon_..."
export UPSTASH_CONTEXT7_API_KEY="ctx7_..."
```
