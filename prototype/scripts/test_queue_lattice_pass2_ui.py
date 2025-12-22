#!/usr/bin/env python3
"""
Queue Lattice PASS 2 UI/API Acceptance Test

Tests the hololoop-only flow through the API:
1. Create Queue items ONLY (no D/M/H)
2. Get 4 hololoop options for selection
3. Create hololoop bond from user selection
4. Verify no D/M output creation paths are used

Run: python3 prototype/scripts/test_queue_lattice_pass2_ui.py
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from http.server import HTTPServer
from threading import Thread
import time
import urllib.request
import urllib.parse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import reset_store


def test_api_queue_item_creation():
    """Test that API only creates Queue items."""
    print("\n=== Test 1: API Queue Item Creation ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create first Queue item
        item1_id = cli.cmd_item_create(
            title="Testing Queue Items",
            body="This is a test to verify only Queue items are created.",
            item_type="Q",
        )

        item1 = cli.store.get_item(item1_id)
        assert item1 is not None, "Item not found"
        assert item1["type"] == "Q", f"Expected type 'Q', got '{item1['type']}'"

        # Create second Queue item
        item2_id = cli.cmd_item_create(
            title="Second Test Item",
            body="Another Queue item for hololoop testing.",
            item_type="Q",
        )

        item2 = cli.store.get_item(item2_id)
        assert item2 is not None, "Item 2 not found"
        assert item2["type"] == "Q", f"Expected type 'Q', got '{item2['type']}'"

        # Verify no D/M/H items exist
        all_items = cli.store.load_items()
        for item in all_items:
            assert item["type"] == "Q", f"Found non-Queue item: {item['type']}"

        print(f"  ✓ Created {len(all_items)} Queue items only")
        print(f"  ✓ No D/M/H items created")
        return True


def test_hololoop_options_api():
    """Test the hololoop options generation API."""
    print("\n=== Test 2: Hololoop Options API ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create two Queue items
        item1_id = cli.cmd_item_create(
            title="Machine Learning Model",
            body="Training neural networks with deep learning techniques.",
            item_type="Q",
        )

        item2_id = cli.cmd_item_create(
            title="Data Pipeline",
            body="ETL processes for data preprocessing and feature engineering.",
            item_type="Q",
        )

        # Get hololoop options using CLI method
        from fieldkit.hololoop_engine import generate_hololoop_options

        item1 = cli.store.get_item(item1_id)
        item2 = cli.store.get_item(item2_id)

        result = generate_hololoop_options(item1, item2, return_debug=True)

        assert "options" in result, "Missing 'options' in result"
        assert len(result["options"]) == 4, f"Expected 4 options, got {len(result['options'])}"

        # Verify each option has proper structure
        for i, opt in enumerate(result["options"]):
            assert "option_index" in opt, f"Option {i} missing option_index"
            assert "link_text_forward" in opt, f"Option {i} missing link_text_forward"
            assert "link_text_return" in opt, f"Option {i} missing link_text_return"

            # Verify no intent labels in link text
            fwd = opt["link_text_forward"].lower()
            ret = opt["link_text_return"].lower()

            for forbidden in ["extends:", "supports:", "contrasts:", "elaborates:"]:
                assert forbidden not in fwd, f"Found intent label '{forbidden}' in forward text"
                assert forbidden not in ret, f"Found intent label '{forbidden}' in return text"

            print(f"  ✓ Option {opt['option_index']}: clean link text (no visible intent labels)")

        print(f"  ✓ All 4 options generated without visible intent labels")
        return True


def test_hololoop_selection_creates_bond():
    """Test that selecting a hololoop option creates a bond."""
    print("\n=== Test 3: Hololoop Selection Creates Bond ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create two Queue items
        item1_id = cli.cmd_item_create(
            title="API Design",
            body="RESTful endpoints with authentication and rate limiting.",
            item_type="Q",
        )

        item2_id = cli.cmd_item_create(
            title="Database Schema",
            body="PostgreSQL tables with foreign keys and indexes.",
            item_type="Q",
        )

        # Select option 2 to create hololoop
        bond_id = cli.cmd_hololoop_create(item1_id, item2_id, option_index=2)

        # Verify bond was created correctly
        bond = cli.store.get_bond(bond_id)
        assert bond is not None, "Bond not found"
        assert bond["bond_kind"] == "hololoop", f"Expected bond_kind 'hololoop', got {bond.get('bond_kind')}"
        assert bond["status"] == "draft", f"Expected status 'draft', got {bond['status']}"
        assert bond["link_text_forward"] is not None, "Missing link_text_forward"
        assert bond["link_text_return"] is not None, "Missing link_text_return"
        assert len(bond["input_item_ids"]) == 2, "Should have 2 input items"

        print(f"  ✓ Hololoop bond created: {bond_id}")
        print(f"  ✓ bond_kind: hololoop")
        print(f"  ✓ status: draft")
        print(f"  ✓ Forward link: {bond['link_text_forward'][:60]}...")
        print(f"  ✓ Return link: {bond['link_text_return'][:60]}...")

        return True


def test_no_dm_output_creation():
    """Test that no D/M output items are created in the flow."""
    print("\n=== Test 4: No D/M Output Creation ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create multiple Queue items
        for i in range(3):
            cli.cmd_item_create(
                title=f"Test Item {i+1}",
                body=f"Content for test item {i+1}.",
                item_type="Q",
            )

        # Create hololoop between items 1 and 2
        items = cli.store.load_items()
        cli.cmd_hololoop_create(items[0]["id"], items[1]["id"], option_index=1)

        # Verify no D/M/H items exist
        all_items = cli.store.load_items()
        item_types = [item["type"] for item in all_items]

        assert "D" not in item_types, "Found Dialogue item - D/M output was created!"
        assert "M" not in item_types, "Found Monologue item - D/M output was created!"
        assert "H" not in item_types, "Found Holologue item - unexpected item type!"

        q_count = item_types.count("Q")
        assert q_count == 3, f"Expected 3 Queue items, got {q_count}"

        print(f"  ✓ {q_count} Queue items created")
        print(f"  ✓ 0 Dialogue items (D) - CORRECT")
        print(f"  ✓ 0 Monologue items (M) - CORRECT")
        print(f"  ✓ No accidental output generation")

        return True


def test_hololoop_directions_both_ways():
    """Test that hololoop has both forward and return directions."""
    print("\n=== Test 5: Hololoop Both Directions ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create items with substantive content
        item1_id = cli.cmd_item_create(
            title="Frontend Architecture",
            body="React components with TypeScript, state management via Redux.",
            item_type="Q",
        )

        item2_id = cli.cmd_item_create(
            title="Backend Services",
            body="Node.js microservices with Express, connected to PostgreSQL.",
            item_type="Q",
        )

        bond_id = cli.cmd_hololoop_create(item1_id, item2_id, option_index=1)

        bond = cli.store.get_bond(bond_id)

        # Verify both directions are present and non-empty
        fwd = bond.get("link_text_forward", "")
        ret = bond.get("link_text_return", "")

        assert len(fwd) >= 20, f"Forward link too short: {len(fwd)} chars"
        assert len(ret) >= 20, f"Return link too short: {len(ret)} chars"

        # Verify they're different (not just copied)
        assert fwd != ret, "Forward and return links are identical!"

        print(f"  ✓ Forward (A→B): {fwd}")
        print(f"  ✓ Return (B→A): {ret}")
        print(f"  ✓ Both directions present and distinct")

        return True


def test_handles_extracted_on_creation():
    """Test that handles are extracted when Queue items are created."""
    print("\n=== Test 6: Handles Extracted on Creation ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create item with content containing extractable handles
        item_id = cli.cmd_item_create(
            title="Cloud Infrastructure",
            body="""Key components:
