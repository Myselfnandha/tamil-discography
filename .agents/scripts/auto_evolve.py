#!/usr/bin/env python3
"""
ZeroGravity OS: Auto-Evolving Knowledge Capture Engine (`auto_evolve.py`)
=========================================================================

Automatically captures, deduplicates, categorizes, and accumulates user strategies,
coding patterns, build methods, tool preferences, debug techniques, and project context
without manual intervention.

Usage:
    python3 auto_evolve.py capture --type <type> --title <title> --content <content> [--tags <tags>]
    python3 auto_evolve.py list [--type <type>]
    python3 auto_evolve.py stats
    python3 auto_evolve.py sync [--dry-run]
    python3 auto_evolve.py export [--json]
"""

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent
MEMORY_DIR = WORKSPACE_ROOT / ".agents" / "memory"
STRATEGIES_JSON = MEMORY_DIR / "learned_strategies.json"
ECOSYSTEMS_DIR = WORKSPACE_ROOT / ".agents" / "knowledge" / "ecosystems"

# Valid knowledge types
KNOWLEDGE_TYPES = {
    "build_method": "Build Methods & Commands",
    "coding_pattern": "Coding Patterns & Strategies",
    "tool_preference": "Tool Preferences & Workflows",
    "framework_convention": "Framework & Library Conventions",
    "debug_strategy": "Debug Strategies & Techniques",
    "project_context": "Project-Specific Context",
    "user_correction": "User Corrections & Preferences",
    "error_recovery": "Error Recovery Patterns",
}

# Ecosystem classification keywords
ECOSYSTEM_KEYWORDS = {
    "web": ["react", "vite", "next", "vue", "tailwind", "css", "html", "browser", "frontend", "npm", "yarn", "node", "webpack", "eslint", "zustand", "redux", "typescript"],
    "python": ["python", "pip", "pep", "venv", "pytest", "fastapi", "flask", "django", "pydantic", "poetry", "uv", "asyncio", "uvicorn"],
    "docker": ["docker", "container", "dockerfile", "compose", "podman", "k8s", "kubernetes", "image", "entrypoint"],
    "mobile": ["react-native", "flutter", "ios", "android", "swift", "kotlin", "expo", "pod", "dart"],
    "general": ["git", "security", "sast", "architecture", "cli", "bash", "shell", "invariant", "memory", "testing", "ci", "cd"],
}


def load_strategies() -> Dict:
    """Load the accumulated learned strategies database."""
    if not STRATEGIES_JSON.exists():
        return {
            "version": "1.0.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "strategies": [],
        }
    try:
        with open(STRATEGIES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "version": "1.0.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "strategies": [],
        }


