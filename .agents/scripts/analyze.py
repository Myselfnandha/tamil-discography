#!/usr/bin/env python3
"""
analyze.py — Antigravity High-Performance Codebase Analysis Engine.

Scans a project directory end-to-end and produces:
  1. codebase_summary.md  — Full source code + per-file heuristic summaries
  2. codebase_index.md    — Compact tree + 1-line summary per file (for KI memory)
  3. codebase_patch.md    — Rolling changelog of last 30 scans with timestamps
  4. codebase.db          — SQLite state database for atomic sub-millisecond caching

Features:
  - Multi-layer ignore engine (DEFAULT_IGNORES, .gitignore, .agentignore)
  - Zero-introspection protection (strictly excludes .agent/ from scanning itself)
  - Two-stage staleness verification (fast os.stat with SHA-256 fallback)
  - Lockfile dependency manifest extraction (uv.lock, package-lock.json, etc.)
  - 100% full-fidelity source code preservation for all project code files
  - Antigravity Knowledge Item (KI) auto-injection for persistent LLM memory
"""

import os
import sys
import re
import fnmatch
import argparse
import hashlib
from datetime import datetime, timezone

# Ensure sibling scripts can be imported
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from summarizer import summarize_file
from ki_injector import inject_ki, ensure_workspace_rule, ensure_global_rule
from db_cache import CodebaseCacheDB, compute_file_hash
from lockfile_extractor import is_lockfile, extract_lockfile_manifest


# Multi-layer default ignores across modern tech stacks
DEFAULT_IGNORES = {
    # Antigravity & Agent framework protection (P0: prevents recursive self-loop)
    '.agent', '.agents', '.gemini',
    # Version Control & IDEs
    '.git', '.vscode', '.idea', '.DS_Store', 'Thumbs.db',
    # Python
    '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', '.venv', 'venv', 'env',
    # JavaScript / Web
    'node_modules', 'dist', 'build', '.next', '.nuxt', '.turbo', '.svelte-kit',
    # Flutter / Dart
    '.dart_tool', '.flutter-plugins', '.flutter-plugins-dependencies', 'ephemeral',
    # Mobile (Android / iOS)
    '.gradle', 'DerivedData', 'Pods', '.cxx',
    # Compiled / Systems / Automation State
    'target', 'vendor', 'browser_profiles',
    # Translations / Duplicate Docs
    'docs_zh-CN',
}

# Files that should always be excluded from output
SELF_EXCLUDES = {
    'analyze.py',
    'codebase_summary.md',
    'codebase_index.md',
    'codebase_patch.md',
    'codebase.db',
    'codebase.db-wal',
    'codebase.db-shm',
    '.codebase.db',
    '.codebase.db-wal',
    '.codebase.db-shm',
    'install.sh',
    'antigravity-agent-bundle.tar.gz',
    'antigravity-slim-bundle.tar.xz',
}

# Max patch log entries
MAX_PATCH_ENTRIES = 30

# Tiered KI grouping threshold
KI_FILE_CAP = 100

# Mapping of file extensions to markdown language tags for syntax highlighting
LANGUAGE_TAGS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.json': 'json',
    '.md': 'markdown',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.ps1': 'powershell',
    '.rs': 'rust',
    '.go': 'go',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.h': 'cpp',
    '.hpp': 'cpp',
    '.dart': 'dart',
    '.java': 'java',
    '.kt': 'kotlin',
    '.swift': 'swift',
    '.rb': 'ruby',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.xml': 'xml',
    '.sql': 'sql',
    '.ini': 'ini',
    '.conf': 'ini',
    '.dockerfile': 'dockerfile',
    'Dockerfile': 'dockerfile',
}


