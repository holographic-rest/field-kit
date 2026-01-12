#!/usr/bin/env python3
"""
Field-Kit v0.1 Backup & Restore Tests (Sprint S10)

Tests for backup/export and restore functionality.
"""

import sys
import json
import tempfile
import tarfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.backup import (
    create_backup,
    restore_backup,
    verify_backup,
    export_episode,
    list_backups,
    format_backup_report,
    _compute_file_hash,
    _count_jsonl_lines,
)
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
)


class TestBackupHelpers:
    """Tests for backup helper functions."""

    def test_compute_file_hash(self, tmp_path):
        """Test file hash computation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash1 = _compute_file_hash(test_file)
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

        # Same content should produce same hash
        hash2 = _compute_file_hash(test_file)
        assert hash1 == hash2

    def test_count_jsonl_lines(self, tmp_path):
        """Test JSONL line counting."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(
            '{"id": "1"}\n'
            '{"id": "2"}\n'
            '{"id": "3"}\n'
        )

        count = _count_jsonl_lines(jsonl_file)
        assert count == 3

    def test_count_jsonl_lines_empty(self, tmp_path):
        """Test counting empty file."""
        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.write_text("")

        count = _count_jsonl_lines(jsonl_file)
        assert count == 0

    def test_count_jsonl_lines_nonexistent(self, tmp_path):
        """Test counting non-existent file."""
        count = _count_jsonl_lines(tmp_path / "nonexistent.jsonl")
        assert count == 0


class TestCreateBackup:
    """Tests for create_backup function."""

    def test_create_backup_empty_dir(self, tmp_path):
        """Test creating backup from empty directory."""
        output_path = tmp_path / "backup.tar"
        manifest = create_backup(tmp_path, output_path, verbose=False)

        assert output_path.exists()
        assert manifest["backup_version"] == "1.0"
        assert "created_at" in manifest

    def test_create_backup_with_jsonl(self, tmp_path):
        """Test creating backup with JSONL files."""
        # Create JSONL data
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "title": "Test Item 1"}\n'
            '{"id": "it_002", "title": "Test Item 2"}\n'
        )

        events_file = tmp_path / "qdpi_events.jsonl"
        events_file.write_text(
            '{"id": "ev_001", "name": "test.event"}\n'
        )

        output_path = tmp_path / "backup.tar"
        manifest = create_backup(tmp_path, output_path, verbose=False)

        # Verify manifest
        assert manifest["counts"]["items"] == 2
        assert manifest["counts"]["events"] == 1
        assert "items.jsonl" in manifest["files"]
        assert "qdpi_events.jsonl" in manifest["files"]

        # Verify tar contents
        with tarfile.open(output_path, "r") as tar:
            names = tar.getnames()
            assert "items.jsonl" in names
            assert "qdpi_events.jsonl" in names
            assert "manifest.json" in names

    def test_create_backup_with_sqlite(self, tmp_path):
        """Test creating backup with SQLite database."""
        # Create SQLite database
        db_path = tmp_path / "fieldkit.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id TEXT)")
        conn.commit()
        conn.close()

        output_path = tmp_path / "backup.tar"
        manifest = create_backup(tmp_path, output_path, include_sqlite=True, verbose=False)

        assert manifest["store_type"] == "sqlite"
        assert "fieldkit.db" in manifest["files"]

    def test_create_backup_exclude_sqlite(self, tmp_path):
        """Test creating backup excluding SQLite."""
        # Create SQLite database
        db_path = tmp_path / "fieldkit.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id TEXT)")
        conn.commit()
        conn.close()

        output_path = tmp_path / "backup.tar"
        manifest = create_backup(tmp_path, output_path, include_sqlite=False, verbose=False)

        assert manifest["store_type"] == "jsonl"
        assert "fieldkit.db" not in manifest["files"]


class TestRestoreBackup:
    """Tests for restore_backup function."""

    def test_restore_backup_basic(self, tmp_path):
        """Test basic backup restoration."""
        # Create backup
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        items_file = data_dir / "items.jsonl"
        items_file.write_text('{"id": "it_001", "title": "Test"}\n')

        backup_path = tmp_path / "backup.tar"
        create_backup(data_dir, backup_path, verbose=False)

        # Restore to new directory
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verbose=False)

        assert result["success"]
        assert "items.jsonl" in result["restored_files"]
        assert (restore_dir / "items.jsonl").exists()

    def test_restore_backup_verifies_hashes(self, tmp_path):
        """Test that restore verifies file hashes."""
        # Create backup
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        items_file = data_dir / "items.jsonl"
        items_file.write_text('{"id": "it_001"}\n')

        backup_path = tmp_path / "backup.tar"
        create_backup(data_dir, backup_path, verbose=False)

        # Restore
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verify=True, verbose=False)

        assert result["success"]
        assert len(result["issues"]) == 0

    def test_restore_backup_manifest(self, tmp_path):
        """Test that restore returns manifest."""
        # Create backup
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        backup_path = tmp_path / "backup.tar"
        create_backup(data_dir, backup_path, verbose=False)

        # Restore
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verbose=False)

        assert result["manifest"] is not None
        assert "backup_version" in result["manifest"]


