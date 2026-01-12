"""
Field-Kit v0.1 Session State (Sprint S07)

Implements RMC-style multi-slot memory for session continuity.

Key concepts from research:
- RMC (Essay #19): Multiple memory slots that interact via attention
- LSTM (Essay #4): Gating for forget/input/output control
- NTM (Essay #21): External memory with explicit read/write heads

This module provides structured session state without ML training,
using heuristic attention that can be swapped for learned weights later.

6 Slots:
- active_page: Current subject item/page
- user_intent: Current action intent or ask
- entities: Extracted entities from handles
- open_questions: Unresolved clarify/test intents
- recent_evidence: Recent evidence shards
- vault_anchors: Curated/pinned items as constraints

All updates are deterministic. State influence on suggestions is
designed to be no-op when state is None or empty.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict
import time
import hashlib


# === Slot IDs ===
SLOT_IDS = [
    "active_page",
    "user_intent",
    "entities",
    "open_questions",
    "recent_evidence",
    "vault_anchors",
]


@dataclass
class MemorySlot:
    """
    A single memory slot in the session state.

    Slots hold structured content plus metadata for attention weighting.
    Embedding field is reserved for future learned representations.
    """
    slot_id: str
    content: Dict[str, Any] = field(default_factory=dict)
    recency: float = 0.0  # Higher = more recent (event index or timestamp)
    is_pinned: bool = False  # Pinned slots get higher attention weight
    embedding: Optional[List[float]] = None  # Reserved for future use

    def is_empty(self) -> bool:
        """Check if slot has no meaningful content."""
        return not self.content or all(
            v is None or v == [] or v == {} or v == ""
            for v in self.content.values()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "content": self.content,
            "recency": self.recency,
            "is_pinned": self.is_pinned,
            "is_empty": self.is_empty(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemorySlot":
        return cls(
            slot_id=d["slot_id"],
            content=d.get("content", {}),
            recency=d.get("recency", 0.0),
            is_pinned=d.get("is_pinned", False),
            embedding=d.get("embedding"),
        )


class SessionState:
    """
    Multi-slot session state (RMC-inspired).

    Maintains 6 memory slots that can influence suggestion generation.
    Slots interact via heuristic attention weighting.
    """

    def __init__(self, slots: Optional[Dict[str, MemorySlot]] = None):
        if slots is None:
            slots = {slot_id: MemorySlot(slot_id=slot_id) for slot_id in SLOT_IDS}
        self.slots = slots
        self._step_counter = 0  # Increments on each update

    def get_slot(self, slot_id: str) -> MemorySlot:
        """Get a slot by ID, creating if missing."""
        if slot_id not in self.slots:
            self.slots[slot_id] = MemorySlot(slot_id=slot_id)
        return self.slots[slot_id]

    def set_slot_content(
        self,
        slot_id: str,
        content: Dict[str, Any],
        is_pinned: bool = False,
    ) -> None:
        """Update a slot's content and recency."""
        slot = self.get_slot(slot_id)
        slot.content = content
        slot.recency = self._step_counter
        slot.is_pinned = is_pinned

    def increment_step(self) -> None:
        """Advance the step counter (call after each action)."""
        self._step_counter += 1

    def get_step(self) -> int:
        """Get current step counter."""
        return self._step_counter

    def non_empty_slots(self) -> List[MemorySlot]:
        """Return list of slots with content."""
        return [s for s in self.slots.values() if not s.is_empty()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slots": {k: v.to_dict() for k, v in self.slots.items()},
            "step_counter": self._step_counter,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionState":
        slots = {
            slot_id: MemorySlot.from_dict(slot_data)
            for slot_id, slot_data in d.get("slots", {}).items()
        }
        state = cls(slots)
        state._step_counter = d.get("step_counter", 0)
        return state

    def summary_hash(self) -> str:
        """Return short hash of current state for logging."""
        content_str = str(sorted(
            (k, str(v.content)[:50]) for k, v in self.slots.items()
        ))
        return hashlib.md5(content_str.encode()).hexdigest()[:8]


def default_session_state() -> SessionState:
    """
    Create a fresh session state with empty slots.

    This is the identity-safe default that produces no behavior change.
    """
    return SessionState()


def slot_attention(slots: Dict[str, MemorySlot]) -> Dict[str, float]:
    """
    Compute attention weights for each slot (RMC-inspired).

    Heuristic weighting based on:
    - is_pinned: +2.0 weight
    - recency: higher recency = higher weight
    - has_content: +1.0 if non-empty

    Returns weights normalized to sum to ~1.0.
    """
    raw_weights: Dict[str, float] = {}

    max_recency = max((s.recency for s in slots.values()), default=1.0)
    if max_recency == 0:
        max_recency = 1.0

    for slot_id, slot in slots.items():
        weight = 0.0

        # Base weight for non-empty content
        if not slot.is_empty():
            weight += 1.0

        # Pinned slots get bonus
        if slot.is_pinned:
            weight += 2.0

        # Recency bonus (0-1 range)
        recency_score = slot.recency / max_recency
        weight += recency_score * 1.0

        raw_weights[slot_id] = weight

    # Normalize
    total = sum(raw_weights.values())
    if total == 0:
        # All empty - uniform weights
        return {slot_id: 1.0 / len(slots) for slot_id in slots}

    return {slot_id: w / total for slot_id, w in raw_weights.items()}


def update_from_action(
    state: SessionState,
    *,
    subject_item: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[Dict[str, Any]]] = None,
    evidence_shards: Optional[List[Dict[str, Any]]] = None,
    chosen_intent: Optional[str] = None,
) -> SessionState:
    """
    Update session state from a user action.

    This is the primary update path after:
    - Navigating to an item
    - Receiving suggestions
    - Selecting a suggestion
    - Executing a bond

    Args:
        state: Current session state
        subject_item: The current/selected item dict
        suggestions: List of suggestions presented
        evidence_shards: Evidence shards from suggestions
        chosen_intent: The intent user chose (if any)

    Returns:
        Updated session state (same object, mutated)
    """
    state.increment_step()
    step = state.get_step()

    # Update active_page from subject item
    if subject_item:
        state.set_slot_content("active_page", {
            "item_id": subject_item.get("id"),
            "title": subject_item.get("title"),
            "type": subject_item.get("type"),
        })

        # Extract entities from handles if available
        handles = subject_item.get("handles", [])
        if handles:
            entities = _extract_entities_from_handles(handles)
            existing = state.get_slot("entities").content.get("entities", [])
            # Merge and dedupe, keeping recent at front
            merged = _merge_entities(entities, existing, max_count=10)
            state.set_slot_content("entities", {"entities": merged})

    # Update user_intent from chosen intent
    if chosen_intent:
        state.set_slot_content("user_intent", {
            "intent": chosen_intent,
            "step": step,
        })

    # Update open_questions from suggestions
    if suggestions:
        open_q = []
        for s in suggestions:
            intent = s.get("intent") or s.get("intent_type")
            if intent in ("clarify", "test"):
                open_q.append({
                    "handle": s.get("handle_quote", ""),
                    "intent": intent,
                    "prompt": s.get("prompt_text", "")[:100],
                })
        if open_q:
            existing = state.get_slot("open_questions").content.get("questions", [])
            # Keep last 5
            merged = (open_q + existing)[:5]
            state.set_slot_content("open_questions", {"questions": merged})

    # Update recent_evidence from evidence shards
    if evidence_shards:
        recent = []
        for shard in evidence_shards[:5]:  # Keep top 5
            recent.append({
                "source_id": shard.get("source_id"),
                "text_span": shard.get("text_span", "")[:100],
                "scale": shard.get("scale", "local"),
            })
        if recent:
            existing = state.get_slot("recent_evidence").content.get("shards", [])
            merged = (recent + existing)[:8]  # Keep last 8
            state.set_slot_content("recent_evidence", {"shards": merged})

    return state


