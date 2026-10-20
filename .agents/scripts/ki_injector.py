#!/usr/bin/env python3
"""
Knowledge Item (KI) Injector for Antigravity IDE.

Writes/updates a KI entry in ~/.gemini/antigravity-ide/knowledge/ so that
codebase context is automatically injected at every conversation start.

Also creates/updates workspace rules and global rules for auto-context loading.

Zero external dependencies. Uses only Python stdlib.
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone


# KI base directory
KI_BASE_DIR = os.path.expanduser('~/.gemini/antigravity-ide/knowledge')

# Global rules directory
GLOBAL_RULES_DIR = os.path.expanduser('~/.gemini/config/rules')



def get_ki_dir_name(project_name):
    """Generate KI directory name from project name."""
    # Sanitize project name for use as directory name
    safe_name = project_name.lower().replace(' ', '-').replace('_', '-')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '-')
    return f"codebase-context-{safe_name}"


def inject_ki(project_name, project_path, index_content, patch_content=None):
    """
    Write/update a Knowledge Item for the given project.

    Args:
        project_name: Name of the project (e.g., 'songstore')
        project_path: Absolute path to the project root
        index_content: Content of codebase_index.md
        patch_content: Content of codebase_patch.md (optional)

    Returns:
        str: Path to the created/updated KI directory
    """
    ki_dir_name = get_ki_dir_name(project_name)
    ki_dir = os.path.join(KI_BASE_DIR, ki_dir_name)
    artifacts_dir = os.path.join(ki_dir, 'artifacts')

    # Create directories
    os.makedirs(artifacts_dir, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()

    # Check if metadata exists (update vs create)
    metadata_path = os.path.join(ki_dir, 'metadata.json')
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            metadata['updated_at'] = now
        except Exception:
            metadata = _create_metadata(project_name, project_path, now)
    else:
        metadata = _create_metadata(project_name, project_path, now)

    agent_dir_name = '.agents' if os.path.isdir(os.path.join(project_path, '.agents')) else '.agent'
    metadata['references'] = [
        {
            'type': 'file',
            'path': os.path.join(project_path, agent_dir_name, 'codebase_summary.md')
        },
        {
            'type': 'file',
            'path': os.path.join(project_path, agent_dir_name, 'codebase_index.md')
        }
    ]

    # Count files from index content
    file_count = index_content.count('\n- `')
    metadata['summary'] = (
        f"Codebase context for {project_name}: "
        f"{file_count} files indexed. "
        f"Updated {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
        f"Source: {project_path}"
    )

    # Write metadata
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Write index artifact
    index_path = os.path.join(artifacts_dir, 'codebase_index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)

    # Write patch artifact if provided
    if patch_content:
        patch_path = os.path.join(artifacts_dir, 'codebase_patch.md')
        with open(patch_path, 'w', encoding='utf-8') as f:
            f.write(patch_content)

    print(f"KI injected: {ki_dir}")
    return ki_dir


def _create_metadata(project_name, project_path, now):
    """Create a new metadata.json structure."""
    agent_dir_name = '.agents' if os.path.isdir(os.path.join(project_path, '.agents')) else '.agent'
    return {
        'summary': f"Codebase context for {project_name}",
        'created_at': now,
        'updated_at': now,
        'references': [
            {
                'type': 'file',
                'path': os.path.join(project_path, agent_dir_name, 'codebase_summary.md')
            },
            {
                'type': 'file',
                'path': os.path.join(project_path, agent_dir_name, 'codebase_index.md')
            }
        ]
    }


def ensure_workspace_rule(workspace_root):
    """
    Create or verify the workspace rule that points agents to KI context.

    Args:
        workspace_root: Absolute path to workspace root
    """
    if os.path.isdir(os.path.join(workspace_root, '.agents')):
        agent_dir_name = '.agents'
    else:
        agent_dir_name = '.agent'
    rules_dir = os.path.join(workspace_root, agent_dir_name, 'rules')
    rule_path = os.path.join(rules_dir, 'codebase_context.md')

    os.makedirs(rules_dir, exist_ok=True)

    rule_content = f"""---
trigger: model_decision
---

# Codebase Context Auto-Loader

