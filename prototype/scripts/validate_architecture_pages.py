#!/usr/bin/env python3
"""
Architecture Page Validator

Validates docs/architecture/field_overview/*.md files for expected format:
- Line 1 should match: PAGE <n> – ...
- Must contain a Title: line

Default behavior: report warnings, exit 0
With --strict: exit 1 on any violations

Usage:
    python prototype/scripts/validate_architecture_pages.py
    python prototype/scripts/validate_architecture_pages.py --strict
"""

import sys
import re
import argparse
from pathlib import Path


SOURCE_DIR = Path(__file__).parent.parent.parent / "docs" / "architecture" / "field_overview"


def validate_page(file_path: Path) -> list:
    """
    Validate a single architecture page.

    Returns list of warning messages (empty if valid).
    """
    warnings = []

    content = file_path.read_text()
    lines = content.split("\n")

    if not lines:
        warnings.append(f"{file_path.name}: File is empty")
        return warnings

    # Check line 1: PAGE <n> – ...
    line1 = lines[0] if lines else ""
    page_pattern = r'^PAGE\s+\d+\s*[–-]'
    if not re.match(page_pattern, line1):
        warnings.append(f"{file_path.name}: Line 1 does not match 'PAGE <n> – ...' format")
        warnings.append(f"  Got: {line1[:50]}...")

    # Check for Title: line
    has_title = any(line.strip().startswith("Title:") for line in lines)
    if not has_title:
        warnings.append(f"{file_path.name}: Missing 'Title:' line")

    return warnings


def main():
    parser = argparse.ArgumentParser(
        description="Validate architecture page format",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any violations",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ARCHITECTURE PAGE VALIDATOR")
    print("=" * 60)
    print(f"Source: {SOURCE_DIR}")
    print()

    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return 1

    md_files = sorted(SOURCE_DIR.glob("*.md"))
    print(f"Found {len(md_files)} markdown files")
    print()

    all_warnings = []
    valid_count = 0
    invalid_count = 0

    for file_path in md_files:
        warnings = validate_page(file_path)
        if warnings:
            invalid_count += 1
            all_warnings.extend(warnings)
            print(f"[WARN] {file_path.name}")
            for w in warnings:
                if not w.startswith("  "):
                    print(f"       {w}")
        else:
            valid_count += 1
            print(f"[OK]   {file_path.name}")

    print()
    print("-" * 60)
    print(f"Valid: {valid_count}")
    print(f"With warnings: {invalid_count}")
    print("-" * 60)

    if all_warnings:
        print()
        print("WARNINGS:")
        for w in all_warnings:
            print(f"  {w}")

    if args.strict and all_warnings:
        print()
        print("STRICT MODE: Exiting with error due to warnings")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
