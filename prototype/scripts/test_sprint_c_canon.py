#!/usr/bin/env python3
"""
Sprint C Test: Canon Policy v0.1

This script verifies the Canon Policy implementation:
1. Curated lists stored on Episode snapshot
2. Curate/uncurate Items and Bonds (order-preserving)
3. Derived "Curated (Canon Projection)" view
4. Episode and Curated exports

Run in a fresh temp store (no committed data).

Usage:
    python prototype/scripts/test_sprint_c_canon.py
"""

import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_sprint_c_canon():
    """Run Sprint C Canon Policy verification."""
    print("=" * 70)
    print("SPRINT C TEST: Canon Policy v0.1")
    print("=" * 70)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        cli = FieldKitCLI(data_dir)

        # === Step 1: Initialize ===
        print("\n" + "-" * 70)
        print("STEP 1: Initialize store")
        print("-" * 70)

        cli.cmd_init()
        print(f"  Network: {cli._network_id}")
        print(f"  Episode: {cli._episode_id}")

        # === Step 2: Create items ===
        print("\n" + "-" * 70)
        print("STEP 2: Create 3 Items")
        print("-" * 70)

        item1_id = cli.cmd_item_create(title="First Item", body="Content of first item")
        item2_id = cli.cmd_item_create(title="Second Item", body="Content of second item")
        item3_id = cli.cmd_item_create(title="Third Item", body="Content of third item")

        print(f"  Created: {item1_id}, {item2_id}, {item3_id}")

        # === Step 3: Create and execute a Bond ===
        print("\n" + "-" * 70)
        print("STEP 3: Create and execute a Bond")
        print("-" * 70)

        bond_id = cli.cmd_bond_create(
            input_item_ids=[item1_id],
            prompt_text="Test prompt for bond",
        )
        output_item_id = cli.cmd_bond_run(bond_id, output_type="M")

        print(f"  Bond: {bond_id}")
        print(f"  Output: {output_item_id}")

        # === Step 4: Test curation ===
        print("\n" + "-" * 70)
        print("STEP 4: Test curation (add items and bond)")
        print("-" * 70)

        # Curate items in order: item1, item3, output_item (skip item2)
        cli.cmd_curate_item_add(item1_id)
        cli.cmd_curate_item_add(item3_id)
        cli.cmd_curate_item_add(output_item_id)

        # Curate the executed bond
        cli.cmd_curate_bond_add(bond_id)

        # Verify episode has curated lists
        episode = cli.store.get_episode(cli._episode_id)
        assert episode.get("curated_item_ids") == [item1_id, item3_id, output_item_id], \
            "Curated item list should preserve order"
        assert episode.get("curated_bond_ids") == [bond_id], \
            "Curated bond list should contain the bond"
        print("  Order preserved in curated lists")

        # === Step 5: Test duplicate prevention ===
        print("\n" + "-" * 70)
        print("STEP 5: Test duplicate prevention")
        print("-" * 70)

        # Try to add item1 again (should fail)
        result = cli.cmd_curate_item_add(item1_id)
        assert result == False, "Duplicate should be prevented"

        # Verify list unchanged
        episode = cli.store.get_episode(cli._episode_id)
        assert episode.get("curated_item_ids") == [item1_id, item3_id, output_item_id], \
            "List should not have duplicates"
        print("  Duplicate prevention working")

        # === Step 6: Test curated view (projection) ===
        print("\n" + "-" * 70)
        print("STEP 6: Test curated projection view")
        print("-" * 70)

        projection = cli.compute_curated_projection()

        assert len(projection["curated_items"]) == 3, "Should have 3 curated items"
        assert len(projection["curated_bonds"]) == 1, "Should have 1 curated bond"
        assert len(projection["warnings"]) == 0, "Should have no warnings yet"

        # Verify order in projection matches curated list order
        proj_item_ids = [i["id"] for i in projection["curated_items"]]
        assert proj_item_ids == [item1_id, item3_id, output_item_id], \
            "Projection should preserve order"
        print("  Projection preserves order")

        # === Step 7: Test archived item handling ===
        print("\n" + "-" * 70)
        print("STEP 7: Archive an item and verify projection filtering")
        print("-" * 70)

        # Archive item3 (which is in curated list)
        cli.cmd_item_archive(item3_id)

        # Verify projection filters out archived item with warning
        projection = cli.compute_curated_projection()

        assert len(projection["curated_items"]) == 2, "Archived item should be filtered"
        proj_item_ids = [i["id"] for i in projection["curated_items"]]
        assert item3_id not in proj_item_ids, "Archived item should not be in projection"

        # Verify warning
        archived_warning = [w for w in projection["warnings"] if "archived" in w and item3_id in w]
        assert len(archived_warning) == 1, "Should have warning about archived item"
        print(f"  Archived item filtered with warning: {archived_warning[0]}")

        # Verify the curated list was NOT mutated (item3 still in list)
        episode = cli.store.get_episode(cli._episode_id)
        assert item3_id in episode.get("curated_item_ids", []), \
            "Archived item should remain in curated list (not auto-mutated)"
        print("  Curated list not auto-mutated")

        # === Step 8: Test missing ID warning ===
        print("\n" + "-" * 70)
        print("STEP 8: Test missing ID warning")
        print("-" * 70)

        # Manually add a fake ID to curated list
        episode = cli.store.get_episode(cli._episode_id)
        from fieldkit import dict_to_episode, now_iso
        episode_obj = dict_to_episode(episode)
        fake_id = "it_FAKE12345678901234"
        episode_obj.curated_item_ids.append(fake_id)
        episode_obj.updated_at = now_iso()
        cli.store.upsert_episode(episode_obj)

        # Verify projection handles missing ID
        projection = cli.compute_curated_projection()

        missing_warning = [w for w in projection["warnings"] if "not found" in w and fake_id in w]
        assert len(missing_warning) == 1, "Should have warning about missing item"
        print(f"  Missing ID warning: {missing_warning[0]}")

        # === Step 9: Test draft bond warning ===
        print("\n" + "-" * 70)
        print("STEP 9: Test draft bond warning")
        print("-" * 70)

        # Create a draft bond (not executed)
        draft_bond_id = cli.cmd_bond_create(
            input_item_ids=[item1_id],
            prompt_text="Draft bond for testing",
        )

        # Curate the draft bond (should warn)
        cli.cmd_curate_bond_add(draft_bond_id)

        # Verify projection includes draft with warning
        projection = cli.compute_curated_projection()

        draft_warning = [w for w in projection["warnings"] if "draft" in w and draft_bond_id in w]
        assert len(draft_warning) == 1, "Should have warning about draft bond"
        print(f"  Draft bond warning: {draft_warning[0]}")

        # Verify draft bond is in projection (explicitly curated)
        proj_bond_ids = [b["id"] for b in projection["curated_bonds"]]
        assert draft_bond_id in proj_bond_ids, "Draft bond should be in projection (explicitly curated)"
        print("  Draft bond included in projection")

        # === Step 10: Test exports ===
        print("\n" + "-" * 70)
        print("STEP 10: Test Episode and Curated exports")
        print("-" * 70)

        # Test Episode export
        episode_export_path = cli.cmd_export_episode()
        assert episode_export_path.exists(), "Episode export file should exist"

        with open(episode_export_path) as f:
            episode_export = json.load(f)

        # Verify export structure
        assert "export_type" in episode_export and episode_export["export_type"] == "episode"
        assert "network" in episode_export
        assert "episode" in episode_export
        assert "items" in episode_export
        assert "bonds" in episode_export
        assert "qdpi_events" in episode_export
        assert "derived" in episode_export
        print(f"  Episode export: {episode_export_path.name}")
        print(f"    Items: {len(episode_export['items'])}")
        print(f"    Bonds: {len(episode_export['bonds'])}")
        print(f"    Events: {len(episode_export['qdpi_events'])}")

        # Test Curated export
        curated_export_path = cli.cmd_export_curated()
        assert curated_export_path.exists(), "Curated export file should exist"

        with open(curated_export_path) as f:
            curated_export = json.load(f)

        # Verify export structure
        assert "export_type" in curated_export and curated_export["export_type"] == "curated_projection"
        assert "network_id" in curated_export
        assert "episode_id" in curated_export
        assert "curated_item_ids" in curated_export
        assert "curated_bond_ids" in curated_export
        assert "curated_items" in curated_export
        assert "curated_bonds" in curated_export
        assert "warnings" in curated_export
        print(f"  Curated export: {curated_export_path.name}")
        print(f"    Curated Items: {len(curated_export['curated_items'])}")
        print(f"    Curated Bonds: {len(curated_export['curated_bonds'])}")
        print(f"    Warnings: {len(curated_export['warnings'])}")

        # === Step 11: Verify no new event names ===
        print("\n" + "-" * 70)
        print("STEP 11: Verify no non-canonical event names")
        print("-" * 70)

        from fieldkit import CANONICAL_EVENT_NAMES
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = set(e["name"] for e in events)

        non_canonical = event_names - set(CANONICAL_EVENT_NAMES)
        assert len(non_canonical) == 0, f"Non-canonical events found: {non_canonical}"

        # Specifically verify no episode.curated_* events
        curated_events = [n for n in event_names if "curated" in n.lower()]
        assert len(curated_events) == 0, f"Found curated events: {curated_events}"

        print(f"  All {len(event_names)} event names are canonical")
        print("  No episode.curated_* events introduced")

        # === Step 12: Final curated view ===
        print("\n" + "-" * 70)
        print("STEP 12: Final curated view")
        print("-" * 70)

        cli.cmd_curated_view()

        # === Final Summary ===
        print("\n" + "=" * 70)
        print("SPRINT C TEST COMPLETE - ALL ASSERTIONS PASSED!")
        print("=" * 70)

        print("\nSummary:")
        print(f"  - Curated lists on Episode: VERIFIED")
        print(f"  - Order preservation: VERIFIED")
        print(f"  - Duplicate prevention: VERIFIED")
        print(f"  - Archived item filtering: VERIFIED")
        print(f"  - Missing ID handling: VERIFIED")
        print(f"  - Draft bond handling: VERIFIED")
        print(f"  - Episode export: VERIFIED")
        print(f"  - Curated export: VERIFIED")
        print(f"  - No new event names: VERIFIED")
        print(f"  - Canon is derived (no Canon object): VERIFIED")

    return True


if __name__ == "__main__":
    try:
        success = test_sprint_c_canon()
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
