#!/usr/bin/env python3
"""
Field-Kit v0.1 SQLite Store Tests (Sprint S10)

Tests for SQLite storage layer with FTS5 full-text search.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.store_sqlite import SQLiteStore, migrate_jsonl_to_sqlite, FTS5_AVAILABLE
from fieldkit.schemas import (
    Network,
    Episode,
    Item,
    Bond,
    QDPIEvent,
    generate_network_id,
    generate_episode_id,
    generate_item_id,
    generate_bond_id,
    generate_event_id,
    now_iso,
    Vec3,
    ActorRef,
    ItemProvenanceUser,
    SYSTEM_ACTOR,
)


class TestSQLiteStoreBasic:
    """Basic tests for SQLiteStore initialization."""

    def test_store_init_creates_db(self, tmp_path):
        """Test that SQLiteStore creates database file."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        assert store.db_path.exists()
        assert store.db_path.name == "fieldkit.db"

    def test_store_init_custom_db_path(self, tmp_path):
        """Test custom database path."""
        custom_path = tmp_path / "custom.db"
        store = SQLiteStore(data_dir=tmp_path, db_path=custom_path)
        store.init()

        assert custom_path.exists()
        store.close()

    def test_store_get_stats(self, tmp_path):
        """Test get_stats returns expected structure."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        stats = store.get_stats()

        assert stats["store_type"] == "sqlite"
        assert "db_path" in stats
        assert "fts5_enabled" in stats
        assert stats["items_count"] == 0
        assert stats["events_count"] == 0

        store.close()

    def test_store_is_initialized_empty(self, tmp_path):
        """Test is_initialized returns False for empty store."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Empty store (no networks) should return False
        assert not store.is_initialized()
        store.close()


