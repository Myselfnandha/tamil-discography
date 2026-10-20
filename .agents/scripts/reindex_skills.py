#!/usr/bin/env python3
"""
reindex_skills.py — Dynamic Skill Registry Indexer for Antigravity.

Scans all skill directories across .agents/plugins/ and .agents/skills/,
parses their SKILL.md frontmatter, verifies their existence on disk, and
generates an accurate, canonical skills_index.json with exact relative paths.

Zero external dependencies. Uses only Python stdlib.
"""

import os
import sys
import re
import json


def parse_skill_frontmatter(skill_md_path):
    """Extract metadata from a SKILL.md frontmatter block."""
    info = {
        'name': os.path.basename(os.path.dirname(skill_md_path)),
        'description': '',
        'category': 'general',
        'risk': 'safe',
        'date_added': '2026-03-01',
    }
    try:
        with open(skill_md_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                for line in frontmatter.splitlines():
                    line = line.strip()
                    if line.startswith('name:'):
                        info['name'] = line.split(':', 1)[1].strip().strip('"\'')
                    elif line.startswith('description:'):
                        info['description'] = line.split(':', 1)[1].strip().strip('"\'')
                    elif line.startswith('category:'):
                        info['category'] = line.split(':', 1)[1].strip().strip('"\'')
                    elif line.startswith('risk:'):
                        info['risk'] = line.split(':', 1)[1].strip().strip('"\'')
                    elif line.startswith('date_added:'):
                        info['date_added'] = line.split(':', 1)[1].strip().strip('"\'')

        if not info['description']:
            # Fallback: first non-empty header/paragraph
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('---'):
                    info['description'] = line[:150]
                    break
    except Exception as e:
        info['description'] = f"[Error parsing skill: {e}]"

    return info


def reindex_all_skills(agents_root):
    """Scan and index all skills under the canonical .agents root."""
    agents_root = os.path.abspath(agents_root)
    output_index_path = os.path.join(agents_root, 'skills_index.json')

    skills = []
    seen_ids = set()

    # Walk plugins and skills directories
    search_dirs = [
        os.path.join(agents_root, 'plugins'),
        os.path.join(agents_root, 'skills'),
    ]

    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            if 'SKILL.md' in files:
                skill_md = os.path.join(root, 'SKILL.md')
                rel_skill_dir = os.path.relpath(root, agents_root).replace('\\', '/')
                meta = parse_skill_frontmatter(skill_md)

                skill_id = meta['name'] or os.path.basename(root)
                if skill_id in seen_ids:
                    # Make unique by scoping with parent plugin
                    parent_scope = rel_skill_dir.split('/')[1] if 'plugins/' in rel_skill_dir else ''
                    if parent_scope:
                        skill_id = f"{parent_scope}:{skill_id}"

                seen_ids.add(skill_id)

                skills.append({
                    'id': skill_id,
                    'path': rel_skill_dir,
                    'name': meta['name'],
                    'description': meta['description'],
                    'category': meta['category'],
                    'risk': meta['risk'],
                    'date_added': meta['date_added'],
                })

    skills.sort(key=lambda s: s['id'].lower())

    with open(output_index_path, 'w', encoding='utf-8') as f:
        json.dump(skills, f, indent=2)

    print(f"Success: Indexed {len(skills)} skills into {output_index_path}")
    return len(skills)


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    count = reindex_all_skills(root)
    sys.exit(0 if count > 0 else 1)
