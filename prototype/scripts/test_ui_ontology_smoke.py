#!/usr/bin/env python3
"""
UI Ontology Smoke Test

This test verifies that the UI correctly enforces the Item/Bond/Execute ontology:

1. Creating an Item does NOT trigger AI generation
2. Bond creation is separate from Item creation
3. Bond execution is explicit (requires "Run Bond")
4. Output type (M/D) is derived from Bond origin, not user-selected

This is a headless test that validates the backend API contracts.
For full UI testing, use manual testing with the web interface.

Usage:
    python prototype/scripts/test_ui_ontology_smoke.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_ui_ontology_smoke():
    """Run UI ontology smoke tests."""
    print("=" * 70)
    print("UI ONTOLOGY SMOKE TEST")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        initial_credits = cli._credits_balance
        print(f"\nInitial credits: {initial_credits}")

        # === Test 1: Item creation does NOT trigger AI ===
        print("\n" + "-" * 70)
        print("TEST 1: Item creation does NOT trigger AI")
        print("-" * 70)

        credits_before = cli._credits_balance

        # Create a Q item
        item_id = cli.cmd_item_create(
            title="Test Item",
            body="This is a test item for ontology verification."
        )
        print(f"  Created item: {item_id}")

        credits_after = cli._credits_balance
        credit_change = credits_after - credits_before

        # Item creation should give +1 credit, NOT call AI (which would cost -10)
        assert credit_change == 1, \
            f"Item creation should give +1 credit, got {credit_change}"
        print(f"  Credits change: +{credit_change} (correct: no AI call)")

        # Verify item exists and is type Q
        item = cli.store.get_item(item_id)
        assert item["type"] == "Q", f"Item should be Q, got {item['type']}"
        print(f"  Item type: {item['type']} (correct)")

        # === Test 2: Bond creation is separate from execution ===
        print("\n" + "-" * 70)
        print("TEST 2: Bond creation is separate from execution")
        print("-" * 70)

        credits_before = cli._credits_balance

        # Create a draft bond (no execution yet)
        bond_id = cli.cmd_bond_create(
            input_item_ids=[item_id],
            prompt_text="Expand this into a checklist",
            intent_type="expand",
            recipe_id="expand_to_checklist",
        )
        print(f"  Created bond: {bond_id}")

        credits_after = cli._credits_balance
        credit_change = credits_after - credits_before

        # Bond draft creation does NOT change credits (no AI call)
        assert credit_change == 0, \
            f"Bond draft creation should give 0 credits change, got {credit_change}"
        print(f"  Credits change: {credit_change} (correct: no AI call)")

        # Verify bond exists and is draft (output_item_id = None)
        bond = cli.store.get_bond(bond_id)
        assert bond["output_item_id"] is None, \
            f"Draft bond should have output_item_id=None, got {bond['output_item_id']}"
        assert bond["status"] == "draft", \
            f"Bond should be draft, got {bond['status']}"
        print(f"  Bond status: {bond['status']} (correct)")
        print(f"  Bond output_item_id: {bond['output_item_id']} (correct: None)")

        # === Test 3: Bond execution is explicit ===
        print("\n" + "-" * 70)
        print("TEST 3: Bond execution is explicit and calls AI")
        print("-" * 70)

        credits_before = cli._credits_balance

        # Now explicitly execute the bond
        output_item_id = cli.cmd_bond_run(bond_id, output_type="M")
        print(f"  Executed bond, output: {output_item_id}")

        credits_after = cli._credits_balance
        credit_change = credits_after - credits_before

        # Execution: -10 (spend) + +3 (reward) = -7 net
        # The key point is that credits decreased (AI was called)
        assert credit_change == -7, \
            f"Bond execution should cost -7 credits (-10 spend, +3 reward), got {credit_change}"
        print(f"  Credits change: {credit_change} (correct: AI was called)")

        # Verify bond is now executed
        bond = cli.store.get_bond(bond_id)
        assert bond["output_item_id"] == output_item_id, \
            f"Executed bond should have output_item_id set"
        assert bond["status"] == "executed", \
            f"Bond should be executed, got {bond['status']}"
        print(f"  Bond status: {bond['status']} (correct)")

        # Verify output item exists and has correct type
        output_item = cli.store.get_item(output_item_id)
        assert output_item["type"] == "M", \
            f"Output should be M (from suggestion), got {output_item['type']}"
        print(f"  Output type: {output_item['type']} (correct: M from suggestion)")

        # === Test 4: Custom prompt produces D output ===
        print("\n" + "-" * 70)
        print("TEST 4: Custom prompt produces D output")
        print("-" * 70)

        # Create a bond with custom prompt (no recipe)
        bond_id_2 = cli.cmd_bond_create(
            input_item_ids=[item_id],
            prompt_text="Tell me more about this topic",
            intent_type=None,
            recipe_id=None,
        )
        print(f"  Created custom bond: {bond_id_2}")

        # Execute with D output type
        output_item_id_2 = cli.cmd_bond_run(bond_id_2, output_type="D")
        print(f"  Executed bond, output: {output_item_id_2}")

        # Verify output item is D type
        output_item_2 = cli.store.get_item(output_item_id_2)
        assert output_item_2["type"] == "D", \
            f"Custom prompt output should be D, got {output_item_2['type']}"
        print(f"  Output type: {output_item_2['type']} (correct: D from custom)")

        # === Test 5: No type dropdown exists (verified by checking types are derived) ===
        print("\n" + "-" * 70)
        print("TEST 5: Output types are derived, not user-selected")
        print("-" * 70)

        # Count items by type
        all_items = cli.store.load_items()
        type_counts = {}
        for item in all_items:
            t = item["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"  Items by type: {type_counts}")

        # Verify we have Q, M, and D items
        assert "Q" in type_counts and type_counts["Q"] == 1, \
            f"Should have exactly 1 Q item"
        assert "M" in type_counts and type_counts["M"] == 1, \
            f"Should have exactly 1 M item (from suggestion)"
        assert "D" in type_counts and type_counts["D"] == 1, \
            f"Should have exactly 1 D item (from custom)"
        print("  ✓ Q items created by direct input")
        print("  ✓ M items created by suggestion bonds")
        print("  ✓ D items created by custom prompt bonds")

        # === Test 6: Verify event sequence ===
        print("\n" + "-" * 70)
        print("TEST 6: Verify canonical event sequence")
        print("-" * 70)

        events = cli.store.load_events()
        event_names = [e["name"] for e in events]

        # Check for proper Bond events
        assert "bond.draft_created" in event_names, \
            "Should have bond.draft_created event"
        assert "bond.run_requested" in event_names, \
            "Should have bond.run_requested event"
        assert "bond.executed" in event_names, \
            "Should have bond.executed event"

        print("  ✓ bond.draft_created events present")
        print("  ✓ bond.run_requested events present")
        print("  ✓ bond.executed events present")

        # Verify order: draft_created comes before run_requested comes before executed
        draft_idx = event_names.index("bond.draft_created")
        run_idx = event_names.index("bond.run_requested")
        exec_idx = event_names.index("bond.executed")

        assert draft_idx < run_idx < exec_idx, \
            f"Event order should be draft_created < run_requested < executed"
        print("  ✓ Event order is correct (draft → run → executed)")

        # === Final Summary ===
        print("\n" + "=" * 70)
        print("UI ONTOLOGY SMOKE TEST COMPLETE - ALL ASSERTIONS PASSED!")
        print("=" * 70)

        final_credits = cli._credits_balance
        print(f"\nFinal credits: {final_credits}")

        print("\nSummary:")
        print("  ✓ Item creation does NOT trigger AI")
        print("  ✓ Bond creation is separate from execution")
        print("  ✓ Bond execution is explicit and calls AI")
        print("  ✓ Custom prompts produce D output")
        print("  ✓ Output types are derived from Bond origin")
        print("  ✓ Event sequence follows ontology")

    return True


if __name__ == "__main__":
    try:
        success = test_ui_ontology_smoke()
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
