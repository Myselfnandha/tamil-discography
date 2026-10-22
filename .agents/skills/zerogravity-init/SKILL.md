---
name: zerogravity-init
description: "Initialize ZeroGravity: create the single-page walkthrough artifact and display the stacked command matrix."
---

# ZeroGravity OS — Initialization & Walkthrough Protocol

When the user says `init`, runs `/init`, or starts a new session:

## 1. Create the Walkthrough Artifact
Always use `write_to_file` to create the persistent single-page walkthrough artifact at:
`<appDataDir>/brain/<conversation-id>/zerogravity_walkthrough.md`

Artifact Content includes:
- Overview of ZeroGravity OS (Zero-Default on-demand architecture: 0 background rules, 541 baseline prompt tokens).
- The complete stacked matrix mapping all 39 slash commands and 52 individual skills.
- The 12 on-demand MCP servers and offline catalog instructions.

## 2. Output the Stacked Matrix in Chat
Render the unified 6-row zero-scroll table directly in the conversation:

| Domain | Stacked Slash Commands | Matching Individual Skills (On-Demand) | Purpose & Quick Runbook |
|:---|:---|:---|:---|
| **🏗️ Define & Spec** | **`/build-feature`** · **`/grill-me`**<br>`/create` · `/enhance`<br>`/spec` · `/plan` · `/goal` | `interview-me` · `idea-refine`<br>`spec-driven-development`<br>`planning-and-task-breakdown`<br>`constraint-driven-development` | • **Grill & Socratic**: Socratic design interview (`/grill-me`) & intent extraction<br>• **Ideation & Spec**: Refine ideas & establish quality bar/contracts<br>• **Execution**: 5-stage autonomous pipeline or iterative app builder |
| **📐 Architecture** | `/codebase-design`<br>`/domain-model`<br>`/brainstorm` · `/orchestrate` | `api-and-interface-design`<br>`context-engineering`<br>`documentation-and-adrs`<br>`doubt-driven-development` | • **Interfaces**: Deep module design & clean testable seams<br>• **Models**: Business entities, database schemas, & ADRs<br>• **Review**: Adversarial cross-examination of high-stakes architecture |
| **🧪 Verify & Quality**| **`/verify`** · **`/test`**<br>`/review` · `/safety-check`<br>`/audit-agent` | `verification-gate` · `test-driven-development`<br>`code-review-and-quality`<br>`safety-gates` · `security-and-hardening`<br>`browser-testing-with-devtools` | • **Testing**: TDD cycle + AAA unit test proof with terminal output<br>• **Review**: 5-axis code quality audit & OWASP security hardening<br>• **Guards**: Block destructive drops, force-pushes, & secret leaks |
| **🔍 Debug & Optimize**| **`/debug`** · **`/tools`**<br>`/immunize` · `/harness`<br>`/yagni-simplify` · `/webperf` | `debugging-and-error-recovery`<br>`tool-optimization` · `mistake-immunization`<br>`code-simplification` · `performance-optimization`<br>`harness` · `coding-interview` | • **Fix**: Systematic root-cause bug isolation & fastest tool choice<br>• **Memory**: Check `anti_patterns.json` traps & auto-tune agent harness<br>• **Speed & YAGNI**: Cut over-engineering with stdlib & boost Core Web Vitals |
| **🌐 Search & UI** | **`/reach`** · **`/agent-reach`**<br>`/mcp` · `/skill`<br>`/react-components` · `/design-ui` | `agent-reach` · `mcp`<br>`frontend-ui-engineering`<br>`react-components` · `skill-router`<br>`using-agent-skills` · `source-driven-development` | • **Live Search**: Research Twitter, Reddit, YouTube, GitHub, & Web<br>• **UI Engineering**: 1,105+ React/shadcn components & modern dark/light UI<br>• **Ecosystem**: 2,600+ on-demand MCP servers & 1,500+ offline skills |
| **⚡ Flow & Release** | `/effort-low` · `mid` · `high` · `ultra`<br>`/compress-tokens` · `/humanize-text`<br>`/focus` · `/learn`<br>`/ship` · `/deploy` · `/schedule` | `compress-tokens` · `humanize-text`<br>`git-workflow-and-versioning`<br>`ci-cd-and-automation` · `shipping-and-launch`<br>`deprecation-and-migration`<br>`agy-*` (7 subagents) · `ponytail-*` (6 YAGNI) | • **Reasoning Depth**: Instant effort toggles (`low` fast to `ultra` deep)<br>• **Prose Style**: 75% token reduction or natural human writing<br>• **Subagents**: Delegate to Antigravity CLI (`agy-*`) & Senior YAGNI (`ponytail-*`)<br>• **Launch**: Pre-flight Go/No-Go sign-off, CI/CD, & production deployment |

💡 *Zero-Default Architecture: 0 background rules. Everything runs strictly on demand.*
