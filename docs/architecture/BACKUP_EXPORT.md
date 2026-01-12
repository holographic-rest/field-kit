# Backup & Export Architecture

> **Sprint S10 — January 2025**

This document describes the backup, export, and restore functionality for Field data.

---

## Overview

Field-Kit provides:
- **Full backups**: Archive all data to a portable tar file
- **Verification**: SHA-256 hashes for integrity checking
- **Restoration**: Restore to any directory with verification
- **Episode export**: Export single episodes to JSON

---

## Backup Format

Backups are tar archives containing:

```
backup.tar
├── manifest.json       # Metadata, counts, hashes
├── qdpi_events.jsonl   # Event ledger (always included)
├── items.jsonl         # Item snapshots
├── bonds.jsonl         # Bond snapshots
├── episodes.jsonl      # Episode snapshots
├── networks.jsonl      # Network snapshots
└── fieldkit.db         # SQLite database (if present)
```

### Manifest Structure

```json
{
  "backup_version": "1.0",
  "created_at": "2025-01-01T00:00:00Z",
  "source_dir": "/path/to/data",
  "store_type": "jsonl",
  "files": {
    "items.jsonl": {
      "hash": "sha256...",
      "size": 1024
    },
    "qdpi_events.jsonl": {
      "hash": "sha256...",
      "size": 2048
    }
  },
  "counts": {
    "items": 50,
    "bonds": 10,
    "events": 200
  }
}
```

---

## CLI Commands

### Create Backup

```bash
# Default: creates backup_TIMESTAMP.tar in data directory
python3 src/cli.py backup:create

# Specify output path
python3 src/cli.py backup:create --output /path/to/backup.tar

# Exclude SQLite database
python3 src/cli.py backup:create --no-sqlite
```

### Restore Backup

```bash
# Restore to auto-generated directory
python3 src/cli.py backup:restore /path/to/backup.tar

# Specify output directory
python3 src/cli.py backup:restore /path/to/backup.tar --output-dir /path/to/restore

# Skip hash verification
python3 src/cli.py backup:restore /path/to/backup.tar --no-verify
```

### Verify Backup

```bash
python3 src/cli.py backup:verify /path/to/backup.tar
```

Output:
```
Verifying backup: /path/to/backup.tar
  Backup version: 1.0
  Created: 2025-01-01T00:00:00Z
  Found: items.jsonl
  Found: qdpi_events.jsonl
  Counts:
    items: 50
    events: 200
Backup verification passed!
```

### List Backups

```bash
# List backups in data directory
python3 src/cli.py backup:list

# List backups in specific directory
python3 src/cli.py backup:list --directory /path/to/backups
```

---

## Python API

### Create Backup

```python
from fieldkit.backup import create_backup

manifest = create_backup(
    data_dir=Path("./data"),
    output_path=Path("./backup.tar"),
    include_sqlite=True,
    verbose=True
)

print(f"Backed up {manifest['counts']['items']} items")
```

### Restore Backup

```python
from fieldkit.backup import restore_backup

result = restore_backup(
    input_path=Path("./backup.tar"),
    output_dir=Path("./restored"),
    verify=True,
    verbose=True
)

if result["success"]:
    print("Restore complete!")
else:
    print(f"Issues: {result['issues']}")
```

### Verify Backup

```python
from fieldkit.backup import verify_backup

result = verify_backup(Path("./backup.tar"), verbose=True)

if result["valid"]:
    print("Backup is valid")
    print(f"Contains: {result['manifest']['counts']}")
```

### Export Episode

```python
from fieldkit.backup import export_episode

export = export_episode(
    data_dir=Path("./data"),
    episode_id="ep_001",
    output_path=Path("./episode_export.json"),
    verbose=True
)

print(f"Exported {export['counts']['items']} items")
```

### List Backups

```python
from fieldkit.backup import list_backups

backups = list_backups(Path("./backups"))
for b in backups:
    print(f"{b['path']}: {b['created_at']}")
```

---

## Verification

### Hash Verification

All files in the backup have SHA-256 hashes stored in the manifest. During restore with `verify=True`:

1. Each file is extracted
2. Hash is computed
3. Compared against manifest
4. Any mismatch is reported

### Integrity Guarantees

- **Atomic writes**: Tar is created as a single operation
- **Complete verification**: All listed files must be present
- **Hash validation**: Bit-for-bit integrity check

---

## Design Decisions

### Why tar format?

- **Universal**: Works on all platforms
- **Single file**: Easy to move, copy, store
- **No dependencies**: Python stdlib only
- **Streamable**: Can process without full extraction

### Why separate manifest?

- **Quick inspection**: Check backup without extracting
- **Version tracking**: Know backup format version
- **Counts verification**: Validate expected vs actual

### Why SHA-256?

- **Strong integrity**: Cryptographic hash
- **Fast**: Hardware acceleration available
- **Standard**: Widely used and trusted

---

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/backup.py` | Backup/restore implementation |
| `tests/test_backup_restore.py` | Unit tests (20 tests) |

---

## Functions Reference

| Function | Description |
|----------|-------------|
| `create_backup(data_dir, output_path, include_sqlite, verbose)` | Create backup archive |
| `restore_backup(input_path, output_dir, verify, verbose)` | Restore from archive |
| `verify_backup(backup_path, verbose)` | Verify without extracting |
| `export_episode(data_dir, episode_id, output_path, verbose)` | Export single episode |
| `list_backups(directory)` | List valid backups |
| `format_backup_report(manifest)` | Format manifest as report |

---

## Future Work

1. **Incremental backups**: Only backup changes since last backup
2. **Compression**: gzip or zstd compression option
3. **Encryption**: Encrypt backup archives
4. **Remote storage**: S3/GCS upload integration
5. **Scheduled backups**: Automatic periodic backups

---

## See Also

- [STORAGE_SQLITE.md](STORAGE_SQLITE.md) — SQLite storage layer
- Research: `research/12-23-2025-research/local_first/05_local_first_storage_privacy.md`