def update_from_event(
    state: SessionState,
    event: Dict[str, Any],
) -> SessionState:
    """
    Update session state from a QDPI event.

    Handles key event types:
    - item.created: Update active_page
    - bond.suggestions.presented: Update open_questions
    - bond.executed: Clear relevant open_questions, update user_intent

    Args:
        state: Current session state
        event: QDPI event dict

    Returns:
        Updated session state
    """
    event_name = event.get("name", "")
    refs = event.get("refs", {})

    if event_name == "item.created":
        item_id = refs.get("item_id")
        item_type = refs.get("item_type", "Q")
        title = refs.get("title", "")
        state.increment_step()
        state.set_slot_content("active_page", {
            "item_id": item_id,
            "title": title,
            "type": item_type,
        })

    elif event_name == "bond.suggestions.presented":
        suggestions = refs.get("suggestions", [])
        state.increment_step()
        if suggestions:
            update_from_action(state, suggestions=suggestions)

    elif event_name == "bond.executed":
        state.increment_step()
        # Update user_intent based on execution
        state.set_slot_content("user_intent", {
            "intent": "executed_bond",
            "bond_id": refs.get("bond_id"),
            "step": state.get_step(),
        })

    elif event_name == "holologue.completed":
        state.increment_step()
        # Update user_intent
        state.set_slot_content("user_intent", {
            "intent": "completed_holologue",
            "artifact_kind": refs.get("artifact_kind"),
            "step": state.get_step(),
        })

    return state


