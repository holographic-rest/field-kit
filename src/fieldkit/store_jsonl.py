"""
Field-Kit v0.1 JSONL Store

Storage layer for Field-Kit using JSONL files as specified in:
- /docs/specs/02_core_data_objects_v0.1.md
- /prototype/README.md

Files:
- items.jsonl - Item snapshots (latest by id)
- bonds.jsonl - Bond snapshots (latest by id)
- episodes.jsonl - Episode snapshots (latest by id)
- networks.jsonl - Network snapshots (latest by id)
- qdpi_events.jsonl - Append-only, immutable events
"""

import json
import os
from pathlib import Path
from typing import Optional, Any, TypeVar, Callable, Dict, List
from dataclasses import dataclass

from .schemas import (
    Network, Episode, Item, Bond, QDPIEvent,
    generate_event_id, now_iso, SYSTEM_ACTOR,
    Vec3, ActorRef,
    ItemProvenanceUser, ItemProvenanceBond, ItemProvenanceHolologue,
    ErrorInfo,
)


# Default data directory (can be overridden by FIELDKIT_DATA_DIR env var)
def _get_default_data_dir() -> Path:
    """Get the default data directory from env var or fallback."""
    env_dir = os.environ.get("FIELDKIT_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent / "prototype" / "data"


DEFAULT_DATA_DIR = _get_default_data_dir()


@dataclass
class Store:
    """JSONL-based store for Field-Kit v0.1."""

    data_dir: Path
    _seq_cache: Dict[str, int]  # episode_id -> last seq

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = _get_default_data_dir()
        self._seq_cache = {}
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # === File paths ===

    @property
    def items_file(self) -> Path:
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

    # === Low-level JSONL operations ===

    def _append_line(self, file_path: Path, data: dict):
        """Append a JSON line to a file."""
        with open(file_path, "a") as f:
            f.write(json.dumps(data) + "\n")

    def _read_lines(self, file_path: Path) -> List[dict]:
        """Read all JSON lines from a file."""
        if not file_path.exists():
            return []
        lines = []
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return lines

    def _load_latest_by_id(self, file_path: Path) -> Dict[str, dict]:
        """Load all records and keep only the latest by id."""
        records = {}
        for record in self._read_lines(file_path):
            records[record["id"]] = record
        return records

    # === Snapshot operations (Items/Bonds/Episodes/Networks) ===

    def upsert_network(self, network: Network):
        """Upsert a Network snapshot."""
        self._append_line(self.networks_file, network.to_dict())

    def load_networks(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Network snapshots, applying optional filters."""
        networks = list(self._load_latest_by_id(self.networks_file).values())
        return self._apply_filters(networks, filters)

    def get_network(self, network_id: str) -> Optional[dict]:
        """Get a single Network by id."""
        networks = self._load_latest_by_id(self.networks_file)
        return networks.get(network_id)

    def upsert_episode(self, episode: Episode):
        """Upsert an Episode snapshot."""
        self._append_line(self.episodes_file, episode.to_dict())

    def load_episodes(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Episode snapshots, applying optional filters."""
        episodes = list(self._load_latest_by_id(self.episodes_file).values())
        return self._apply_filters(episodes, filters)

    def get_episode(self, episode_id: str) -> Optional[dict]:
        """Get a single Episode by id."""
        episodes = self._load_latest_by_id(self.episodes_file)
        return episodes.get(episode_id)

    def upsert_item(self, item: Item):
        """Upsert an Item snapshot."""
        self._append_line(self.items_file, item.to_dict())

    def load_items(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Item snapshots, applying optional filters."""
        items = list(self._load_latest_by_id(self.items_file).values())
        return self._apply_filters(items, filters)

    def get_item(self, item_id: str) -> Optional[dict]:
        """Get a single Item by id."""
        items = self._load_latest_by_id(self.items_file)
        return items.get(item_id)

    def upsert_bond(self, bond: Bond):
        """Upsert a Bond snapshot."""
        self._append_line(self.bonds_file, bond.to_dict())

    def load_bonds(self, filters: Optional[dict] = None) -> List[dict]:
        """Load Bond snapshots, applying optional filters."""
        bonds = list(self._load_latest_by_id(self.bonds_file).values())
        return self._apply_filters(bonds, filters)

    def get_bond(self, bond_id: str) -> Optional[dict]:
        """Get a single Bond by id."""
        bonds = self._load_latest_by_id(self.bonds_file)
        return bonds.get(bond_id)

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

    # === Event operations (append-only) ===

    def _get_next_seq(self, episode_id: str) -> int:
        """
        Get the next sequence number for an episode.

        Does NOT increment the counter - that happens in append_event.
        """
        # Check cache first
        if episode_id in self._seq_cache:
            return self._seq_cache[episode_id]

        # Load from file to find max seq
        events = self.load_events(episode_id=episode_id)
        if events:
            max_seq = max(e["seq"] for e in events)
            self._seq_cache[episode_id] = max_seq + 1
        else:
            self._seq_cache[episode_id] = 1

        return self._seq_cache[episode_id]

    def append_event(self, event: QDPIEvent):
        """
        Append an event to the event log.

        Events are immutable and append-only.
        Sequence numbers are monotonic per episode.
        """
        # Verify sequence number is correct
        expected_seq = self._get_next_seq(event.episode_id)
        if event.seq != expected_seq:
            # Auto-correct seq if not set properly
            event.seq = expected_seq

        # Append the event
        self._append_line(self.events_file, event.to_dict())

        # Increment the seq counter after successful append
        self._seq_cache[event.episode_id] = event.seq + 1

    def load_events(self, episode_id: Optional[str] = None) -> List[dict]:
        """
        Load events, optionally filtered by episode_id.

        Events are returned ordered by (episode_id, seq).
        """
        events = self._read_lines(self.events_file)

        if episode_id:
            events = [e for e in events if e["episode_id"] == episode_id]

        # Sort by (episode_id, seq)
        events.sort(key=lambda e: (e["episode_id"], e["seq"]))
        return events

    def get_event(self, event_id: str) -> Optional[dict]:
        """Get a single event by id."""
        for event in self._read_lines(self.events_file):
            if event["id"] == event_id:
                return event
        return None

    # === Store status ===

    def is_initialized(self) -> bool:
        """Check if the store has been initialized (has at least one network)."""
        return len(self.load_networks()) > 0

    def clear(self):
        """Clear all data (for testing)."""
        for f in [self.items_file, self.bonds_file, self.episodes_file,
                  self.networks_file, self.events_file]:
            if f.exists():
                f.unlink()
        self._seq_cache.clear()

    # === Derived views ===

    def compute_credits_balance(self, episode_id: Optional[str] = None) -> int:
        """
        Compute the current credits balance from credits.delta events.

        Returns the balance_after from the most recent credits.delta event,
        or 0 if no credits events exist.
        """
        events = self.load_events(episode_id=episode_id)
        credits_events = [e for e in events if e["name"] == "credits.delta"]

        if not credits_events:
            return 0

        # Return the most recent balance_after
        return credits_events[-1]["refs"].get("balance_after", 0)


# === Helper functions for creating objects ===

def dict_to_item(d: dict) -> Item:
    """Convert a dict to an Item object."""
    prov_data = d["provenance"]
    if prov_data["created_by"] == "bond":
        provenance = ItemProvenanceBond(
            bond_id=prov_data["bond_id"],
            input_item_ids=prov_data["input_item_ids"],
        )
    elif prov_data["created_by"] == "holologue":
        provenance = ItemProvenanceHolologue(
            holologue_event_id=prov_data["holologue_event_id"],
            selected_item_ids=prov_data["selected_item_ids"],
            artifact_kind=prov_data["artifact_kind"],
        )
    else:
        provenance = ItemProvenanceUser(created_by=prov_data["created_by"])

    pos = d["position"]
    actor = None
    if "created_by_actor" in d:
        a = d["created_by_actor"]
        actor = ActorRef(kind=a["kind"], id=a.get("id"), display=a.get("display"))

    return Item(
        id=d["id"],
        network_id=d["network_id"],
        episode_id=d["episode_id"],
        scope=d["scope"],
        type=d["type"],
        title=d["title"],
        position=Vec3(x=pos["x"], y=pos["y"], z=pos["z"]),
        provenance=provenance,
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        schema_version=d.get("schema_version", 1),
        body=d.get("body"),
        archived_at=d.get("archived_at"),
        created_by_actor=actor,
    )


def dict_to_bond(d: dict) -> Bond:
    """Convert a dict to a Bond object."""
    actor = None
    if "created_by_actor" in d:
        a = d["created_by_actor"]
        actor = ActorRef(kind=a["kind"], id=a.get("id"), display=a.get("display"))

    last_error = None
    if "last_error" in d:
        e = d["last_error"]
        last_error = ErrorInfo(
            message=e["message"],
            at=e["at"],
            code=e.get("code"),
            detail=e.get("detail"),
        )

    return Bond(
        id=d["id"],
        network_id=d["network_id"],
        episode_id=d["episode_id"],
        scope=d["scope"],
        input_item_ids=d["input_item_ids"],
        prompt_text=d["prompt_text"],
        status=d["status"],
        output_item_id=d.get("output_item_id"),
        created_by=d["created_by"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        schema_version=d.get("schema_version", 1),
        intent_type=d.get("intent_type"),
        executed_at=d.get("executed_at"),
        execution_count=d.get("execution_count"),
        last_error=last_error,
        created_by_actor=actor,
        archived_at=d.get("archived_at"),
    )


# Singleton store instance
_default_store: Optional[Store] = None


def get_store(data_dir: Optional[Path] = None) -> Store:
    """Get or create the default store instance."""
    global _default_store
    if _default_store is None or (data_dir and _default_store.data_dir != Path(data_dir)):
        _default_store = Store(data_dir)
    return _default_store


def reset_store():
    """Reset the default store (for testing)."""
    global _default_store
    _default_store = None
