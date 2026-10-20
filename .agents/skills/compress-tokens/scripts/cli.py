#!/usr/bin/env python3
"""
caveman-compress — Compress Markdown memory/context files to save tokens.
Usage:
    python .agents/skills/caveman-compress/scripts/cli.py <filepath>
"""
import os
import re
import sys
from pathlib import Path

FILLER_PHRASES = [
    (r"\bBasically,?\s*", ""),
    (r"\bIn order to\b", "To"),
    (r"\bIt is important to note that\b", "Note:"),
    (r"\bPlease note that\b", "Note:"),
    (r"\bKeep in mind that\b", "Note:"),
    (r"\bMake sure to\b", "Must"),
    (r"\bIt should be noted that\b", "Note:"),
    (r"\bAs mentioned previously,?\s*", ""),
    (r"\bAt the end of the day,?\s*", ""),
    (r"\bIn terms of\b", "For"),
    (r"\bDue to the fact that\b", "Because"),
    (r"\bFor the purpose of\b", "For"),
    (r"\bWith respect to\b", "Regarding"),
    (r"\bThere are a number of\b", "Several"),
    (r"\bA large number of\b", "Many"),
    (r"\bAt this point in time\b", "Now"),
]

def compress_line(line: str) -> str:
    # Preserve code fences, blockquotes markers, and tables verbatim
    stripped = line.strip()
    if stripped.startswith("```") or stripped.startswith("|") or stripped.startswith(">"):
        return line

    for pattern, replacement in FILLER_PHRASES:
        line = re.sub(pattern, replacement, line, flags=re.IGNORECASE)

    # Clean double spaces
    line = re.sub(r"[ \t]{2,}", " ", line)
    return line

def compress_file(filepath: Path) -> None:
    if not filepath.exists():
        print(f"❌ Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    backup_path = filepath.with_name(f"{filepath.stem}.original{filepath.suffix}")
    content = filepath.read_text(encoding="utf-8")

    # Create backup if not already present
    if not backup_path.exists():
        backup_path.write_text(content, encoding="utf-8")
        print(f"📦 Backup created: {backup_path}")

    lines = content.splitlines(keepends=True)
    in_code_block = False
    compressed_lines = []

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            compressed_lines.append(line)
            continue

        if in_code_block:
            compressed_lines.append(line)
        else:
            compressed_lines.append(compress_line(line))

    compressed_content = "".join(compressed_lines)
    filepath.write_text(compressed_content, encoding="utf-8")

    orig_len = len(content)
    new_len = len(compressed_content)
    saved = max(0, orig_len - new_len)
    pct = (saved / orig_len * 100) if orig_len > 0 else 0

    print(f"⚡ Compressed: {filepath} ({orig_len} → {new_len} chars, saved {pct:.1f}%)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python cli.py <filepath>")
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    compress_file(target)

if __name__ == "__main__":
    main()
