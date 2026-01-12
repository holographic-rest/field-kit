"""
Field-Kit v0.1 Backup & Restore (Sprint S10)

Implements backup/export and restore functionality for Field data.
Works with both JSONL and SQLite stores.

Backup format:
- tar archive containing:
  - manifest.json: metadata (timestamp, store type, counts, versions)
  - qdpi_events.jsonl: event ledger (always included)
  - items.jsonl: item snapshots
  - bonds.jsonl: bond snapshots
  - episodes.jsonl: episode snapshots
  - networks.jsonl: network snapshots
  - fieldkit.db: SQLite database (if present)

The backup is designed to be:
- Self-contained: all data needed to restore
- Verifiable: manifest includes counts and checksums
- Portable: tar format works everywhere
"""

import json
import hashlib
import tarfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _count_jsonl_lines(file_path: Path) -> int:
    """Count lines in a JSONL file."""
    if not file_path.exists():
        return 0
    count = 0
    with open(file_path, "r") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def create_backup(
    data_dir: Path,
    output_path: Path,
    include_sqlite: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Create a backup archive of Field data.

    Args:
        data_dir: Directory containing data files
        output_path: Path for output tar file
        include_sqlite: Include SQLite database if present
        verbose: Print progress

    Returns:
        Dict with backup metadata (same as manifest)
    """
    data_dir = Path(data_dir)
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Files to include
    jsonl_files = [
        "qdpi_events.jsonl",
        "items.jsonl",
        "bonds.jsonl",
        "episodes.jsonl",
        "networks.jsonl",
    ]

    # Also check for events.jsonl (older name)
    if (data_dir / "events.jsonl").exists() and not (data_dir / "qdpi_events.jsonl").exists():
        jsonl_files[0] = "events.jsonl"

    # Build manifest
    manifest = {
        "backup_version": "1.0",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_dir": str(data_dir),
        "files": {},
        "counts": {},
        "store_type": "jsonl",  # Default, will update if sqlite found
    }

    # Create tar archive
    with tarfile.open(output_path, "w") as tar:
        # Add JSONL files
        for filename in jsonl_files:
            file_path = data_dir / filename
            if file_path.exists():
                tar.add(file_path, arcname=filename)
                manifest["files"][filename] = {
                    "hash": _compute_file_hash(file_path),
                    "size": file_path.stat().st_size,
                }

                # Count records
                count_key = filename.replace(".jsonl", "").replace("qdpi_", "")
                manifest["counts"][count_key] = _count_jsonl_lines(file_path)

                if verbose:
                    print(f"  Added {filename}: {manifest['counts'][count_key]} records")

        # Add SQLite database if present and requested
        sqlite_path = data_dir / "fieldkit.db"
        if include_sqlite and sqlite_path.exists():
            tar.add(sqlite_path, arcname="fieldkit.db")
            manifest["files"]["fieldkit.db"] = {
                "hash": _compute_file_hash(sqlite_path),
                "size": sqlite_path.stat().st_size,
            }
            manifest["store_type"] = "sqlite"
            if verbose:
                print(f"  Added fieldkit.db ({sqlite_path.stat().st_size} bytes)")

        # Write manifest to temp file and add to tar
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(manifest, f, indent=2)
            temp_manifest = f.name

        tar.add(temp_manifest, arcname="manifest.json")
        Path(temp_manifest).unlink()

    if verbose:
        print(f"Backup created: {output_path}")
        print(f"  Total files: {len(manifest['files'])}")
        print(f"  Store type: {manifest['store_type']}")

    return manifest


def restore_backup(
    input_path: Path,
    output_dir: Path,
    verify: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Restore Field data from a backup archive.

    Args:
        input_path: Path to backup tar file
        output_dir: Directory to restore to
        verify: Verify file hashes after restore
        verbose: Print progress

    Returns:
        Dict with restore status and any issues
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "success": True,
        "restored_files": [],
        "manifest": None,
        "issues": [],
    }

    # Extract archive
    with tarfile.open(input_path, "r") as tar:
        # First, extract and read manifest
        manifest_member = tar.getmember("manifest.json")
        tar.extract(manifest_member, output_dir)
        manifest_path = output_dir / "manifest.json"

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        result["manifest"] = manifest

        if verbose:
            print(f"Restoring backup from {input_path}")
            print(f"  Backup created: {manifest['created_at']}")
            print(f"  Store type: {manifest['store_type']}")

        # Extract all other files
        for member in tar.getmembers():
            if member.name == "manifest.json":
                continue

            tar.extract(member, output_dir)
            result["restored_files"].append(member.name)

            if verbose:
                print(f"  Restored: {member.name}")

    # Verify file hashes
    if verify:
        for filename, info in manifest["files"].items():
            file_path = output_dir / filename
            if file_path.exists():
                actual_hash = _compute_file_hash(file_path)
                if actual_hash != info["hash"]:
                    issue = f"Hash mismatch for {filename}: expected {info['hash'][:8]}..., got {actual_hash[:8]}..."
                    result["issues"].append(issue)
                    result["success"] = False
                    if verbose:
                        print(f"  WARNING: {issue}")
            else:
                issue = f"Missing file: {filename}"
                result["issues"].append(issue)
                result["success"] = False
                if verbose:
                    print(f"  WARNING: {issue}")

    if verbose:
        if result["success"]:
            print("Restore completed successfully!")
        else:
            print(f"Restore completed with {len(result['issues'])} issues")

    return result


def verify_backup(
    backup_path: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Verify a backup archive without extracting.

    Args:
        backup_path: Path to backup tar file
        verbose: Print progress

    Returns:
        Dict with verification status
    """
    backup_path = Path(backup_path)

    result = {
        "valid": True,
        "manifest": None,
        "issues": [],
    }

    try:
        with tarfile.open(backup_path, "r") as tar:
            # Check for manifest
            try:
                manifest_info = tar.getmember("manifest.json")
            except KeyError:
                result["valid"] = False
                result["issues"].append("Missing manifest.json")
                return result

            # Extract and parse manifest
            f = tar.extractfile(manifest_info)
            manifest = json.load(f)
            result["manifest"] = manifest

            if verbose:
                print(f"Verifying backup: {backup_path}")
                print(f"  Backup version: {manifest.get('backup_version', 'unknown')}")
                print(f"  Created: {manifest['created_at']}")

            # Verify all listed files are present
            for filename in manifest["files"].keys():
                try:
                    tar.getmember(filename)
                    if verbose:
                        print(f"  Found: {filename}")
                except KeyError:
                    result["valid"] = False
                    issue = f"Listed file missing from archive: {filename}"
                    result["issues"].append(issue)
                    if verbose:
                        print(f"  MISSING: {filename}")

            # Check for expected counts
            if verbose:
                print("  Counts:")
                for key, count in manifest.get("counts", {}).items():
                    print(f"    {key}: {count}")

    except tarfile.TarError as e:
        result["valid"] = False
        result["issues"].append(f"Invalid tar archive: {e}")

    if verbose:
        if result["valid"]:
            print("Backup verification passed!")
        else:
            print(f"Backup verification FAILED: {len(result['issues'])} issues")

    return result


def export_episode(
    data_dir: Path,
    episode_id: str,
    output_path: Path,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Export a single episode to JSON.

    Args:
        data_dir: Data directory
        episode_id: Episode ID to export
        output_path: Path for output JSON file
        verbose: Print progress

    Returns:
        Dict with export metadata
    """
    from .store_jsonl import Store

    data_dir = Path(data_dir)
    output_path = Path(output_path)

    store = Store(data_dir)

    # Load episode data
    episode = store.get_episode(episode_id)
    if not episode:
        raise ValueError(f"Episode not found: {episode_id}")

    # Load related data
    events = store.load_events(episode_id=episode_id)
    items = store.load_items(filters={"episode_id": episode_id})
    bonds = store.load_bonds(filters={"episode_id": episode_id})

    # Build export object
    export = {
        "export_version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "episode_id": episode_id,
        "episode": episode,
        "items": items,
        "bonds": bonds,
        "events": events,
        "counts": {
            "items": len(items),
            "bonds": len(bonds),
            "events": len(events),
        },
    }

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(export, f, indent=2)

    if verbose:
        print(f"Exported episode {episode_id} to {output_path}")
        print(f"  Items: {len(items)}")
        print(f"  Bonds: {len(bonds)}")
        print(f"  Events: {len(events)}")

    return export


def list_backups(
    directory: Path,
) -> List[Dict[str, Any]]:
    """
    List backup files in a directory.

    Args:
        directory: Directory to search

    Returns:
        List of backup info dicts
    """
    directory = Path(directory)
    backups = []

    for path in directory.glob("*.tar"):
        try:
            result = verify_backup(path, verbose=False)
            if result["valid"] and result["manifest"]:
                backups.append({
                    "path": str(path),
                    "created_at": result["manifest"]["created_at"],
                    "store_type": result["manifest"].get("store_type", "unknown"),
                    "counts": result["manifest"].get("counts", {}),
                })
        except Exception:
            continue

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


def format_backup_report(manifest: Dict[str, Any]) -> str:
    """Format backup manifest as human-readable report."""
    lines = [
        "=" * 60,
        "BACKUP REPORT",
        "=" * 60,
        "",
        f"Backup Version: {manifest.get('backup_version', 'unknown')}",
        f"Created: {manifest['created_at']}",
        f"Source: {manifest.get('source_dir', 'unknown')}",
        f"Store Type: {manifest.get('store_type', 'unknown')}",
        "",
        "--- Files ---",
    ]

    for filename, info in manifest.get("files", {}).items():
        size_kb = info["size"] / 1024
        lines.append(f"  {filename}: {size_kb:.1f} KB (hash: {info['hash'][:8]}...)")

    lines.append("")
    lines.append("--- Record Counts ---")

    for key, count in manifest.get("counts", {}).items():
        lines.append(f"  {key}: {count}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
