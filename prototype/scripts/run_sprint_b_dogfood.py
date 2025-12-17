#!/usr/bin/env python3
"""
Field-Kit v0.1 Sprint B Dogfood Runner

This script runs the Sprint B dogfood flow:
1. Init store (Episode 0) in prototype/data_dogfood/
2. Ingest all 27 architecture pages as Q Items
3. Run Bond on P02 (one-sentence definition)
4. Run Holologue on P01-P05 with artifact_kind="plan"
5. Run Bond on Holologue output
6. Open Ledger

Assertions:
- Final Item count >= 30 (27 Q + at least 3 generated)
- Final credits balance matches expected calculation

Usage:
    python prototype/scripts/run_sprint_b_dogfood.py [--fresh]

Options:
    --fresh  Archive existing data and start fresh
"""

import sys
import os
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from ingest_architecture_pages import run_ingestion, get_default_dogfood_data_dir


def archive_existing_data(data_dir: Path):
    """Archive existing JSONL files to data_archive/<timestamp>/"""
    jsonl_files = list(data_dir.glob("*.jsonl"))
    if not jsonl_files:
        print("No existing JSONL files to archive.")
        return

    # Create archive directory with timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = data_dir.parent / "data_archive" / ts
    archive_dir.mkdir(parents=True, exist_ok=True)

    print(f"Archiving {len(jsonl_files)} JSONL files to {archive_dir}/")
    for f in jsonl_files:
        shutil.move(str(f), str(archive_dir / f.name))
        print(f"  Moved: {f.name}")

    print("Archive complete. Starting fresh.")