class TestVerifyBackup:
    """Tests for verify_backup function."""

    def test_verify_valid_backup(self, tmp_path):
        """Test verifying a valid backup."""
        # Create backup
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        items_file = data_dir / "items.jsonl"
        items_file.write_text('{"id": "it_001"}\n')

        backup_path = tmp_path / "backup.tar"
        create_backup(data_dir, backup_path, verbose=False)

        # Verify
        result = verify_backup(backup_path, verbose=False)

        assert result["valid"]
        assert result["manifest"] is not None
        assert len(result["issues"]) == 0

    def test_verify_invalid_tar(self, tmp_path):
        """Test verifying an invalid tar file."""
        invalid_path = tmp_path / "invalid.tar"
        invalid_path.write_text("not a tar file")

        result = verify_backup(invalid_path, verbose=False)

        assert not result["valid"]
        assert len(result["issues"]) > 0

    def test_verify_missing_manifest(self, tmp_path):
        """Test verifying backup without manifest."""
        # Create tar without manifest
        backup_path = tmp_path / "no_manifest.tar"
        with tarfile.open(backup_path, "w") as tar:
            items_file = tmp_path / "items.jsonl"
            items_file.write_text('{"id": "it_001"}\n')
            tar.add(items_file, arcname="items.jsonl")

        result = verify_backup(backup_path, verbose=False)

        assert not result["valid"]
        assert "manifest" in result["issues"][0].lower()


