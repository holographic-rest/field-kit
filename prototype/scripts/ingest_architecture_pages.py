#!/usr/bin/env python3
"""
Field-Kit v0.1 Architecture Pages Ingestion Script

Ingests the 27 architecture pages from docs/architecture/field_overview/
as Q Items into the Field-Kit store.

Source directory: docs/architecture/field_overview/
Output: prototype/outputs/dogfood_architecture_index.json

Page parsing rules:
- Line 1: PAGE <n> – <subtitle>
- Line 3: Title: <title>
- Rest: body content (raw markdown)

Usage:
    python prototype/scripts/ingest_architecture_pages.py [--data-dir PATH]
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


# Source directory for architecture pages
SOURCE_DIR = Path(__file__).parent.parent.parent / "docs" / "architecture" / "field_overview"

# Output directory for index
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def get_default_dogfood_data_dir() -> Path:
    """Get the default dogfood data directory."""
    env_dir = os.environ.get("FIELDKIT_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent / "data_dogfood"


def parse_page(file_path: Path) -> Optional[Dict]:
    """
    Parse an architecture page markdown file.

    Returns dict with: page_num, title, subtitle, body, filename
    Returns None if file is empty or unparseable.

    Format expected:
    - Line 1: PAGE <n> – <subtitle>
    - Line 3: Title: <title>
    - Rest: body

    Fallback: If PAGE header missing, extract page number from filename (e.g., 03_xxx.md -> 3)
    """
    content = file_path.read_text().strip()
    if not content:
        return None

    lines = content.split('\n')
    if len(lines) < 1:
        return None

    # Parse PAGE <n> – <subtitle> from line 1
    page_match = re.match(r'^PAGE\s+(\d+)\s*[–-]\s*(.*)$', lines[0])

    if page_match:
        # Standard format with PAGE header
        page_num = int(page_match.group(1))
        subtitle = page_match.group(2).strip()
        title_line_idx = 2  # Title on line 3 (index 2)
        body_start = 3
    else:
        # Fallback: extract page number from filename (e.g., 03_field_five_layers.md)
        filename_match = re.match(r'^(\d+)_', file_path.name)
        if not filename_match:
            return None
        page_num = int(filename_match.group(1))
        subtitle = ""
        title_line_idx = 0  # Title might be on line 1 if no PAGE header
        body_start = 1

    # Parse Title: <title>
    title_line = lines[title_line_idx] if len(lines) > title_line_idx else ""
    title_match = re.match(r'^Title:\s*(.*)$', title_line)
    if title_match:
        title = title_match.group(1).strip()
        # Body starts after title line (skip blank line if present)
        body_start = title_line_idx + 1
        if len(lines) > body_start and lines[body_start].strip() == "":
            body_start += 1
    else:
        # If no title line, use subtitle or page number
        title = subtitle or f"Page {page_num}"

    body = '\n'.join(lines[body_start:]).strip() if len(lines) > body_start else ""

    return {
        "page_num": page_num,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "filename": file_path.name,
        "raw_markdown": content,
    }


def discover_pages(source_dir: Path) -> List[Dict]:
    """
    Discover and parse all architecture pages.

    Returns list of parsed pages sorted by page_num.
    """
    pages = []

    for file_path in sorted(source_dir.glob("*.md")):
        parsed = parse_page(file_path)
        if parsed:
            pages.append(parsed)
        else:
            print(f"  [SKIP] {file_path.name} (empty or unparseable)")

    # Sort by page number
    pages.sort(key=lambda p: p["page_num"])
    return pages


def ingest_pages(cli: FieldKitCLI, pages: List[Dict]) -> List[Dict]:
    """
    Ingest parsed pages as Q Items.

    Returns list of created items with item_id added.
    """
    created_items = []

    for page in pages:
        # Create item with page number in title
        item_title = f"P{page['page_num']:02d}: {page['title']}"

        # Body is the raw markdown content
        item_body = page["raw_markdown"]

        # Create the item
        item_id = cli.cmd_item_create(title=item_title, body=item_body)

        # Add item_id to page record
        page["item_id"] = item_id
        created_items.append(page)

        print(f"  [OK] {item_title} -> {item_id}")

    return created_items


def write_index(items: List[Dict], output_path: Path):
    """Write the index JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create index with essential fields
    index = {
        "total_pages": len(items),
        "pages": [
            {
                "page_num": item["page_num"],
                "title": item["title"],
                "item_id": item["item_id"],
                "filename": item["filename"],
            }
            for item in items
        ]
    }

    with open(output_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\nIndex written to: {output_path}")


def verify_first_five_titles(items: List[Dict]):
    """
    Verify the first five extracted titles match expected values.

    Expected (pages 1-5):
    - P01: FIELD – Purpose of the Field Overview
    - P02: FIELD – One-Sentence Definition
    - P03: FIELD – The Five Layers
    - P04: L0 – Math & Metal: Core Concepts
    - P05: L0 – Math & Metal: Physics of the Field
    """
    expected_titles = [
        "FIELD – Purpose of the Field Overview",
        "FIELD – One-Sentence Definition",
        "FIELD – The Five Layers",
        "L0 – Math & Metal: Core Concepts",
        "L0 – Math & Metal: Physics of the Field",
    ]

    first_five = items[:5]

    print("\nVerifying first five titles...")
    all_match = True
    for i, (item, expected) in enumerate(zip(first_five, expected_titles)):
        actual = item["title"]
        match = actual == expected
        status = "OK" if match else "MISMATCH"
        print(f"  [{status}] P{item['page_num']:02d}: {actual}")
        if not match:
            print(f"         Expected: {expected}")
            all_match = False

    assert all_match, "First five titles do not match expected values"
    print("All first five titles verified!")


def run_ingestion(data_dir: Path = None) -> List[Dict]:
    """
    Run the full ingestion pipeline.

    Returns list of created items.
    """
    print("=" * 70)
    print("FIELD-KIT v0.1 — ARCHITECTURE PAGES INGESTION")
    print("=" * 70)

    # Resolve data directory
    if data_dir is None:
        data_dir = get_default_dogfood_data_dir()

    print(f"\nSource: {SOURCE_DIR}")
    print(f"Data dir: {data_dir}")

    # Create CLI (will init store but not emit init events)
    cli = FieldKitCLI(data_dir)

    # Discover pages
    print(f"\nDiscovering pages...")
    pages = discover_pages(SOURCE_DIR)
    print(f"Found {len(pages)} parseable pages")

    # Verify source directory has expected content (27 pages)
    assert len(pages) >= 27, f"Expected at least 27 pages, found {len(pages)}"

    # Ingest as Q Items
    print(f"\nIngesting pages as Q Items...")
    created_items = ingest_pages(cli, pages)
    print(f"\nCreated {len(created_items)} Items")

    # Write index
    index_path = OUTPUT_DIR / "dogfood_architecture_index.json"
    write_index(created_items, index_path)

    # Verify first five titles
    verify_first_five_titles(created_items)

    # Print credits
    print(f"\nCredits balance: {cli._credits_balance}")

    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)

    return created_items


def main():
    parser = argparse.ArgumentParser(
        description="Field-Kit v0.1 Architecture Pages Ingestion",
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=None,
        help="Data directory (default: prototype/data_dogfood/)",
    )
    args = parser.parse_args()

    try:
        run_ingestion(args.data_dir)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
