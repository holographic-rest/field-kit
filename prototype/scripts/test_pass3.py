#!/usr/bin/env python3
"""
Pass 3 Run Check: Create Bond (draft) + Run Bond (success path)

This script verifies:
1. bond:create creates draft Bond with status:"draft", output_item_id:null
2. bond:run creates output Item and updates Bond to executed
3. Correct events are logged in order
4. Credits flow: -10 (spend) + 3 (reward) = -7 net per bond run
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_pass3():
    """Run Pass 3 verification."""
    print("=" * 60)
    print("Pass 3 Run Check: Create Bond (draft) + Run Bond")
    print("=" * 60)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        # Create CLI and initialize
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()
        print(f"\nInitialized. Credits: {cli._credits_balance}")

        # Create Item 1
        item1_id = cli.cmd_item_create(title="My First Field Item")
        print(f"\nCreated Item 1: {item1_id}")
        print(f"Credits: {cli._credits_balance}")  # Should be 101

        # 1) Show suggestions (events-only)
        print("\n1) Showing suggestions...")
        suggestions = cli.cmd_suggestions_show(item1_id)
        assert len(suggestions) == 4, "Should show 4 suggestions"
        print(f"   ✓ 4 suggestions presented (events-only)")

        # Verify no Bond created
        bonds = cli.store.load_bonds()
        assert len(bonds) == 0, "No Bond should be created yet"
        print("   ✓ No Bond created (events-only)")

        # 2) Create Bond draft
        print("\n2) Creating Bond draft...")
        bond1_id = cli.cmd_bond_create(
            input_item_ids=[item1_id],
            prompt_text="Propose a minimal experiment to probe this.",
            intent_type="experiment",
        )
        print(f"   Bond created: {bond1_id}")

        # Verify Bond is draft
        bond_dict = cli.store.get_bond(bond1_id)
        assert bond_dict is not None, "Bond should exist"
        assert bond_dict["status"] == "draft", "Bond should be draft"
        assert bond_dict["output_item_id"] is None, "output_item_id should be null"
        assert bond_dict["input_item_ids"] == [item1_id], "input_item_ids should match"
        print("   ✓ Bond is draft, output_item_id is null")

        # Check credits (unchanged for draft creation)
        assert cli._credits_balance == 101, f"Credits should be 101, got {cli._credits_balance}"
        print(f"   ✓ Credits unchanged: {cli._credits_balance}")

        # 3) Run Bond (success path)
        print("\n3) Running Bond...")
        output1_id = cli.cmd_bond_run(bond1_id, output_type="M")
        print(f"   Output Item: {output1_id}")

        # Verify Bond is executed
        bond_dict = cli.store.get_bond(bond1_id)
        assert bond_dict["status"] == "executed", "Bond should be executed"
        assert bond_dict["output_item_id"] == output1_id, "output_item_id should be set"
        assert bond_dict["execution_count"] == 1, "execution_count should be 1"
        assert bond_dict["executed_at"] is not None, "executed_at should be set"
        print("   ✓ Bond is executed, output_item_id is set")

        # Verify output Item exists with provenance
        output_item = cli.store.get_item(output1_id)
        assert output_item is not None, "Output Item should exist"
        assert output_item["type"] == "M", "Output Item type should be M"
        assert output_item["provenance"]["created_by"] == "bond", "Provenance should be bond"
        assert output_item["provenance"]["bond_id"] == bond1_id, "Provenance bond_id should match"
        assert output_item["provenance"]["input_item_ids"] == [item1_id], "Provenance input_item_ids should match"
        print("   ✓ Output Item has correct provenance")

        # Check credits: 101 - 10 + 3 = 94
        assert cli._credits_balance == 94, f"Credits should be 94, got {cli._credits_balance}"
        print(f"   ✓ Credits: {cli._credits_balance} (101 - 10 + 3)")

        # 4) Verify events in order
        print("\n4) Verifying events...")
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]

        # Check for required events
        assert "bond.suggestions.presented" in event_names, "Should log bond.suggestions.presented"
        assert "bond.draft_created" in event_names, "Should log bond.draft_created"
        assert "bond.run_requested" in event_names, "Should log bond.run_requested"
        assert "bond.executed" in event_names, "Should log bond.executed"
        print("   ✓ All required events logged")

        # Verify ordering: run_requested before executed
        run_idx = event_names.index("bond.run_requested")
        exec_idx = event_names.index("bond.executed")
        assert run_idx < exec_idx, "bond.run_requested should precede bond.executed"
        print("   ✓ Event ordering: run_requested < executed")

        # 5) Create and run a second Bond (Q→D)
        print("\n5) Creating and running second Bond (Q→D)...")
        bond2_id = cli.cmd_bond_create(
            input_item_ids=[item1_id],
            prompt_text="Write a short decision note (5 bullets) that makes one clear choice based on Item 1.",
        )
        output2_id = cli.cmd_bond_run(bond2_id, output_type="D")
        print(f"   Bond 2: {bond2_id}")
        print(f"   Output 2: {output2_id}")

        # Verify output type is D
        output2_item = cli.store.get_item(output2_id)
        assert output2_item["type"] == "D", "Output Item type should be D"
        print("   ✓ Output Item 2 type is D")

        # Check credits: 94 - 10 + 3 = 87
        assert cli._credits_balance == 87, f"Credits should be 87, got {cli._credits_balance}"
        print(f"   ✓ Credits: {cli._credits_balance} (94 - 10 + 3)")

        # 6) Final verification
        print("\n6) Final verification...")
        items = cli.store.load_items()
        bonds = cli.store.load_bonds()

        assert len(items) == 3, f"Should have 3 items (Q, M, D), got {len(items)}"
        assert len(bonds) == 2, f"Should have 2 bonds, got {len(bonds)}"

        # Verify both bonds are executed
        for bond in bonds:
            assert bond["status"] == "executed", f"Bond {bond['id']} should be executed"
            assert bond["output_item_id"] is not None, f"Bond {bond['id']} should have output"

        print(f"   ✓ Items: {len(items)} (Q, M, D)")
        print(f"   ✓ Bonds: {len(bonds)} (both executed)")

        # Open ledger
        print("\n7) Opening ledger...")
        cli.cmd_ledger_open()

    print("\n" + "=" * 60)
    print("PASS 3 COMPLETE - All checks passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_pass3()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
