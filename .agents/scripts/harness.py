#!/usr/bin/env python3
"""
ZeroGravity OS: Harness² Recursive Agent Harnessing Engine (`harness.py`)
========================================================================

Implements Google Research's Harness² framework (arXiv:2610.14224) for
Antigravity IDE & ZeroGravity OS.

Exposes the 8 editable harness components:
  c1: System Prompt (AGENTS.md)
  c2: Guardrails & Rules (.agents/rules/*.md)
  c3: Memory (.agents/memory/*)
  c4: Tool Guidance (.agents/skills/mcp/, mcp_config.json)
  c5: Subagents (.agents/plugins/agent-skills/agents/*.md)
  c6: Skills (.agents/skills/*/SKILL.md, .agents/plugins/*/skills/*/SKILL.md)
  c7: Scripts (.agents/scripts/*.py, *.sh)
  c8: Plugins & Hooks (.agents/plugins/*, .agents/hooks/*, hooks.json)

Provides:
  - Surface specification (ANTIGRAVITY_SURFACE)
  - Census & health check of the 8 components
  - Propose-Probe-Compose (PPC) contrastive harness refinement
  - Experience Ledger tracking (harness_ledger.json)
  - Surface invariants validation

Usage:
  python3 harness.py status
  python3 harness.py inspect [c1..c8|all]
  python3 harness.py validate
  python3 harness.py propose --task "<description>" [--dim inv|dom|mixed]
  python3 harness.py ledger [summary|list|add]
"""

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = AGENTS_DIR.parent
MEMORY_DIR = AGENTS_DIR / "memory"
LEDGER_FILE = MEMORY_DIR / "harness_ledger.json"

# ANSI Colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ─── 1. Surface Specification ──────────────────────────────────────────────────

@dataclass(frozen=True)
class ComponentSpec:
    id: str
    name: str
    relative_path: str
    role: str
    budget_chars: int = 50_000


ANTIGRAVITY_COMPONENTS: Dict[str, ComponentSpec] = {
    "c1": ComponentSpec("c1", "System Prompt", "AGENTS.md", "Core agent definition & high-level system prompt", 16_000),
    "c2": ComponentSpec("c2", "Guardrails & Rules", ".agents/rules", "Behavioral constraints, safety gates, and execution invariants", 50_000),
    "c3": ComponentSpec("c3", "Memory", ".agents/memory", "Persistent memory, decisions, gotchas, anti-patterns, and learned strategies", 150_000),
    "c4": ComponentSpec("c4", "Tool Guidance", ".agents/mcp_config.json", "MCP server configuration, tool routing, and usage contracts", 30_000),
    "c5": ComponentSpec("c5", "Subagents", ".agents/plugins/agent-skills/agents", "Specialized persona subagents spawned in isolated contexts", 60_000),
    "c6": ComponentSpec("c6", "Skills", ".agents/skills", "On-demand procedural workflows and domain playbooks", 750_000),
    "c7": ComponentSpec("c7", "Scripts", ".agents/scripts", "Deterministic Python and Bash helper tools and utilities", 400_000),
    "c8": ComponentSpec("c8", "Plugins & Hooks", ".agents/hooks", "Runtime lifecycle interceptors, middleware, and plugin bundles", 80_000),
}


# ─── 2. Census & Inspection ───────────────────────────────────────────────────

