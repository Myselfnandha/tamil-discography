# 🐍 Python Ecosystem Knowledge

Categorized strategies, verified build flows, packaging rules, and gotchas for Python applications.

---

## 🏗️ Verified Build Flows & Setup Recipes
- **Modern Virtual Environment Bootstrap (PEP 668 compliant)**:
  - Command: `python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip`
  - Invariant: Never use `sudo pip install` on modern Linux distributions (Debian 12+, Ubuntu 24+, Arch).
- **Standalone Isolated Tool Provisioning**:
  - Command: Install CLI tools in isolated environments at `~/.local/share/<tool>/venv` and symlink binaries to `~/.local/bin/`.

---

## 🛡️ Known Gotchas & Anti-Patterns
- **PEP 668 Externally Managed Environment**:
  - *Gotcha*: `pip install` errors with `error: externally-managed-environment`.
  - *Strategy*: Isolate in virtual environment (`venv`) or install via `pipx`.
- **AsyncIO Unhandled Task Exceptions**:
  - *Gotcha*: Fire-and-forget background tasks silently dying without stack traces.
  - *Strategy*: Attach `task.add_done_callback()` or wrap in try/except with structured error logging.

### [FLOW-001] FastAPI Production Runner
```bash
  $ uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```
- **Notes**: Production ASGI multi-worker launch
