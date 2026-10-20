#!/usr/bin/env python3
"""
ZeroGravity OS: Impact Analysis & Blast Radius Tool (`impact_check.py`)
======================================================================
Finds all references, callers, and downstream consumers of a symbol or file
to prevent multi-file inconsistency and out-of-scope breaking changes.

Usage:
    python3 impact_check.py <symbol> [--workspace <path>]
    python3 impact_check.py --file <path> [--workspace <path>]
    python3 impact_check.py <symbol> --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

DEFAULT_EXCLUDES = {
    ".agents",
    ".agent",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".json", ".md", ".yml", ".yaml", ".sh", ".bash",
    ".html", ".css", ".scss", ".sql", ".rs", ".go", ".c", ".cpp", ".h"
}


def is_binary_file(file_path: Path) -> bool:
    """Quick heuristic to determine if file is binary."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
        return False
    except Exception:
        return True


def should_skip_path(path: Path, workspace: Path, custom_excludes: Set[str], base_excludes: Optional[Set[str]] = None) -> bool:
    """Check if file or directory should be skipped based on excludes."""
    rel = path.relative_to(workspace)
    parts = set(rel.parts)
    active_base = DEFAULT_EXCLUDES if base_excludes is None else base_excludes
    if parts & (active_base | custom_excludes):
        return True
    return False


def extract_symbols_from_file(file_path: Path) -> List[str]:
    """Extract exported/defined symbols from a Python, JS/TS, or source file."""
    if not file_path.exists() or is_binary_file(file_path):
        return []

    symbols: Set[str] = set()
    suffix = file_path.suffix.lower()

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    if suffix == ".py":
        # Python: def, class, __all__, UPPERCASE_CONSTANTS
        all_match = re.search(r"__all__\s*=\s*\[([^\]]+)\]", content)
        if all_match:
            for item in re.findall(r"['\"]([a-zA-Z0-9_]+)['\"]", all_match.group(1)):
                symbols.add(item)

        for match in re.finditer(r"^(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(", content, re.MULTILINE):
            name = match.group(1)
            if not name.startswith("_") or name.startswith("__") and name.endswith("__"):
                symbols.add(name)

        for match in re.finditer(r"^class\s+([a-zA-Z0-9_]+)\b", content, re.MULTILINE):
            symbols.add(match.group(1))

        for match in re.finditer(r"^([A-Z][A-Z0-9_]{2,})\s*=", content, re.MULTILINE):
            symbols.add(match.group(1))

    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        # JS/TS: export function, export const/let/var, export class/interface/type
        for match in re.finditer(r"export\s+(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)", content):
            symbols.add(match.group(1))

        for match in re.finditer(r"export\s+(?:const|let|var)\s+([a-zA-Z0-9_$]+)", content):
            symbols.add(match.group(1))

        for match in re.finditer(r"export\s+(?:class|interface|type|enum)\s+([a-zA-Z0-9_$]+)", content):
            symbols.add(match.group(1))

        # module.exports / exports.foo
        for match in re.finditer(r"exports\.([a-zA-Z0-9_$]+)\s*=", content):
            symbols.add(match.group(1))

        mod_exports = re.search(r"module\.exports\s*=\s*\{([^}]+)\}", content)
        if mod_exports:
            for item in re.findall(r"([a-zA-Z0-9_$]+)", mod_exports.group(1)):
                symbols.add(item)

    else:
        # Generic heuristic: function or class declarations
        for match in re.finditer(r"\b(?:func|fn|function|class)\s+([a-zA-Z0-9_]+)\b", content):
            symbols.add(match.group(1))

    return sorted(list(symbols))


def find_symbol_references(
    workspace: Path,
    symbol: str,
    custom_excludes: Optional[Set[str]] = None,
    ignore_file: Optional[Path] = None,
    base_excludes: Optional[Set[str]] = None
) -> List[Dict[str, any]]:
    """
    Search workspace for all occurrences of the exact symbol as a word token.
    Returns a list of match dicts: {'file': rel_path, 'line': line_no, 'content': line_text}
    """
    excludes = custom_excludes or set()
    matches: List[Dict[str, any]] = []
    pattern = re.compile(rf"\b{re.escape(symbol)}\b")

    for root, dirs, files in os.walk(workspace):
        root_path = Path(root)
        if should_skip_path(root_path, workspace, excludes, base_excludes):
            dirs.clear()
            continue

        dirs[:] = [d for d in dirs if not should_skip_path(root_path / d, workspace, excludes, base_excludes)]

        for file_name in files:
            file_path = root_path / file_name
            if should_skip_path(file_path, workspace, excludes, base_excludes):
                continue
            if ignore_file and file_path.resolve() == ignore_file.resolve():
                continue
            if file_path.suffix.lower() not in TEXT_EXTENSIONS and not is_binary_file(file_path):
                # allow scanning text files without standard extension if not binary
                pass
            elif file_path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            try:
                rel_path = str(file_path.relative_to(workspace))
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, start=1):
                        if pattern.search(line):
                            matches.append({
                                "file": rel_path,
                                "line": line_no,
                                "content": line.strip()
                            })
            except Exception:
                continue

    return matches