class TestSQLiteStoreNetworks:
    """Tests for network operations."""

    def test_upsert_and_get_network(self, tmp_path):
        """Test upserting and retrieving a network."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        network = Network(
            id=generate_network_id(),
            scope="private",
            title="Test Network",
            root_episode_id="ep_test",
            created_by="user",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_network(network)

        # Retrieve
        result = store.get_network(network.id)
        assert result is not None
        assert result["id"] == network.id
        assert result["title"] == "Test Network"

        store.close()

    def test_load_networks(self, tmp_path):
        """Test loading all networks."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Create 2 networks
        for i in range(2):
            network = Network(
                id=generate_network_id(),
                scope="private",
                title=f"Network {i}",
                root_episode_id="ep_test",
                created_by="user",
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            store.upsert_network(network)

        networks = store.load_networks()
        assert len(networks) == 2

        store.close()


class TestSQLiteStoreItems:
    """Tests for item operations."""

    def test_upsert_and_get_item(self, tmp_path):
        """Test upserting and retrieving an item."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        item = Item(
            id=generate_item_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            type="Q",
            title="Test Question",
            body="What is the meaning of life?",
            position=Vec3(0, 0, 0),
            provenance=ItemProvenanceUser(created_by="user"),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_item(item)

        result = store.get_item(item.id)
        assert result is not None
        assert result["title"] == "Test Question"
        assert result["type"] == "Q"

        store.close()

    def test_load_items_with_filter(self, tmp_path):
        """Test loading items with filter."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Create Q and M items
        for item_type in ["Q", "M"]:
            item = Item(
                id=generate_item_id(),
                network_id="nw_test",
                episode_id="ep_test",
                scope="private",
                type=item_type,
                title=f"Test {item_type}",
                position=Vec3(),
                provenance=ItemProvenanceUser(),
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            store.upsert_item(item)

        # Filter by type
        q_items = store.load_items(filters={"type": "Q"})
        assert len(q_items) == 1
        assert q_items[0]["type"] == "Q"

        store.close()

    def test_search_items_basic(self, tmp_path):
        """Test basic item search."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Create items with searchable content
        item1 = Item(
            id=generate_item_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            type="Q",
            title="Machine Learning Question",
            body="How do neural networks work?",
            position=Vec3(),
            provenance=ItemProvenanceUser(),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_item(item1)

        item2 = Item(
            id=generate_item_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            type="M",
            title="Cooking Recipe",
            body="How to bake bread",
            position=Vec3(),
            provenance=ItemProvenanceUser(),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_item(item2)

        # Search should find ML item
        results = store.search_items("neural")
        assert len(results) >= 1
        assert any("neural" in r.get("body", "").lower() for r in results)

        store.close()

    def test_search_items_no_results(self, tmp_path):
        """Test search with no matches."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        results = store.search_items("xyznonexistent123")
        assert len(results) == 0

        store.close()


class TestSQLiteStoreBonds:
    """Tests for bond operations."""

    def test_upsert_and_get_bond(self, tmp_path):
        """Test upserting and retrieving a bond."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        bond = Bond(
            id=generate_bond_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            input_item_ids=["it_1", "it_2"],
            prompt_text="Generate response",
            status="draft",
            output_item_id=None,
            created_by="user",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_bond(bond)

        result = store.get_bond(bond.id)
        assert result is not None
        assert result["input_item_ids"] == ["it_1", "it_2"]
        assert result["status"] == "draft"

        store.close()

    def test_load_bonds_with_filter(self, tmp_path):
        """Test loading bonds with status filter."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Create draft and executed bonds
        for status in ["draft", "executed"]:
            bond = Bond(
                id=generate_bond_id(),
                network_id="nw_test",
                episode_id="ep_test",
                scope="private",
                input_item_ids=["it_1"],
                prompt_text="Test prompt",
                status=status,
                output_item_id="it_2" if status == "executed" else None,
                created_by="user",
                created_at=now_iso(),
                updated_at=now_iso(),
            )
            store.upsert_bond(bond)

        executed = store.load_bonds(filters={"status": "executed"})
        assert len(executed) == 1
        assert executed[0]["status"] == "executed"

        store.close()


class TestSQLiteStoreEvents:
    """Tests for event operations."""

    def test_append_and_load_events(self, tmp_path):
        """Test appending and loading events."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        episode_id = generate_episode_id()
        network_id = generate_network_id()

        # Append events
        for i in range(3):
            event = QDPIEvent(
                id=generate_event_id(),
                network_id=network_id,
                episode_id=episode_id,
                ts=now_iso(),
                seq=i + 1,
                qdpi="Q",
                direction="user→field",
                actor=SYSTEM_ACTOR,
                name=f"test.event.{i}",
                refs={},
            )
            store.append_event(event)

        # Load all events for episode
        events = store.load_events(episode_id=episode_id)
        assert len(events) == 3

        # Verify sequence order
        for i, event in enumerate(events):
            assert event["seq"] == i + 1

        store.close()

    def test_append_event_auto_seq(self, tmp_path):
        """Test that seq is auto-corrected if wrong."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        episode_id = generate_episode_id()
        network_id = generate_network_id()

        # First event
        event1 = QDPIEvent(
            id=generate_event_id(),
            network_id=network_id,
            episode_id=episode_id,
            ts=now_iso(),
            seq=1,
            qdpi="Q",
            direction="user→field",
            actor=SYSTEM_ACTOR,
            name="first",
            refs={},
        )
        store.append_event(event1)

        # Second event with wrong seq (should be auto-corrected to 2)
        event2 = QDPIEvent(
            id=generate_event_id(),
            network_id=network_id,
            episode_id=episode_id,
            ts=now_iso(),
            seq=999,  # Wrong!
            qdpi="M",
            direction="field→user",
            actor=SYSTEM_ACTOR,
            name="second",
            refs={},
        )
        store.append_event(event2)

        events = store.load_events(episode_id=episode_id)
        assert len(events) == 2
        assert events[0]["seq"] == 1
        assert events[1]["seq"] == 2

        store.close()

    def test_get_event(self, tmp_path):
        """Test getting a single event by id."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        event = QDPIEvent(
            id=generate_event_id(),
            network_id="nw_test",
            episode_id="ep_test",
            ts=now_iso(),
            seq=1,
            qdpi="Q",
            direction="user→field",
            actor=SYSTEM_ACTOR,
            name="test.event",
            refs={"data": "value"},
        )
        store.append_event(event)

        result = store.get_event(event.id)
        assert result is not None
        assert result["name"] == "test.event"
        assert result["refs"]["data"] == "value"

        store.close()


class TestSQLiteStoreEpisodes:
    """Tests for episode operations."""

    def test_upsert_and_get_episode(self, tmp_path):
        """Test upserting and retrieving an episode."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        ts = now_iso()
        episode = Episode(
            id=generate_episode_id(),
            network_id="nw_test",
            scope="private",
            title="Test Episode",
            status="active",
            started_at=ts,
            last_active_at=ts,
            created_by="user",
            created_at=ts,
            updated_at=ts,
        )
        store.upsert_episode(episode)

        result = store.get_episode(episode.id)
        assert result is not None
        assert result["title"] == "Test Episode"
        assert result["status"] == "active"

        store.close()


class TestSQLiteStoreCredits:
    """Tests for credits balance computation."""

    def test_compute_credits_balance(self, tmp_path):
        """Test credits balance computation from events."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        episode_id = generate_episode_id()
        network_id = generate_network_id()

        # Initial credit event
        event1 = QDPIEvent(
            id=generate_event_id(),
            network_id=network_id,
            episode_id=episode_id,
            ts=now_iso(),
            seq=1,
            qdpi="Q",
            direction="system→field",
            actor=SYSTEM_ACTOR,
            name="credits.delta",
            refs={"delta": 100, "balance_after": 100},
        )
        store.append_event(event1)

        # Spend credits
        event2 = QDPIEvent(
            id=generate_event_id(),
            network_id=network_id,
            episode_id=episode_id,
            ts=now_iso(),
            seq=2,
            qdpi="Q",
            direction="system→field",
            actor=SYSTEM_ACTOR,
            name="credits.delta",
            refs={"delta": -30, "balance_after": 70},
        )
        store.append_event(event2)

        balance = store.compute_credits_balance(episode_id=episode_id)
        assert balance == 70

        store.close()


class TestSQLiteStoreClear:
    """Tests for clearing store data."""

    def test_clear_removes_all_data(self, tmp_path):
        """Test that clear removes all data."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Add some data
        network = Network(
            id=generate_network_id(),
            scope="private",
            title="Test",
            root_episode_id="ep_test",
            created_by="user",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_network(network)

        item = Item(
            id=generate_item_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            type="Q",
            title="Test",
            position=Vec3(),
            provenance=ItemProvenanceUser(),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_item(item)

        # Clear
        store.clear()

        assert len(store.load_networks()) == 0
        assert len(store.load_items()) == 0

        store.close()


class TestMigration:
    """Tests for JSONL to SQLite migration."""

    def test_migrate_empty_store(self, tmp_path):
        """Test migrating empty JSONL store."""
        counts = migrate_jsonl_to_sqlite(tmp_path, verbose=False)

        assert counts["networks"] == 0
        assert counts["items"] == 0
        assert counts["events"] == 0

        # SQLite file should exist
        assert (tmp_path / "fieldkit.db").exists()

    def test_migrate_with_data(self, tmp_path):
        """Test migrating JSONL store with data."""
        # Create JSONL data
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            json.dumps({
                "id": "it_001",
                "network_id": "nw_001",
                "episode_id": "ep_001",
                "scope": "private",
                "type": "Q",
                "title": "Test Question",
                "position": {"x": 0, "y": 0, "z": 0},
                "provenance": {"created_by": "user"},
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }) + "\n"
        )

        networks_file = tmp_path / "networks.jsonl"
        networks_file.write_text(
            json.dumps({
                "id": "nw_001",
                "scope": "private",
                "title": "Test Network",
                "root_episode_id": "ep_001",
                "created_by": "user",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }) + "\n"
        )

        episodes_file = tmp_path / "episodes.jsonl"
        episodes_file.write_text(
            json.dumps({
                "id": "ep_001",
                "network_id": "nw_001",
                "scope": "private",
                "title": "Test Episode",
                "status": "active",
                "started_at": "2025-01-01T00:00:00Z",
                "last_active_at": "2025-01-01T00:00:00Z",
                "created_by": "user",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }) + "\n"
        )

        counts = migrate_jsonl_to_sqlite(tmp_path, verbose=False)

        assert counts["networks"] == 1
        assert counts["episodes"] == 1
        assert counts["items"] == 1

        # Verify data in SQLite
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        item = store.get_item("it_001")
        assert item is not None
        assert item["title"] == "Test Question"

        store.close()


class TestFTS5:
    """Tests for FTS5 full-text search functionality."""

    def test_fts5_availability_reported(self, tmp_path):
        """Test that FTS5 availability is correctly reported."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # fts5_enabled should be a boolean
        assert isinstance(store.fts5_enabled, bool)

        store.close()

    def test_search_with_fts5_or_fallback(self, tmp_path):
        """Test that search works regardless of FTS5 availability."""
        store = SQLiteStore(data_dir=tmp_path)
        store.init()

        # Add searchable items
        item = Item(
            id=generate_item_id(),
            network_id="nw_test",
            episode_id="ep_test",
            scope="private",
            type="Q",
            title="Machine Learning Pipeline",
            body="This is about training neural networks with transformers.",
            position=Vec3(),
            provenance=ItemProvenanceUser(),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        store.upsert_item(item)

        # Search should work
        results = store.search_items("transformers")
        assert len(results) >= 1

        store.close()


def run_tests():
    """Run all tests and report results."""
    try:
        import pytest
        result = pytest.main([__file__, "-v", "--tb=short"])
        return result == 0
    except ImportError:
        return run_tests_manual()


def run_tests_manual():
    """Run tests without pytest."""
    import inspect

    passed = 0
    failed = 0
    errors = []

    test_classes = [
        TestSQLiteStoreBasic,
        TestSQLiteStoreNetworks,
        TestSQLiteStoreItems,
        TestSQLiteStoreBonds,
        TestSQLiteStoreEvents,
        TestSQLiteStoreEpisodes,
        TestSQLiteStoreCredits,
        TestSQLiteStoreClear,
        TestMigration,
        TestFTS5,
    ]

    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    try:
                        method = getattr(instance, method_name)
                        sig = inspect.signature(method)
                        if "tmp_path" in sig.parameters:
                            method(tmp_path)
                        else:
                            method()
                        passed += 1
                        print(f"  PASS: {cls.__name__}.{method_name}")
                    except AssertionError as e:
                        failed += 1
                        errors.append(f"{cls.__name__}.{method_name}: {e}")
                        print(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                    except Exception as e:
                        failed += 1
                        errors.append(f"{cls.__name__}.{method_name}: {e}")
                        print(f"  ERROR: {cls.__name__}.{method_name}: {e}")

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        success = run_tests_manual()
        sys.exit(0 if success else 1)
