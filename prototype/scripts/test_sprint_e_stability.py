#!/usr/bin/env python3
"""
Sprint E Test: Stability + Forced Failure Tests

This script verifies:
1. Forced bond failure: spend then refund, no output item, last_error set
2. Forced holologue failure: spend then refund, no H item created
3. Credits balance returns to pre-spend balance after refunds
4. Event ordering: run_requested before failed
5. No new event names introduced

Run in an isolated temp store (never touches prototype/data/).

Usage:
    python prototype/scripts/test_sprint_e_stability.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import CANONICAL_EVENT_NAMES


def test_forced_bond_failure():
    """Test forced bond execution failure with refund."""
    print("\n" + "-" * 70)
    print("TEST 1: Forced Bond Failure")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)

        # Initialize
        cli.cmd_init()
        print(f"  Initialized. Credits: {cli._credits_balance}")
        assert cli._credits_balance == 100, "Initial credits should be 100"

        # Create 1 Q item
        item_id = cli.cmd_item_create(title="Test Item", body="Test body")
        print(f"  Created item: {item_id}")
        credits_after_item = cli._credits_balance
        assert credits_after_item == 101, "Credits after item creation should be 101"

        # Create bond draft
        bond_id = cli.cmd_bond_create(
            input_item_ids=[item_id],
            prompt_text="Test prompt",
        )
        print(f"  Created bond: {bond_id}")

        # Verify bond is draft
        bond_dict = cli.store.get_bond(bond_id)
        assert bond_dict["status"] == "draft", "Bond should be draft"
        assert bond_dict["output_item_id"] is None, "Bond should have no output item"

        # Record credits before run
        credits_before_run = cli._credits_balance
        print(f"  Credits before run: {credits_before_run}")

        # Run bond with force_fail=True
        result = cli.cmd_bond_run(bond_id, force_fail=True, fail_reason="test_forced_failure")

        # Verify return value is None (no output item)
        assert result is None, "Forced failure should return None"

        # Verify bond remains draft
        bond_dict = cli.store.get_bond(bond_id)
        assert bond_dict["status"] == "draft", "Bond should still be draft after failure"
        assert bond_dict["output_item_id"] is None, "Bond should still have no output item"

        # Verify last_error is set
        assert "last_error" in bond_dict, "Bond should have last_error set"
        assert bond_dict["last_error"]["message"] == "test_forced_failure", "Error message mismatch"
        print(f"  last_error set: {bond_dict['last_error']['message']}")

        # Verify no output item exists with this bond's provenance
        items = cli.store.load_items()
        bond_output_items = [
            i for i in items
            if i.get("provenance", {}).get("bond_id") == bond_id
        ]
        assert len(bond_output_items) == 0, "No output item should exist for failed bond"
        print("  No phantom output item created")

        # Verify credits returned to pre-run balance
        assert cli._credits_balance == credits_before_run, \
            f"Credits should be {credits_before_run}, got {cli._credits_balance}"
        print(f"  Credits returned to {credits_before_run} (spend + refund)")

        # Verify event order
        events = cli.store.load_events(episode_id=cli._episode_id)

        # Find run_requested and execution_failed events
        run_requested_events = [e for e in events if e["name"] == "bond.run_requested"]
        execution_failed_events = [e for e in events if e["name"] == "bond.execution_failed"]

        assert len(run_requested_events) == 1, "Should have 1 run_requested event"
        assert len(execution_failed_events) == 1, "Should have 1 execution_failed event"

        run_seq = run_requested_events[0]["seq"]
        failed_seq = execution_failed_events[0]["seq"]
        assert run_seq < failed_seq, "run_requested should come before execution_failed"
        print(f"  Event order verified: run_requested (seq={run_seq}) < execution_failed (seq={failed_seq})")

        # Verify credits.delta events include spend and refund
        credits_events = [e for e in events if e["name"] == "credits.delta"]
        spend_events = [e for e in credits_events if e["refs"]["reason"] == "bond_run_spend"]
        refund_events = [e for e in credits_events if e["refs"]["reason"] == "bond_run_refund"]

        assert len(spend_events) >= 1, "Should have spend event"
        assert len(refund_events) >= 1, "Should have refund event"

        # Verify refund delta is +10
        refund = refund_events[-1]
        assert refund["refs"]["delta"] == 10, "Refund delta should be +10"
        print(f"  Refund event verified: delta={refund['refs']['delta']}")

        print("  TEST 1 PASSED: Forced bond failure with refund")
        return True


def test_forced_holologue_failure():
    """Test forced holologue generation failure with refund."""
    print("\n" + "-" * 70)
    print("TEST 2: Forced Holologue Failure")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)

        # Initialize
        cli.cmd_init()
        print(f"  Initialized. Credits: {cli._credits_balance}")

        # Create 2 Q items (holologue needs at least 2)
        item1_id = cli.cmd_item_create(title="Item 1", body="Body 1")
        item2_id = cli.cmd_item_create(title="Item 2", body="Body 2")
        print(f"  Created items: {item1_id}, {item2_id}")

        credits_before_run = cli._credits_balance
        print(f"  Credits before run: {credits_before_run}")

        # Count H items before run
        items_before = cli.store.load_items()
        h_items_before = [i for i in items_before if i["type"] == "H"]
        print(f"  H items before: {len(h_items_before)}")

        # Run holologue with force_fail=True
        result = cli.cmd_holologue_run(
            selected_item_ids=[item1_id, item2_id],
            artifact_kind="plan",
            force_fail=True,
            fail_reason="test_generation_failed",
        )

        # Verify return value is None (no output item)
        assert result is None, "Forced failure should return None"

        # Verify no H item created
        items_after = cli.store.load_items()
        h_items_after = [i for i in items_after if i["type"] == "H"]
        assert len(h_items_after) == len(h_items_before), "No new H item should be created"
        print(f"  H items after: {len(h_items_after)} (no change)")

        # Verify credits returned to pre-run balance
        assert cli._credits_balance == credits_before_run, \
            f"Credits should be {credits_before_run}, got {cli._credits_balance}"
        print(f"  Credits returned to {credits_before_run} (spend + refund)")

        # Verify event order
        events = cli.store.load_events(episode_id=cli._episode_id)

        # Find run_requested and failed events
        run_requested_events = [e for e in events if e["name"] == "holologue.run_requested"]
        failed_events = [e for e in events if e["name"] == "holologue.failed"]

        assert len(run_requested_events) == 1, "Should have 1 run_requested event"
        assert len(failed_events) == 1, "Should have 1 failed event"

        run_seq = run_requested_events[0]["seq"]
        failed_seq = failed_events[0]["seq"]
        assert run_seq < failed_seq, "run_requested should come before failed"
        print(f"  Event order verified: run_requested (seq={run_seq}) < failed (seq={failed_seq})")

        # Verify failed event has correct reason
        assert failed_events[0]["refs"]["reason"] == "test_generation_failed", "Failed reason mismatch"

        # Verify credits.delta events include spend and refund
        credits_events = [e for e in events if e["name"] == "credits.delta"]
        spend_events = [e for e in credits_events if e["refs"]["reason"] == "holologue_run_spend"]
        refund_events = [e for e in credits_events if e["refs"]["reason"] == "holologue_run_refund"]

        assert len(spend_events) >= 1, "Should have spend event"
        assert len(refund_events) >= 1, "Should have refund event"

        # Verify refund delta is +20
        refund = refund_events[-1]
        assert refund["refs"]["delta"] == 20, "Refund delta should be +20"
        print(f"  Refund event verified: delta={refund['refs']['delta']}")

        print("  TEST 2 PASSED: Forced holologue failure with refund")
        return True


def test_no_new_event_names():
    """Verify no new event names introduced."""
    print("\n" + "-" * 70)
    print("TEST 3: No New Event Names")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)

        # Run through failure scenarios
        cli.cmd_init()
        item1 = cli.cmd_item_create(title="Item 1")
        item2 = cli.cmd_item_create(title="Item 2")

        # Forced bond failure
        bond_id = cli.cmd_bond_create([item1], "Test")
        cli.cmd_bond_run(bond_id, force_fail=True)

        # Forced holologue failure
        cli.cmd_holologue_run([item1, item2], force_fail=True)

        # Collect all event names
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = set(e["name"] for e in events)

        # Verify all are canonical
        non_canonical = event_names - set(CANONICAL_EVENT_NAMES)
        assert len(non_canonical) == 0, f"Non-canonical events found: {non_canonical}"

        print(f"  All {len(event_names)} event names are canonical:")
        for name in sorted(event_names):
            print(f"    - {name}")

        print("  TEST 3 PASSED: No new event names")
        return True


def test_validation_failure_no_spend():
    """Verify validation failure doesn't spend/refund."""
    print("\n" + "-" * 70)
    print("TEST 4: Validation Failure (no spend/refund)")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)

        cli.cmd_init()
        item1 = cli.cmd_item_create(title="Item 1")
        credits_before = cli._credits_balance
        print(f"  Credits before validation failure: {credits_before}")

        # Try to run holologue with only 1 item (should fail validation)
        try:
            cli.cmd_holologue_run([item1])
            assert False, "Should have exited"
        except SystemExit:
            pass  # Expected

        # Credits should be unchanged (no spend, no refund)
        # Note: CLI exits, so we need to check the store directly
        # Reload to get fresh balance
        cli2 = FieldKitCLI(data_dir)
        cli2._load_context()
        credits_after = cli2.store.compute_credits_balance(cli2._episode_id)
        print(f"  Credits after validation failure: {credits_after}")

        assert credits_after == credits_before, "Credits should be unchanged after validation failure"

        # Verify validation_failed event exists but no spend/refund
        events = cli2.store.load_events(episode_id=cli2._episode_id)
        validation_events = [e for e in events if e["name"] == "holologue.validation_failed"]
        assert len(validation_events) == 1, "Should have 1 validation_failed event"

        # No holologue spend/refund events
        credits_events = [e for e in events if e["name"] == "credits.delta"]
        holo_spend = [e for e in credits_events if e["refs"]["reason"] == "holologue_run_spend"]
        holo_refund = [e for e in credits_events if e["refs"]["reason"] == "holologue_run_refund"]

        assert len(holo_spend) == 0, "No holologue spend should occur on validation failure"
        assert len(holo_refund) == 0, "No holologue refund should occur on validation failure"

        print("  TEST 4 PASSED: Validation failure has no spend/refund")
        return True


def test_sprint_e_stability():
    """Run all Sprint E stability tests."""
    print("=" * 70)
    print("SPRINT E TEST: Stability + Forced Failure Tests")
    print("=" * 70)

    test_forced_bond_failure()
    test_forced_holologue_failure()
    test_no_new_event_names()
    test_validation_failure_no_spend()

    print("\n" + "=" * 70)
    print("SPRINT E TEST COMPLETE - ALL ASSERTIONS PASSED!")
    print("=" * 70)

    print("\nSummary:")
    print("  - Forced bond failure: VERIFIED")
    print("    - Bond remains draft, no output item")
    print("    - last_error set")
    print("    - Credits refunded (+10)")
    print("  - Forced holologue failure: VERIFIED")
    print("    - No H item created")
    print("    - Credits refunded (+20)")
    print("  - Event ordering: VERIFIED")
    print("  - No new event names: VERIFIED")
    print("  - Validation failure (no spend): VERIFIED")

    return True


if __name__ == "__main__":
    try:
        success = test_sprint_e_stability()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