def parse_gitignore_line(line, base_dir):
    """
    Parses a single .gitignore or .agentignore line and returns a tuple (compiled_regex, negate) or None.
    base_dir is the absolute path of the directory containing the ignore file.
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    negate = False
    if line.startswith('!'):
        negate = True
        line = line[1:].strip()
        if not line:
            return None

    # Normalize Windows path separators
    line = line.replace('\\', '/')

    match_dir_only = False
    if line.endswith('/'):
        match_dir_only = True
        line = line[:-1]

    if not line:
        return None

    is_anchored = '/' in line or line.startswith('/')
    if line.startswith('/'):
        line = line[1:]

    if not line:
        return None

    # Convert gitignore pattern to regex with accurate length bounds
    parts = []
    i = 0
    n = len(line)

    while i < n:
        char = line[i]
        if char == '*':
            if i + 1 < n and line[i+1] == '*':
                if i + 2 < n and line[i+2] == '/':
                    parts.append('(?:.*/)?')
                    i += 3
                else:
                    parts.append('.*')
                    i += 2
            else:
                parts.append('[^/]*')
                i += 1
        elif char == '?':
            parts.append('[^/]')
            i += 1
        elif char in ['.', '+', '^', '$', '(', ')', '[', ']', '{', '}', '|']:
            parts.append(re.escape(char))
            i += 1
        else:
            parts.append(char)
            i += 1

    regex_str = ''.join(parts)

    if not is_anchored:
        regex_str = f'(?:^|.*/){regex_str}'
    else:
        regex_str = f'^{regex_str}'

    if match_dir_only:
        regex_str = f'{regex_str}/(?:$|.*)'
    else:
        regex_str = f'{regex_str}(?:$|/.*)'

    try:
        compiled = re.compile(regex_str)
        return compiled, negate
    except Exception:
        return None


class GitIgnoreMatcher:
    """Manages multi-layer loading and matching of .gitignore and .agentignore files."""
    def __init__(self, root_dir, use_defaults=True):
        self.root_dir = os.path.abspath(root_dir)
        self.use_defaults = use_defaults
        # Map directory path -> list of (regex, negate)
        self.rules_cache = {}

    def load_for_dir(self, dir_path):
        dir_path = os.path.abspath(dir_path)
        if dir_path in self.rules_cache:
            return self.rules_cache[dir_path]

        rules = []
        for ignore_filename in ('.gitignore', '.agentignore'):
            ignore_path = os.path.join(dir_path, ignore_filename)
            if os.path.isfile(ignore_path):
                try:
                    with open(ignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            rule = parse_gitignore_line(line, dir_path)
                            if rule:
                                rules.append(rule)
                except Exception as e:
                    print(f"Warning: Failed to read {ignore_path}: {e}", file=sys.stderr)

        self.rules_cache[dir_path] = rules
        return rules

    def is_ignored(self, path, is_dir=False):
        abs_path = os.path.abspath(path)

        # Check default system ignores first if enabled
        if self.use_defaults:
            rel_parts = os.path.relpath(abs_path, self.root_dir).replace('\\', '/').split('/')
            for part in rel_parts:
                if part in DEFAULT_IGNORES:
                    return True

        # Resolve all ancestor directories up to the root_dir
        ancestors = []
        curr = abs_path if is_dir else os.path.dirname(abs_path)

        while True:
            ancestors.append(curr)
            if curr == self.root_dir or curr == os.path.dirname(curr):
                break
            curr = os.path.dirname(curr)

        # Apply rules starting from root_dir down to the file's dir
        ancestors.reverse()
        ignored = False

        for ancestor in ancestors:
            if not ancestor.startswith(self.root_dir):
                continue
            rules = self.load_for_dir(ancestor)
            rel_path = os.path.relpath(abs_path, ancestor).replace('\\', '/')
            if is_dir and not rel_path.endswith('/'):
                rel_path += '/'

            for regex, negate in rules:
                if regex.match(rel_path):
                    ignored = not negate

        return ignored


def is_binary(file_path):
    """Detects if a file is binary by looking for a null byte in the first 1024 bytes."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return True


def matches_any_pattern(rel_path, patterns, is_dir=False):
    """Checks if a relative path matches any custom glob pattern."""
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue

        pat = pat.replace('\\', '/')

        if pat.endswith('/'):
            if not is_dir:
                continue
            pat_clean = pat[:-1]
        else:
            pat_clean = pat

        name = rel_path.split('/')[-1]

        if '/' in pat_clean:
            if fnmatch.fnmatch(rel_path, pat_clean) or fnmatch.fnmatch(rel_path + ('/' if is_dir else ''), pat_clean):
                return True
        else:
            if fnmatch.fnmatch(name, pat_clean):
                return True
    return False


