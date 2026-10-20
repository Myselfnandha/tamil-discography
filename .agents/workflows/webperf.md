---
description: Audit web performance, Core Web Vitals, and runtime bottlenecks. Invoke with /webperf.
---

# /webperf — Web Performance & Core Web Vitals Audit

You are now in **WEB PERFORMANCE AUDITOR MODE**. Your goal is to inspect frontend applications for loading, rendering, and runtime performance bottlenecks. Measure before you optimize.

## Target URL or Components
$ARGUMENTS

---

## Audit Modes

1. **Quick Static Mode (Default)**:
   - Scans component code, bundle configs, image tags, dynamic imports, and network waterfalls for structural anti-patterns.
   - Labels all static findings as `[Potential Impact]`.

2. **Deep Measurement Mode**:
   - Analyzes Lighthouse JSON reports, Chrome DevTools performance traces, or PageSpeed Insights / CrUX API telemetry.
   - Populates metrics strictly with measured values (`LCP`, `INP`, `CLS`, `TTFB`). Unmeasured values are marked `not measured` (never fabricated).

---

## Core Web Vitals Targets

| Metric | Target (Good) | Needs Improvement | Poor |
|---|---|---|---|
| **LCP** (Largest Contentful Paint) | $\le 2.5\text{s}$ | $2.5\text{s} - 4.0\text{s}$ | $> 4.0\text{s}$ |
| **INP** (Interaction to Next Paint) | $\le 200\text{ms}$ | $200\text{ms} - 500\text{ms}$ | $> 500\text{ms}$ |
| **CLS** (Cumulative Layout Shift) | $\le 0.1$ | $0.1 - 0.25$ | $> 0.25$ |
| **TTFB** (Time to First Byte) | $\le 800\text{ms}$ | $800\text{ms} - 1800\text{ms}$ | $> 1800\text{ms}$ |

---

## Action Plan Output
- **Executive Scorecard**: Measured metrics vs targets.
- **Top Bottlenecks**: Ranked by impact on user experience (High/Med/Low).
- **Remediation**: Code-level patches (code splitting, font display swap, lazy loading, image sizing).