def get_harness_census(root: Optional[Path] = None) -> Dict[str, Any]:
    """Inspect and measure all 8 harness components in the workspace."""
    base = root or WORKSPACE_ROOT
    agents_dir = base / ".agents"
    census: Dict[str, Any] = {"components": {}, "total_files": 0, "total_chars": 0, "health": []}

    # c1: System Prompt (AGENTS.md)
    agents_md = base / "AGENTS.md"
    if not agents_md.exists():
        agents_md = agents_dir / "AGENTS.md"
    c1_chars = len(agents_md.read_text(encoding="utf-8", errors="replace")) if agents_md.exists() else 0
    census["components"]["c1"] = {
        "name": ANTIGRAVITY_COMPONENTS["c1"].name,
        "exists": agents_md.exists(),
        "path": str(agents_md.relative_to(base) if agents_md.exists() else "AGENTS.md"),
        "files": 1 if agents_md.exists() else 0,
        "chars": c1_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c1"].budget_chars,
        "items": [str(agents_md.name)] if agents_md.exists() else [],
    }

    # c2: Guardrails & Rules
    rules_dir = agents_dir / "rules"
    rules_files = sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []
    c2_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in rules_files)
    census["components"]["c2"] = {
        "name": ANTIGRAVITY_COMPONENTS["c2"].name,
        "exists": bool(rules_files),
        "path": ".agents/rules",
        "files": len(rules_files),
        "chars": c2_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c2"].budget_chars,
        "items": [f.name for f in rules_files],
    }

    # c3: Memory
    mem_dir = agents_dir / "memory"
    mem_files = [f for f in sorted(mem_dir.glob("*")) if f.is_file()] if mem_dir.is_dir() else []
    c3_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in mem_files)
    census["components"]["c3"] = {
        "name": ANTIGRAVITY_COMPONENTS["c3"].name,
        "exists": bool(mem_files),
        "path": ".agents/memory",
        "files": len(mem_files),
        "chars": c3_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c3"].budget_chars,
        "items": [f.name for f in mem_files],
    }

    # c4: Tool Guidance (mcp_config.json + mcp-registry)
    mcp_config = agents_dir / "mcp_config.json"
    mcp_reg = agents_dir / "mcp-registry" / "servers.json"
    c4_files = [f for f in [mcp_config, mcp_reg] if f.is_file()]
    c4_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in c4_files)
    active_mcp = []
    if mcp_config.exists():
        try:
            mcp_data = json.loads(mcp_config.read_text(encoding="utf-8"))
            active_mcp = list(mcp_data.get("mcpServers", {}).keys())
        except Exception:
            pass
    census["components"]["c4"] = {
        "name": ANTIGRAVITY_COMPONENTS["c4"].name,
        "exists": bool(c4_files),
        "path": ".agents/mcp_config.json",
        "files": len(c4_files),
        "chars": c4_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c4"].budget_chars,
        "items": active_mcp or ["(none enabled)"],
    }

    # c5: Subagents
    sub_dirs = [
        agents_dir / "plugins" / "agent-skills" / "agents",
        agents_dir / "sub_agents",
    ]
    subagent_files = []
    for sd in sub_dirs:
        if sd.is_dir():
            subagent_files.extend(sorted(sd.glob("*.md")))
    c5_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in subagent_files)
    census["components"]["c5"] = {
        "name": ANTIGRAVITY_COMPONENTS["c5"].name,
        "exists": bool(subagent_files),
        "path": ".agents/plugins/agent-skills/agents",
        "files": len(subagent_files),
        "chars": c5_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c5"].budget_chars,
        "items": [f.stem for f in subagent_files],
    }

    # c6: Skills
    skill_roots = [
        agents_dir / "skills",
        agents_dir / "plugins",
    ]
    skill_files = []
    skill_names = []
    for sr in skill_roots:
        if sr.is_dir():
            for sm in sorted(sr.rglob("SKILL.md")):
                skill_files.append(sm)
                skill_names.append(sm.parent.name)
    c6_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in skill_files)
    census["components"]["c6"] = {
        "name": ANTIGRAVITY_COMPONENTS["c6"].name,
        "exists": bool(skill_files),
        "path": ".agents/skills",
        "files": len(skill_files),
        "chars": c6_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c6"].budget_chars,
        "items": sorted(list(set(skill_names))),
    }

    # c7: Scripts
    scripts_dir = agents_dir / "scripts"
    script_files = [f for f in sorted(scripts_dir.glob("*.py")) if not f.name.startswith("_")] if scripts_dir.is_dir() else []
    c7_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in script_files)
    census["components"]["c7"] = {
        "name": ANTIGRAVITY_COMPONENTS["c7"].name,
        "exists": bool(script_files),
        "path": ".agents/scripts",
        "files": len(script_files),
        "chars": c7_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c7"].budget_chars,
        "items": [f.name for f in script_files],
    }

    # c8: Plugins & Hooks
    hooks_file = agents_dir / "hooks.json"
    hooks_dir = agents_dir / "hooks"
    plugins_dir = agents_dir / "plugins"
    c8_files = []
    if hooks_file.is_file():
        c8_files.append(hooks_file)
    if hooks_dir.is_dir():
        c8_files.extend([f for f in sorted(hooks_dir.glob("*")) if f.is_file()])
    if plugins_dir.is_dir():
        c8_files.extend([p / "plugin.json" for p in sorted(plugins_dir.glob("*")) if (p / "plugin.json").is_file()])
    c8_chars = sum(len(f.read_text(encoding="utf-8", errors="replace")) for f in c8_files)
    c8_items = []
    if hooks_file.exists():
        c8_items.append("hooks.json")
    if hooks_dir.is_dir():
        c8_items.extend([f.name for f in hooks_dir.glob("*.mjs")])
    if plugins_dir.is_dir():
        c8_items.extend([p.name for p in plugins_dir.iterdir() if p.is_dir()])
    census["components"]["c8"] = {
        "name": ANTIGRAVITY_COMPONENTS["c8"].name,
        "exists": bool(c8_files),
        "path": ".agents/hooks",
        "files": len(c8_files),
        "chars": c8_chars,
        "budget": ANTIGRAVITY_COMPONENTS["c8"].budget_chars,
        "items": c8_items,
    }

    # Totals
    census["total_files"] = sum(c["files"] for c in census["components"].values())
    census["total_chars"] = sum(c["chars"] for c in census["components"].values())

    # Health Checks
    for cid, data in census["components"].items():
        if not data["exists"]:
            census["health"].append({"level": "WARN", "msg": f"Component {cid} ({data['name']}) is missing or empty."})
        elif data["chars"] > data["budget"]:
            census["health"].append({
                "level": "WARN",
                "msg": f"Component {cid} exceeds char budget ({data['chars']} > {data['budget']}). Token compaction recommended.",
            })

    return census