def load_vault_anchors(
    state: SessionState,
    curated_items: List[Dict[str, Any]],
) -> SessionState:
    """
    Load curated/pinned items into vault_anchors slot.

    Args:
        state: Current session state
        curated_items: List of curated item dicts

    Returns:
        Updated session state
    """
    anchors = []
    for item in curated_items[:5]:  # Keep top 5 curated
        anchors.append({
            "item_id": item.get("id"),
            "title": item.get("title"),
            "type": item.get("type"),
        })

    if anchors:
        state.set_slot_content("vault_anchors", {"anchors": anchors}, is_pinned=True)

    return state


def _extract_entities_from_handles(handles: List[Any]) -> List[str]:
    """
    Extract entity strings from item handles.

    Handles can be dicts with 'quote' key or ItemHandle objects.
    """
    entities = []
    for h in handles[:10]:  # Limit
        if isinstance(h, dict):
            quote = h.get("quote", "")
        elif hasattr(h, "quote"):
            quote = h.quote
        else:
            quote = str(h)

        # Extract multi-word phrases as entities
        if quote and len(quote) > 3:
            entities.append(quote)

    return entities


def _merge_entities(new: List[str], existing: List[str], max_count: int = 10) -> List[str]:
    """
    Merge entity lists, deduping and keeping recent.
    """
    seen = set()
    merged = []

    for e in new + existing:
        normalized = e.lower().strip()
        if normalized not in seen and len(normalized) > 2:
            seen.add(normalized)
            merged.append(e)
            if len(merged) >= max_count:
                break

    return merged


def get_state_influence_keywords(state: SessionState) -> Set[str]:
    """
    Extract keywords from state for influence on evidence selection.

    Returns set of keywords from:
    - entities slot
    - open_questions slot handles
    - recent_evidence text spans

    These can be used to bias evidence selection toward state-relevant content.
    """
    keywords = set()

    # From entities
    entities_slot = state.get_slot("entities")
    for entity in entities_slot.content.get("entities", []):
        for word in entity.lower().split():
            if len(word) > 3:
                keywords.add(word)

    # From open questions
    questions_slot = state.get_slot("open_questions")
    for q in questions_slot.content.get("questions", []):
        handle = q.get("handle", "")
        for word in handle.lower().split():
            if len(word) > 3:
                keywords.add(word)

    # From recent evidence
    evidence_slot = state.get_slot("recent_evidence")
    for shard in evidence_slot.content.get("shards", []):
        text = shard.get("text_span", "")
        for word in text.lower().split()[:10]:  # First 10 words
            if len(word) > 3:
                keywords.add(word)

    return keywords


def format_state_summary(state: SessionState) -> str:
    """
    Format session state as human-readable summary.
    """
    lines = [
        "=" * 50,
        "SESSION STATE",
        "=" * 50,
        f"Step: {state.get_step()}",
        "",
    ]

    weights = slot_attention(state.slots)

    for slot_id in SLOT_IDS:
        slot = state.get_slot(slot_id)
        weight = weights.get(slot_id, 0)
        pinned = " [PINNED]" if slot.is_pinned else ""
        empty = " (empty)" if slot.is_empty() else ""

        lines.append(f"--- {slot_id}{pinned}{empty} ---")
        lines.append(f"  Weight: {weight:.2%}")
        lines.append(f"  Recency: {slot.recency}")

        if not slot.is_empty():
            # Show content summary
            content_str = str(slot.content)[:100]
            if len(str(slot.content)) > 100:
                content_str += "..."
            lines.append(f"  Content: {content_str}")

        lines.append("")

    lines.append("=" * 50)
    return "\n".join(lines)