class TestListBackups:
    """Tests for list_backups function."""

    def test_list_backups_empty_dir(self, tmp_path):
        """Test listing backups in empty directory."""
        backups = list_backups(tmp_path)
        assert backups == []

    def test_list_backups_multiple(self, tmp_path):
        """Test listing multiple backups."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create 2 backups
        backup1 = tmp_path / "backup1.tar"
        create_backup(data_dir, backup1, verbose=False)

        backup2 = tmp_path / "backup2.tar"
        create_backup(data_dir, backup2, verbose=False)

        backups = list_backups(tmp_path)
        assert len(backups) == 2

        # Should be sorted by creation time (newest first)
        for b in backups:
            assert "created_at" in b
            assert "path" in b


class TestFormatBackupReport:
    """Tests for format_backup_report function."""

    def test_format_backup_report(self):
        """Test formatting backup manifest as report."""
        manifest = {
            "backup_version": "1.0",
            "created_at": "2025-01-01T00:00:00Z",
            "source_dir": "/path/to/data",
            "store_type": "jsonl",
            "files": {
                "items.jsonl": {"size": 1024, "hash": "abc123def456"},
            },
            "counts": {
                "items": 10,
                "events": 5,
            },
        }

        report = format_backup_report(manifest)

        assert "BACKUP REPORT" in report
        assert "items.jsonl" in report
        assert "items: 10" in report


class TestRoundTrip:
    """Tests for complete backup/restore round trips."""

    def test_roundtrip_preserves_data(self, tmp_path):
        """Test that backup/restore preserves all data."""
        # Setup source data
        data_dir = tmp_path / "source"
        data_dir.mkdir()

        items = [
            {"id": "it_001", "type": "Q", "title": "Question One"},
            {"id": "it_002", "type": "M", "title": "Message Two"},
        ]
        events = [
            {"id": "ev_001", "name": "item.created", "episode_id": "ep_001", "seq": 1},
            {"id": "ev_002", "name": "item.created", "episode_id": "ep_001", "seq": 2},
        ]

        (data_dir / "items.jsonl").write_text(
            "\n".join(json.dumps(i) for i in items) + "\n"
        )
        (data_dir / "qdpi_events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )

        # Create backup
        backup_path = tmp_path / "backup.tar"
        manifest = create_backup(data_dir, backup_path, verbose=False)

        # Verify counts in manifest
        assert manifest["counts"]["items"] == 2
        assert manifest["counts"]["events"] == 2

        # Restore to new location
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verbose=False)

        assert result["success"]

        # Verify restored data
        restored_items = []
        with open(restore_dir / "items.jsonl") as f:
            for line in f:
                if line.strip():
                    restored_items.append(json.loads(line))

        assert len(restored_items) == 2
        assert restored_items[0]["id"] == "it_001"
        assert restored_items[1]["title"] == "Message Two"

    def test_roundtrip_with_sqlite(self, tmp_path):
        """Test backup/restore with SQLite database."""
        # Setup source with SQLite
        data_dir = tmp_path / "source"
        data_dir.mkdir()

        # Create SQLite database with data
        import sqlite3
        db_path = data_dir / "fieldkit.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE items (id TEXT, title TEXT)")
        conn.execute("INSERT INTO items VALUES ('it_001', 'Test Item')")
        conn.commit()
        conn.close()

        # Create backup
        backup_path = tmp_path / "backup.tar"
        manifest = create_backup(data_dir, backup_path, include_sqlite=True, verbose=False)

        assert manifest["store_type"] == "sqlite"

        # Restore
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verbose=False)

        assert result["success"]
        assert (restore_dir / "fieldkit.db").exists()

        # Verify SQLite data
        conn = sqlite3.connect(str(restore_dir / "fieldkit.db"))
        row = conn.execute("SELECT title FROM items WHERE id = 'it_001'").fetchone()
        conn.close()

        assert row[0] == "Test Item"


class TestGoldenFlowBackup:
    """Integration tests with golden flow data."""

    def test_backup_golden_flow_data(self, tmp_path):
        """Test backing up golden flow style data."""
        # Simulate golden flow data structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Network
        network = {
            "id": "nw_001",
            "title": "Field",
            "scope": "private",
            "root_episode_id": "ep_001",
            "created_by": "user",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        (data_dir / "networks.jsonl").write_text(json.dumps(network) + "\n")

        # Episode
        episode = {
            "id": "ep_001",
            "network_id": "nw_001",
            "title": "First Session",
            "scope": "private",
            "status": "active",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        (data_dir / "episodes.jsonl").write_text(json.dumps(episode) + "\n")

        # Items (Q then M)
        items = [
            {
                "id": "it_001",
                "network_id": "nw_001",
                "episode_id": "ep_001",
                "scope": "private",
                "type": "Q",
                "title": "Test Question",
                "position": {"x": 0, "y": 0, "z": 0},
                "provenance": {},
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
            {
                "id": "it_002",
                "network_id": "nw_001",
                "episode_id": "ep_001",
                "scope": "private",
                "type": "M",
                "title": "Test Response",
                "position": {"x": 1, "y": 0, "z": 0},
                "provenance": {},
                "created_at": now_iso(),
                "updated_at": now_iso(),
            },
        ]
        (data_dir / "items.jsonl").write_text(
            "\n".join(json.dumps(i) for i in items) + "\n"
        )

        # Bond
        bond = {
            "id": "bd_001",
            "network_id": "nw_001",
            "episode_id": "ep_001",
            "scope": "private",
            "input_item_ids": ["it_001"],
            "output_item_id": "it_002",
            "status": "executed",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        (data_dir / "bonds.jsonl").write_text(json.dumps(bond) + "\n")

        # Events
        events = [
            {
                "id": "ev_001",
                "episode_id": "ep_001",
                "seq": 1,
                "name": "session.started",
                "qdpi": "Q",
                "direction": "user→field",
                "timestamp": now_iso(),
                "created_at": now_iso(),
            },
            {
                "id": "ev_002",
                "episode_id": "ep_001",
                "seq": 2,
                "name": "item.created",
                "qdpi": "Q",
                "direction": "user→field",
                "refs": {"item_id": "it_001"},
                "timestamp": now_iso(),
                "created_at": now_iso(),
            },
        ]
        (data_dir / "qdpi_events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )

        # Create backup
        backup_path = tmp_path / "golden_backup.tar"
        manifest = create_backup(data_dir, backup_path, verbose=False)

        # Verify counts
        assert manifest["counts"]["items"] == 2
        assert manifest["counts"]["bonds"] == 1
        assert manifest["counts"]["episodes"] == 1
        assert manifest["counts"]["networks"] == 1
        assert manifest["counts"]["events"] == 2

        # Restore and verify
        restore_dir = tmp_path / "restored"
        result = restore_backup(backup_path, restore_dir, verbose=False)

        assert result["success"]

        # Count restored items
        restored_count = 0
        with open(restore_dir / "items.jsonl") as f:
            for line in f:
                if line.strip():
                    restored_count += 1

        assert restored_count == 2


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

    test_classes = [
        TestBackupHelpers,
        TestCreateBackup,
        TestRestoreBackup,
        TestVerifyBackup,
        TestListBackups,
        TestFormatBackupReport,
        TestRoundTrip,
        TestGoldenFlowBackup,
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
                        print(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                    except Exception as e:
                        failed += 1
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