def get_code_fence(content):
    """Calculates the markdown code fence backtick count to prevent nested block breaks."""
    max_backticks = 0
    curr_backticks = 0
    for char in content:
        if char == '`':
            curr_backticks += 1
            if curr_backticks > max_backticks:
                max_backticks = curr_backticks
        else:
            curr_backticks = 0
    fence_len = max(3, max_backticks + 1)
    return '`' * fence_len


def build_ascii_tree(dir_path, matcher, custom_excludes=None, prefix="", root_dir=None, output_path=None):
    """Generates a list of strings representing the ASCII tree structure of the directory."""
    if root_dir is None:
        root_dir = dir_path

    lines = []
    try:
        entries = sorted(os.listdir(dir_path))
    except Exception as e:
        return [f"{prefix}└── [Error reading directory: {e}]"]

    filtered = []
    for entry in entries:
        full_path = os.path.join(dir_path, entry)
        is_dir = os.path.isdir(full_path)
        rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')

        if output_path and os.path.normcase(os.path.abspath(full_path)) == os.path.normcase(os.path.abspath(output_path)):
            continue
        if entry in SELF_EXCLUDES:
            continue
        if matcher.is_ignored(full_path, is_dir=is_dir):
            continue
        if custom_excludes and matches_any_pattern(rel_path, custom_excludes, is_dir=is_dir):
            continue

        filtered.append((entry, full_path, is_dir))

    for index, (entry, full_path, is_dir) in enumerate(filtered):
        is_last = (index == len(filtered) - 1)
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry}{'/' if is_dir else ''}")

        if is_dir:
            sub_prefix = "    " if is_last else "│   "
            lines.extend(build_ascii_tree(full_path, matcher, custom_excludes, prefix + sub_prefix, root_dir, output_path))

    return lines


def get_agent_dir(target_dir):
    """
    Determine the agent folder (.agents or .agent) inside target_dir.
    Prioritizes an existing agent folder; defaults to .agent if neither exists.
    """
    for dirname in ('.agents', '.agent'):
        candidate = os.path.join(target_dir, dirname)
        if os.path.isdir(candidate):
            return candidate
    return os.path.join(target_dir, '.agent')


def get_cache_db_path(target_dir, output_path=None):
    """Determine the optimal storage path for the SQLite cache database."""
    agent_dir = get_agent_dir(target_dir)
    cache_dir = os.path.join(agent_dir, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, 'codebase.db')


def _write_patch_log(patch_path, project_name, changed_files, scan_date):
    """Write or append to the rolling patch log (keeps at most MAX_PATCH_ENTRIES entries)."""
    new_entry_lines = []
    new_entry_lines.append(f"## {scan_date} ({len(changed_files)} file{'s' if len(changed_files) != 1 else ''} changed)")
    for rel_path, summary in changed_files:
        new_entry_lines.append(f"- `{rel_path}` — {summary}")
    new_entry_lines.append("")
    new_entry = '\n'.join(new_entry_lines)

    existing_entries = []
    header = f"# Codebase Patches: {project_name}\n\n"

    if os.path.exists(patch_path):
        try:
            with open(patch_path, 'r', encoding='utf-8') as f:
                content = f.read()

            parts = re.split(r'(?=^## )', content, flags=re.M)
            for part in parts:
                part = part.strip()
                if part.startswith('## '):
                    existing_entries.append(part)
        except Exception:
            pass

    all_entries = [new_entry.strip()] + existing_entries
    all_entries = all_entries[:MAX_PATCH_ENTRIES]

    with open(patch_path, 'w', encoding='utf-8') as f:
        f.write(header)
        for entry in all_entries:
            f.write(entry)
            f.write('\n\n')