def analyze_file_impact(
    workspace: Path,
    file_path: Path,
    custom_excludes: Optional[Set[str]] = None,
    base_excludes: Optional[Set[str]] = None
) -> Dict[str, any]:
    """Extract symbols from file and find downstream impact across workspace."""
    resolved_file = file_path.resolve()
    symbols = extract_symbols_from_file(resolved_file)
    rel_target = str(resolved_file.relative_to(workspace)) if resolved_file.is_relative_to(workspace) else str(resolved_file)

    impact_by_symbol: Dict[str, List[Dict[str, any]]] = {}
    affected_files: Set[str] = set()

    for sym in symbols:
        refs = find_symbol_references(workspace, sym, custom_excludes, ignore_file=resolved_file, base_excludes=base_excludes)
        if refs:
            impact_by_symbol[sym] = refs
            for r in refs:
                affected_files.add(r["file"])

    return {
        "target_file": rel_target,
        "exported_symbols": symbols,
        "affected_files_count": len(affected_files),
        "affected_files": sorted(list(affected_files)),
        "symbol_references": impact_by_symbol
    }


def main():
    parser = argparse.ArgumentParser(
        description="ZeroGravity OS Impact Analysis & Blast Radius Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", nargs="?", help="Symbol (function, class, constant) to search for")
    parser.add_argument("--file", "-f", help="Target file to analyze for downstream impact")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace root directory (default: .)")
    parser.add_argument("--exclude", "-e", action="append", default=[], help="Additional directories to exclude")
    parser.add_argument("--include-agents", action="store_true", help="Include .agents and .agent directories in scan")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    custom_excludes = set(args.exclude)

    base_excludes = set(DEFAULT_EXCLUDES)
    if args.include_agents:
        base_excludes -= {".agents", ".agent"}


    if not args.symbol and not args.file:
        parser.print_help()
        sys.exit(1)

    if args.file:
        target_path = Path(args.file)
        if not target_path.is_absolute():
            target_path = (workspace / target_path).resolve()

        if not target_path.exists():
            print(f"Error: Target file not found: {target_path}", file=sys.stderr)
            sys.exit(1)

        result = analyze_file_impact(workspace, target_path, custom_excludes, base_excludes=base_excludes)

        if args.json:
            print(json.dumps(result, indent=2))
            return

        print("\n" + "=" * 70)
        print(f"🎯 IMPACT ANALYSIS: {result['target_file']}")
        print("=" * 70)
        print(f"Exported / Defined Symbols ({len(result['exported_symbols'])}):")
        for sym in result["exported_symbols"]:
            ref_count = len(result["symbol_references"].get(sym, []))
            print(f"  • {sym} -> {ref_count} downstream reference(s)")

        print(f"\nDownstream Consumer Files Affected: {result['affected_files_count']}")
        for af in result["affected_files"]:
            print(f"  📁 {af}")

        print("\nDetailed References:")
        for sym, refs in result["symbol_references"].items():
            print(f"\n  [{sym}]")
            for r in refs:
                print(f"    {r['file']}:{r['line']}  ->  {r['content']}")
        print("\n" + "=" * 70 + "\n")

    elif args.symbol:
        sym = args.symbol
        refs = find_symbol_references(workspace, sym, custom_excludes, base_excludes=base_excludes)

        if args.json:
            print(json.dumps({
                "symbol": sym,
                "total_references": len(refs),
                "references": refs
            }, indent=2))
            return

        print("\n" + "=" * 70)
        print(f"🔍 SYMBOL IMPACT SEARCH: '{sym}'")
        print("=" * 70)
        print(f"Total References Found: {len(refs)}\n")

        # Group by file
        by_file: Dict[str, List[Tuple[int, str]]] = {}
        for r in refs:
            by_file.setdefault(r["file"], []).append((r["line"], r["content"]))

        for f_path, occurrences in by_file.items():
            print(f"📁 {f_path} ({len(occurrences)} matches):")
            for line_no, content in occurrences:
                print(f"  L{line_no}: {content}")
            print()
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
