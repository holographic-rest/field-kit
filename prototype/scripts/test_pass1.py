#!/usr/bin/env python3
"""
Pass 1 Run Check: Storage + Event Log (append-only)

This script verifies:
1. Local store directory exists
2. Events can be appended to qdpi_events.jsonl
3. Events can be reloaded with order preserved
4. Sequence numbers are monotonic per episode
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit import (
    Store, get_store, reset_store,
    EventLogger,
    generate_network_id, generate_episode_id, now_iso,
)


def test_pass1():
    """Run Pass 1 verification."""
    print("=" * 60)
    print("Pass 1 Run Check: Storage + Event Log")
    print("=" * 60)

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"

        # 1) Create store
        print("\n1) Creating store...")
        store = Store(data_dir)
        assert store.data_dir.exists(), "Data directory should exist"
        print(f"   ✓ Store directory created: {store.data_dir}")

        # 2) Create event logger
        print("\n2) Creating event logger...")
        logger = EventLogger(store)
        print("   ✓ Event logger created")

        # 3) Create test IDs
        network_id = generate_network_id()
        episode_id = generate_episode_id()
        print(f"\n3) Test IDs:")
        print(f"   Network: {network_id}")
        print(f"   Episode: {episode_id}")

        # 4) Append events
        print("\n4) Appending events...")

        # Event 1: app.first_run.started
        e1 = logger.app_first_run_started(network_id, episode_id)
        print(f"   Event 1: {e1.name} (seq={e1.seq})")
        assert e1.seq == 1, f"First event should have seq=1, got {e1.seq}"

        # Event 2: episode.created
        e2 = logger.episode_created(network_id, episode_id, "Session 0", ordinal=0)
        print(f"   Event 2: {e2.name} (seq={e2.seq})")
        assert e2.seq == 2, f"Second event should have seq=2, got {e2.seq}"

        # Event 3: credits.delta (seed)
        e3 = logger.credits_delta(network_id, episode_id, delta=100, balance_after=100, reason="seed")
        print(f"   Event 3: {e3.name} (seq={e3.seq})")
        assert e3.seq == 3, f"Third event should have seq=3, got {e3.seq}"

        # Event 4: store.commit
        e4 = logger.store_commit(network_id, episode_id)
        print(f"   Event 4: {e4.name} (seq={e4.seq})")
        assert e4.seq == 4, f"Fourth event should have seq=4, got {e4.seq}"

        print("   ✓ All events appended with monotonic seq")

        # 5) Verify events file exists
        print("\n5) Verifying events file...")
        assert store.events_file.exists(), "Events file should exist"
        print(f"   ✓ Events file created: {store.events_file}")

        # 6) Reload events and verify order
        print("\n6) Reloading events...")
        events = store.load_events(episode_id=episode_id)
        assert len(events) == 4, f"Should have 4 events, got {len(events)}"

        # Verify order preserved
        for i, event in enumerate(events, 1):
            assert event["seq"] == i, f"Event {i} should have seq={i}, got {event['seq']}"
            print(f"   Event {i}: {event['name']} (seq={event['seq']})")

        print("   ✓ Events reloaded in correct order")

        # 7) Verify event contents
        print("\n7) Verifying event contents...")
        assert events[0]["name"] == "app.first_run.started"
        assert events[0]["qdpi"] == "Q"
        assert events[0]["direction"] == "system→field"

        assert events[1]["name"] == "episode.created"
        assert events[1]["refs"]["title"] == "Session 0"

        assert events[2]["name"] == "credits.delta"
        assert events[2]["refs"]["delta"] == 100
        assert events[2]["refs"]["balance_after"] == 100
        assert events[2]["refs"]["reason"] == "seed"

        assert events[3]["name"] == "store.commit"

        print("   ✓ All event contents verified")

        # 8) Test new store instance reloads correctly
        print("\n8) Testing fresh store reload...")
        store2 = Store(data_dir)
        events2 = store2.load_events(episode_id=episode_id)
        assert len(events2) == 4, "Fresh store should load 4 events"
        print("   ✓ Fresh store correctly reloads events")

        # 9) Test seq continuity after reload
        print("\n9) Testing seq continuity after reload...")
        logger2 = EventLogger(store2)
        e5 = logger2.tutorial_started(network_id, episode_id)
        assert e5.seq == 5, f"Fifth event should have seq=5, got {e5.seq}"
        print(f"   Event 5: {e5.name} (seq={e5.seq})")
        print("   ✓ Seq continuity maintained after reload")

    print("\n" + "=" * 60)
    print("PASS 1 COMPLETE - All checks passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_pass1()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