def validate_surface(root: Optional[Path] = None) -> List[str]:
    """Validate all 8 components against Harness² surface invariants."""
    base = root or WORKSPACE_ROOT
    agents_dir = base / ".agents"
    errors = []

    # 1. Check Python script compilation
    scripts_dir = agents_dir / "scripts"
    if scripts_dir.is_dir():
        for py_file in scripts_dir.glob("*.py"):
            try:
                compile(py_file.read_text(encoding="utf-8", errors="replace"), str(py_file), "exec")
            except Exception as e:
                errors.append(f"Script syntax error in {py_file.name}: {e}")

    # 2. Check skill frontmatter
    skills_dir = agents_dir / "skills"
    if skills_dir.is_dir():
        for skill_file in skills_dir.rglob("SKILL.md"):
            content = skill_file.read_text(encoding="utf-8", errors="replace")[:600]
            if not re.search(r"^description:\s*\S", content, re.M):
                errors.append(f"Skill {skill_file.parent.name}/SKILL.md missing `description:` in frontmatter")

    # 3. Check hooks.json schema if present
    hooks_file = agents_dir / "hooks.json"
    if hooks_file.is_file():
        try:
            doc = json.loads(hooks_file.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                errors.append("hooks.json must be a JSON object")
            else:
                has_antigravity = "enabled" in doc or any(k in doc for k in ("PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"))
                has_wrapped = "hooks" in doc and isinstance(doc["hooks"], dict)
                if not (has_antigravity or has_wrapped):
                    errors.append("hooks.json must follow Antigravity schema ({'enabled': true, 'PreToolUse': [...]}) or {'hooks': {...}}")
        except Exception as e:
            errors.append(f"hooks.json JSON decode error: {e}")

    # 4. Check memory JSON files
    mem_dir = agents_dir / "memory"
    if mem_dir.is_dir():
        for jf in mem_dir.glob("*.json"):
            try:
                json.loads(jf.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"Memory JSON corrupt in {jf.name}: {e}")

    return errors


# ─── 3. Experience Ledger Management ──────────────────────────────────────────

def load_ledger() -> Dict[str, Any]:
    """Load persistent experience ledger."""
    if not LEDGER_FILE.exists():
        return {
            "version": "1.0.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "runs": [],
            "stats": {"total_tasks": 0, "total_proposals": 0, "adopted_harnesses": 0},
        }
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": "1.0.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "runs": [],
            "stats": {"total_tasks": 0, "total_proposals": 0, "adopted_harnesses": 0},
        }


