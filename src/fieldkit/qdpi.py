"""
Field-Kit v0.1 QDPI Event System

Event creation and logging following the canonical event taxonomy from CLAUDE.md.

Canonical event names (do not invent new names):
- app.first_run.started
- episode.created
- field.opened
- tutorial.started
- item.created
- bond.suggestions.presented
- bond.draft_created
- bond.run_requested
- bond.executed
- bond.execution_failed
- holologue.run_requested
- holologue.validation_failed
- holologue.completed
- holologue.failed
- bond.proposals.presented
- ledger.opened
- store.commit
- store.commit_failed
- credits.delta
"""

from typing import Optional, Any, Dict, List

from .schemas import (
    QDPIEvent, QDPI, EventDirection, ActorRef,
    generate_event_id, now_iso,
    SYSTEM_ACTOR, USER_ACTOR,
    CANONICAL_EVENT_NAMES,
)
from .store_jsonl import Store, get_store


class EventLogger:
    """
    Event logger for Field-Kit QDPI events.

    Ensures events are created with proper structure and appended to the store.
    """

    def __init__(self, store: Optional[Store] = None):
        self.store = store or get_store()
        self._credits_balance = 0  # Track credits balance for delta events

    def _create_event(
        self,
        network_id: str,
        episode_id: str,
        name: str,
        qdpi: QDPI,
        direction: EventDirection,
        refs: Dict[str, Any],
        actor: Optional[ActorRef] = None,
        is_debug: Optional[bool] = None,
    ) -> QDPIEvent:
        """Create and return a QDPIEvent (does not append)."""
        if name not in CANONICAL_EVENT_NAMES:
            raise ValueError(f"Invalid event name: {name}. Must be one of {CANONICAL_EVENT_NAMES}")

        # Default actor based on direction
        if actor is None:
            actor = USER_ACTOR if direction == "user→field" else SYSTEM_ACTOR

        # Get next sequence number
        seq = self.store._get_next_seq(episode_id)

        return QDPIEvent(
            id=generate_event_id(),
            network_id=network_id,
            episode_id=episode_id,
            ts=now_iso(),
            seq=seq,
            qdpi=qdpi,
            direction=direction,
            actor=actor,
            name=name,
            refs=refs,
            is_debug=is_debug,
        )

    def log_event(
        self,
        network_id: str,
        episode_id: str,
        name: str,
        qdpi: QDPI,
        direction: EventDirection,
        refs: Dict[str, Any],
        actor: Optional[ActorRef] = None,
        is_debug: Optional[bool] = None,
    ) -> QDPIEvent:
        """Create and append a QDPIEvent to the store."""
        event = self._create_event(
            network_id=network_id,
            episode_id=episode_id,
            name=name,
            qdpi=qdpi,
            direction=direction,
            refs=refs,
            actor=actor,
            is_debug=is_debug,
        )
        self.store.append_event(event)
        return event

    # === Convenience methods for each event type ===

    def app_first_run_started(self, network_id: str, episode_id: str) -> QDPIEvent:
        """Log app.first_run.started event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="app.first_run.started",
            qdpi="Q",
            direction="system→field",
            refs={},
        )

    def episode_created(
        self,
        network_id: str,
        episode_id: str,
        episode_title: str,
        ordinal: Optional[int] = None,
    ) -> QDPIEvent:
        """Log episode.created event."""
        refs = {"episode_id": episode_id, "title": episode_title}
        if ordinal is not None:
            refs["ordinal"] = ordinal
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="episode.created",
            qdpi="Q",
            direction="system→field",
            refs=refs,
        )

    def tutorial_started(self, network_id: str, episode_id: str) -> QDPIEvent:
        """Log tutorial.started event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="tutorial.started",
            qdpi="Q",
            direction="user→field",
            refs={},
        )

    def item_created(
        self,
        network_id: str,
        episode_id: str,
        item_id: str,
        item_type: str,
        title: str,
    ) -> QDPIEvent:
        """Log item.created event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="item.created",
            qdpi="M",
            direction="user→field",
            refs={"item_id": item_id, "type": item_type, "title": title},
        )

    def bond_suggestions_presented(
        self,
        network_id: str,
        episode_id: str,
        item_id: str,
        suggestions: List[dict],
    ) -> QDPIEvent:
        """Log bond.suggestions.presented event (events-only; no Bond created)."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.suggestions.presented",
            qdpi="Q",
            direction="system→field",
            refs={"item_id": item_id, "suggestions": suggestions},
        )

    def bond_draft_created(
        self,
        network_id: str,
        episode_id: str,
        bond_id: str,
        input_item_ids: List[str],
        prompt_text: str,
        origin: Optional[str] = None,
    ) -> QDPIEvent:
        """Log bond.draft_created event."""
        refs = {
            "bond_id": bond_id,
            "input_item_ids": input_item_ids,
            "prompt_text": prompt_text,
        }
        if origin:
            refs["origin"] = origin
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.draft_created",
            qdpi="D",
            direction="user→field",
            refs=refs,
        )

    def bond_run_requested(
        self,
        network_id: str,
        episode_id: str,
        bond_id: str,
    ) -> QDPIEvent:
        """Log bond.run_requested event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.run_requested",
            qdpi="Q",
            direction="user→field",
            refs={"bond_id": bond_id},
        )

    def bond_executed(
        self,
        network_id: str,
        episode_id: str,
        bond_id: str,
        input_item_ids: List[str],
        output_item_id: str,
        execution_count: int = 1,
    ) -> QDPIEvent:
        """Log bond.executed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.executed",
            qdpi="M",
            direction="system→field",
            refs={
                "bond_id": bond_id,
                "input_item_ids": input_item_ids,
                "output_item_id": output_item_id,
                "execution_count": execution_count,
            },
        )

    def bond_execution_failed(
        self,
        network_id: str,
        episode_id: str,
        bond_id: str,
        reason: str,
    ) -> QDPIEvent:
        """Log bond.execution_failed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.execution_failed",
            qdpi="M",
            direction="system→field",
            refs={"bond_id": bond_id, "reason": reason},
        )

    def holologue_run_requested(
        self,
        network_id: str,
        episode_id: str,
        selected_item_ids: List[str],
        artifact_kind: str,
        artifact_target_text: Optional[str] = None,
    ) -> QDPIEvent:
        """Log holologue.run_requested event."""
        refs = {
            "selected_item_ids": selected_item_ids,
            "artifact_kind": artifact_kind,
        }
        if artifact_target_text:
            refs["artifact_target_text"] = artifact_target_text
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="holologue.run_requested",
            qdpi="H",
            direction="user→field",
            refs=refs,
        )

    def holologue_validation_failed(
        self,
        network_id: str,
        episode_id: str,
        reason: str,
    ) -> QDPIEvent:
        """Log holologue.validation_failed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="holologue.validation_failed",
            qdpi="H",
            direction="user→field",
            refs={"reason": reason},
        )

    def holologue_completed(
        self,
        network_id: str,
        episode_id: str,
        selected_item_ids: List[str],
        output_item_id: str,
        artifact_kind: str,
    ) -> QDPIEvent:
        """Log holologue.completed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="holologue.completed",
            qdpi="H",
            direction="system→field",
            refs={
                "selected_item_ids": selected_item_ids,
                "output_item_id": output_item_id,
                "artifact_kind": artifact_kind,
            },
        )

    def holologue_failed(
        self,
        network_id: str,
        episode_id: str,
        reason: str,
    ) -> QDPIEvent:
        """Log holologue.failed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="holologue.failed",
            qdpi="H",
            direction="system→field",
            refs={"reason": reason},
        )

    def bond_proposals_presented(
        self,
        network_id: str,
        episode_id: str,
        source_output_item_id: str,
        suggestions: List[dict],
    ) -> QDPIEvent:
        """Log bond.proposals.presented event (events-only; no Bond created)."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="bond.proposals.presented",
            qdpi="Q",
            direction="system→field",
            refs={
                "source": {"kind": "holologue", "output_item_id": source_output_item_id},
                "suggestions": suggestions,
            },
        )

    def ledger_opened(self, network_id: str, episode_id: str) -> QDPIEvent:
        """Log ledger.opened event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="ledger.opened",
            qdpi="Q",
            direction="user→field",
            refs={},
        )

    def store_commit(self, network_id: str, episode_id: str) -> QDPIEvent:
        """Log store.commit event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="store.commit",
            qdpi="Q",
            direction="system→field",
            refs={},
        )

    def store_commit_failed(
        self,
        network_id: str,
        episode_id: str,
        reason: str,
    ) -> QDPIEvent:
        """Log store.commit_failed event."""
        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="store.commit_failed",
            qdpi="Q",
            direction="system→field",
            refs={"reason": reason},
        )

    def credits_delta(
        self,
        network_id: str,
        episode_id: str,
        delta: int,
        balance_after: int,
        reason: str,
        item_id: Optional[str] = None,
        bond_id: Optional[str] = None,
        output_item_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> QDPIEvent:
        """
        Log credits.delta event.

        Per CLAUDE.md:
        - qdpi: Q
        - direction: system→field
        - refs MUST include: delta, balance_after, reason
        - Optional direct refs: item_id, bond_id, output_item_id, event_id
        - NO related_* keys
        """
        refs = {
            "delta": delta,
            "balance_after": balance_after,
            "reason": reason,
        }
        if item_id:
            refs["item_id"] = item_id
        if bond_id:
            refs["bond_id"] = bond_id
        if output_item_id:
            refs["output_item_id"] = output_item_id
        if event_id:
            refs["event_id"] = event_id

        return self.log_event(
            network_id=network_id,
            episode_id=episode_id,
            name="credits.delta",
            qdpi="Q",
            direction="system→field",
            refs=refs,
        )


# Singleton logger
_default_logger: Optional[EventLogger] = None


def get_logger(store: Optional[Store] = None) -> EventLogger:
    """Get or create the default event logger."""
    global _default_logger
    if _default_logger is None or store is not None:
        _default_logger = EventLogger(store)
    return _default_logger
