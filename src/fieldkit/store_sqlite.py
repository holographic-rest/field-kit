"""
Field-Kit v0.1 SQLite Store (Sprint S10)

SQLite-based storage layer with FTS5 full-text search support.
Designed as an opt-in alternative to JSONL store.

Key concepts:
- Events table is append-only source of truth (event sourcing)
- Projection tables (items, bonds, episodes, networks) are derived views
- FTS5 virtual table for full-text search when available
- Same interface as Store from store_jsonl.py for drop-in compatibility

Schema:
- events: Append-only event ledger
- items: Latest item snapshots by id
- bonds: Latest bond snapshots by id
- episodes: Latest episode snapshots by id
- networks: Latest network snapshots by id
- items_fts: FTS5 virtual table (if supported)
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


def _check_fts5_support() -> bool:
    """Check if FTS5 is available in the sqlite3 build."""
    try:
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("PRAGMA compile_options;")
        options = [row[0] for row in cur.fetchall()]
        conn.close()
        # FTS5 is usually enabled by default in modern SQLite
        return "ENABLE_FTS5" in options or True  # Optimistically try
    except Exception:
        return False


# Check FTS5 support at module load
FTS5_AVAILABLE = _check_fts5_support()


# === Schema definitions ===

SCHEMA_SQL = """
-- Events table (append-only ledger, source of truth)
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    qdpi TEXT NOT NULL,
    direction TEXT NOT NULL,
    actor_ref TEXT,
    refs TEXT,  -- JSON blob
    payload TEXT,  -- JSON blob
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(episode_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_events_episode_seq ON events(episode_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);

-- Items table (projection, latest snapshot by id)
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    position TEXT,  -- JSON blob
    provenance TEXT,  -- JSON blob
    handles TEXT,  -- JSON blob
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    created_by_actor TEXT,  -- JSON blob
    schema_version INTEGER DEFAULT 1,
    raw_json TEXT NOT NULL  -- Full original JSON for compatibility
);

CREATE INDEX IF NOT EXISTS idx_items_episode ON items(episode_id);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);

-- Bonds table (projection, latest snapshot by id)
CREATE TABLE IF NOT EXISTS bonds (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    input_item_ids TEXT,  -- JSON array
    prompt_text TEXT,
    status TEXT NOT NULL,
    output_item_id TEXT,
    intent_type TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    executed_at TEXT,
    execution_count INTEGER,
    last_error TEXT,  -- JSON blob
    created_by_actor TEXT,  -- JSON blob
    bond_kind TEXT,
    link_text_forward TEXT,
    link_text_return TEXT,
    schema_version INTEGER DEFAULT 1,
    raw_json TEXT NOT NULL  -- Full original JSON for compatibility
);

CREATE INDEX IF NOT EXISTS idx_bonds_episode ON bonds(episode_id);
CREATE INDEX IF NOT EXISTS idx_bonds_status ON bonds(status);

-- Episodes table (projection, latest snapshot by id)
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    network_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    last_active_at TEXT,
    ended_at TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ordinal INTEGER,
    curated_item_ids TEXT,  -- JSON array
    curated_bond_ids TEXT,  -- JSON array
    created_by_actor TEXT,  -- JSON blob
    schema_version INTEGER DEFAULT 1,
    raw_json TEXT NOT NULL  -- Full original JSON for compatibility
);

-- Networks table (projection, latest snapshot by id)
CREATE TABLE IF NOT EXISTS networks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    schema_version INTEGER DEFAULT 1,
    raw_json TEXT NOT NULL  -- Full original JSON for compatibility
);

-- Metadata table for store info
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

FTS5_SCHEMA_SQL = """
-- FTS5 virtual table for full-text search on items
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    id,
    title,
    body,
    content='items',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, id, title, body)
    VALUES (new.rowid, new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, id, title, body)
    VALUES ('delete', old.rowid, old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, id, title, body)
    VALUES ('delete', old.rowid, old.id, old.title, old.body);
    INSERT INTO items_fts(rowid, id, title, body)
    VALUES (new.rowid, new.id, new.title, new.body);
END;
"""