def run_sprint_b_dogfood(data_dir: Path = None, fresh: bool = False):
    """
    Execute Sprint B dogfood flow.

    Returns True if all assertions pass.
    """
    print("=" * 70)
    print("FIELD-KIT v0.1 — SPRINT B DOGFOOD")
    print("=" * 70)

    # Resolve data directory
    if data_dir is None:
        data_dir = get_default_dogfood_data_dir()

    # Handle fresh flag
    if fresh and data_dir.exists():
        print("\n[--fresh] Archiving existing data...")
        archive_existing_data(data_dir)
        print()

    # === Step 1: Init store ===
    print("\n" + "-" * 70)
    print("STEP 1: Init store (Episode 0)")
    print("-" * 70)

    cli = FieldKitCLI(data_dir)
    cli.cmd_init()

    print(f"Network: {cli._network_id}")
    print(f"Episode: {cli._episode_id}")
    print(f"Credits: {cli._credits_balance}")

    # Track expected credits
    # Seed: +100
    expected_credits = 100
    assert cli._credits_balance == expected_credits

    # === Step 2: Ingest architecture pages ===
    print("\n" + "-" * 70)
    print("STEP 2: Ingest 27 architecture pages")
    print("-" * 70)

    # Note: We already have CLI initialized, so we'll call ingestion functions directly
    # but use the same CLI instance for proper episode tracking

    from ingest_architecture_pages import discover_pages, ingest_pages, write_index, SOURCE_DIR, OUTPUT_DIR

    pages = discover_pages(SOURCE_DIR)
    print(f"Discovered {len(pages)} pages")

    created_items = ingest_pages(cli, pages)
    print(f"Created {len(created_items)} Q Items")

    # Write index
    index_path = OUTPUT_DIR / "dogfood_architecture_index.json"
    write_index(created_items, index_path)

    # Credits: +1 per item = +27
    expected_credits += len(created_items)
    print(f"Credits: {cli._credits_balance} (expected {expected_credits})")
    assert cli._credits_balance == expected_credits, f"Expected {expected_credits}, got {cli._credits_balance}"

    # Find P02 item (one-sentence definition)
    p02_item = next((p for p in created_items if p["page_num"] == 2), None)
    assert p02_item is not None, "P02 not found"
    print(f"\nP02 Item ID: {p02_item['item_id']}")

    # Find P01-P05 items
    p01_to_p05 = [p for p in created_items if 1 <= p["page_num"] <= 5]
    p01_to_p05_ids = [p["item_id"] for p in sorted(p01_to_p05, key=lambda x: x["page_num"])]
    print(f"P01-P05 Item IDs: {p01_to_p05_ids}")

    # === Step 3: Run Bond on P02 ===
    print("\n" + "-" * 70)
    print("STEP 3: Run Bond on P02 (one-sentence definition)")
    print("-" * 70)

    # Create Bond with a synthesis prompt
    bond1_id = cli.cmd_bond_create(
        input_item_ids=[p02_item["item_id"]],
        prompt_text="Expand this one-sentence definition into a 3-paragraph executive summary suitable for technical stakeholders.",
    )
    print(f"Bond created: {bond1_id}")

    # Run Bond -> output M
    output_m1_id = cli.cmd_bond_run(bond1_id, output_type="M")
    print(f"Output M: {output_m1_id}")

    # Credits: -10 (spend) +3 (reward) = -7
    expected_credits += -10 + 3
    print(f"Credits: {cli._credits_balance} (expected {expected_credits})")
    assert cli._credits_balance == expected_credits

    # === Step 4: Run Holologue on P01-P05 ===
    print("\n" + "-" * 70)
    print("STEP 4: Run Holologue on P01-P05 (artifact_kind=plan)")
    print("-" * 70)

    output_h_id = cli.cmd_holologue_run(
        selected_item_ids=p01_to_p05_ids,
        artifact_kind="plan",
    )
    print(f"Output H: {output_h_id}")

    # Credits: -20 (spend) +5 (reward) = -15
    expected_credits += -20 + 5
    print(f"Credits: {cli._credits_balance} (expected {expected_credits})")
    assert cli._credits_balance == expected_credits

    # === Step 5: Run Bond on Holologue output ===
    print("\n" + "-" * 70)
    print("STEP 5: Run Bond on Holologue output")
    print("-" * 70)

    # Create Bond on the H output
    bond2_id = cli.cmd_bond_create(
        input_item_ids=[output_h_id],
        prompt_text="Create a decision document that prioritizes the top 3 action items from this plan.",
    )
    print(f"Bond created: {bond2_id}")

    # Run Bond -> output D
    output_d_id = cli.cmd_bond_run(bond2_id, output_type="D")
    print(f"Output D: {output_d_id}")

    # Credits: -10 (spend) +3 (reward) = -7
    expected_credits += -10 + 3
    print(f"Credits: {cli._credits_balance} (expected {expected_credits})")
    assert cli._credits_balance == expected_credits

    # === Step 6: Open Ledger ===
    print("\n" + "-" * 70)
    print("STEP 6: Open Ledger")
    print("-" * 70)

    cli.cmd_ledger_open()

    # === Final Assertions ===
    print("\n" + "=" * 70)
    print("FINAL ASSERTIONS")
    print("=" * 70)

    # Load final state
    items = cli.store.load_items()
    bonds = cli.store.load_bonds()
    events = cli.store.load_events(episode_id=cli._episode_id)

    # 1) Item count >= 30 (27 Q + 3 generated: M, H, D)
    expected_item_count = 27 + 3  # 27 Q items + M + H + D
    assert len(items) >= expected_item_count, f"Expected >= {expected_item_count} items, got {len(items)}"
    print(f"Items: {len(items)} (27 Q + 3 generated)")

    # Count by type
    type_counts = {}
    for item in items:
        t = item["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  Types: {type_counts}")

    # Verify we have expected types
    assert type_counts.get("Q", 0) == 27, f"Expected 27 Q items, got {type_counts.get('Q', 0)}"
    assert type_counts.get("M", 0) >= 1, f"Expected at least 1 M item"
    assert type_counts.get("H", 0) >= 1, f"Expected at least 1 H item"
    assert type_counts.get("D", 0) >= 1, f"Expected at least 1 D item"

    # 2) Bonds == 2 (both executed)
    assert len(bonds) == 2, f"Expected 2 bonds, got {len(bonds)}"
    for bond in bonds:
        assert bond["status"] == "executed", f"Bond {bond['id']} should be executed"
    print(f"Bonds: {len(bonds)} (both executed)")

    # 3) Credits balance
    # Expected: 100 (seed) + 27 (items) - 7 (bond1) - 15 (holologue) - 7 (bond2) = 98
    final_expected_credits = 100 + 27 - 7 - 15 - 7
    assert cli._credits_balance == final_expected_credits, f"Expected {final_expected_credits} credits, got {cli._credits_balance}"
    print(f"Credits: {cli._credits_balance} (expected {final_expected_credits})")

    # 4) Verify derived balance from store
    derived = cli.store.compute_credits_balance(cli._episode_id)
    assert derived == final_expected_credits, f"Derived balance should be {final_expected_credits}, got {derived}"
    print(f"Derived balance: {derived}")

    # Print success-path events
    print("\n--- Success-path events ---")
    event_names = [e["name"] for e in events]
    for name in sorted(set(event_names)):
        count = event_names.count(name)
        print(f"  {name}: {count}x")

    print("\n" + "=" * 70)
    print("SPRINT B DOGFOOD COMPLETE — ALL ASSERTIONS PASSED!")
    print("=" * 70)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Field-Kit v0.1 Sprint B Dogfood Runner",
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=None,
        help="Data directory (default: prototype/data_dogfood/)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Archive existing JSONL files and start fresh",
    )
    args = parser.parse_args()

    try:
        run_sprint_b_dogfood(args.data_dir, args.fresh)
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
