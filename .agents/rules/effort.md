---
trigger: model_decision
---

# §9 EFFORT — Model Reasoning Effort Override

Active effort level controls 5 dimensions. Default: `high`. Override anytime via `/effort-<level>`.

| Dimension | `low` | `mid` | `high` (default) | `ultra` |
|:---|:---|:---|:---|:---|
| **Reasoning** | Act immediately. Max 1 file read. | 2-5 file reads. Check KI. | Full sweep. Read all relevant KI. | Exhaustive. Read every file/doc. |
| **Verbosity** | Conclusion-only. 1-3 lines max. | Conclusion-first. 3-8 lines. | Full reasoning chain & trade-offs. | Detailed report, alternatives & risks. |
| **Planning** | Never plan. Just execute. | Plan multi-file architecture only. | Plan non-trivial edits with blast radius. | Full implementation_plan.md + walkthrough.md. |
| **Verification**| Trust edit. No test runs. | Run existing test suite. | Run tests + lint + build verification. | Full test suite + Skylos + manual checklist. |
| **Research** | Immediate context only. | Check KI + grep files. | KI + grep + read docs + web search. | Cross-reference KI, grep, docs & web. |

Override anytime: `/effort-low`, `/effort-mid`, `/effort-high`, or `/effort-ultra`. Announce once on override: `⚡ Effort: <level>`.
