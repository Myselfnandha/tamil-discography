#!/usr/bin/env python3
"""
Lockfile Dependency Extractor for analyze.py.

Extracts concise dependency manifests (package name + version) from massive
lockfiles (uv.lock, package-lock.json, pubspec.lock, Cargo.lock, poetry.lock),
reducing ~100k token noise down to ~300 tokens while preserving 100% architectural
visibility for the AI model.

Zero external dependencies. Uses only Python stdlib.
"""

import os
import re
import json


LOCKFILE_NAMES = {
    'uv.lock',
    'poetry.lock',
    'package-lock.json',
    'pnpm-lock.yaml',
    'pubspec.lock',
    'Cargo.lock',
}


def is_lockfile(filename):
    """Check if a filename or basename is a known lockfile."""
    base = os.path.basename(filename)
    return base in LOCKFILE_NAMES or base.endswith('.lock')


def extract_lockfile_manifest(filepath, content=None):
    """
    Extract a structured, human-and-LLM-readable dependency manifest from a lockfile.
    Returns: (manifest_text, total_packages_count)
    """
    basename = os.path.basename(filepath)
    if content is None:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return f"[Error reading lockfile: {e}]", 0

    packages = []

    # 1. uv.lock or poetry.lock (TOML structure)
    if basename in ('uv.lock', 'poetry.lock'):
        # Match [[package]] blocks
        pkg_blocks = re.split(r'(?=^\[\[package\]\])', content, flags=re.M)
        for block in pkg_blocks:
            name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
            ver_match = re.search(r'version\s*=\s*"([^"]+)"', block)
            if name_match and ver_match:
                packages.append((name_match.group(1), ver_match.group(1)))

    # 2. Cargo.lock (TOML structure)
    elif basename == 'Cargo.lock':
        pkg_blocks = re.split(r'(?=^\[\[package\]\])', content, flags=re.M)
        for block in pkg_blocks:
            name_match = re.search(r'name\s*=\s*"([^"]+)"', block)
            ver_match = re.search(r'version\s*=\s*"([^"]+)"', block)
            if name_match and ver_match:
                packages.append((name_match.group(1), ver_match.group(1)))

    # 3. package-lock.json (JSON structure)
    elif basename == 'package-lock.json':
        try:
            data = json.loads(content)
            # Modern npm v7+ packages map
            if 'packages' in data and isinstance(data['packages'], dict):
                for pkg_path, pkg_info in data['packages'].items():
                    if not pkg_path:  # root project
                        continue
                    clean_name = pkg_path.replace('node_modules/', '')
                    ver = pkg_info.get('version', '')
                    if clean_name and ver:
                        packages.append((clean_name, ver))
            # Legacy npm v6 dependencies map
            elif 'dependencies' in data and isinstance(data['dependencies'], dict):
                for name, info in data['dependencies'].items():
                    ver = info.get('version', '') if isinstance(info, dict) else ''
                    if name and ver:
                        packages.append((name, ver))
        except Exception:
            # Fallback regex
            for m in re.finditer(r'"([^"]+)":\s*\{\s*"version":\s*"([^"]+)"', content):
                packages.append((m.group(1), m.group(2)))

    # 4. pubspec.lock (YAML structure)
    elif basename == 'pubspec.lock':
        # Simple YAML regex extraction for packages
        pkg_matches = re.finditer(r'^\s{2}(\w[\w-]*):\s*\n\s+dependency:\s*"?([^"\n]+)"?\s*\n\s+description:\s*(?:.*\n)*?\s+version:\s*"([^"]+)"', content, re.M)
        for m in pkg_matches:
            name = m.group(1)
            dep_type = m.group(2).strip()
            ver = m.group(3).strip()
            packages.append((name, f"{ver} ({dep_type})"))
        if not packages:
            # Fallback simpler regex
            for m in re.finditer(r'^\s{2}(\w[\w-]*):[\s\S]*?version:\s*"([^"]+)"', content, re.M):
                packages.append((m.group(1), m.group(2)))

    # Sort packages alphabetically
    packages = sorted(list(set(packages)), key=lambda x: x[0].lower())
    total_count = len(packages)

    # Format into markdown manifest
    lines = [
        f"> [!NOTE]",
        f"> **Compact Dependency Manifest**: Extracted {total_count} resolved packages from `{basename}`.",
        f"> Full cryptographic integrity hashes and raw lock metadata omitted to preserve context window.",
        "",
        "| Package | Resolved Version |",
        "| :--- | :--- |",
    ]

    for name, ver in packages:
        lines.append(f"| `{name}` | `{ver}` |")

    if not packages:
        lines.append(f"| (No packages parsed) | - |")

    return '\n'.join(lines), total_count
