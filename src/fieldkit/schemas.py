"""
Field-Kit v0.1 Core Data Schemas

Canonical objects as defined in /docs/specs/02_core_data_objects_v0.1.md
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Literal, Any, Union, List, Dict
import uuid


# === Type definitions ===

QDPI = Literal["Q", "M", "D", "H"]
ItemType = Literal["Q", "M", "D", "H"]
Scope = Literal["private", "shared", "public"]
BondStatus = Literal["draft", "executed"]
EventDirection = Literal["user→field", "system→field", "field→user"]
ActorKind = Literal["user", "system", "agent"]


# === ID generation ===

def generate_id(prefix: str) -> str:
    """Generate a prefixed ULID-style ID (using UUID4 for simplicity in v0.1)."""
    # Using UUID4 hex for simplicity; ULID can be added later
    return f"{prefix}{uuid.uuid4().hex[:24].upper()}"


def generate_network_id() -> str:
    return generate_id("nw_")


def generate_episode_id() -> str:
    return generate_id("ep_")


def generate_item_id() -> str:
    return generate_id("it_")


def generate_bond_id() -> str:
    return generate_id("bd_")


def generate_event_id() -> str:
    return generate_id("ev_")


def now_iso() -> str:
    """Return current time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# === Shared types ===

@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class ActorRef:
    kind: ActorKind
    id: Optional[str] = None
    display: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"kind": self.kind}
        if self.id:
            d["id"] = self.id
        if self.display:
            d["display"] = self.display
        return d


# Default actors
SYSTEM_ACTOR = ActorRef(kind="system", id="system", display="Field-Kit")
USER_ACTOR = ActorRef(kind="user", id="local-user", display="You")


# === Network ===

@dataclass
class Network:
    id: str
    scope: Scope
    title: str
    root_episode_id: str
    created_by: Literal["user", "system"]
    created_at: str
    updated_at: str
    schema_version: int = 1
    description: Optional[str] = None
    active_episode_id: Optional[str] = None
    created_by_actor: Optional[ActorRef] = None
    archived_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "scope": self.scope,
            "title": self.title,
            "root_episode_id": self.root_episode_id,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.description:
            d["description"] = self.description
        if self.active_episode_id:
            d["active_episode_id"] = self.active_episode_id
        if self.created_by_actor:
            d["created_by_actor"] = self.created_by_actor.to_dict()
        if self.archived_at:
            d["archived_at"] = self.archived_at
        return d


# === Episode ===

@dataclass
class Episode:
    id: str
    network_id: str
    scope: Scope
    title: str
    status: Literal["active", "archived"]
    started_at: str
    last_active_at: str
    created_by: Literal["user", "system"]
    created_at: str
    updated_at: str
    schema_version: int = 1
    ordinal: Optional[int] = None
    curated_item_ids: Optional[List[str]] = None
    curated_bond_ids: Optional[List[str]] = None
    ended_at: Optional[str] = None
    created_by_actor: Optional[ActorRef] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "network_id": self.network_id,
            "scope": self.scope,
            "title": self.title,
            "status": self.status,
            "started_at": self.started_at,
            "last_active_at": self.last_active_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.ordinal is not None:
            d["ordinal"] = self.ordinal
        if self.curated_item_ids:
            d["curated_item_ids"] = self.curated_item_ids
        if self.curated_bond_ids:
            d["curated_bond_ids"] = self.curated_bond_ids
        if self.ended_at:
            d["ended_at"] = self.ended_at
        if self.created_by_actor:
            d["created_by_actor"] = self.created_by_actor.to_dict()
        return d


# === Item Provenance ===

@dataclass
class ItemProvenanceUser:
    created_by: Literal["user", "system"] = "user"

    def to_dict(self) -> dict:
        return {"created_by": self.created_by}


@dataclass
class ItemProvenanceBond:
    bond_id: str
    input_item_ids: List[str]
    created_by: Literal["bond"] = "bond"

    def to_dict(self) -> dict:
        return {
            "created_by": self.created_by,
            "bond_id": self.bond_id,
            "input_item_ids": self.input_item_ids,
        }


