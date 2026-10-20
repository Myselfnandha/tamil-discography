#!/usr/bin/env python3
"""
ZeroGravity OS: Autonomous Knowledge, Strategy & Build-Flow Auto-Sync Engine (`sync_knowledge.py`)

Extracts, sanitizes, categorizes, and synchronizes learned strategies, build flows,
methods, and architectural context back to the central repository (Myselfnandha/ZeroGravity).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent
AGENTS_DIR = WORKSPACE_ROOT / ".agents"
MEMORY_DIR = AGENTS_DIR / "memory"
ECOSYSTEMS_DIR = AGENTS_DIR / "knowledge" / "ecosystems"
ANTI_PATTERNS_JSON = MEMORY_DIR / "anti_patterns.json"
GOTCHAS_MD = MEMORY_DIR / "gotchas.md"
DECISIONS_MD = MEMORY_DIR / "decisions.md"
BUILD_FLOWS_JSON = MEMORY_DIR / "build_flows.json"
SYNC_HISTORY_JSON = MEMORY_DIR / "sync_history.json"
STRATEGIES_JSON = MEMORY_DIR / "learned_strategies.json"

CENTRAL_REPO = "Myselfnandha/ZeroGravity"
CENTRAL_GIT_URL = f"https://github.com/{CENTRAL_REPO}.git"

# Regex patterns for sanitization
ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
HOME_UNIX_REGEX = re.compile(r"/(?:home|Users)/[a-zA-Z0-9._-]+")
WINDOWS_USER_REGEX = re.compile(r"[a-zA-Z]:\\(?:[Uu]sers)\\[a-zA-Z0-9._-]+")
IPV4_REGEX = re.compile(r"\b(?!(?:127\.0\.0\.1|0\.0\.0\.0))\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Secret detection patterns (Skylos SAST inspired)
SECRET_PATTERNS = [
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GOOGLE_API_KEY]"),
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(?i)(password|passwd|secret|api_key|access_token)\s*[:=]\s*['\"][^'\"]{4,}['\"]"), r'\1: "[REDACTED_SECRET]"'),
]

ECOSYSTEM_KEYWORDS = {
    "web": ["react", "vite", "next", "vue", "tailwind", "css", "html", "browser", "frontend", "npm", "yarn", "node", "webpack", "eslint"],
    "python": ["python", "pip", "pep", "venv", "pytest", "fastapi", "flask", "django", "pydantic", "poetry", "uv", "asyncio"],
    "docker": ["docker", "container", "dockerfile", "compose", "podman", "k8s", "kubernetes", "image", "entrypoint"],
    "mobile": ["react-native", "flutter", "ios", "android", "swift", "kotlin", "expo", "pod"],
    "general": ["git", "security", "sast", "architecture", "cli", "bash", "shell", "invariant", "memory", "testing"]
}


def sanitize_text(text: str) -> str:
    """Scrub local machine paths, usernames, IP addresses, ANSI escapes, and credentials."""
    if not text or not isinstance(text, str):
        return text or ""
    
    # 1. Strip ANSI codes
    s = ANSI_REGEX.sub("", text)
    
    # 2. Strip secrets and keys
    for pattern, replacement in SECRET_PATTERNS:
        s = pattern.sub(replacement, s)
        
    # 3. Strip user home paths
    s = HOME_UNIX_REGEX.sub("~", s)
    s = WINDOWS_USER_REGEX.sub("~", s)
    
    # 4. Strip IPs and personal emails
    s = IPV4_REGEX.sub("[REDACTED_IP]", s)
    s = EMAIL_REGEX.sub("[REDACTED_EMAIL]", s)
    
    return s


def sanitize_structure(data):
    """Recursively sanitize dict, list, or primitive structure."""
    if isinstance(data, dict):
        return {sanitize_text(k): sanitize_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_structure(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    else:
        return data


def classify_ecosystem(text: str, tags=None) -> str:
    """Detect most appropriate ecosystem for given strategy/snippet."""
    blob = (text + " " + " ".join(tags or [])).lower()
    scores = {}
    for eco, keywords in ECOSYSTEM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in blob)
        scores[eco] = score
    
    best_eco = max(scores, key=scores.get)
    return best_eco if scores[best_eco] > 0 else "general"


def load_build_flows():
    if not BUILD_FLOWS_JSON.exists():
        return {"version": "1.0.0", "flows": []}
    try:
        with open(BUILD_FLOWS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0.0", "flows": []}


def save_build_flows(data):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = BUILD_FLOWS_JSON.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(BUILD_FLOWS_JSON)


def record_build_flow(name: str, stack: str, commands: list, notes: str = "", tags: list = None):
    """Save a verified build flow / method locally."""
    flows_data = load_build_flows()
    flows = flows_data.setdefault("flows", [])
    
    flow_id = f"FLOW-{len(flows) + 1:03d}"
    entry = {
        "id": flow_id,
        "name": name,
        "stack": stack or classify_ecosystem(name + " " + " ".join(commands)),
        "commands": commands,
        "notes": notes,
        "tags": tags or [],
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    flows.append(entry)
    save_build_flows(flows_data)
    return entry


def package_knowledge_payload():
    """Package all locally recorded strategies, gotchas, decisions, flows, and auto-evolved knowledge."""
    # 1. Anti-patterns
    anti_patterns = []
    if ANTI_PATTERNS_JSON.exists():
        try:
            with open(ANTI_PATTERNS_JSON, "r", encoding="utf-8") as f:
                ap_data = json.load(f)
                anti_patterns = ap_data.get("anti_patterns", [])
        except Exception:
            pass

    # 2. Build flows
    flows = load_build_flows().get("flows", [])

    # 3. Decisions
    decisions = []
    if DECISIONS_MD.exists():
        try:
            with open(DECISIONS_MD, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if line.strip().startswith("- **") or line.strip().startswith("1."):
                        decisions.append(line.strip())
        except Exception:
            pass

    # 4. Auto-evolved strategies
    learned_strategies = []
    if STRATEGIES_JSON.exists():
        try:
            with open(STRATEGIES_JSON, "r", encoding="utf-8") as f:
                strat_data = json.load(f)
                learned_strategies = strat_data.get("strategies", [])
        except Exception:
            pass

    payload = {
        "generator": "ZeroGravity-KnowledgeSync-v1.1.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "central_target": CENTRAL_REPO,
        "anti_patterns": anti_patterns,
        "build_flows": flows,
        "decisions": decisions,
        "learned_strategies": learned_strategies,
    }

    # Scrub all fields
    return sanitize_structure(payload)


def is_repo_owner() -> bool:
    """Check if current environment is the repository owner with direct git push permissions."""
    try:
        remote_res = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, cwd=WORKSPACE_ROOT)
        remote_url = remote_res.stdout.strip()
        if CENTRAL_REPO.lower() not in remote_url.lower():
            return False
        
        # Test dry-run push permission
        push_test = subprocess.run(["git", "push", "--dry-run", "origin", "HEAD"], capture_output=True, text=True, cwd=WORKSPACE_ROOT)
        return push_test.returncode == 0
    except Exception:
        return False


def update_ecosystem_files(sanitized_payload) -> int:
    """Update local .agents/knowledge/ecosystems/ files with categorized entries."""
    ECOSYSTEMS_DIR.mkdir(parents=True, exist_ok=True)
    updated_count = 0
    
    # Process anti-patterns
    for ap in sanitized_payload.get("anti_patterns", []):
        text = f"{ap.get('mistake', '')} {ap.get('root_cause', '')} {ap.get('strategy', '')}"
        eco = ap.get("category") or classify_ecosystem(text)
        if eco not in ECOSYSTEM_KEYWORDS:
            eco = "general"
        
        eco_file = ECOSYSTEMS_DIR / f"{eco}.md"
        if not eco_file.exists():
            eco_file.write_text(f"# 🌐 {eco.capitalize()} Ecosystem Knowledge\n\n## 🛡️ Known Gotchas & Anti-Patterns\n", encoding="utf-8")
        
        current_content = eco_file.read_text(encoding="utf-8")
        entry_marker = f"[{ap.get('id', 'AP-???')}]"
        if entry_marker not in current_content:
            new_block = (
                f"\n### {entry_marker} {ap.get('mistake')}\n"
                f"- **Root Cause**: {ap.get('root_cause')}\n"
                f"- **Prevention Strategy**: {ap.get('strategy')}\n"
                f"- **Invariant Rule**: {ap.get('invariant_rule', ap.get('strategy'))}\n"
            )
            with open(eco_file, "a", encoding="utf-8") as f:
                f.write(new_block)
            updated_count += 1

    # Process build flows
    for flow in sanitized_payload.get("build_flows", []):
        eco = flow.get("stack") or classify_ecosystem(flow.get("name", "") + " " + " ".join(flow.get("commands", [])))
        if eco not in ECOSYSTEM_KEYWORDS:
            eco = "general"
            
        eco_file = ECOSYSTEMS_DIR / f"{eco}.md"
        current_content = eco_file.read_text(encoding="utf-8") if eco_file.exists() else ""
        flow_marker = f"[{flow.get('id', 'FLOW-???')}]"
        if flow_marker not in current_content:
            cmds_str = "\n".join(f"  $ {c}" for c in flow.get("commands", []))
            new_block = (
                f"\n### {flow_marker} {flow.get('name')}\n"
                f"```bash\n{cmds_str}\n```\n"
                f"- **Notes**: {flow.get('notes', 'Verified execution flow.')}\n"
            )
            with open(eco_file, "a", encoding="utf-8") as f:
                f.write(new_block)
            updated_count += 1

    return updated_count


def dispatch_owner_sync(payload, dry_run=False):
    """Owner mode: commit updated ecosystem files and push directly to GitHub."""
    print("👑 Mode: Repo Owner detected. Running direct repository synchronization...")
    updated = update_ecosystem_files(payload)
    print(f"📦 Categorized & updated {updated} entries across ecosystem catalogs.")
    
    if dry_run:
        print("🧪 [DRY RUN]: Direct push skipped.")
        return True

    # Stage, commit, push
    subprocess.run(["git", "add", ".agents/knowledge/ecosystems/"], cwd=WORKSPACE_ROOT, check=True)
    subprocess.run(["git", "add", ".agents/memory/"], cwd=WORKSPACE_ROOT, check=True)
    
    # Check if there are changes to commit
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=WORKSPACE_ROOT)
    if diff.returncode != 0:
        subprocess.run(
            ["git", "commit", "-m", "feat(knowledge): auto-sync learned strategies and build flows [skip ci]"],
            cwd=WORKSPACE_ROOT, check=True
        )
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=WORKSPACE_ROOT, check=True)
        print("🚀 Successfully committed and pushed latest knowledge to Myselfnandha/ZeroGravity (origin)!")
    else:
        print("✅ Central knowledge is already up-to-date. No diffs to push.")
    return True


def dispatch_cloner_sync(payload, dry_run=False):
    """External/Cloner mode: submit sanitized knowledge via GitHub Issue ingestion bot or Webhook."""
    print(f"🌍 Mode: Community Contributor / Cloner detected.")
    print(f"🔒 Sanitizing payload with Zero-Knowledge filter...")
    
    summary = f"Community Knowledge Sync: {len(payload.get('anti_patterns', []))} patterns, {len(payload.get('build_flows', []))} flows"
    json_body = json.dumps(payload, indent=2)
    
    issue_body = (
        "## 🌌 ZeroGravity OS Knowledge Ingestion Payload\n\n"
        "> [!NOTE]\n"
        "> This issue was automatically generated by ZeroGravity OS client-side sync engine. "
        "The payload below is pre-sanitized (zero local paths, zero credentials).\n\n"
        "```json\n"
        f"{json_body}\n"
        "```\n"
    )

    if dry_run:
        print(f"🧪 [DRY RUN]: Issue submission payload generated ({len(json_body)} bytes).")
        print(f"Title: [Knowledge Sync] {summary}")
        return True

    # Check for gh CLI
    has_gh = subprocess.run(["which", "gh"], capture_output=True).returncode == 0
    if has_gh:
        print("📬 Submitting sanitized payload via GitHub Issue ingestion bot...")
        cmd = [
            "gh", "issue", "create",
            "--repo", CENTRAL_REPO,
            "--title", f"[Knowledge Sync] {summary}",
            "--body", issue_body,
            "--label", "community-learning"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Ingestion issue opened successfully: {res.stdout.strip()}")
            return True
        else:
            print(f"⚠️ gh issue create error: {res.stderr.strip()}")

    # Check for Webhook URL if set
    webhook_url = os.getenv("ZG_WEBHOOK_URL")
    if webhook_url:
        print(f"📡 Sending payload to Webhook: {webhook_url}...")
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "ZeroGravity-OS-Client"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201, 202):
                    print("✅ Webhook payload delivered successfully.")
                    return True
        except Exception as e:
            print(f"⚠️ Webhook dispatch failed: {e}")

    print("ℹ️ Submission saved locally. Run with 'gh auth login' or configured webhook for community sync.")
    return False


def main():
    parser = argparse.ArgumentParser(description="ZeroGravity OS Knowledge & Strategy Auto-Sync Engine")
    subparsers = parser.add_subparsers(dest="command")

    # sync (default)
    p_sync = subparsers.add_parser("sync", help="Synchronize learned strategies & build flows to GitHub")
    p_sync.add_argument("--dry-run", action="store_true", help="Perform dry run without pushing or submitting")
    p_sync.add_argument("--force-cloner", action="store_true", help="Force cloner/community issue ingestion route")

    # record-flow
    p_flow = subparsers.add_parser("record-flow", help="Record a verified build flow / method")
    p_flow.add_argument("--name", "-n", required=True, help="Descriptive name of the build flow")
    p_flow.add_argument("--stack", "-s", default="", help="Tech stack (web, python, docker, mobile, general)")
    p_flow.add_argument("--cmd", "-c", action="append", required=True, help="Command in sequence (can specify multiple)")
    p_flow.add_argument("--notes", default="", help="Execution notes or gotchas")

    # list-flows
    subparsers.add_parser("list-flows", help="List all locally captured build flows")

    # status
    subparsers.add_parser("status", help="Show synchronization status & summary")

    args = parser.parse_args()

    if args.command == "record-flow":
        entry = record_build_flow(args.name, args.stack, args.cmd, args.notes)
        print(f"✅ Recorded Build Flow [{entry['id']}]: {entry['name']} ({entry['stack']})")
        print(f"   Commands: {len(entry['commands'])} step(s)")
        return

    if args.command == "list-flows":
        data = load_build_flows()
        flows = data.get("flows", [])
        print("\n" + "=" * 70)
        print("🏗️  ZEROGRAVITY OS CAPTURED BUILD FLOWS & METHODS")
        print("=" * 70)
        if not flows:
            print("No build flows recorded yet. Use 'zg flow record' to add one.")
        for f in flows:
            print(f"\n[{f.get('id', 'FLOW-???')}] {f.get('name')} ({f.get('stack', 'general').upper()})")
            for c in f.get("commands", []):
                print(f"  $ {c}")
            if f.get("notes"):
                print(f"  ℹ️  Notes: {f.get('notes')}")
        print("\n" + "=" * 70 + "\n")
        return

    if args.command == "status":
        payload = package_knowledge_payload()
        print("\n" + "=" * 70)
        print("🌌 ZEROGRAVITY OS KNOWLEDGE SYNC STATUS")
        print("=" * 70)
        print(f"  • Central Target Repository : {CENTRAL_REPO}")
        print(f"  • Owner Privileges Detected : {'Yes' if is_repo_owner() else 'No (Community Mode)'}")
        print(f"  • Immunized Anti-Patterns   : {len(payload.get('anti_patterns', []))}")
        print(f"  • Captured Build Flows      : {len(payload.get('build_flows', []))}")
        print(f"  • Architectural Decisions   : {len(payload.get('decisions', []))}")
        print("=" * 70 + "\n")
        return

    # Default command: sync
    dry_run = getattr(args, "dry_run", False)
    force_cloner = getattr(args, "force_cloner", False)
    
    print("\n🌌 ZeroGravity OS Knowledge & Strategy Auto-Sync")
    print(f"🎯 Target Repository: {CENTRAL_GIT_URL}\n")
    
    payload = package_knowledge_payload()
    print(f"📦 Packaged {len(payload.get('anti_patterns', []))} anti-patterns, {len(payload.get('build_flows', []))} flows, and {len(payload.get('decisions', []))} decisions.")
    
    if is_repo_owner() and not force_cloner:
        dispatch_owner_sync(payload, dry_run=dry_run)
    else:
        dispatch_cloner_sync(payload, dry_run=dry_run)


if __name__ == "__main__":
    main()