def save_strategies(data: Dict):
    """Atomically save the strategies database."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp_file = STRATEGIES_JSON.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            import os
            os.fsync(f.fileno())
        temp_file.replace(STRATEGIES_JSON)
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


def content_hash(title: str, content: str) -> str:
    """Generate a deduplication hash from title + content."""
    blob = f"{title.strip().lower()}|{content.strip().lower()}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def classify_ecosystem(text: str, tags: Optional[List[str]] = None) -> str:
    """Detect most appropriate ecosystem for given knowledge entry."""
    blob = (text + " " + " ".join(tags or [])).lower()
    scores = {}
    for eco, keywords in ECOSYSTEM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in blob)
        scores[eco] = score
    best_eco = max(scores, key=scores.get)
    return best_eco if scores[best_eco] > 0 else "general"


def is_duplicate(data: Dict, hash_val: str) -> bool:
    """Check if an entry with the same content hash already exists."""
    for entry in data.get("strategies", []):
        if entry.get("hash") == hash_val:
            return True
    return False


def capture_strategy(
    knowledge_type: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    source: str = "agent",
    project: str = "",
) -> Optional[Dict]:
    """
    Capture a new learned strategy, pattern, or preference.
    Returns the entry dict if captured, None if duplicate.
    """
    if knowledge_type not in KNOWLEDGE_TYPES:
        print(f"⚠️  Unknown knowledge type: {knowledge_type}", file=sys.stderr)
        print(f"   Valid types: {', '.join(KNOWLEDGE_TYPES.keys())}", file=sys.stderr)
        return None

    data = load_strategies()
    strategies = data.setdefault("strategies", [])

    h = content_hash(title, content)
    if is_duplicate(data, h):
        return None  # Silent dedup

    # Auto-detect project name if not provided
    if not project:
        try:
            project = WORKSPACE_ROOT.name
        except Exception:
            project = "unknown"

    # Compute next ID
    existing_nums = []
    for s in strategies:
        sid = s.get("id", "")
        if sid.startswith("STR-"):
            try:
                existing_nums.append(int(sid.split("-")[1]))
            except (IndexError, ValueError):
                pass
    next_num = (max(existing_nums) + 1) if existing_nums else 1

    entry = {
        "id": f"STR-{next_num:04d}",
        "type": knowledge_type,
        "type_label": KNOWLEDGE_TYPES[knowledge_type],
        "title": title.strip(),
        "content": content.strip(),
        "ecosystem": classify_ecosystem(title + " " + content, tags),
        "tags": tags or [],
        "source": source,
        "project": project,
        "hash": h,
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "synced": False,
    }

    strategies.append(entry)
    save_strategies(data)
    return entry


def list_strategies(filter_type: Optional[str] = None) -> List[Dict]:
    """List all captured strategies, optionally filtered by type."""
    data = load_strategies()
    strategies = data.get("strategies", [])
    if filter_type:
        strategies = [s for s in strategies if s.get("type") == filter_type]
    return strategies


def get_stats() -> Dict:
    """Get summary statistics of captured knowledge."""
    data = load_strategies()
    strategies = data.get("strategies", [])

    by_type: Dict[str, int] = {}
    by_eco: Dict[str, int] = {}
    synced = 0
    unsynced = 0

    for s in strategies:
        t = s.get("type", "unknown")
        e = s.get("ecosystem", "general")
        by_type[t] = by_type.get(t, 0) + 1
        by_eco[e] = by_eco.get(e, 0) + 1
        if s.get("synced"):
            synced += 1
        else:
            unsynced += 1

    return {
        "total": len(strategies),
        "synced": synced,
        "pending_sync": unsynced,
        "by_type": by_type,
        "by_ecosystem": by_eco,
        "updated_at": data.get("updated_at", "never"),
    }


def mark_synced():
    """Mark all strategies as synced after successful GitHub push."""
    data = load_strategies()
    for s in data.get("strategies", []):
        s["synced"] = True
    save_strategies(data)


def export_unsynced() -> List[Dict]:
    """Export only unsynced strategies for the sync pipeline."""
    data = load_strategies()
    return [s for s in data.get("strategies", []) if not s.get("synced")]


def update_ecosystem_files(strategies: List[Dict]) -> int:
    """Append new strategies to ecosystem knowledge catalog files."""
    ECOSYSTEMS_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0

    for s in strategies:
        eco = s.get("ecosystem", "general")
        if eco not in ECOSYSTEM_KEYWORDS:
            eco = "general"

        eco_file = ECOSYSTEMS_DIR / f"{eco}.md"
        if not eco_file.exists():
            eco_file.write_text(
                f"# 🌐 {eco.capitalize()} Ecosystem Knowledge\n\n",
                encoding="utf-8",
            )

        current = eco_file.read_text(encoding="utf-8")
        marker = f"[{s.get('id', 'STR-????')}]"
        if marker in current:
            continue

        type_label = s.get("type_label", s.get("type", "Unknown"))
        block = (
            f"\n### {marker} {s.get('title')}\n"
            f"- **Type**: {type_label}\n"
            f"- **Content**: {s.get('content')}\n"
        )
        if s.get("tags"):
            block += f"- **Tags**: {', '.join(s['tags'])}\n"

        with open(eco_file, "a", encoding="utf-8") as f:
            f.write(block)
        updated += 1

    return updated


def sync_to_github(dry_run: bool = False) -> bool:
    """
    Sync accumulated strategies to GitHub:
    1. Export unsynced entries
    2. Update ecosystem knowledge files
    3. Git add + commit + push (if owner)
    4. Mark entries as synced
    """
    unsynced = export_unsynced()
    if not unsynced:
        print("✅ No pending strategies to sync. Knowledge base is up-to-date.")
        return True

    print(f"📦 Found {len(unsynced)} unsynced strategy entries.")

    updated = update_ecosystem_files(unsynced)
    print(f"📝 Updated {updated} ecosystem catalog entries.")

    if dry_run:
        print("🧪 [DRY RUN]: Git push skipped.")
        for s in unsynced:
            print(f"  • [{s['id']}] ({s['type']}) {s['title']}")
        return True

    # Stage and commit
    try:
        subprocess.run(
            ["git", "add", ".agents/knowledge/ecosystems/", ".agents/memory/learned_strategies.json"],
            cwd=str(WORKSPACE_ROOT),
            check=True,
            capture_output=True,
        )

        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(WORKSPACE_ROOT),
        )
        if diff.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m",
                 f"feat(knowledge): auto-evolve {len(unsynced)} learned strategies [skip ci]"],
                cwd=str(WORKSPACE_ROOT),
                check=True,
                capture_output=True,
            )
            push_res = subprocess.run(
                ["git", "push", "origin", "HEAD"],
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
            )
            if push_res.returncode == 0:
                mark_synced()
                print(f"🚀 Pushed {len(unsynced)} strategies to GitHub!")
                return True
            else:
                print(f"⚠️  Push failed: {push_res.stderr.strip()}")
                return False
        else:
            mark_synced()
            print("✅ No new diffs to push (entries already in ecosystem files).")
            return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git operation failed: {e}")
        return False


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cmd_capture(args):
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    entry = capture_strategy(
        knowledge_type=args.type,
        title=args.title,
        content=args.content,
        tags=tags,
        source=args.source or "agent",
        project=args.project or "",
    )
    if entry:
        print(f"🧠 Captured [{entry['id']}] ({entry['type_label']}): {entry['title']}")
        print(f"   Ecosystem: {entry['ecosystem']} | Tags: {', '.join(entry['tags']) or 'none'}")
    else:
        print("⏭️  Duplicate entry — already captured.")


def cmd_list(args):
    strategies = list_strategies(args.type)
    print("\n" + "=" * 74)
    print("🧠 ZEROGRAVITY OS: AUTO-EVOLVED KNOWLEDGE BASE")
    print("=" * 74)

    if not strategies:
        print("No strategies captured yet.")
        print("=" * 74 + "\n")
        return

    for s in strategies:
        sync_icon = "✅" if s.get("synced") else "⏳"
        print(f"\n{sync_icon} [{s['id']}] ({s.get('type_label', s['type'])})")
        print(f"   📌 {s['title']}")
        print(f"   📝 {s['content'][:120]}{'...' if len(s.get('content', '')) > 120 else ''}")
        print(f"   🏷️  {s['ecosystem']} | {', '.join(s.get('tags', [])) or 'no tags'} | {s.get('project', '?')}")

    print("\n" + "=" * 74)
    print(f"Total: {len(strategies)} entries")
    print("=" * 74 + "\n")


def cmd_stats(args):
    stats = get_stats()
    print("\n" + "=" * 74)
    print("📊 ZEROGRAVITY OS: KNOWLEDGE EVOLUTION STATS")
    print("=" * 74)
    print(f"  Total Captured    : {stats['total']}")
    print(f"  Synced to GitHub  : {stats['synced']}")
    print(f"  Pending Sync      : {stats['pending_sync']}")
    print(f"  Last Updated      : {stats['updated_at']}")

    if stats["by_type"]:
        print("\n  By Type:")
        for t, count in sorted(stats["by_type"].items()):
            label = KNOWLEDGE_TYPES.get(t, t)
            print(f"    • {label}: {count}")

    if stats["by_ecosystem"]:
        print("\n  By Ecosystem:")
        for e, count in sorted(stats["by_ecosystem"].items()):
            print(f"    • {e}: {count}")

    print("\n" + "=" * 74 + "\n")


def cmd_sync(args):
    print("\n🌌 ZeroGravity OS Auto-Evolve Knowledge Sync")
    print("=" * 50)
    sync_to_github(dry_run=args.dry_run)


def cmd_export(args):
    data = load_strategies()
    strategies = data.get("strategies", [])
    if args.json:
        print(json.dumps(strategies, indent=2))
    else:
        for s in strategies:
            print(f"[{s['id']}] {s['type']}: {s['title']}")


def main():
    parser = argparse.ArgumentParser(
        description="ZeroGravity OS Auto-Evolving Knowledge Capture Engine"
    )
    subparsers = parser.add_subparsers(dest="command")

    # capture
    p_cap = subparsers.add_parser("capture", help="Capture a learned strategy or pattern")
    p_cap.add_argument("--type", "-t", required=True, choices=list(KNOWLEDGE_TYPES.keys()),
                       help="Knowledge type category")
    p_cap.add_argument("--title", required=True, help="Brief descriptive title")
    p_cap.add_argument("--content", "-c", required=True, help="Detailed content or description")
    p_cap.add_argument("--tags", default="", help="Comma-separated tags")
    p_cap.add_argument("--source", default="agent", help="Source: agent, user, error, test")
    p_cap.add_argument("--project", default="", help="Project name (auto-detected if empty)")

    # list
    p_list = subparsers.add_parser("list", help="List captured strategies")
    p_list.add_argument("--type", "-t", choices=list(KNOWLEDGE_TYPES.keys()),
                        help="Filter by type")

    # stats
    subparsers.add_parser("stats", help="Show knowledge evolution statistics")

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync accumulated knowledge to GitHub")
    p_sync.add_argument("--dry-run", action="store_true", help="Preview without pushing")

    # export
    p_export = subparsers.add_parser("export", help="Export all strategies")
    p_export.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    dispatch = {
        "capture": cmd_capture,
        "list": cmd_list,
        "stats": cmd_stats,
        "sync": cmd_sync,
        "export": cmd_export,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
