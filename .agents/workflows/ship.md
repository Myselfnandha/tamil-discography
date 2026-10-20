---
description: Multi-specialist pre-launch verification fan-out and Go/No-Go decision. Invoke with /ship.
---

# /ship — Production Shipping & Pre-Launch Verification

You are now in **SHIPPING ORCHESTRATION MODE**. Faster is safer. Run the multi-specialist verification pass before deploying to production.

## Release Target
$ARGUMENTS

---

## 3-Phase Shipping Protocol

### PHASE A: MULTI-SPECIALIST FAN-OUT
Evaluate the candidate release across three concurrent axes:
1. **Quality & Regressions**: Verify test suite execution, linters, and type checking (`npm test`, `pytest`, `cargo test`).
2. **Security & Vulnerabilities**: Check dependencies for known CVEs, ensure zero leaked secrets or debug keys in build output.
3. **Infrastructure & Environment**: Verify environment variables, database migrations, rollback scripts, and feature flags.

### PHASE B: MERGE & IMPACT ANALYSIS
Synthesize findings into a single risk profile:
- **Blockers**: Critical test failures, broken migrations, or security flaws.
- **Rollback Readiness**: Explicit trigger conditions and step-by-step recovery procedure.

### PHASE C: DECISION
Output the final scorecard:
```markdown
## Ship Decision: [GO | NO-GO]

### Blockers (Must fix before deployment)
- [None | Item + line reference]

### Rollback Plan
- **Trigger Conditions**: [What telemetry metric or error rate triggers rollback]
- **Procedure**: [Git revert command or deployment command]
- **Target RTO**: [< 5 minutes]
```

### PHASE D: AUTO-LEARN & POST-LAUNCH GRILL-ME
- **Auto-run `/learn`**: Distill deployment/release learnings, migration quirks, and gotchas into `.agents/memory/` (`decisions.md`, `gotchas.md`).
- **Quick `/grill-me`**: Conclude with an `ask_question` prompt to confirm follow-up deployment tasks, telemetry monitoring, or canary rollout milestones.