For this workspace:
1. Injected `codebase-context-*` KI provides the index and recent patches at conversation start.
2. Inspect code and directory structures directly via `view_file` and `grep_search`. Read `{agent_dir_name}/codebase_summary.md` for directory overviews.
3. NEVER spawn background Python analyzer scripts. Access persistent KI and summary natively with zero overhead.
"""

    with open(rule_path, 'w', encoding='utf-8') as f:
        f.write(rule_content)

    print(f"Created workspace rule: {rule_path}")
    return rule_path


def ensure_global_rule():
    """
    Create or verify the global rule for auto-context in all .agent/ or .agents/ workspaces.
    """
    os.makedirs(GLOBAL_RULES_DIR, exist_ok=True)
    legacy_path = os.path.join(GLOBAL_RULES_DIR, 'auto_codebase_context.md')
    if os.path.exists(legacy_path):
        try:
            os.remove(legacy_path)
        except OSError:
            pass

    rule_path = os.path.join(GLOBAL_RULES_DIR, 'codebase_context.md')
    rule_content = """---
trigger: always_on
---

# Codebase Context Auto-Loader

For any workspace containing a `.agent/` or `.agents/` directory:
1. Injected `codebase-context-*` KI provides the index and recent patches at conversation start.
2. Inspect code and directory structures directly via `view_file` and `grep_search`. Read `.agents/codebase_summary.md` for directory overviews.
3. NEVER spawn background Python analyzer scripts. Access persistent KI and summary natively with zero overhead.
"""

    with open(rule_path, 'w', encoding='utf-8') as f:
        f.write(rule_content)

    print(f"Created global rule: {rule_path}")
    return rule_path


def remove_ki(project_name):
    """Remove a KI entry for a project."""
    ki_dir_name = get_ki_dir_name(project_name)
    ki_dir = os.path.join(KI_BASE_DIR, ki_dir_name)

    if os.path.exists(ki_dir):
        shutil.rmtree(ki_dir)
        print(f"Removed KI: {ki_dir}")
    else:
        print(f"KI not found: {ki_dir}")


def list_kis():
    """List all codebase context KIs."""
    if not os.path.exists(KI_BASE_DIR):
        print("No KI directory found.")
        return []

    kis = []
    for entry in sorted(os.listdir(KI_BASE_DIR)):
        if entry.startswith('codebase-context-'):
            ki_dir = os.path.join(KI_BASE_DIR, entry)
            if os.path.isdir(ki_dir):
                metadata_path = os.path.join(ki_dir, 'metadata.json')
                summary = entry
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            meta = json.load(f)
                            summary = meta.get('summary', entry)
                    except Exception:
                        pass
                kis.append({'name': entry, 'path': ki_dir, 'summary': summary})
                print(f"  {entry}: {summary}")

    if not kis:
        print("  No codebase context KIs found.")
    return kis


# CLI interface
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Knowledge Item Injector for Antigravity IDE')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # inject command
    inject_parser = subparsers.add_parser('inject', help='Inject/update a KI')
    inject_parser.add_argument('project_name', help='Project name')
    inject_parser.add_argument('project_path', help='Project root path')
    inject_parser.add_argument('index_file', help='Path to codebase_index.md')
    inject_parser.add_argument('--patch-file', help='Path to codebase_patch.md')

    # list command
    subparsers.add_parser('list', help='List all codebase context KIs')

    # remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a KI')
    remove_parser.add_argument('project_name', help='Project name to remove')

    # rules command
    rules_parser = subparsers.add_parser('setup-rules', help='Setup workspace and global rules')
    rules_parser.add_argument('workspace_root', help='Workspace root path')

    args = parser.parse_args()

    if args.command == 'inject':
        with open(args.index_file, 'r', encoding='utf-8') as f:
            index_content = f.read()
        patch_content = None
        if args.patch_file and os.path.exists(args.patch_file):
            with open(args.patch_file, 'r', encoding='utf-8') as f:
                patch_content = f.read()
        inject_ki(args.project_name, os.path.abspath(args.project_path), index_content, patch_content)

    elif args.command == 'list':
        list_kis()

    elif args.command == 'remove':
        remove_ki(args.project_name)

    elif args.command == 'setup-rules':
        ensure_workspace_rule(os.path.abspath(args.workspace_root))
        ensure_global_rule()

    else:
        parser.print_help()
