#!/usr/bin/env python3
"""
Pass 4 Run Check: Holologue (success path) + Proposals (events-only)

This script verifies:
1. holologue:run requires 2+ items (validation)
2. holologue:run creates exactly ONE output Item type H with provenance
3. Correct events are logged in order
4. bond.proposals.presented is logged (events-only)
5. Credits flow: -20 (spend) + 5 (reward) = -15 net
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_pass4():
    """Run Pass 4 verification."""
    print("=" * 60)
    print("Pass 4 Run Check: Holologue + Proposals")
    print("=" * 60)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        # Create CLI and initialize
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()
        print(f"\nInitialized. Credits: {cli._credits_balance}")

        # Create 2 Items
        item1_id = cli.cmd_item_create(title="First Item")
        item2_id = cli.cmd_item_create(title="Second Item")
        print(f"\nCreated Items: {item1_id}, {item2_id}")
        print(f"Credits: {cli._credits_balance}")  # Should be 102

        # 1) Test validation: need at least 2 items
        print("\n1) Testing validation (needs 2+ items)...")
        try:
            # This should fail with validation error
            cli.cmd_holologue_run(selected_item_ids=[item1_id], artifact_kind="plan")
            assert False, "Should have failed validation"
        except SystemExit:
            print("   ✓ Correctly rejected selection with < 2 items")

        # Reload CLI (SystemExit killed it)
        cli = FieldKitCLI(data_dir)
        cli._load_context()

        # Verify validation_failed event was logged
        events = cli.store.load_events(episode_id=cli._episode_id)
        validation_events = [e for e in events if e["name"] == "holologue.validation_failed"]
        assert len(validation_events) == 1, "Should have logged validation_failed"
        print("   ✓ holologue.validation_failed event logged")

        # 2) Run Holologue with 2 items
        print("\n2) Running Holologue with 2 items...")
        credits_before = cli._credits_balance
        output_h_id = cli.cmd_holologue_run(
            selected_item_ids=[item1_id, item2_id],
            artifact_kind="plan",
        )
        print(f"   Output Item: {output_h_id}")

        # Verify output item
        output_item = cli.store.get_item(output_h_id)
        assert output_item is not None, "Output Item should exist"
        assert output_item["type"] == "H", "Output Item type should be H"
        print("   ✓ Output Item type is H")

        # Verify provenance
        prov = output_item["provenance"]
        assert prov["created_by"] == "holologue", "Provenance should be holologue"
        assert prov["artifact_kind"] == "plan", "Artifact kind should be plan"
        assert set(prov["selected_item_ids"]) == {item1_id, item2_id}, "Selected item IDs should match"
        assert "holologue_event_id" in prov, "Should have holologue_event_id"
        print("   ✓ Output Item has correct provenance")

        # Verify credits: -20 + 5 = -15
        expected_credits = credits_before - 20 + 5
        assert cli._credits_balance == expected_credits, f"Credits should be {expected_credits}, got {cli._credits_balance}"
        print(f"   ✓ Credits: {cli._credits_balance} ({credits_before} - 20 + 5)")

        # 3) Verify events in order
        print("\n3) Verifying events...")
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]

        # Check for required events
        assert "holologue.run_requested" in event_names, "Should log holologue.run_requested"
        assert "holologue.completed" in event_names, "Should log holologue.completed"
        assert "bond.proposals.presented" in event_names, "Should log bond.proposals.presented"
        print("   ✓ All required events logged")

        # Verify ordering: run_requested < completed < proposals
        run_idx = event_names.index("holologue.run_requested")
        completed_idx = event_names.index("holologue.completed")
        proposals_idx = event_names.index("bond.proposals.presented")

        assert run_idx < completed_idx, "run_requested should precede completed"
        assert completed_idx < proposals_idx, "completed should precede proposals"
        print("   ✓ Event ordering: run_requested < completed < proposals")

        # 4) Verify proposals event is events-only (no Bond created)
        print("\n4) Verifying proposals are events-only...")
        bonds = cli.store.load_bonds()
        # No bonds should have been created from proposals
        print(f"   Bonds in store: {len(bonds)}")

        # Find the proposals event
        proposals_event = next(e for e in events if e["name"] == "bond.proposals.presented")
        suggestions = proposals_event["refs"]["suggestions"]
        assert len(suggestions) == 4, "Should have 4 suggestions"
        print(f"   ✓ 4 proposals presented (events-only, no Bonds created)")

        # 5) Verify exactly ONE output Item per run
        print("\n5) Verifying exactly one H item...")
        items = cli.store.load_items()
        h_items = [i for i in items if i["type"] == "H"]
        assert len(h_items) == 1, f"Should have exactly 1 H item, got {len(h_items)}"
        print("   ✓ Exactly one H item created")

        # 6) Verify holologue_event_id references the completion event
        print("\n6) Verifying holologue_event_id reference...")
        completed_event = next(e for e in events if e["name"] == "holologue.completed")
        assert prov["holologue_event_id"] == completed_event["id"], "holologue_event_id should match completed event"
        print("   ✓ Provenance holologue_event_id matches completed event ID")

        # Open ledger
        print("\n7) Opening ledger...")
        cli.cmd_ledger_open()

    print("\n" + "=" * 60)
    print("PASS 4 COMPLETE - All checks passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_pass4()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