@dataclass
class SQLiteStore:
    """SQLite-based store for Field-Kit v0.1."""

    db_path: Path
    data_dir: Path
    _conn: Optional[sqlite3.Connection] = None
    _seq_cache: Dict[str, int] = None
    _fts5_enabled: bool = False

    def __init__(self, data_dir: Optional[Path] = None, db_path: Optional[Path] = None):
        """
        Initialize SQLite store.

        Args:
            data_dir: Directory for data files (default: prototype/data)
            db_path: Path to SQLite database file (default: data_dir/fieldkit.db)
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            from .store_jsonl import _get_default_data_dir
            self.data_dir = _get_default_data_dir()

        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.data_dir / "fieldkit.db"

        self._seq_cache = {}
        self._fts5_enabled = False
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency and crash safety
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init(self):
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript(SCHEMA_SQL)

        # Try to enable FTS5
        if FTS5_AVAILABLE:
            try:
                conn.executescript(FTS5_SCHEMA_SQL)
                self._fts5_enabled = True
            except sqlite3.OperationalError:
                # FTS5 not available, continue without it
                self._fts5_enabled = False

        # Store metadata
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("schema_version", "1")
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("fts5_enabled", str(self._fts5_enabled))
        )
        conn.commit()

    @property
    def fts5_enabled(self) -> bool:
        """Check if FTS5 is enabled for this store."""
        return self._fts5_enabled

    # === File path compatibility properties ===

    @property
    def items_file(self) -> Path:
        """For compatibility with JSONL store interface."""
        return self.data_dir / "items.jsonl"

    @property
    def bonds_file(self) -> Path:
        return self.data_dir / "bonds.jsonl"

    @property
    def episodes_file(self) -> Path:
        return self.data_dir / "episodes.jsonl"

    @property
    def networks_file(self) -> Path:
        return self.data_dir / "networks.jsonl"

    @property
    def events_file(self) -> Path:
        return self.data_dir / "qdpi_events.jsonl"

    # === Network operations ===

    def upsert_network(self, network):
        """Upsert a Network snapshot."""
        d = network.to_dict()
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO networks
            (id, title, created_by, created_at, updated_at, schema_version, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["title"], d.get("created_by"),
            d["created_at"], d["updated_at"],
            d.get("schema_version", 1), json.dumps(d)
        ))
        conn.commit()

    def load_networks(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Network snapshots."""
        conn = self._get_conn()
        rows = conn.execute("SELECT raw_json FROM networks").fetchall()
        networks = [json.loads(row["raw_json"]) for row in rows]
        return self._apply_filters(networks, filters)

    def get_network(self, network_id: str) -> Optional[dict]:
        """Get a single Network by id."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT raw_json FROM networks WHERE id = ?",
            (network_id,)
        ).fetchone()
        return json.loads(row["raw_json"]) if row else None

    # === Episode operations ===

    def upsert_episode(self, episode):
        """Upsert an Episode snapshot."""
        d = episode.to_dict()
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO episodes
            (id, network_id, scope, title, status, started_at, last_active_at, ended_at,
             created_by, created_at, updated_at, ordinal, curated_item_ids, curated_bond_ids,
             created_by_actor, schema_version, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["network_id"], d["scope"], d["title"], d["status"],
            d.get("started_at"), d.get("last_active_at"), d.get("ended_at"),
            d.get("created_by"), d["created_at"], d["updated_at"],
            d.get("ordinal"),
            json.dumps(d.get("curated_item_ids")) if d.get("curated_item_ids") else None,
            json.dumps(d.get("curated_bond_ids")) if d.get("curated_bond_ids") else None,
            json.dumps(d.get("created_by_actor")) if d.get("created_by_actor") else None,
            d.get("schema_version", 1), json.dumps(d)
        ))
        conn.commit()

    def load_episodes(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Episode snapshots."""
        conn = self._get_conn()
        rows = conn.execute("SELECT raw_json FROM episodes").fetchall()
        episodes = [json.loads(row["raw_json"]) for row in rows]
        return self._apply_filters(episodes, filters)

    def get_episode(self, episode_id: str) -> Optional[dict]:
        """Get a single Episode by id."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT raw_json FROM episodes WHERE id = ?",
            (episode_id,)
        ).fetchone()
        return json.loads(row["raw_json"]) if row else None

    # === Item operations ===

    def upsert_item(self, item):
        """Upsert an Item snapshot."""
        d = item.to_dict()
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO items
            (id, network_id, episode_id, scope, type, title, body, position, provenance,
             handles, created_at, updated_at, archived_at, created_by_actor, schema_version, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["network_id"], d["episode_id"], d["scope"], d["type"],
            d["title"], d.get("body"),
            json.dumps(d["position"]),
            json.dumps(d["provenance"]),
            json.dumps(d.get("handles")) if d.get("handles") else None,
            d["created_at"], d["updated_at"], d.get("archived_at"),
            json.dumps(d.get("created_by_actor")) if d.get("created_by_actor") else None,
            d.get("schema_version", 1), json.dumps(d)
        ))
        conn.commit()

    def load_items(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Item snapshots."""
        conn = self._get_conn()
        rows = conn.execute("SELECT raw_json FROM items").fetchall()
        items = [json.loads(row["raw_json"]) for row in rows]
        return self._apply_filters(items, filters)

    def get_item(self, item_id: str) -> Optional[dict]:
        """Get a single Item by id."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT raw_json FROM items WHERE id = ?",
            (item_id,)
        ).fetchone()
        return json.loads(row["raw_json"]) if row else None

    def search_items(self, query: str, limit: int = 10) -> List[dict]:
        """
        Search items using FTS5 full-text search.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of matching item dicts, ordered by relevance
        """
        conn = self._get_conn()

        if self._fts5_enabled:
            try:
                rows = conn.execute("""
                    SELECT items.raw_json
                    FROM items_fts
                    JOIN items ON items_fts.id = items.id
                    WHERE items_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit)).fetchall()
                return [json.loads(row["raw_json"]) for row in rows]
            except sqlite3.OperationalError:
                # FTS query failed, fall back to LIKE
                pass

        # Fallback: simple LIKE search
        like_query = f"%{query}%"
        rows = conn.execute("""
            SELECT raw_json FROM items
            WHERE title LIKE ? OR body LIKE ?
            LIMIT ?
        """, (like_query, like_query, limit)).fetchall()
        return [json.loads(row["raw_json"]) for row in rows]

    # === Bond operations ===

    def upsert_bond(self, bond):
        """Upsert a Bond snapshot."""
        d = bond.to_dict()
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO bonds
            (id, network_id, episode_id, scope, input_item_ids, prompt_text, status,
             output_item_id, intent_type, created_by, created_at, updated_at, archived_at,
             executed_at, execution_count, last_error, created_by_actor, bond_kind,
             link_text_forward, link_text_return, schema_version, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["network_id"], d["episode_id"], d["scope"],
            json.dumps(d["input_item_ids"]),
            d.get("prompt_text"), d["status"], d.get("output_item_id"),
            d.get("intent_type"), d.get("created_by"),
            d["created_at"], d["updated_at"], d.get("archived_at"),
            d.get("executed_at"), d.get("execution_count"),
            json.dumps(d.get("last_error")) if d.get("last_error") else None,
            json.dumps(d.get("created_by_actor")) if d.get("created_by_actor") else None,
            d.get("bond_kind"), d.get("link_text_forward"), d.get("link_text_return"),
            d.get("schema_version", 1), json.dumps(d)
        ))
        conn.commit()

    def load_bonds(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Bond snapshots."""
        conn = self._get_conn()
        rows = conn.execute("SELECT raw_json FROM bonds").fetchall()
        bonds = [json.loads(row["raw_json"]) for row in rows]
        return self._apply_filters(bonds, filters)

    def get_bond(self, bond_id: str) -> Optional[dict]:
        """Get a single Bond by id."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT raw_json FROM bonds WHERE id = ?",
            (bond_id,)
        ).fetchone()
        return json.loads(row["raw_json"]) if row else None

    # === Event operations (append-only) ===

    def _get_next_seq(self, episode_id: str) -> int:
        """Get the next sequence number for an episode."""
        if episode_id in self._seq_cache:
            return self._seq_cache[episode_id]

        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(seq) as max_seq FROM events WHERE episode_id = ?",
            (episode_id,)
        ).fetchone()

        if row and row["max_seq"] is not None:
            self._seq_cache[episode_id] = row["max_seq"] + 1
        else:
            self._seq_cache[episode_id] = 1

        return self._seq_cache[episode_id]

    def append_event(self, event):
        """Append an event to the event log."""
        d = event.to_dict()

        # Verify/correct sequence number
        expected_seq = self._get_next_seq(d["episode_id"])
        if d["seq"] != expected_seq:
            d["seq"] = expected_seq
            event.seq = expected_seq

        # Handle field name differences between schema and SQL
        # QDPIEvent uses: ts, actor, refs
        # SQL schema uses: timestamp, actor_ref, refs, payload
        timestamp = d.get("ts") or d.get("timestamp", "")
        actor_ref = d.get("actor") or d.get("actor_ref")
        refs = d.get("refs")
        # For backward compat, created_at may be same as ts
        created_at = d.get("created_at") or timestamp

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO events
            (id, episode_id, seq, name, qdpi, direction, actor_ref, refs, payload, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["id"], d["episode_id"], d["seq"], d["name"], d["qdpi"], d["direction"],
            json.dumps(actor_ref) if actor_ref else None,
            json.dumps(refs) if refs else None,
            json.dumps(d.get("payload")) if d.get("payload") else None,
            timestamp, created_at
        ))
        conn.commit()

        # Increment seq counter
        self._seq_cache[d["episode_id"]] = d["seq"] + 1

    def load_events(self, episode_id: Optional[str] = None) -> List[dict]:
        """Load events, optionally filtered by episode_id."""
        conn = self._get_conn()

        if episode_id:
            rows = conn.execute(
                "SELECT * FROM events WHERE episode_id = ? ORDER BY seq",
                (episode_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY episode_id, seq"
            ).fetchall()

        events = []
        for row in rows:
            event = {
                "id": row["id"],
                "episode_id": row["episode_id"],
                "seq": row["seq"],
                "name": row["name"],
                "qdpi": row["qdpi"],
                "direction": row["direction"],
                "timestamp": row["timestamp"],
                "created_at": row["created_at"],
            }
            if row["actor_ref"]:
                event["actor_ref"] = json.loads(row["actor_ref"])
            if row["refs"]:
                event["refs"] = json.loads(row["refs"])
            if row["payload"]:
                event["payload"] = json.loads(row["payload"])
            events.append(event)

        return events

    def get_event(self, event_id: str) -> Optional[dict]:
        """Get a single event by id."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if not row:
            return None

        event = {
            "id": row["id"],
            "episode_id": row["episode_id"],
            "seq": row["seq"],
            "name": row["name"],
            "qdpi": row["qdpi"],
            "direction": row["direction"],
            "timestamp": row["timestamp"],
            "created_at": row["created_at"],
        }
        if row["actor_ref"]:
            event["actor_ref"] = json.loads(row["actor_ref"])
        if row["refs"]:
            event["refs"] = json.loads(row["refs"])
        if row["payload"]:
            event["payload"] = json.loads(row["payload"])
        return event

    # === Store status ===

    def is_initialized(self) -> bool:
        """Check if the store has been initialized."""
        try:
            return len(self.load_networks()) > 0
        except sqlite3.OperationalError:
            return False

    def clear(self):
        """Clear all data (for testing)."""
        conn = self._get_conn()
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM bonds")
        conn.execute("DELETE FROM episodes")
        conn.execute("DELETE FROM networks")
        if self._fts5_enabled:
            try:
                conn.execute("DELETE FROM items_fts")
            except sqlite3.OperationalError:
                pass
        conn.commit()
        self._seq_cache.clear()

    # === Derived views ===

    def compute_credits_balance(self, episode_id: Optional[str] = None) -> int:
        """Compute current credits balance from credits.delta events."""
        events = self.load_events(episode_id=episode_id)
        credits_events = [e for e in events if e["name"] == "credits.delta"]

        if not credits_events:
            return 0

        return credits_events[-1]["refs"].get("balance_after", 0)

    # === Utility methods ===

    def _apply_filters(self, records: List[dict], filters: Optional[dict]) -> List[dict]:
        """Apply simple equality filters to records."""
        if not filters:
            return records
        filtered = []
        for record in records:
            match = True
            for key, value in filters.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(record)
        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        conn = self._get_conn()
        stats = {
            "store_type": "sqlite",
            "db_path": str(self.db_path),
            "fts5_enabled": self._fts5_enabled,
        }

        for table in ["events", "items", "bonds", "episodes", "networks"]:
            try:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                stats[f"{table}_count"] = row["cnt"]
            except sqlite3.OperationalError:
                stats[f"{table}_count"] = 0

        return stats


# === Migration utilities ===

def migrate_jsonl_to_sqlite(
    data_dir: Path,
    sqlite_path: Optional[Path] = None,
    verbose: bool = True,
) -> Dict[str, int]:
    """
    Migrate data from JSONL files to SQLite database.

    Args:
        data_dir: Directory containing JSONL files
        sqlite_path: Path for SQLite database (default: data_dir/fieldkit.db)
        verbose: Print progress

    Returns:
        Dict with counts of migrated records
    """
    from .store_jsonl import Store as JSONLStore

    data_dir = Path(data_dir)
    if sqlite_path is None:
        sqlite_path = data_dir / "fieldkit.db"

    # Create stores
    jsonl_store = JSONLStore(data_dir)
    sqlite_store = SQLiteStore(data_dir, sqlite_path)
    sqlite_store.init()

    counts = {
        "networks": 0,
        "episodes": 0,
        "items": 0,
        "bonds": 0,
        "events": 0,
    }

    if verbose:
        print(f"Migrating from {data_dir} to {sqlite_path}")
        print(f"FTS5 enabled: {sqlite_store.fts5_enabled}")

    # Migrate networks
    from .store_jsonl import dict_to_item, dict_to_episode, dict_to_bond
    from .schemas import Network

    for network_dict in jsonl_store.load_networks():
        network = Network(
            id=network_dict["id"],
            scope=network_dict.get("scope", "private"),
            title=network_dict["title"],
            root_episode_id=network_dict.get("root_episode_id", ""),
            created_by=network_dict.get("created_by", "user"),
            created_at=network_dict["created_at"],
            updated_at=network_dict["updated_at"],
            schema_version=network_dict.get("schema_version", 1),
        )
        sqlite_store.upsert_network(network)
        counts["networks"] += 1

    if verbose:
        print(f"  Networks: {counts['networks']}")

    # Migrate episodes
    for episode_dict in jsonl_store.load_episodes():
        episode = dict_to_episode(episode_dict)
        sqlite_store.upsert_episode(episode)
        counts["episodes"] += 1

    if verbose:
        print(f"  Episodes: {counts['episodes']}")

    # Migrate items
    for item_dict in jsonl_store.load_items():
        item = dict_to_item(item_dict)
        sqlite_store.upsert_item(item)
        counts["items"] += 1

    if verbose:
        print(f"  Items: {counts['items']}")

    # Migrate bonds
    for bond_dict in jsonl_store.load_bonds():
        bond = dict_to_bond(bond_dict)
        sqlite_store.upsert_bond(bond)
        counts["bonds"] += 1

    if verbose:
        print(f"  Bonds: {counts['bonds']}")

    # Migrate events (directly insert to avoid seq validation issues)
    conn = sqlite_store._get_conn()
    for event_dict in jsonl_store.load_events():
        conn.execute("""
            INSERT OR REPLACE INTO events
            (id, episode_id, seq, name, qdpi, direction, actor_ref, refs, payload, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_dict["id"],
            event_dict["episode_id"],
            event_dict["seq"],
            event_dict["name"],
            event_dict["qdpi"],
            event_dict["direction"],
            json.dumps(event_dict.get("actor_ref")) if event_dict.get("actor_ref") else None,
            json.dumps(event_dict.get("refs")) if event_dict.get("refs") else None,
            json.dumps(event_dict.get("payload")) if event_dict.get("payload") else None,
            event_dict["timestamp"],
            event_dict["created_at"],
        ))
        counts["events"] += 1

    conn.commit()

    if verbose:
        print(f"  Events: {counts['events']}")
        print(f"Migration complete!")

    return counts
