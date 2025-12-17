#!/usr/bin/env python3
"""
Pass 2 Run Check: Init + Create Item + Ledger (readback)

This script verifies:
1. init creates Network, Episode 0, and logs proper events
2. item:create creates Items and logs events + credits
3. ledger:open shows objects and events
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI


def test_pass2():
    """Run Pass 2 verification."""
    print("=" * 60)
    print("Pass 2 Run Check: Init + Create Item + Ledger")
    print("=" * 60)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        # Create CLI
        cli = FieldKitCLI(data_dir)

        # 1) Init
        print("\n1) Running init...")
        cli.cmd_init()

        # Verify
        assert cli._network_id is not None, "Network should be created"
        assert cli._episode_id is not None, "Episode should be created"
        assert cli._credits_balance == 100, f"Credits should be 100, got {cli._credits_balance}"
        print("   ✓ Init successful")
        print(f"   Network: {cli._network_id}")
        print(f"   Episode: {cli._episode_id}")
        print(f"   Credits: {cli._credits_balance}")

        # Verify events
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]
        assert "app.first_run.started" in event_names, "Should log app.first_run.started"
        assert "episode.created" in event_names, "Should log episode.created"
        assert "credits.delta" in event_names, "Should log credits.delta"
        assert "store.commit" in event_names, "Should log store.commit"
        print(f"   ✓ Events logged: {len(events)}")

        # 2) Create Item 1
        print("\n2) Creating Item 1...")
        item1_id = cli.cmd_item_create(title="My First Field Item")
        assert item1_id is not None
        assert cli._credits_balance == 101, f"Credits should be 101, got {cli._credits_balance}"
        print(f"   ✓ Item 1 created: {item1_id}")

        # 3) Create Item 2
        print("\n3) Creating Item 2...")
        item2_id = cli.cmd_item_create(title="Second Field Item")
        assert item2_id is not None
        assert cli._credits_balance == 102, f"Credits should be 102, got {cli._credits_balance}"
        print(f"   ✓ Item 2 created: {item2_id}")

        # 4) Verify items in store
        print("\n4) Verifying items in store...")
        items = cli.store.load_items()
        assert len(items) == 2, f"Should have 2 items, got {len(items)}"
        print(f"   ✓ Items in store: {len(items)}")

        # 5) Verify events after item creation
        print("\n5) Verifying events after item creation...")
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]

        # Count expected events
        item_created_count = event_names.count("item.created")
        assert item_created_count == 2, f"Should have 2 item.created events, got {item_created_count}"

        credits_delta_count = event_names.count("credits.delta")
        # seed + item1 + item2 = 3
        assert credits_delta_count == 3, f"Should have 3 credits.delta events, got {credits_delta_count}"

        store_commit_count = event_names.count("store.commit")
        # init + item1 + item2 = 3
        assert store_commit_count == 3, f"Should have 3 store.commit events, got {store_commit_count}"

        print(f"   ✓ Events verified: {len(events)} total")
        print(f"      item.created: {item_created_count}")
        print(f"      credits.delta: {credits_delta_count}")
        print(f"      store.commit: {store_commit_count}")

        # 6) Verify event ordering
        print("\n6) Verifying event ordering...")
        for i, event in enumerate(events):
            expected_seq = i + 1
            assert event["seq"] == expected_seq, f"Event {i} should have seq={expected_seq}, got {event['seq']}"
        print(f"   ✓ Event ordering correct (seq 1 to {len(events)})")

        # 7) Ledger open
        print("\n7) Opening ledger...")
        cli.cmd_ledger_open()
        print("   ✓ Ledger opened")

        # Verify ledger.opened event was logged
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]
        assert "ledger.opened" in event_names, "Should log ledger.opened"
        print("   ✓ ledger.opened event logged")

    print("\n" + "=" * 60)
    print("PASS 2 COMPLETE - All checks passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_pass2()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
