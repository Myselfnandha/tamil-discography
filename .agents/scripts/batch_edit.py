#!/usr/bin/env python3
"""
ZeroGravity OS: Atomic Batch File Editor (`batch_edit.py`)
==========================================================

Applies multiple edits to one or more files atomically from a single JSON spec.
Eliminates the agent anti-pattern of read→edit→re-read→edit→re-read→edit loops.

Usage:
    python3 batch_edit.py apply --spec edits.json
    python3 batch_edit.py apply --inline '<json>'
    python3 batch_edit.py validate --spec edits.json
    python3 batch_edit.py preview --spec edits.json

Spec format:
{
  "edits": [
    {
      "file": "src/pages/StockDetails.tsx",
      "replacements": [
        {
          "target": "exact string to find",
          "replacement": "new string to replace with",
          "description": "why this change"
        }
      ]
    }
  ]
}
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent


def load_spec(spec_path: Optional[str] = None, inline: Optional[str] = None) -> Dict:
    """Load edit spec from file or inline JSON string."""
    if inline:
        return json.loads(inline)
    if spec_path:
        with open(spec_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise ValueError("Must provide --spec or --inline")


def resolve_path(file_path: str) -> Path:
    """Resolve file path relative to workspace root."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return WORKSPACE_ROOT / p


def validate_spec(spec: Dict) -> List[str]:
    """Validate edit spec structure and targets. Returns list of errors."""
    errors = []

    if "edits" not in spec:
        errors.append("Missing 'edits' key in spec")
        return errors

    if not isinstance(spec["edits"], list):
        errors.append("'edits' must be a list")
        return errors

    for i, edit in enumerate(spec["edits"]):
        if "file" not in edit:
            errors.append(f"Edit [{i}]: missing 'file' key")
            continue

        file_path = resolve_path(edit["file"])
        if not file_path.exists():
            errors.append(f"Edit [{i}]: file not found: {file_path}")
            continue

        if "replacements" not in edit or not isinstance(edit["replacements"], list):
            errors.append(f"Edit [{i}] ({edit['file']}): missing or invalid 'replacements'")
            continue

        content = file_path.read_text(encoding="utf-8")

        for j, rep in enumerate(edit["replacements"]):
            if "target" not in rep:
                errors.append(f"Edit [{i}][{j}]: missing 'target'")
                continue
            if "replacement" not in rep:
                errors.append(f"Edit [{i}][{j}]: missing 'replacement'")
                continue

            target = rep["target"]
            occurrences = content.count(target)
            if occurrences == 0:
                # Show first 80 chars of target for debugging
                preview = target[:80].replace("\n", "\\n")
                errors.append(
                    f"Edit [{i}][{j}] ({edit['file']}): target not found: \"{preview}...\""
                )
            elif occurrences > 1 and not rep.get("allow_multiple", False):
                errors.append(
                    f"Edit [{i}][{j}] ({edit['file']}): target found {occurrences}x "
                    f"(set allow_multiple:true to replace all)"
                )

    return errors


