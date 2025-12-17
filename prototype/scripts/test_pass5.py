#!/usr/bin/env python3
"""
Pass 5 Run Check: Credits (simulation) as derived view

This script verifies:
1. Credits are computed from credits.delta events
2. balance_after follows the policy exactly
3. All credit operations have proper reasons
4. Derived balance matches expected final state
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_pass5():
    """Run Pass 5 verification."""
    print("=" * 60)
    print("Pass 5 Run Check: Credits (simulation) as derived view")
    print("=" * 60)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        # Create CLI and initialize
        cli = FieldKitCLI(data_dir)

        # Track expected credits step by step
        expected = 0

        # 1) Init: seed +100
        print("\n1) Init...")
        cli.cmd_init()
        expected = 100
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ Seed: +100 (balance={cli._credits_balance})")

        # 2) Item 1: +1
        print("\n2) Create Item 1...")
        item1_id = cli.cmd_item_create(title="Item 1")
        expected += 1  # 101
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ item_created: +1 (balance={cli._credits_balance})")

        # 3) Item 2: +1
        print("\n3) Create Item 2...")
        item2_id = cli.cmd_item_create(title="Item 2")
        expected += 1  # 102
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ item_created: +1 (balance={cli._credits_balance})")

        # 4) Bond 1: -10 (spend) + 3 (reward) = -7
        print("\n4) Create and run Bond 1 (Q→M)...")
        bond1_id = cli.cmd_bond_create([item1_id], "Test prompt")
        # No credits change for draft
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ Draft created: no change (balance={cli._credits_balance})")

        cli.cmd_bond_run(bond1_id, "M")
        expected += -10 + 3  # 95
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ Bond run: -10, executed: +3 (balance={cli._credits_balance})")

        # 5) Bond 2: -10 (spend) + 3 (reward) = -7
        print("\n5) Create and run Bond 2 (Q→D)...")
        bond2_id = cli.cmd_bond_create([item2_id], "Decision prompt")
        cli.cmd_bond_run(bond2_id, "D")
        expected += -10 + 3  # 88
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ Bond run: -10, executed: +3 (balance={cli._credits_balance})")

        # 6) Holologue: -20 (spend) + 5 (reward) = -15
        print("\n6) Run Holologue...")
        cli.cmd_holologue_run([item1_id, item2_id], "plan")
        expected += -20 + 5  # 73
        assert cli._credits_balance == expected, f"Expected {expected}, got {cli._credits_balance}"
        print(f"   ✓ Holologue run: -20, completed: +5 (balance={cli._credits_balance})")

        # 7) Verify final balance matches Golden Flow expected (73)
        print("\n7) Verifying final balance...")
        assert cli._credits_balance == 73, f"Expected 73 (Golden Flow), got {cli._credits_balance}"
        print(f"   ✓ Final balance: {cli._credits_balance} (matches Golden Flow expected)")

        # 8) Verify derived balance from store
        print("\n8) Verifying derived balance from store...")
        derived = cli.store.compute_credits_balance(cli._episode_id)
        assert derived == 73, f"Derived balance should be 73, got {derived}"
        print(f"   ✓ Derived balance from events: {derived}")

        # 9) Verify all credits.delta events have proper structure
        print("\n9) Verifying credits.delta event structure...")
        events = cli.store.load_events(episode_id=cli._episode_id)
        credits_events = [e for e in events if e["name"] == "credits.delta"]

        expected_reasons = [
            ("seed", 100, 100),
            ("item_created", 1, 101),
            ("item_created", 1, 102),
            ("bond_run_spend", -10, 92),
            ("bond_executed_reward", 3, 95),
            ("bond_run_spend", -10, 85),
            ("bond_executed_reward", 3, 88),
            ("holologue_run_spend", -20, 68),
            ("holologue_completed_reward", 5, 73),
        ]

        assert len(credits_events) == len(expected_reasons), f"Expected {len(expected_reasons)} credits events, got {len(credits_events)}"

        for i, (ce, (reason, delta, balance)) in enumerate(zip(credits_events, expected_reasons)):
            refs = ce["refs"]
            assert refs["reason"] == reason, f"Event {i}: expected reason '{reason}', got '{refs['reason']}'"
            assert refs["delta"] == delta, f"Event {i}: expected delta {delta}, got {refs['delta']}"
            assert refs["balance_after"] == balance, f"Event {i}: expected balance {balance}, got {refs['balance_after']}"
            print(f"   ✓ Event {i+1}: reason={reason}, delta={delta:+d}, balance={balance}")

        # 10) Verify credits events have proper qdpi and direction
        print("\n10) Verifying qdpi and direction...")
        for ce in credits_events:
            assert ce["qdpi"] == "Q", f"credits.delta should have qdpi=Q"
            assert ce["direction"] == "system→field", f"credits.delta should have direction=system→field"
        print("   ✓ All credits.delta events have qdpi=Q, direction=system→field")

        # Open ledger
        print("\n11) Opening ledger...")
        cli.cmd_ledger_open()

    print("\n" + "=" * 60)
    print("PASS 5 COMPLETE - All checks passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_pass5()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
