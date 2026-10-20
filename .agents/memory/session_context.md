# 📝 Active Session Context & Contract Scratchpad (`session_context.md`)

This scratchpad is maintained by the active agent during long sessions to immunize against context loss, contract drift, and hallucinated interfaces.

> **Protocol (`gates.md §7`)**:
> 1. Update this document whenever a new interface, function signature, state variable, or API contract is established.
> 2. Re-read this scratchpad after every 10+ tool calls or before undertaking multi-file modifications.

---

## 🎯 Active Task & Scope
- **Task**: 7 Agent Failure-Mode Defenses (Hard & Soft Immunization)
- **Declared Edit Scope (Blast Radius)**:
  - `.agents/rules/gates.md` (§7–§11)
  - `.agents/rules/operating_principles.md` (§2, §3)
  - `.agents/scripts/impact_check.py` (New CLI tool)
  - `.agents/scripts/checklist.py` (Import Verification Gate)
  - `.agents/scripts/learn.py` (UTC datetime cleanups)
  - `.agents/scripts/zg` (`zg impact` command)
  - `.agents/memory/anti_patterns.json` & `gotchas.md` (AP-006–AP-009)
  - `.agents/memory/session_context.md` (Template scratchpad)
  - `tests/test_impact_check.py` (Unit test suite)

---

## 📐 Established Function Signatures & Contracts

### 1. `impact_check.py`
```python
def is_binary_file(file_path: Path) -> bool
def should_skip_path(path: Path, workspace: Path, custom_excludes: Set[str], base_excludes: Optional[Set[str]] = None) -> bool
def extract_symbols_from_file(file_path: Path) -> List[str]
def find_symbol_references(workspace: Path, symbol: str, custom_excludes: Optional[Set[str]] = None, ignore_file: Optional[Path] = None, base_excludes: Optional[Set[str]] = None) -> List[Dict[str, any]]
def analyze_file_impact(workspace: Path, file_path: Path, custom_excludes: Optional[Set[str]] = None, base_excludes: Optional[Set[str]] = None) -> Dict[str, any]
```

### 2. `checklist.py`
```python
def verify_imports(name: str, project_path_str: str) -> dict
# Returns: {"name": str, "passed": bool, "output": str, "error": str, "skipped": bool}
```

---

## 🔑 Key Variable Names & State Types
| Variable / Symbol | Type / Structure | Purpose / Context |
|:---|:---|:---|
| `DEFAULT_EXCLUDES` | `Set[str]` | Default ignore paths (`.agents`, `node_modules`, `venv`, `dist`, `__pycache__`, etc.) |
| `TEXT_EXTENSIONS` | `Set[str]` | Supported source file extensions for symbol scanning |
| `base_excludes` | `Set[str]` | Dynamically tunable exclusion set supporting `--include-agents` |
| `CORE_CHECKS` | `List[Tuple[str, str, bool]]` | Checklist items in `checklist.py` (now 9 gates) |

---

## 💡 Key Architectural Decisions & Invariants
1. **Tiered Verification**: Always verify single writes by re-reading, multi-file edits by running tests, and completion by running `checklist.py`.
2. **Deterministic Imports**: Import verification executes isolated `python3 -c` and relative JS checks to prevent hallucinated module/symbol imports.
3. **Strict Scope Confinement**: Only touch files within the declared blast radius.