@dataclass
class ItemProvenanceHolologue:
    holologue_event_id: str
    selected_item_ids: List[str]
    artifact_kind: str
    created_by: Literal["holologue"] = "holologue"

    def to_dict(self) -> dict:
        return {
            "created_by": self.created_by,
            "holologue_event_id": self.holologue_event_id,
            "selected_item_ids": self.selected_item_ids,
            "artifact_kind": self.artifact_kind,
        }


ItemProvenance = Union[ItemProvenanceUser, ItemProvenanceBond, ItemProvenanceHolologue]


# === Item ===

@dataclass
class Item:
    id: str
    network_id: str
    episode_id: str
    scope: Scope
    type: ItemType
    title: str
    position: Vec3
    provenance: ItemProvenance
    created_at: str
    updated_at: str
    schema_version: int = 1
    body: Optional[str] = None
    archived_at: Optional[str] = None
    created_by_actor: Optional[ActorRef] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "network_id": self.network_id,
            "episode_id": self.episode_id,
            "scope": self.scope,
            "type": self.type,
            "title": self.title,
            "position": self.position.to_dict(),
            "provenance": self.provenance.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.body:
            d["body"] = self.body
        if self.archived_at:
            d["archived_at"] = self.archived_at
        if self.created_by_actor:
            d["created_by_actor"] = self.created_by_actor.to_dict()
        return d


# === Bond ===

@dataclass
class ErrorInfo:
    message: str
    at: str
    code: Optional[str] = None
    detail: Optional[Any] = None

    def to_dict(self) -> dict:
        d = {"message": self.message, "at": self.at}
        if self.code:
            d["code"] = self.code
        if self.detail:
            d["detail"] = self.detail
        return d


@dataclass
class Bond:
    id: str
    network_id: str
    episode_id: str
    scope: Scope
    input_item_ids: List[str]
    prompt_text: str
    status: BondStatus
    output_item_id: Optional[str]
    created_by: Literal["user", "system"]
    created_at: str
    updated_at: str
    schema_version: int = 1
    intent_type: Optional[str] = None
    executed_at: Optional[str] = None
    execution_count: Optional[int] = None
    last_error: Optional[ErrorInfo] = None
    created_by_actor: Optional[ActorRef] = None
    archived_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "network_id": self.network_id,
            "episode_id": self.episode_id,
            "scope": self.scope,
            "input_item_ids": self.input_item_ids,
            "prompt_text": self.prompt_text,
            "status": self.status,
            "output_item_id": self.output_item_id,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.intent_type:
            d["intent_type"] = self.intent_type
        if self.executed_at:
            d["executed_at"] = self.executed_at
        if self.execution_count is not None:
            d["execution_count"] = self.execution_count
        if self.last_error:
            d["last_error"] = self.last_error.to_dict()
        if self.created_by_actor:
            d["created_by_actor"] = self.created_by_actor.to_dict()
        if self.archived_at:
            d["archived_at"] = self.archived_at
        return d


# === QDPIEvent ===

@dataclass
class QDPIEvent:
    id: str
    network_id: str
    episode_id: str
    ts: str
    seq: int
    qdpi: QDPI
    direction: EventDirection
    actor: ActorRef
    name: str
    refs: Dict[str, Any]
    schema_version: int = 1
    is_debug: Optional[bool] = None
    prev_event_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "network_id": self.network_id,
            "episode_id": self.episode_id,
            "ts": self.ts,
            "seq": self.seq,
            "qdpi": self.qdpi,
            "direction": self.direction,
            "actor": self.actor.to_dict(),
            "name": self.name,
            "refs": self.refs,
        }
        if self.is_debug is not None:
            d["is_debug"] = self.is_debug
        if self.prev_event_id:
            d["prev_event_id"] = self.prev_event_id
        return d


# === Canonical event names (from CLAUDE.md) ===

CANONICAL_EVENT_NAMES = [
    "app.first_run.started",
    "episode.created",
    "field.opened",
    "tutorial.started",
    "item.created",
    "bond.suggestions.presented",
    "bond.draft_created",
    "bond.run_requested",
    "bond.executed",
    "bond.execution_failed",
    "holologue.run_requested",
    "holologue.validation_failed",
    "holologue.completed",
    "holologue.failed",
    "bond.proposals.presented",
    "ledger.opened",
    "store.commit",
    "store.commit_failed",
    "credits.delta",
]
