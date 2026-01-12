# S10: Storage & Privacy
**Days:** Jan 4 (1 day)  
**Theme:** SQLite migration + encryption + backup

---

## Objective

Migrate from JSONL to SQLite with FTS5 for full-text search, add encryption-at-rest, and implement backup/export. This completes the local-first storage foundation.

---

## Why This Matters for Fellowship Narrative

- **Demonstrates local-first**: SQLite is portable, no cloud needed
- **Shows security thinking**: Encryption-at-rest protects sensitive content
- **Enables auditability**: SQLite + event sourcing = replayable history
- **Proves recoverability**: Backup/export ensures data safety

---

## Inputs

### Research Documents
- `research/12-23-2025-research/local_first/05_local_first_storage_privacy.md` - Storage stack choices
- `research/12-23-2025-research/ledger_graph/02_event_sourced_graph_indexing.md.md` - Event sourcing

### Repo Modules
- `src/fieldkit/store_jsonl.py` - Current JSONL storage
- `prototype/data/` - Current data directory

---

## Tasks

### Task 1: Design SQLite Schema
1. Create `src/fieldkit/store_sqlite.py` with tables:
   - `events` (ledger: append-only)
   - `items`, `bonds`, `episodes`, `networks` (read model)
   - `evidence_bundles` (evidence registry)
   - FTS5 virtual table for full-text search
2. Design for event sourcing: projections rebuildable from events

### Task 2: Implement SQLite Store
1. Create `SQLiteStore` class:
   - Implements same interface as `JSONLStore`
   - Migrates data from JSONL on first run
   - Maintains backward compatibility (can read JSONL)
2. Add FTS5 indexing for text search

### Task 3: Add Encryption
1. Integrate SQLCipher (or equivalent):
   - Encrypt database file
   - Store key in OS keychain (Electron safeStorage or native)
   - Document key derivation (PBKDF2 or Argon2id)
2. Make encryption optional (flag: `--encrypt`)

### Task 4: Implement Backup/Export
1. Create `src/fieldkit/backup.py` with:
   - `export_episode()`: Full episode JSON (DB + Vault)
   - `backup_database()`: SQLite backup API
   - `restore_from_backup()`: Restore from backup
2. Add CLI commands: `backup:create`, `backup:restore`

### Task 5: Test Migration
1. Test JSONL → SQLite migration:
   - Load existing JSONL data
   - Migrate to SQLite
   - Verify all data present
   - Run golden flow on SQLite store
2. Test encryption (if implemented)

### Task 6: Test Backup/Restore
1. Create backup
2. Restore from backup
3. Verify data integrity (run golden flow)

---

## Acceptance Criteria

- [ ] SQLite schema designed and implemented
- [ ] SQLite store works (same interface as JSONL)
- [ ] FTS5 indexing works (full-text search)
- [ ] Migration from JSONL works (backward compatible)
- [ ] Encryption exists (optional, if time permits)
- [ ] Backup/export works (create + restore)
- [ ] Golden flow runs on SQLite store
- [ ] Documentation: `docs/architecture/STORAGE_SQLITE.md`

---

## Test Plan

### Test 1: SQLite Store
```python
from fieldkit.store_sqlite import SQLiteStore
store = SQLiteStore(":memory:")  # In-memory for testing
store.init()
item_id = store.create_item(...)
item = store.get_item(item_id)
assert item is not None
```
**Expected:** SQLite store works like JSONL store

### Test 2: FTS5 Search
```python
results = store.search_items("test query", limit=10)
assert len(results) > 0
```
**Expected:** Full-text search works

### Test 3: Migration
```bash
python3 src/cli.py migrate:jsonl-to-sqlite --data-dir prototype/data
python3 prototype/scripts/run_golden_flow.py --data-dir prototype/data
```
**Expected:** Migration succeeds; golden flow runs

### Test 4: Backup/Restore
```bash
python3 src/cli.py backup:create --output backup.tar
python3 src/cli.py backup:restore --input backup.tar
python3 prototype/scripts/run_golden_flow.py
```
**Expected:** Backup/restore works; data intact

---

## Documentation Outputs

1. `docs/architecture/STORAGE_SQLITE.md` - SQLite schema and design
2. `docs/architecture/BACKUP_EXPORT.md` - Backup/restore procedures
3. Update `README.md` with migration instructions

---

## Fallback Plan

If SQLite migration is too complex:
- **Fallback:** Keep JSONL, add FTS5 sidecar (Tantivy) only
- **Minimum deliverable:** Backup/export works
- **Document:** Plan to migrate to SQLite post-fellowship

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/store_jsonl.py`, `prototype/data/` directory)
- **Research docs:** All paths match actual files (including `.md.md` extension for event sourcing doc)

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S10: Storage & Privacy.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S10_storage_privacy.md
Also read: research/12-23-2025-research/local_first/05_local_first_storage_privacy.md

Your goal:
1. Design SQLite schema (events, items, bonds, episodes, FTS5)
2. Implement SQLite store (same interface as JSONL)
3. Add encryption (SQLCipher, optional)
4. Implement backup/export (create + restore)
5. Test migration (JSONL → SQLite)
6. Test backup/restore

Constraints:
- Must maintain backward compatibility (read JSONL)
- Encryption is optional (flag)
- Backup format: tar with DB + Vault + manifest
- Must preserve event sourcing (events table is source of truth)

After completion:
- Verify golden flow runs on SQLite
- Test backup/restore works
- Document SQLite architecture

Start by designing the SQLite schema.
```