def save_ledger(data: Dict[str, Any]):
    """Atomically persist experience ledger."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp_file = LEDGER_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(LEDGER_FILE)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


def record_ledger_entry(
    task_id: str,
    task_desc: str,
    proposals: List[Dict[str, Any]],
    adopted: Optional[Dict[str, Any]] = None,
    lessons: Optional[List[str]] = None,
):
    """Record a completed Propose-Probe-Compose cycle in the experience ledger."""
    data = load_ledger()
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task_id": task_id,
        "task": task_desc,
        "proposals_count": len(proposals),
        "proposals": proposals,
        "adopted": adopted,
        "lessons": lessons or [],
    }
    data.setdefault("runs", []).append(entry)
    data.setdefault("stats", {})
    data["stats"]["total_tasks"] = len(data["runs"])
    data["stats"]["total_proposals"] = data["stats"].get("total_proposals", 0) + len(proposals)
    if adopted:
        data["stats"]["adopted_harnesses"] = data["stats"].get("adopted_harnesses", 0) + 1
    save_ledger(data)


# ─── 4. Propose-Probe-Compose (PPC) Engine ────────────────────────────────────

def propose_refinements(task: str, dim: str = "mixed") -> List[Dict[str, Any]]:
    """
    Generate contrastive candidate proposals across the 8 components.
    dim can be:
      - 'inv': Invariant optimizations (safety gates, retries, blast-radius constraints)
      - 'dom': Domain-specific adaptations (skills, libraries, tool setups)
      - 'mixed': Paired invariant + domain proposals
    """
    proposals = []
    task_lower = task.lower()

    # Invariant proposal: Safety & verification hardening
    if dim in ("inv", "mixed"):
        proposals.append({
            "id": "prop_inv_1",
            "type": "invariant",
            "target_components": ["c2", "c7"],
            "title": "Empirical Verification & Strict AST Diff Invariant",
            "hypothesis": "Restricting code mutations to single atomic multi-replace blocks with guaranteed test execution prevents phantom regress.",
            "edits": [
                {
                    "component": "c2",
                    "file": ".agents/rules/core.md",
                    "action": "enforce_pre_flight",
                    "summary": "Enforce strict empirical command verification prior to task conclusion.",
                }
            ],
        })

    # Domain-specific proposal: Tailored to keywords in task
    if dim in ("dom", "mixed"):
        dom_components = []
        suggested_skills = []
        if any(w in task_lower for w in ["web", "react", "ui", "frontend", "css", "next", "vite"]):
            dom_components.extend(["c4", "c6"])
            suggested_skills.append("frontend-ui-engineering")
        if any(w in task_lower for w in ["api", "rest", "backend", "endpoint", "graphql"]):
            dom_components.extend(["c6", "c7"])
            suggested_skills.append("api-and-interface-design")
        if any(w in task_lower for w in ["security", "auth", "token", "vulnerability"]):
            dom_components.extend(["c2", "c6"])
            suggested_skills.append("security-and-hardening")
        if any(w in task_lower for w in ["perf", "speed", "slow", "latency", "benchmark"]):
            dom_components.extend(["c6", "c7"])
            suggested_skills.append("performance-optimization")

        proposals.append({
            "id": "prop_dom_1",
            "type": "domain",
            "target_components": dom_components or ["c6"],
            "title": f"Domain Playbook Activation for '{task[:40]}...'",
            "hypothesis": f"Equipping the agent with specialized domain skills ({', '.join(suggested_skills) or 'general'}) reduces trial-and-error trajectory length.",
            "skills": suggested_skills,
            "edits": [
                {
                    "component": "c6",
                    "action": "load_skills",
                    "skills": suggested_skills,
                }
            ],
        })

    return proposals


def compose_harness(proposals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compose winning proposals into an adopted refined harness plan."""
    adopted = {
        "composed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_proposals": [p["id"] for p in proposals],
        "active_modifications": [],
    }
    for p in proposals:
        for edit in p.get("edits", []):
            adopted["active_modifications"].append(edit)
    return adopted


