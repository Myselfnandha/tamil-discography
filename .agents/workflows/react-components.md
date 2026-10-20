---
description: Search, inspect, and add 1,105+ React components, dashboard blocks, and motion icons from the ReUI shadcn registry.
---

# /react-components — React Component & Dashboard Registry

$ARGUMENTS

---

## Purpose

ReUI is a design-forward, shadcn/ui-compatible component and block registry providing 1,105+ battle-tested React components, 22 custom building blocks (Data Grid, Gantt, Kanban, Event Calendar, Cascader, Filters, etc.), full dashboard blocks, and motion icons.

---

## Usage

| Command | Action |
|---|---|
| `/reui` | Show quick reference and commands. |
| `/reui search <query>` | Search 1,105+ components and dashboard blocks (e.g., `kanban`, `data-grid`, `filters`). |
| `/reui add <component>` | Install a ReUI component or block into the current project via `npx shadcn@latest add`. |
| `/reui inspect <component>` | Inspect props, dependencies, and required packages for a component. |
| `/reui mcp on` | Enable the remote on-demand ReUI MCP server (`https://mcp.reui.io`). |
| `/reui mcp off` | Disable and auto-close the ReUI MCP connection. |
| `/reui mcp status` | Check whether ReUI MCP is active or inactive. |

---

## Core Workflow

1. **Discover**: Search the ReUI catalog using the live MCP server or CLI:
   ```bash
   zg mcp enable reui
   ```
2. **Install**: Add the component directly into your local project via the shadcn CLI:
   ```bash
   npx shadcn@latest add "https://reui.io/r/<component>"
   ```
3. **Inspect & Adapt**: Inspect the installed component or its companion example (`c-*` pattern):
   - Wire application data and state.
   - Match existing project theming (Tailwind CSS tokens).
   - **Reuse, never redesign**: Never rebuild custom primitives that ReUI already provides.
4. **Clean up**: Auto-close MCP connection when done:
   ```bash
   zg mcp disable reui
   ```

---

## Reference

- Official Skill: [SKILL.md](../skills/react-components/SKILL.md)
- Rules & Composition: [rules/components.md](../skills/react-components/rules/components.md)
- Registry & Licensing: [rules/registry.md](../skills/react-components/rules/registry.md)