- Kubernetes orchestration
- Docker containerization
- CI/CD pipeline automation
- Load balancer configuration""",
            item_type="Q",
        )

        item = cli.store.get_item(item_id)

        assert "handles" in item, "Handles not stored on item"
        handles = item["handles"]
        assert handles is not None, "Handles is None"
        assert len(handles) >= 2, f"Expected at least 2 handles, got {len(handles)}"
        assert len(handles) <= 7, f"Expected at most 7 handles, got {len(handles)}"

        # Verify handle structure
        for h in handles:
            assert "quote" in h, "Handle missing 'quote' field"
            assert "kind" in h, "Handle missing 'kind' field"
            assert len(h["quote"]) > 0, "Handle quote is empty"

        print(f"  ✓ {len(handles)} handles extracted and stored")
        for h in handles[:4]:
            print(f"    - \"{h['quote'][:40]}...\" ({h['kind']})")

        return True


def main():
    print("=" * 60)
    print("QUEUE LATTICE PASS 2 UI/API ACCEPTANCE TEST")
    print("Hololoop-Only Flow (No D/M Output)")
    print("=" * 60)

    tests = [
        ("API Queue Item Creation", test_api_queue_item_creation),
        ("Hololoop Options API", test_hololoop_options_api),
        ("Hololoop Selection Creates Bond", test_hololoop_selection_creates_bond),
        ("No D/M Output Creation", test_no_dm_output_creation),
        ("Hololoop Both Directions", test_hololoop_directions_both_ways),
        ("Handles Extracted on Creation", test_handles_extracted_on_creation),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {name} returned False")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