def auto_sync_framework(target_dir, agent_dir, silent=True):
    """
    Silently auto-updates workspace .agents/ from global ~/.gemini/config/
    if the local workspace framework is older than the global installed version.
    Registers the workspace path in ~/.gemini/config/workspaces.json.
    """
    try:
        global_config = os.path.expanduser('~/.gemini/config')
        if not os.path.isdir(global_config):
            return

        norm_target = os.path.abspath(target_dir)

        # 1. Register workspace in ~/.gemini/config/workspaces.json
        workspaces_file = os.path.join(global_config, 'workspaces.json')
        try:
            workspaces = set()
            if os.path.exists(workspaces_file):
                with open(workspaces_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data.get('workspaces'), list):
                        workspaces = set(data['workspaces'])
            if norm_target not in workspaces:
                workspaces.add(norm_target)
                os.makedirs(os.path.dirname(workspaces_file), exist_ok=True)
                with open(workspaces_file, 'w', encoding='utf-8') as f:
                    json.dump({'workspaces': sorted(list(workspaces))}, f, indent=2)
        except Exception:
            pass

        # Protect development repository from self-overwrite
        if os.path.exists(os.path.join(norm_target, 'pack.sh')) and os.path.exists(os.path.join(norm_target, 'bin', 'cli.js')):
            return

        # 2. Check version
        global_version_file = os.path.join(global_config, 'VERSION')
        if not os.path.exists(global_version_file):
            return

        with open(global_version_file, 'r', encoding='utf-8') as f:
            global_ver = f.read().strip()

        local_version_file = os.path.join(agent_dir, 'VERSION')
        local_ver = '0.0.0'
        if os.path.exists(local_version_file):
            try:
                with open(local_version_file, 'r', encoding='utf-8') as f:
                    local_ver = f.read().strip()
            except Exception:
                pass

        if local_ver == global_ver:
            return

        # 3. Synchronize framework components from global config
        sync_dirs = ['rules', 'workflows', 'plugins', 'skills', 'scripts']
        import shutil
        for d in sync_dirs:
            src_dir = os.path.join(global_config, d)
            dest_dir = os.path.join(agent_dir, d)
            if os.path.isdir(src_dir):
                if d in ('plugins', 'skills'):
                    os.makedirs(dest_dir, exist_ok=True)
                    for p in os.listdir(src_dir):
                        sp = os.path.join(src_dir, p)
                        dp = os.path.join(dest_dir, p)
                        if os.path.isdir(sp):
                            if os.path.exists(dp):
                                shutil.rmtree(dp)
                            shutil.copytree(sp, dp)
                else:
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    shutil.copytree(src_dir, dest_dir)

        # Sync key metadata files
        for f in ['skills_index.json']:
            sf = os.path.join(global_config, f)
            df = os.path.join(agent_dir, f)
            if os.path.isfile(sf):
                shutil.copy2(sf, df)

        # Write new local VERSION
        with open(local_version_file, 'w', encoding='utf-8') as f:
            f.write(global_ver + '\n')

        if not silent:
            print(f"[ZeroGravity] Auto-synced {norm_target} from v{local_ver} to v{global_ver}")
    except Exception:
        pass