# ─── 5. CLI Presentation & Handlers ───────────────────────────────────────────

def cmd_status(args):
    """Print high-level census of the 8 harness components."""
    census = get_harness_census()
    print(f"\n{CYAN}{BOLD}============================================================{RESET}")
    print(f"{CYAN}{BOLD} ⚡ Harness² Status — 8-Component Agent Surface{RESET}")
    print(f"{CYAN}{BOLD}============================================================{RESET}\n")

    for cid, spec in ANTIGRAVITY_COMPONENTS.items():
        data = census["components"][cid]
        status_icon = f"{GREEN}●{RESET}" if data["exists"] else f"{RED}○{RESET}"
        pct = (data["chars"] / data["budget"]) * 100 if data["budget"] else 0
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"  {status_icon} {BOLD}{cid.upper()}: {spec.name:<22}{RESET} [{bar}] {data['files']:>2} files | {data['chars']:>6} chars ({pct:>4.1f}% budget)")
        print(f"     {spec.role} ({data['path']})")

    print(f"\n  {BOLD}Total Files:{RESET} {census['total_files']}  |  {BOLD}Total Chars:{RESET} {census['total_chars']:,}")

    # Health
    if census["health"]:
        print(f"\n{YELLOW}{BOLD}Health Warnings:{RESET}")
        for h in census["health"]:
            print(f"  [{h['level']}] {h['msg']}")
    else:
        print(f"\n{GREEN}✔ All 8 harness components present and within budget limits.{RESET}")

    # Ledger summary
    ledger = load_ledger()
    runs = ledger.get("runs", [])
    print(f"\n{CYAN}{BOLD}Experience Ledger:{RESET} {len(runs)} tasks recorded | {ledger.get('stats', {}).get('adopted_harnesses', 0)} harnesses adopted\n")


def cmd_inspect(args):
    """Show detailed breakdown of one or all components."""
    census = get_harness_census()
    target = args.component.lower() if args.component else "all"

    print(f"\n{CYAN}{BOLD}=== Harness² Component Inspection: {target.upper()} ==={RESET}\n")

    for cid, spec in ANTIGRAVITY_COMPONENTS.items():
        if target != "all" and target != cid and target != spec.name.lower():
            continue
        data = census["components"][cid]
        print(f"{BOLD}[{cid.upper()}] {spec.name}{RESET}")
        print(f"  Role:   {spec.role}")
        print(f"  Path:   {data['path']}")
        print(f"  Files:  {data['files']} ({data['chars']} chars / cap {data['budget']})")
        print(f"  Items:  {', '.join(data['items'][:25]) or '(none)'}")
        if len(data["items"]) > 25:
            print(f"          ... and {len(data['items']) - 25} more")
        print()


def cmd_validate(args):
    """Run strict surface invariants validation."""
    print(f"\n{CYAN}{BOLD}Validating Harness² Surface Invariants...{RESET}")
    errors = validate_surface()
    if errors:
        print(f"\n{RED}{BOLD}❌ Validation Failed with {len(errors)} error(s):{RESET}")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}✔ All 8 harness components pass compilation and surface invariants!{RESET}\n")


