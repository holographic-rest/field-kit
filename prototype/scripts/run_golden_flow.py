#!/usr/bin/env python3
"""
Field-Kit v0.1 Demo Golden Flow

This script executes the complete Golden Flow from /docs/specs/05_demo_golden_flow_v0.1.md
and validates all requirements:

1. Items >= 5 (Q, Q, M, D, H)
2. Bonds >= 2 (both executed)
3. Event ordering constraints:
   - bond.run_requested precedes bond.executed
   - holologue.run_requested precedes holologue.completed
   - bond.proposals.presented after holologue.completed
4. Final credits balance == 73

Usage:
    python prototype/scripts/run_golden_flow.py [--data-dir PATH] [--fresh]

Options:
    --data-dir PATH  Data directory (default: prototype/data/ or FIELDKIT_DATA_DIR env var)
    --fresh          Archive existing JSONL files and start fresh
"""

import sys
import os
import argparse
import glob
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def get_default_data_dir() -> Path:
    """Get the default data directory from env var or fallback."""
    env_dir = os.environ.get("FIELDKIT_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent / "data"


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


def run_golden_flow(data_dir: Path = None):
    """
    Execute the Demo Golden Flow v0.1.

    Returns True if all assertions pass, raises AssertionError otherwise.
    """
    print("=" * 70)
    print("FIELD-KIT v0.1 — DEMO GOLDEN FLOW")
    print("=" * 70)

    cli = FieldKitCLI(data_dir)

    # === Step 1: Launch → Episode 0 created → Blank Field visible ===
    print("\n" + "─" * 70)
    print("STEP 1: Launch → Episode 0 created → Blank Field visible")
    print("─" * 70)

    cli.cmd_init()

    # Verify
    assert cli._network_id is not None, "Network should be created"
    assert cli._episode_id is not None, "Episode should be created"
    assert cli._credits_balance == 100, f"Credits should be 100 (seed), got {cli._credits_balance}"

    events = cli.store.load_events(episode_id=cli._episode_id)
    event_names = [e["name"] for e in events]
    assert "app.first_run.started" in event_names
    assert "episode.created" in event_names
    assert "credits.delta" in event_names
    assert "store.commit" in event_names

    print(f"✓ Episode created: {cli._episode_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 2: Start Guided Tutorial ===
    print("\n" + "─" * 70)
    print("STEP 2: Start Guided Tutorial")
    print("─" * 70)

    cli.cmd_tutorial_start()

    events = cli.store.load_events(episode_id=cli._episode_id)
    event_names = [e["name"] for e in events]
    assert "tutorial.started" in event_names

    print("✓ Tutorial started")

    # === Step 3: Create Item 1 (Q) ===
    print("\n" + "─" * 70)
    print("STEP 3: Create Item 1 (Q)")
    print("─" * 70)

    item1_id = cli.cmd_item_create(title="My First Field Item")
    assert cli._credits_balance == 101

    print(f"✓ Item 1: {item1_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 4: Create Item 2 (Q) ===
    print("\n" + "─" * 70)
    print("STEP 4: Create Item 2 (Q)")
    print("─" * 70)

    item2_id = cli.cmd_item_create(title="Second Field Item")
    assert cli._credits_balance == 102

    print(f"✓ Item 2: {item2_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 5: Suggested Bond prompts appear (events only) ===
    print("\n" + "─" * 70)
    print("STEP 5: Suggested Bond prompts appear (events only)")
    print("─" * 70)

    suggestions = cli.cmd_suggestions_show(item1_id)
    assert len(suggestions) == 4

    # Verify no Bond created
    bonds_count = len(cli.store.load_bonds())
    assert bonds_count == 0, "No Bond should be created yet"

    events = cli.store.load_events(episode_id=cli._episode_id)
    event_names = [e["name"] for e in events]
    assert "bond.suggestions.presented" in event_names

    print("✓ 4 suggestions presented (events-only)")
    print("✓ No Bond created")

    # === Step 6: Select suggestion → Create Bond draft → Run Bond → output Item M ===
    print("\n" + "─" * 70)
    print("STEP 6: Q→M via suggested Bond execution")
    print("─" * 70)

    # Create Bond from first suggestion
    bond1_id = cli.cmd_bond_create(
        input_item_ids=[item1_id],
        prompt_text=suggestions[0]["prompt_text"],
        intent_type=suggestions[0].get("intent_type"),
    )

    # Verify draft
    bond1 = cli.store.get_bond(bond1_id)
    assert bond1["status"] == "draft"
    assert bond1["output_item_id"] is None

    # Run Bond
    output_m_id = cli.cmd_bond_run(bond1_id, output_type="M")
    assert cli._credits_balance == 95  # 102 - 10 + 3

    # Verify executed
    bond1 = cli.store.get_bond(bond1_id)
    assert bond1["status"] == "executed"
    assert bond1["output_item_id"] == output_m_id

    # Verify output Item
    output_m = cli.store.get_item(output_m_id)
    assert output_m["type"] == "M"
    assert output_m["provenance"]["created_by"] == "bond"
    assert output_m["provenance"]["bond_id"] == bond1_id

    print(f"✓ Bond 1: {bond1_id}")
    print(f"✓ Output M: {output_m_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 7: Write Bond prompt → Create Bond draft → Run Bond → output Item D ===
    print("\n" + "─" * 70)
    print("STEP 7: Q→D via user-written Bond execution")
    print("─" * 70)

    # Create Bond with user-written prompt
    bond2_id = cli.cmd_bond_create(
        input_item_ids=[item2_id],
        prompt_text="Write a short decision note (5 bullets) that makes one clear choice based on Item 1.",
    )

    # Run Bond
    output_d_id = cli.cmd_bond_run(bond2_id, output_type="D")
    assert cli._credits_balance == 88  # 95 - 10 + 3

    # Verify output Item
    output_d = cli.store.get_item(output_d_id)
    assert output_d["type"] == "D"
    assert output_d["provenance"]["created_by"] == "bond"

    print(f"✓ Bond 2: {bond2_id}")
    print(f"✓ Output D: {output_d_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 8: Select constellation (2+ items) → Run Holologue → output Item H ===
    print("\n" + "─" * 70)
    print("STEP 8: (Q,Q)→H Holologue artifact creation")
    print("─" * 70)

    output_h_id = cli.cmd_holologue_run(
        selected_item_ids=[item1_id, item2_id],
        artifact_kind="plan",
    )
    assert cli._credits_balance == 73  # 88 - 20 + 5

    # Verify output Item
    output_h = cli.store.get_item(output_h_id)
    assert output_h["type"] == "H"
    assert output_h["provenance"]["created_by"] == "holologue"
    assert set(output_h["provenance"]["selected_item_ids"]) == {item1_id, item2_id}

    print(f"✓ Output H: {output_h_id}")
    print(f"✓ Credits: {cli._credits_balance}")

    # === Step 9: Holologue emits 4 proposals (events only) ===
    print("\n" + "─" * 70)
    print("STEP 9: Holologue proposals presented (events only)")
    print("─" * 70)

    events = cli.store.load_events(episode_id=cli._episode_id)
    event_names = [e["name"] for e in events]
    assert "bond.proposals.presented" in event_names

    proposals_event = next(e for e in events if e["name"] == "bond.proposals.presented")
    assert len(proposals_event["refs"]["suggestions"]) == 4

    print("✓ 4 proposals presented (events-only)")

    # === Step 10: Open Ledger → inspect Objects + Events ===
    print("\n" + "─" * 70)
    print("STEP 10: Ledger inspection (Queue/Inspect)")
    print("─" * 70)

    cli.cmd_ledger_open()

    # === FINAL ASSERTIONS ===
    print("\n" + "=" * 70)
    print("FINAL ASSERTIONS")
    print("=" * 70)

    # Load final state
    items = cli.store.load_items()
    bonds = cli.store.load_bonds()
    events = cli.store.load_events(episode_id=cli._episode_id)

    # 1) Items >= 5 (Q, Q, M, D, H)
    assert len(items) >= 5, f"Expected >= 5 items, got {len(items)}"
    item_types = sorted([i["type"] for i in items])
    assert item_types == ["D", "H", "M", "Q", "Q"], f"Expected [D,H,M,Q,Q], got {item_types}"
    print(f"✓ Items: {len(items)} (types: {item_types})")

    # 2) Bonds >= 2 (both executed)
    assert len(bonds) >= 2, f"Expected >= 2 bonds, got {len(bonds)}"
    for bond in bonds:
        assert bond["status"] == "executed", f"Bond {bond['id']} should be executed"
        assert bond["output_item_id"] is not None, f"Bond {bond['id']} should have output_item_id"
    print(f"✓ Bonds: {len(bonds)} (both executed)")

    # 3) Event ordering constraints
    event_names = [e["name"] for e in events]

    # bond.run_requested precedes bond.executed
    run_indices = [i for i, n in enumerate(event_names) if n == "bond.run_requested"]
    exec_indices = [i for i, n in enumerate(event_names) if n == "bond.executed"]
    for run_idx, exec_idx in zip(run_indices, exec_indices):
        assert run_idx < exec_idx, "bond.run_requested should precede bond.executed"
    print("✓ Event ordering: bond.run_requested < bond.executed")

    # holologue.run_requested precedes holologue.completed
    holo_run_idx = event_names.index("holologue.run_requested")
    holo_completed_idx = event_names.index("holologue.completed")
    assert holo_run_idx < holo_completed_idx, "holologue.run_requested should precede holologue.completed"
    print("✓ Event ordering: holologue.run_requested < holologue.completed")

    # bond.proposals.presented after holologue.completed
    proposals_idx = event_names.index("bond.proposals.presented")
    assert holo_completed_idx < proposals_idx, "bond.proposals.presented should occur after holologue.completed"
    print("✓ Event ordering: holologue.completed < bond.proposals.presented")

    # 4) Final credits balance == 73
    assert cli._credits_balance == 73, f"Expected credits 73, got {cli._credits_balance}"
    print(f"✓ Credits: {cli._credits_balance} (matches expected 73)")

    # Print success-path minimum events
    print("\n--- Success-path events found ---")
    success_events = [
        "app.first_run.started",
        "episode.created",
        "credits.delta",
        "tutorial.started",
        "item.created",
        "bond.suggestions.presented",
        "bond.draft_created",
        "bond.run_requested",
        "bond.executed",
        "holologue.run_requested",
        "holologue.completed",
        "bond.proposals.presented",
        "ledger.opened",
        "store.commit",
    ]
    for event_name in success_events:
        count = event_names.count(event_name)
        if count > 0:
            print(f"  ✓ {event_name} ({count}x)")
        else:
            print(f"  ✗ {event_name} (MISSING)")

    print("\n" + "=" * 70)
    print("GOLDEN FLOW COMPLETE — ALL ASSERTIONS PASSED!")
    print("=" * 70)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Field-Kit v0.1 Demo Golden Flow",
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=None,
        help="Data directory (default: prototype/data/ or FIELDKIT_DATA_DIR env var)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Archive existing JSONL files and start fresh",
    )
    args = parser.parse_args()

    # Determine data directory
    data_dir = args.data_dir or get_default_data_dir()

    # Handle --fresh flag
    if args.fresh:
        print("\n[--fresh] Archiving existing data...")
        archive_existing_data(data_dir)
        print()

    try:
        run_golden_flow(data_dir)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ ASSERTION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
