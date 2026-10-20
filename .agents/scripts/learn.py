#!/usr/bin/env python3
"""
ZeroGravity OS: 2-Way Mistake Immunization & Learning Engine (`learn.py`)
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent
MEMORY_DIR = WORKSPACE_ROOT / ".agents" / "memory"
ANTI_PATTERNS_JSON = MEMORY_DIR / "anti_patterns.json"
GOTCHAS_MD = MEMORY_DIR / "gotchas.md"


def load_anti_patterns():
    if not ANTI_PATTERNS_JSON.exists():
        return {"version": "1.0.0", "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "anti_patterns": []}
    with open(ANTI_PATTERNS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_anti_patterns(data):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp_file = ANTI_PATTERNS_JSON.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            import os
            os.fsync(f.fileno())
        temp_file.replace(ANTI_PATTERNS_JSON)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


def sync_to_gotchas_markdown(data):
    lines = [
        "# 🛡️ ZeroGravity OS: Known Gotchas & Immunization Protocol\n",
        "Anti-patterns (AP-001 through AP-{:03d}) are maintained in the machine-readable single source of truth: `anti_patterns.json`.\n".format(
            len(data.get("anti_patterns", []))
        ),
        "---",
        "",
        "## 🛠️ Platform & Tooling Gotchas",
        "",
        "### 1. Skylos SAST on Meta-Directories",
        "- **Gotcha**: Scanning directories containing 1,450+ offline skill scripts causes slow traversal.",
        "- **Rule**: Pass `--exclude .agents --exclude .agent --exclude venv` when running whole-project audits.",
        "",
        "### 2. PEP 668 & Linux System Python Isolation",
        "- **Gotcha**: Modern Linux distros (Arch, Debian 12+, Ubuntu 24+) block system-wide `pip install`.",
        "- **Rule**: Provision isolated virtual environments under `~/.local/share/<tool>/venv` and symlink CLI entrypoints to `~/.local/bin/`.",
        "",
        "### 3. NPM Remote Package Authorization (`EALLOWREMOTE`)",
        "- **Gotcha**: npm v12+ defaults `allow-remote=\"none\"`, failing to install git-based tarball dependencies.",
        "- **Rule**: Configure `npm config set allow-remote all` during environment setup.",
        "",
        "---",
        "",
        "## 🔄 The 2-Way Immunization Protocol",
        "1. **Pre-Action Check**: Before executing a tool call or creating a component, verify against `anti_patterns.json`.",
        "2. **Post-Failure Distillation**: When a mistake, test failure, or user correction occurs:",
        "   - Identify the exact root cause.",
        "   - Formulate an Invariant Prevention Strategy.",
        "   - Append to `anti_patterns.json` via `zg learn add`."
    ]

    with open(GOTCHAS_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def cmd_list(args):
    data = load_anti_patterns()
    patterns = data.get("anti_patterns", [])
    print("\n" + "=" * 78)
    print("🛡️  ZEROGRAVITY OS ANTI-PATTERNS & PREVENTION STRATEGIES")
    print("=" * 78)
    if not patterns:
        print("No anti-patterns recorded yet.")
        return

    for item in patterns:
        print(f"\n[{item.get('id', 'AP-???')}] ({item.get('category', 'general').upper()})")
        print(f"  ⚠️  Mistake  : {item.get('mistake')}")
        print(f"  🔍 Cause    : {item.get('root_cause')}")
        print(f"  🛡️  Strategy : {item.get('strategy')}")
        if "invariant_rule" in item:
            print(f"  ⚡ Rule     : {item.get('invariant_rule')}")
    print("\n" + "=" * 78)
    print(f"Total Anti-Patterns Immunized: {len(patterns)}\n")


def cmd_add(args):
    data = load_anti_patterns()
    patterns = data.setdefault("anti_patterns", [])
    
    # Safely compute next ID to prevent collisions
    existing_nums = []
    for p in patterns:
        pid = p.get("id", "")
        if pid.startswith("AP-"):
            try:
                existing_nums.append(int(pid.split("-")[1]))
            except (IndexError, ValueError):
                pass
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    new_id = f"AP-{next_num:03d}"
    
    entry = {
        "id": new_id,
        "category": args.category or "general",
        "mistake": args.mistake,
        "root_cause": args.cause,
        "strategy": args.strategy,
        "invariant_rule": args.rule or args.strategy
    }
    patterns.append(entry)
    save_anti_patterns(data)
    sync_to_gotchas_markdown(data)
    print(f"✅ Learned & Immunized [{new_id}]: {args.mistake}")
    print(f"🛡️  Invariant Strategy: {args.strategy}")
    if getattr(args, "sync", False):
        sync_script = SCRIPT_DIR / "sync_knowledge.py"
        if sync_script.exists():
            print("🔄 Auto-triggering knowledge sync to GitHub...")
            import subprocess
            subprocess.run(["python3", str(sync_script), "sync"], cwd=WORKSPACE_ROOT)


def cmd_check(args):
    data = load_anti_patterns()
    query = (args.query or "").lower()
    matches = []
    for item in data.get("anti_patterns", []):
        combined = f"{item.get('mistake', '')} {item.get('root_cause', '')} {item.get('strategy', '')}".lower()
        if query in combined:
            matches.append(item)

    if matches:
        print(f"⚠️  Found {len(matches)} matching Anti-Pattern(s) for '{args.query}':")
        for item in matches:
            print(f"  • [{item['id']}] {item['mistake']}")
            print(f"    👉 Apply Strategy: {item['strategy']}")
        sys.exit(1)
    else:
        print(f"✅ Safe: No matching anti-patterns found for '{args.query}'.")


def cmd_audit(args):
    data = load_anti_patterns()
    patterns = data.get("anti_patterns", [])
    print(f"🔍 Auditing Anti-Patterns Database ({len(patterns)} entries)...")
    errors = 0
    ids = set()
    for item in patterns:
        ap_id = item.get("id")
        if not ap_id or ap_id in ids:
            print(f"❌ Duplicate or missing ID: {ap_id}")
            errors += 1
        ids.add(ap_id)
        for key in ["mistake", "root_cause", "strategy"]:
            if not item.get(key):
                print(f"❌ Entry {ap_id} missing field '{key}'")
                errors += 1

    if errors == 0:
        print("✅ Anti-Patterns memory matrix is healthy, valid, and synchronized.")
    else:
        print(f"❌ Audit failed with {errors} errors.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ZeroGravity OS Learning & Anti-Patterns Engine")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List all immunized anti-patterns")

    # add
    p_add = subparsers.add_parser("add", help="Record a new learned anti-pattern & strategy")
    p_add.add_argument("--mistake", "-m", required=True, help="Description of the mistake/failure")
    p_add.add_argument("--cause", "-c", required=True, help="Root cause of the failure")
    p_add.add_argument("--strategy", "-s", required=True, help="Proven prevention strategy")
    p_add.add_argument("--category", "-k", default="general", help="Category (tooling, runtime, architecture, etc.)")
    p_add.add_argument("--rule", "-r", default=None, help="Invariant rule statement")
    p_add.add_argument("--sync", action="store_true", help="Auto-trigger knowledge sync to GitHub after adding")

    # check
    p_check = subparsers.add_parser("check", help="Check planned action against known anti-patterns")
    p_check.add_argument("--query", "-q", required=True, help="Query string or planned command")

    # audit
    subparsers.add_parser("audit", help="Audit integrity of memory matrix")

    args = parser.parse_args()
    if not args.command or args.command == "list":
        cmd_list(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "audit":
        cmd_audit(args)


if __name__ == "__main__":
    main()
