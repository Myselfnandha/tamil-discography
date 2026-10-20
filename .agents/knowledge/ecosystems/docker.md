# 🐳 Docker & Containerization Ecosystem Knowledge

Categorized container recipes, multi-stage build patterns, and orchestration gotchas.

---

## 🏗️ Verified Build Flows & Setup Recipes
- **Minimal Rootless Node/Python Production Build**:
  - Pattern: Multi-stage Dockerfile separating build dependencies from runtime slim image.
  - Invariant: Always declare non-root user (`USER node` or `USER nonroot`) before `CMD`.

---

## 🛡️ Known Gotchas & Anti-Patterns
- **Dangling Build Cache Bloat**:
  - *Gotcha*: Docker build context consuming gigabytes due to missing `.dockerignore`.
  - *Strategy*: Always provide `.dockerignore` excluding `.git`, `node_modules`, `venv`, and build artifacts.
