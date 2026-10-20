# ⚙️ General & Architecture Ecosystem Knowledge

Universal architecture invariants, git workflows, security practices, and agent execution patterns.

---

## 🏗️ Verified Build Flows & Setup Recipes
- **Clean Git Commit & Push Verification**:
  - Invariant: Never push uninspected history; verify with `git status` and run pre-flight checklist.
- **AAA Unit Testing Standard**:
  - Pattern: Arrange dependencies -> Act on method under test -> Assert invariants.

---

## 🛡️ Known Gotchas & Anti-Patterns
- **ANSI Terminal Color Bleed in Script Logs**:
  - *Gotcha*: Raw ANSI escape codes leaking into automated CI logs or markdown files.
  - *Strategy*: Strip ANSI codes with regex before logging or use plain output flags.
- **Sequential File Reading Traversal Anti-Pattern**:
  - *Gotcha*: Calling `view_file` sequentially across dozens of files to understand a workspace.
  - *Strategy*: Use `analyze.py` to auto-heal and read consolidated `codebase_summary.md`.

### [AP-001] Unchecked npx execution polluting JSON-RPC stdout with colored notices and ANSI escape sequences
- **Root Cause**: npx in modern npm writes colored notices to stdout when not silenced, breaking JSON-RPC parsing (invalid character '\x1b')
- **Prevention Strategy**: Always wrap Node-based MCP servers using mcp-npx with NO_COLOR=1, npm_config_loglevel=silent, and --silent flag
- **Invariant Rule**: NEVER run raw npx for MCP STDIO processes; always use mcp-npx wrapper.

### [AP-002] Sentry MCP server falling back to interactive OAuth device code flow and hanging
- **Root Cause**: @sentry/mcp-server defaults to interactive device code login if --access-token or SENTRY_ACCESS_TOKEN is omitted
- **Prevention Strategy**: Pass --access-token ${SENTRY_AUTH_TOKEN} explicitly in CLI arguments and provide environment fallback
- **Invariant Rule**: Always explicitly supply auth tokens via CLI flags when MCP server defaults to interactive browser/device-code login.

### [AP-003] Codebase indexer scanning self-extracting archive payload and inflating codebase database to 40MB+
- **Root Cause**: Scanning binary payloads or packed archive files in analyze.py treats binary blobs as source text
- **Prevention Strategy**: Exclude *.tar.gz, *.tar.xz, install.sh, and dist/ in codebase indexing routines
- **Invariant Rule**: Always configure self-exclusion lists in static analyzers and file crawlers for binary/build artifacts.

### [AP-004] Leaving MCP servers running permanently in background consuming CPU and RAM
- **Root Cause**: Static mcp_config.json with default background servers creates memory bloat and port collisions
- **Prevention Strategy**: Zero-Default profile: start with empty mcpServers ({}), enable dynamically on-demand, and auto-close upon task completion
- **Invariant Rule**: Default mcp_config.json must remain empty (0 active servers). Enable servers dynamically and disable immediately after turn.

### [AP-005] Agent looping over view_file sequentially to understand an entire folder codebase
- **Root Cause**: Sequential view_file calls waste context tokens and cause high latency
- **Prevention Strategy**: Execute analyze.py --check --auto-heal --inject-ki and read the consolidated codebase_summary.md in a single read
- **Invariant Rule**: NEVER call view_file recursively across multiple files in a folder; use codebase_summary.md.

### [AP-006] Refactoring code outside the user's requested scope
- **Root Cause**: Agent interprets adjacent code as needing improvement or unsolicited optimization.
- **Prevention Strategy**: Blast Radius Lock: Declare edit scope upfront; only edit within declared scope; flag out-of-scope issues as follow-up recommendations.
- **Invariant Rule**: Never touch or refactor files or functions outside the declared blast radius without explicit user authorization.

### [AP-007] Claiming success without running verification commands
- **Root Cause**: Token-pressure or speed bias leads agent to skip test runs and pattern-match 'this looks right' or use speculative language.
- **Prevention Strategy**: Evidence Gate: Always run tests or re-read files, report actual terminal output, never say 'should work'.
- **Invariant Rule**: Zero speculative claims: every declaration of success requires empirical terminal execution evidence.

### [AP-008] Editing files based on stale cached memory instead of current on-disk state
- **Root Cause**: Files read early in long sessions get modified externally or by background tasks while agent remembers old lines.
- **Prevention Strategy**: Freshness Gate: Re-read target file if >5 tool calls since last read; run git status before multi-file edits.
- **Invariant Rule**: Always re-read target files before applying diffs if >5 tool calls elapsed or external changes occurred.

### [AP-009] Using invented library functions that don't exist in installed packages
- **Root Cause**: LLM hallucination on fast-moving libraries or niche frameworks where training memory contains plausible APIs.
- **Prevention Strategy**: Hallucination Guard: Verify every unfamiliar API symbol via tool inspection, REPL check, or docs before using.
- **Invariant Rule**: Verify all library APIs and methods via tools before writing code; pass Import Verification Gate.