def apply_edits(spec: Dict, dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """
    Apply all edits atomically.
    Returns: (files_changed, replacements_made, errors)
    """
    errors = validate_spec(spec)
    if errors:
        return 0, 0, errors

    files_changed = 0
    replacements_made = 0
    backup_map: Dict[str, str] = {}  # original_path -> backup_path

    try:
        for edit in spec["edits"]:
            file_path = resolve_path(edit["file"])
            content = file_path.read_text(encoding="utf-8")
            original_content = content

            # Create backup before modifying
            if not dry_run:
                backup_fd, backup_path = tempfile.mkstemp(
                    suffix=file_path.suffix,
                    prefix=f"bak_{file_path.stem}_",
                )
                os.close(backup_fd)
                shutil.copy2(str(file_path), backup_path)
                backup_map[str(file_path)] = backup_path

            for rep in edit["replacements"]:
                target = rep["target"]
                replacement = rep["replacement"]
                allow_multiple = rep.get("allow_multiple", False)

                if allow_multiple:
                    count = content.count(target)
                    content = content.replace(target, replacement)
                    replacements_made += count
                else:
                    # Replace only first occurrence
                    if target in content:
                        content = content.replace(target, replacement, 1)
                        replacements_made += 1

            if content != original_content:
                files_changed += 1
                if not dry_run:
                    # Atomic write
                    temp_fd, temp_path = tempfile.mkstemp(
                        dir=str(file_path.parent),
                        suffix=file_path.suffix,
                    )
                    try:
                        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                            f.write(content)
                            f.flush()
                            os.fsync(f.fileno())
                        os.replace(temp_path, str(file_path))
                    except Exception:
                        # Clean up temp file on failure
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                        raise

        # Success — remove backups
        if not dry_run:
            for backup_path in backup_map.values():
                try:
                    os.unlink(backup_path)
                except OSError:
                    pass

        return files_changed, replacements_made, []

    except Exception as e:
        # Rollback on failure
        if not dry_run:
            for original_path, backup_path in backup_map.items():
                try:
                    shutil.copy2(backup_path, original_path)
                    os.unlink(backup_path)
                except OSError:
                    pass
        return 0, 0, [f"ROLLBACK: {type(e).__name__}: {e}"]


def preview_edits(spec: Dict):
    """Show what would change without applying."""
    errors = validate_spec(spec)
    if errors:
        print("❌ Validation errors:")
        for e in errors:
            print(f"  • {e}")
        return

    print("\n📋 BATCH EDIT PREVIEW")
    print("=" * 60)

    for edit in spec["edits"]:
        file_path = resolve_path(edit["file"])
        print(f"\n📄 {edit['file']}")
        content = file_path.read_text(encoding="utf-8")

        for j, rep in enumerate(edit["replacements"]):
            target = rep["target"]
            replacement = rep["replacement"]
            desc = rep.get("description", "")

            # Count lines affected
            target_lines = target.count("\n") + 1
            replacement_lines = replacement.count("\n") + 1

            # Find line number of target
            before_target = content.split(target)[0]
            line_num = before_target.count("\n") + 1

            print(f"  [{j+1}] L{line_num}: -{target_lines} lines, +{replacement_lines} lines")
            if desc:
                print(f"      ℹ️  {desc}")

    total_replacements = sum(len(e.get("replacements", [])) for e in spec["edits"])
    total_files = len(spec["edits"])
    print(f"\n  Summary: {total_replacements} replacements across {total_files} file(s)")
    print("=" * 60 + "\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ZeroGravity OS Atomic Batch File Editor"
    )
    subparsers = parser.add_subparsers(dest="command")

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply batch edits atomically")
    p_apply.add_argument("--spec", help="Path to JSON edit spec file")
    p_apply.add_argument("--inline", help="Inline JSON edit spec string")
    p_apply.add_argument("--dry-run", action="store_true", help="Validate without applying")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate edit spec without applying")
    p_val.add_argument("--spec", help="Path to JSON edit spec file")
    p_val.add_argument("--inline", help="Inline JSON edit spec string")

    # preview
    p_pre = subparsers.add_parser("preview", help="Preview changes without applying")
    p_pre.add_argument("--spec", help="Path to JSON edit spec file")
    p_pre.add_argument("--inline", help="Inline JSON edit spec string")

    args = parser.parse_args()

    if args.command == "apply":
        spec = load_spec(args.spec, args.inline)
        files, reps, errors = apply_edits(spec, dry_run=args.dry_run)
        if errors:
            print("❌ Batch edit failed:")
            for e in errors:
                print(f"  • {e}")
            sys.exit(1)
        mode = "[DRY RUN] " if args.dry_run else ""
        print(f"✅ {mode}Batch edit complete: {files} file(s) changed, {reps} replacement(s) applied")

    elif args.command == "validate":
        spec = load_spec(args.spec, args.inline)
        errors = validate_spec(spec)
        if errors:
            print("❌ Validation failed:")
            for e in errors:
                print(f"  • {e}")
            sys.exit(1)
        total = sum(len(e.get("replacements", [])) for e in spec["edits"])
        print(f"✅ Spec valid: {len(spec['edits'])} file(s), {total} replacement(s)")

    elif args.command == "preview":
        spec = load_spec(args.spec, args.inline)
        preview_edits(spec)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