def check_npm_update_background():
    """
    Periodically checks if a newer version exists on npm in the background.
    Throttled to once every 12 hours via ~/.gemini/config/last_npm_check.json.
    """
    try:
        import urllib.request, time, subprocess, threading
        global_config = os.path.expanduser('~/.gemini/config')
        stamp_file = os.path.join(global_config, 'last_npm_check.json')
        now = time.time()
        if os.path.exists(stamp_file):
            try:
                with open(stamp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if now - data.get('timestamp', 0) < 43200:
                        return
            except Exception:
                pass

        try:
            with open(stamp_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': now}, f)
        except Exception:
            pass

        def _check():
            try:
                req = urllib.request.Request(
                    'https://registry.npmjs.org/@nandhaalagesan/zerogravity/latest',
                    headers={'User-Agent': 'ZeroGravity-AutoUpdater'}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    npm_data = json.loads(resp.read().decode())
                    npm_ver = npm_data.get('version')
                if not npm_ver:
                    return
                global_ver_file = os.path.join(global_config, 'VERSION')
                cur_ver = '0.0.0'
                if os.path.exists(global_ver_file):
                    cur_ver = open(global_ver_file).read().strip()
                if npm_ver != cur_ver:
                    subprocess.Popen(
                        ['npx', '-y', '@nandhaalagesan/zerogravity', 'update', '--global', '-y'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
            except Exception:
                pass

        t = threading.Thread(target=_check, daemon=True)
        t.start()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a folder end-to-end and generate a single Markdown summary for LLM context windows."
    )
    parser.add_argument("target_dir", nargs="?", default=".", help="Target directory to scan (default: .)")
    parser.add_argument("-o", "--output", default=None, help="Markdown summary path (default: <agent_dir>/codebase_summary.md)")
    parser.add_argument("-e", "--exclude", help="Comma-separated additional exclude glob patterns (e.g. '*.log,tests/').")
    parser.add_argument("-t", "--token-limit", type=int, default=300000, help="Warning token limit threshold (default: 300,000)")
    parser.add_argument("--no-defaults", action="store_true", help="Disable default system ignores")
    parser.add_argument("-y", "--non-interactive", action="store_true", help="Skip confirmation prompts for automated/agent usage")
    parser.add_argument("--check", action="store_true", help="Check staleness (exit 0 if fresh, exit 1 if stale)")
    parser.add_argument("--auto-heal", action="store_true", help="Automatically regenerate summary and refresh KI if stale during --check")
    parser.add_argument("--max-file-tokens", type=int, default=0, help="Skip files exceeding this token count (0 = no limit)")
    parser.add_argument("--summary-only", action="store_true", help="Output tree + file metadata only (no code blocks)")
    parser.add_argument("--inject-ki", action="store_true", help="Inject codebase context into Antigravity Knowledge Items")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.target_dir)

    if not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    agent_dir = get_agent_dir(target_dir)
    os.makedirs(agent_dir, exist_ok=True)

    # Silent framework auto-sync from global configuration & background npm check
    auto_sync_framework(target_dir, agent_dir, silent=True)
    check_npm_update_background()

    # codebase_summary, codebase_index, and codebase_patch MUST live in the .agent folder only
    if (not args.output or
        args.output in ("codebase_summary.md", "./codebase_summary.md") or
        os.path.normpath(os.path.abspath(args.output)) == os.path.normpath(os.path.join(target_dir, "codebase_summary.md"))):
        output_path = os.path.join(agent_dir, "codebase_summary.md")
    else:
        output_path = os.path.abspath(args.output)

    index_path = os.path.join(agent_dir, 'codebase_index.md')
    patch_path = os.path.join(agent_dir, 'codebase_patch.md')

    # Clean up legacy root files if they exist to keep project root clean
    for legacy_name in ('codebase_summary.md', 'codebase_index.md', 'codebase_patch.md'):
        legacy_file = os.path.join(target_dir, legacy_name)
        if os.path.isfile(legacy_file) and os.path.normpath(legacy_file) != os.path.normpath(output_path):
            try:
                os.remove(legacy_file)
                print(f"Cleaned up legacy root file: {legacy_file}")
            except Exception:
                pass

    custom_excludes = [p.strip() for p in args.exclude.split(',')] if args.exclude else []

    # Initialize SQLite Cache DB
    db_path = get_cache_db_path(target_dir, output_path)
    db = CodebaseCacheDB(db_path)

    matcher = GitIgnoreMatcher(target_dir, use_defaults=not args.no_defaults)

    # =========================================================================
    # Fast Two-Stage Staleness Check (--check mode)
    # =========================================================================
    if args.check:
        cached_count = db.count()
        if cached_count == 0 or not os.path.exists(output_path):
            if args.auto_heal:
                print("CHECK: Summary missing or cache empty. Auto-healing codebase summary and refreshing KI...")
            else:
                print("CHECK: Summary missing or cache empty. Stale.")
                db.close()
                sys.exit(1)
        else:
            stale = False
            current_files = set()

            for root, dirs, filenames in os.walk(target_dir):
                dirs[:] = [
                    d for d in dirs
                    if not matcher.is_ignored(os.path.join(root, d), is_dir=True)
                    and not (custom_excludes and matches_any_pattern(os.path.relpath(os.path.join(root, d), target_dir).replace('\\', '/'), custom_excludes, is_dir=True))
                ]

                for f in filenames:
                    fp = os.path.join(root, f)
                    if os.path.normcase(os.path.abspath(fp)) == os.path.normcase(output_path):
                        continue
                    if f in SELF_EXCLUDES:
                        continue
                    if matcher.is_ignored(fp, is_dir=False):
                        continue
                    rp = os.path.relpath(fp, target_dir).replace('\\', '/')
                    if custom_excludes and matches_any_pattern(rp, custom_excludes, is_dir=False):
                        continue
                    if is_binary(fp):
                        continue

                    current_files.add(rp)
                    cached = db.get_file(rp)
                    if not cached:
                        stale = True
                        break

                    try:
                        st = os.stat(fp)
                        st_mtime = round(st.st_mtime, 3)
                        st_size = st.st_size
                    except Exception:
                        stale = True
                        break

                    # Stage 1: Fast os.stat comparison (sub-millisecond)
                    if cached['file_size'] == st_size and abs(cached['mtime'] - st_mtime) < 0.001:
                        continue

                    # Stage 2: Content-hash comparison (eliminates git checkout/stash false positives)
                    chash = compute_file_hash(fp)
                    if chash and chash == cached['content_hash']:
                        # Hash is identical: auto-heal mtime in DB without marking stale
                        db.update_mtime_only(rp, st_mtime)
                        continue

                    stale = True
                    break

                if stale:
                    break

            # Check for deleted files
            if not stale and cached_count != len(current_files):
                stale = True

            if stale:
                if args.auto_heal:
                    print("CHECK: Summary is STALE. Auto-healing codebase summary and refreshing KI...")
                else:
                    db.close()
                    print("CHECK: Summary is STALE. Regeneration needed.")
                    sys.exit(1)
            else:
                db.close()
                print("CHECK: Summary is FRESH. No changes detected.")
                sys.exit(0)

    # =========================================================================
    # Full Codebase Scan & Incremental Regeneration
    # =========================================================================
    print(f"Scanning target directory: {target_dir}")
    print(f"Output markdown path:      {output_path}")
    print(f"State SQLite cache path:   {db_path}")

    files_to_process = []
    file_status = {}
    total_chars = 0
    total_estimated_tokens = 0
    cache_hits = 0
    cache_misses = 0

    for root, dirs, filenames in os.walk(target_dir):
        # Exclude directories in-place to prune walk traversal
        dirs[:] = [
            d for d in dirs
            if not matcher.is_ignored(os.path.join(root, d), is_dir=True)
            and not (custom_excludes and matches_any_pattern(os.path.relpath(os.path.join(root, d), target_dir).replace('\\', '/'), custom_excludes, is_dir=True))
        ]

        for f in filenames:
            file_path = os.path.join(root, f)
            if os.path.normcase(os.path.abspath(file_path)) == os.path.normcase(output_path):
                continue
            if f in SELF_EXCLUDES:
                continue
            if matcher.is_ignored(file_path, is_dir=False):
                continue

            rel_file_path = os.path.relpath(file_path, target_dir).replace('\\', '/')
            if custom_excludes and matches_any_pattern(rel_file_path, custom_excludes, is_dir=False):
                continue
            if is_binary(file_path):
                continue

            try:
                st = os.stat(file_path)
                mtime = round(st.st_mtime, 3)
                file_size = st.st_size
            except Exception:
                mtime = 0.0
                file_size = 0

            # Query SQLite cache
            cached = db.get_file(rel_file_path)
            is_cached = False

            if cached:
                # Stage 1: Stat match
                if cached['file_size'] == file_size and abs(cached['mtime'] - mtime) < 0.001:
                    is_cached = True
                else:
                    # Stage 2: Hash fallback
                    chash = compute_file_hash(file_path)
                    if chash and chash == cached['content_hash']:
                        db.update_mtime_only(rel_file_path, mtime)
                        cached['mtime'] = mtime
                        is_cached = True

            if is_cached:
                cache_hits += 1
                file_status[rel_file_path] = {
                    'status': 'cached',
                    'mtime': mtime,
                    'file_size': file_size,
                    'tokens': cached['token_count'],
                    'summary': cached['summary'],
                    'section_text': cached['section_text']
                }
                total_estimated_tokens += cached['token_count']
            else:
                cache_misses += 1
                file_est_tokens = file_size // 4
                if args.max_file_tokens > 0 and file_est_tokens > args.max_file_tokens:
                    print(f"  Skipping {rel_file_path} (~{file_est_tokens:,} tokens > limit {args.max_file_tokens:,})")
                    continue

                file_status[rel_file_path] = {
                    'status': 'dirty',
                    'mtime': mtime,
                    'file_size': file_size,
                    'abs_path': file_path
                }
                total_chars += file_size

            files_to_process.append(rel_file_path)

    files_to_process.sort()
    total_estimated_tokens += total_chars // 4

    print(f"Found {len(files_to_process)} text files.")
    print(f"  - {cache_hits} files up-to-date (using SQLite cache)")
    print(f"  - {cache_misses} files modified/new (will be processed)")
    print(f"Estimated total size: ~{total_estimated_tokens:,} tokens.")

    if total_estimated_tokens > args.token_limit:
        print(f"\nWARNING: Estimated token count ({total_estimated_tokens:,}) exceeds the threshold ({args.token_limit:,}).")
        if not args.non_interactive:
            confirm = input("Do you want to continue? [y/N]: ").strip().lower()
            if confirm not in ('y', 'yes'):
                print("Aborted.")
                db.close()
                sys.exit(0)
        else:
            print("Non-interactive mode: proceeding anyway.")

    # =========================================================================
    # Process Dirty Files & Extract Summaries
    # =========================================================================
    print("Processing file contents and heuristic summaries...")
    file_summaries = {}
    changed_files = []

    for rel_path in files_to_process:
        status_info = file_status[rel_path]

        if status_info['status'] == 'cached':
            file_summaries[rel_path] = status_info['summary']
            continue

        # Dirty/New file: Process content
        abs_path = status_info['abs_path']
        mtime = status_info['mtime']
        file_size = status_info['file_size']
        content_hash = compute_file_hash(abs_path)

        # Check for lockfiles -> extract clean dependency manifest
        if is_lockfile(rel_path):
            manifest_text, pkg_count = extract_lockfile_manifest(abs_path)
            summary = f"Lockfile manifest: {pkg_count} resolved dependencies"
            file_tokens = len(manifest_text) // 4
            section_text = (
                f"### File: `{rel_path}`\n"
                f"- **Summary:** {summary}\n"
                f"- **Path:** `{rel_path}`\n"
                f"- **Estimated Tokens:** {file_tokens:,}\n"
                f"- **mtime:** {mtime}\n\n"
                f"{manifest_text}\n\n"
                f"---\n\n"
            )
        else:
            # 100% Full-Fidelity Source Code
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='replace') as f_in:
                    content = f_in.read()
            except Exception as e:
                content = f"[Error reading file: {e}]"

            summary = summarize_file(abs_path)
            file_tokens = len(content) // 4
            fence = get_code_fence(content)

            file_ext = os.path.splitext(rel_path)[1]
            lang_tag = LANGUAGE_TAGS.get(file_ext, LANGUAGE_TAGS.get(os.path.basename(rel_path), ''))

            if not content.endswith('\n'):
                content += '\n'

            section_text = (
                f"### File: `{rel_path}`\n"
                f"- **Summary:** {summary}\n"
                f"- **Path:** `{rel_path}`\n"
                f"- **Estimated Tokens:** {file_tokens:,}\n"
                f"- **mtime:** {mtime}\n\n"
                f"{fence}{lang_tag}\n"
                f"{content}"
                f"{fence}\n\n"
                f"---\n\n"
            )

        file_summaries[rel_path] = summary
        changed_files.append((rel_path, summary))

        # Store in SQLite DB
        db.upsert_file(
            rel_path=rel_path,
            mtime=mtime,
            file_size=file_size,
            content_hash=content_hash,
            token_count=file_tokens,
            summary=summary,
            section_text=section_text
        )

        status_info['section_text'] = section_text
        status_info['tokens'] = file_tokens

    # Clean up deleted files from SQLite cache
    db.delete_missing(files_to_process)

    # Generate ASCII directory tree
    print("Generating directory tree...")
    tree_lines = build_ascii_tree(target_dir, matcher, custom_excludes, output_path=output_path)
    tree_text = "\n".join(tree_lines)

    project_name = os.path.basename(target_dir)
    scan_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # =========================================================================
    # Write codebase_summary.md
    # =========================================================================
    print("Writing summary report...")
    try:
        with open(output_path, 'w', encoding='utf-8') as out:
            out.write(f"# Codebase Summary: {project_name}\n\n")
            out.write("## Overview\n")
            out.write(f"- **Scan Date:** {scan_date}\n")
            out.write(f"- **Source Folder:** `{target_dir}`\n")
            out.write(f"- **Total Text Files:** {len(files_to_process)}\n")
            out.write(f"- **Estimated Token Count:** {total_estimated_tokens:,}\n\n")

            out.write("## File Summaries\n\n")
            for rel_path in files_to_process:
                summary = file_summaries.get(rel_path, '')
                out.write(f"- `{rel_path}` — {summary}\n")
            out.write("\n")

            out.write("## Directory Tree\n")
            out.write("```text\n")
            out.write(f"{project_name}/\n")
            out.write(tree_text)
            out.write("\n```\n\n")

            out.write("## File Contents\n\n")
            for idx, rel_path in enumerate(files_to_process, 1):
                status_info = file_status[rel_path]
                if args.summary_only:
                    tokens = status_info.get('tokens', 0)
                    summary = file_summaries.get(rel_path, '')
                    out.write(f"- `{rel_path}` — ~{tokens:,} tokens | {summary}\n")
                else:
                    out.write(status_info['section_text'])

        print(f"Success! Codebase summary saved to: {output_path}")
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        db.close()
        sys.exit(1)

    # =========================================================================
    # Write codebase_index.md
    # =========================================================================
    print(f"Writing codebase index to: {index_path}")

    try:
        with open(index_path, 'w', encoding='utf-8') as idx_out:
            idx_out.write(f"# Codebase Context: {project_name}\n")
            idx_out.write(f"> Auto-generated on {scan_date}. ")
            idx_out.write(f"{len(files_to_process)} files, ~{total_estimated_tokens:,} tokens.\n\n")

            if len(files_to_process) > KI_FILE_CAP:
                idx_out.write("## Directory Overview\n\n")
                dir_groups = {}
                for rel_path in files_to_process:
                    top_dir = rel_path.split('/')[0] if '/' in rel_path else '.'
                    if top_dir not in dir_groups:
                        dir_groups[top_dir] = []
                    dir_groups[top_dir].append(rel_path)

                for dir_name in sorted(dir_groups.keys()):
                    files_in_dir = dir_groups[dir_name]
                    idx_out.write(f"### `{dir_name}/` ({len(files_in_dir)} files)\n")
                    for rp in files_in_dir[:12]:
                        summary = file_summaries.get(rp, '')
                        idx_out.write(f"- `{rp}` — {summary}\n")
                    if len(files_in_dir) > 12:
                        idx_out.write(f"- ... and {len(files_in_dir) - 12} more files\n")
                    idx_out.write("\n")
            else:
                idx_out.write("## Structure\n```text\n")
                idx_out.write(f"{project_name}/\n")
                idx_out.write(tree_text)
                idx_out.write("\n```\n\n## File Index\n\n")
                for rel_path in files_to_process:
                    summary = file_summaries.get(rel_path, '')
                    idx_out.write(f"- `{rel_path}` — {summary}\n")
                idx_out.write("\n")

        print(f"Codebase index saved to: {index_path}")
    except Exception as e:
        print(f"Error writing index file: {e}", file=sys.stderr)

    # =========================================================================
    # Write / Update codebase_patch.md
    # =========================================================================
    if changed_files:
        print(f"Writing patch log ({len(changed_files)} changes) to: {patch_path}")
        try:
            _write_patch_log(patch_path, project_name, changed_files, scan_date)
            print(f"Patch log saved to: {patch_path}")
        except Exception as e:
            print(f"Error writing patch log: {e}", file=sys.stderr)
    else:
        print("No file changes detected — patch log not updated.")

    # =========================================================================
    # Antigravity Knowledge Item (KI) Auto-Injection
    # =========================================================================
    if args.inject_ki:
        print("\nInjecting codebase context into Antigravity Knowledge Items...")
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()

            patch_content = None
            if os.path.exists(patch_path):
                with open(patch_path, 'r', encoding='utf-8') as f:
                    patch_content = f.read()

            inject_ki(project_name, target_dir, index_content, patch_content)

            # Ensure workspace and global rules exist
            workspace_root = target_dir
            check_dir = target_dir
            while check_dir != os.path.dirname(check_dir):
                if os.path.isdir(os.path.join(check_dir, '.agents')) or os.path.isdir(os.path.join(check_dir, '.agent')):
                    workspace_root = check_dir
                    break
                check_dir = os.path.dirname(check_dir)

            ensure_workspace_rule(workspace_root)
            ensure_global_rule()
            print("KI injection complete!")
        except Exception as e:
            print(f"Error injecting KI: {e}", file=sys.stderr)

    db.close()


if __name__ == "__main__":
    main()