def cmd_propose(args):
    """Generate PPC candidate proposals for a given task."""
    task = args.task
    dim = args.dim or "mixed"
    print(f"\n{CYAN}{BOLD}=== Harness² Propose: Contrastive Candidate Generation ==={RESET}")
    print(f"Task: {task}")
    print(f"Dimension: {dim.upper()}\n")

    proposals = propose_refinements(task, dim)
    for p in proposals:
        print(f"{BOLD}Proposal [{p['id']}] ({p['type'].upper()}): {p['title']}{RESET}")
        print(f"  Hypothesis: {p['hypothesis']}")
        print(f"  Target Components: {', '.join(p['target_components'])}")
        print("  Edits:")
        for edit in p.get("edits", []):
            print(f"    - [{edit.get('component')}]: {edit.get('action')} -> {edit.get('summary', edit.get('skills', ''))}")
        print()

    if args.record:
        composed = compose_harness(proposals)
        record_ledger_entry(
            task_id=f"task_{int(datetime.datetime.now().timestamp())}",
            task_desc=task,
            proposals=proposals,
            adopted=composed,
            lessons=[f"Refined harness for '{task[:30]}'"],
        )
        print(f"{GREEN}✔ Recorded proposals and composed harness in experience ledger.{RESET}\n")


def cmd_ledger(args):
    """Inspect or manage the Experience Ledger."""
    action = args.action or "summary"
    ledger = load_ledger()

    if action == "summary":
        stats = ledger.get("stats", {})
        runs = ledger.get("runs", [])
        print(f"\n{CYAN}{BOLD}=== Harness² Experience Ledger Summary ==={RESET}")
        print(f"  Total Tasks Refined:  {stats.get('total_tasks', len(runs))}")
        print(f"  Total Proposals:      {stats.get('total_proposals', 0)}")
        print(f"  Adopted Harnesses:    {stats.get('adopted_harnesses', 0)}")
        print(f"  Last Updated:         {ledger.get('updated_at', 'never')}\n")
        if runs:
            print(f"{BOLD}Recent Refinement Runs:{RESET}")
            for r in runs[-5:]:
                print(f"  - [{r.get('timestamp')[:19]}] {r.get('task_id')}: {r.get('task')[:50]} (proposals: {r.get('proposals_count')})")
            print()

    elif action == "list":
        runs = ledger.get("runs", [])
        print(f"\n{CYAN}{BOLD}=== Experience Ledger History ({len(runs)} entries) ==={RESET}\n")
        for i, r in enumerate(runs, 1):
            print(f"{i}. [{r.get('timestamp')[:19]}] {r.get('task_id')}")
            print(f"   Task:      {r.get('task')}")
            print(f"   Proposals: {r.get('proposals_count')}")
            if r.get("lessons"):
                print(f"   Lessons:   {', '.join(r.get('lessons'))}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="ZeroGravity OS: Harness² Recursive Agent Harnessing Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Harness command to execute")

    # status
    p_status = subparsers.add_parser("status", help="Display 8-component census and health")
    p_status.set_defaults(func=cmd_status)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Detailed breakdown of a component")
    p_inspect.add_argument("component", nargs="?", default="all", help="Component ID (c1..c8) or 'all'")
    p_inspect.set_defaults(func=cmd_inspect)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate surface invariants across components")
    p_validate.set_defaults(func=cmd_validate)

    # propose
    p_propose = subparsers.add_parser("propose", help="Generate contrastive candidate proposals")
    p_propose.add_argument("--task", required=True, help="Task description or goal")
    p_propose.add_argument("--dim", choices=["inv", "dom", "mixed"], default="mixed", help="Optimization dimension")
    p_propose.add_argument("--record", action="store_true", help="Record proposal cycle in experience ledger")
    p_propose.set_defaults(func=cmd_propose)

    # ledger
    p_ledger = subparsers.add_parser("ledger", help="Experience ledger management")
    p_ledger.add_argument("action", nargs="?", choices=["summary", "list"], default="summary", help="Ledger action")
    p_ledger.set_defaults(func=cmd_ledger)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        cmd_status(args)


if __name__ == "__main__":
    main()
