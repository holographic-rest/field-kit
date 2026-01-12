# SQLite Storage Architecture

> **Sprint S10 — January 2025**

This document describes the SQLite-based storage layer implemented as an opt-in alternative to JSONL.

---

## Overview

SQLite storage provides:
- **Structured queries**: SQL for complex filtering and joins
- **FTS5 full-text search**: Fast keyword search across items
- **WAL mode**: Better concurrency and crash recovery
- **Single-file storage**: Portable database in `fieldkit.db`

JSONL remains the **default** store. SQLite is opt-in.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│                        (cli.py, etc)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Store Interface                           │
│   upsert_*() / load_*() / get_*() / append_event()          │
└─────────────────────────────────────────────────────────────┘
          │                                     │
          ▼                                     ▼
┌─────────────────────┐           ┌─────────────────────────┐
│   Store (JSONL)     │           │    SQLiteStore          │
│   (store_jsonl.py)  │           │   (store_sqlite.py)     │
│                     │           │                         │
│   *.jsonl files     │           │   fieldkit.db           │
│   One file per type │           │   + FTS5 (if available) │
└─────────────────────┘           └─────────────────────────┘
        DEFAULT                          OPT-IN
```

---

## Schema

### Events Table (Append-Only Ledger)

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    qdpi TEXT NOT NULL,
    direction TEXT NOT NULL,
    actor_ref TEXT,          -- JSON blob
    refs TEXT,               -- JSON blob
    payload TEXT,            -- JSON blob (legacy compat)
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(episode_id, seq)
);
```

Events are **append-only**. Never update or delete events.

### Projection Tables

Items, bonds, episodes, and networks are **projections** derived from events.

```sql
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    position TEXT,           -- JSON blob
    provenance TEXT,         -- JSON blob
    handles TEXT,            -- JSON blob
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    raw_json TEXT NOT NULL   -- Full JSON for compatibility
);

CREATE TABLE bonds (...);
CREATE TABLE episodes (...);
CREATE TABLE networks (...);
```

Each projection table includes a `raw_json` column storing the complete JSON object for compatibility with code expecting dict-like access.

### FTS5 Full-Text Search

When FTS5 is available:

```sql
CREATE VIRTUAL TABLE items_fts USING fts5(
    id, title, body,
    content='items',
    content_rowid='rowid'
);
```

Triggers keep FTS in sync with the items table.

---

## Usage

### Creating a SQLite Store

```python
from fieldkit.store_sqlite import SQLiteStore

store = SQLiteStore(data_dir=Path("./data"))
store.init()  # Creates schema and FTS5 if available

# Use same interface as JSONL store
store.upsert_item(item)
result = store.get_item(item_id)
items = store.load_items(filters={"type": "Q"})
```

### FTS5 Search

```python
# Search items by keyword
results = store.search_items("neural network", limit=10)

# Falls back to LIKE queries if FTS5 unavailable
```

### Checking FTS5 Status

```python
if store.fts5_enabled:
    print("FTS5 search available")
else:
    print("Using LIKE fallback")
```

---

## Migration

### CLI Command

```bash
python3 src/cli.py migrate:jsonl-to-sqlite
```

Migrates all JSONL data to SQLite, creating `fieldkit.db`.

### Programmatic Migration

```python
from fieldkit.store_sqlite import migrate_jsonl_to_sqlite

counts = migrate_jsonl_to_sqlite(
    data_dir=Path("./data"),
    sqlite_path=Path("./data/fieldkit.db"),  # optional
    verbose=True
)

print(counts)
# {'networks': 1, 'episodes': 2, 'items': 50, 'bonds': 10, 'events': 200}
```

---

## WAL Mode

SQLite uses WAL (Write-Ahead Logging) mode for:
- **Better concurrency**: Readers don't block writers
- **Crash safety**: Atomic commits survive power loss
- **Performance**: Fewer fsync calls

Enabled automatically:
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

---

## Store Interface Contract

SQLiteStore implements the same interface as the JSONL Store:

| Method | Description |
|--------|-------------|
| `upsert_network(network)` | Insert or update network |
| `load_networks(filters=None)` | Load all networks |
| `get_network(id)` | Get single network |
| `upsert_episode(episode)` | Insert or update episode |
| `load_episodes(filters=None)` | Load all episodes |
| `get_episode(id)` | Get single episode |
| `upsert_item(item)` | Insert or update item |
| `load_items(filters=None)` | Load all items |
| `get_item(id)` | Get single item |
| `search_items(query, limit)` | FTS5/LIKE search |
| `upsert_bond(bond)` | Insert or update bond |
| `load_bonds(filters=None)` | Load all bonds |
| `get_bond(id)` | Get single bond |
| `append_event(event)` | Append to event ledger |
| `load_events(episode_id=None)` | Load events |
| `get_event(id)` | Get single event |
| `is_initialized()` | Check if store has data |
| `clear()` | Clear all data (testing) |
| `compute_credits_balance(episode_id)` | Get credits balance |

---

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/store_sqlite.py` | SQLiteStore implementation |
| `tests/test_store_sqlite.py` | Unit tests (22 tests) |

---

## Limitations

- **No auto-sync**: Changes to JSONL aren't reflected in SQLite
- **No encryption**: SQLCipher integration is future work
- **Single-writer**: WAL allows concurrent reads, but writes are serialized
- **No remote**: SQLite is local-only

---

## Future Work

1. **SQLCipher encryption**: At-rest encryption with OS keychain
2. **Auto-migration**: Detect and migrate on startup
3. **Hybrid mode**: Write to both stores for redundancy
4. **Query optimization**: Add indexes based on access patterns

---

## See Also

- [BACKUP_EXPORT.md](BACKUP_EXPORT.md) — Backup and restore functionality
- Research: `research/12-23-2025-research/local_first/05_local_first_storage_privacy.md`
