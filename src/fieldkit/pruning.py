"""
Field-Kit v0.1 Pruning Plans (Sprint S06)

Decay/archive without deletion. Pruning suggests archiving stale or
redundant items, but protects evidence and never deletes.

Key concepts:
- PruneCandidate: Item identified for potential archiving
- PrunePlan: Collection of candidates with reasoning
- Archive-only: "Prune" means status="archived", not deletion

Prune criteria:
- Duplicates: Same title prefix (near-identical items)
- Orphans: No bonds, no recent activity
- Low-entropy: Never generated evidence shards
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime


@dataclass
class PruneCandidate:
    """
    An item identified as a candidate for archiving.
    """
    item_id: str
    item_title: str
    reason: str  # "duplicate" | "orphan" | "low_entropy" | "stale"
    details: str  # Human-readable explanation
    priority: float  # 0.0 to 1.0, higher = more urgent to prune
    related_ids: List[str] = field(default_factory=list)  # e.g., duplicate of

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_title": self.item_title,
            "reason": self.reason,
            "details": self.details,
            "priority": self.priority,
            "related_ids": self.related_ids,
        }


@dataclass
class PrunePlan:
    """
    A plan for archiving items.

    Does NOT delete items. "Prune" means setting status to "archived".
    """
    plan_id: str
    candidates: List[PruneCandidate]
    created_at: str
    status: str = "proposed"  # proposed | accepted | executed
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "candidates": [c.to_dict() for c in self.candidates],
            "created_at": self.created_at,
            "status": self.status,
            "summary": self.summary,
            "total_candidates": len(self.candidates),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PrunePlan":
        candidates = [
            PruneCandidate(
                item_id=c["item_id"],
                item_title=c["item_title"],
                reason=c["reason"],
                details=c["details"],
                priority=c["priority"],
                related_ids=c.get("related_ids", []),
            )
            for c in d.get("candidates", [])
        ]
        return cls(
            plan_id=d["plan_id"],
            candidates=candidates,
            created_at=d["created_at"],
            status=d.get("status", "proposed"),
            summary=d.get("summary", ""),
        )


def detect_prune_candidates(
    data_dir: Path,
    orphan_threshold_sessions: int = 3,
) -> List[PruneCandidate]:
    """
    Detect items that are candidates for archiving.

    Identifies:
    - Duplicates: Items with same title prefix
    - Orphans: Items with no bonds and no recent activity
    - Low-entropy: Items never used as evidence sources

    Args:
        data_dir: Path to data directory
        orphan_threshold_sessions: Orphan if no activity for N sessions

    Returns:
        List of PruneCandidate objects
    """
    data_dir = Path(data_dir)
    items_file = data_dir / "items.jsonl"
    bonds_file = data_dir / "bonds.jsonl"
    events_file = data_dir / "qdpi_events.jsonl"
    if not events_file.exists():
        events_file = data_dir / "events.jsonl"

    candidates: List[PruneCandidate] = []

    # Load items
    items = []
    if items_file.exists():
        with open(items_file) as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))

    if not items:
        return []

    item_by_id = {item.get("id"): item for item in items}

    # Load bonds
    bonds = []
    if bonds_file.exists():
        with open(bonds_file) as f:
            for line in f:
                if line.strip():
                    bond = json.loads(line)
                    if bond.get("status") == "executed":
                        bonds.append(bond)

    # Load events
    events = []
    if events_file.exists():
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

    # 1. Detect duplicates by title prefix
    dup_candidates = _detect_duplicates(items)
    candidates.extend(dup_candidates)

    # 2. Detect orphans (not in any bond)
    orphan_candidates = _detect_orphans(items, bonds, events)
    candidates.extend(orphan_candidates)

    # 3. Detect low-entropy items (never used as evidence source)
    low_entropy_candidates = _detect_low_entropy(items, events)
    candidates.extend(low_entropy_candidates)

    # De-duplicate candidates (same item might match multiple criteria)
    seen_ids: Set[str] = set()
    unique_candidates: List[PruneCandidate] = []
    for c in candidates:
        if c.item_id not in seen_ids:
            seen_ids.add(c.item_id)
            unique_candidates.append(c)
        else:
            # Merge reasons
            for uc in unique_candidates:
                if uc.item_id == c.item_id:
                    uc.details += f"; also {c.reason}: {c.details}"
                    uc.priority = max(uc.priority, c.priority)
                    break

    # Sort by priority descending
    unique_candidates.sort(key=lambda c: c.priority, reverse=True)

    return unique_candidates


def _detect_duplicates(items: List[Dict[str, Any]], prefix_len: int = 50) -> List[PruneCandidate]:
    """
    Detect near-duplicate items by title prefix.
    """
    candidates: List[PruneCandidate] = []

    # Group by title prefix hash
    prefix_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        title = (item.get("title") or "").lower().strip()[:prefix_len]
        prefix_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        prefix_groups[prefix_hash].append(item)

    # Find groups with duplicates
    for prefix_hash, group in prefix_groups.items():
        if len(group) > 1:
            # Keep the first (oldest by position), mark rest as duplicates
            # Sort by created_at if available, else by position
            sorted_group = sorted(
                group,
                key=lambda x: x.get("created_at", "9999"),
            )
            original = sorted_group[0]
            original_id = original.get("id", "")

            for dup in sorted_group[1:]:
                dup_id = dup.get("id", "")
                dup_title = dup.get("title", "Untitled")

                candidates.append(PruneCandidate(
                    item_id=dup_id,
                    item_title=dup_title[:50],
                    reason="duplicate",
                    details=f"Near-duplicate of {original_id} (same title prefix)",
                    priority=0.7,
                    related_ids=[original_id],
                ))

    return candidates


def _detect_orphans(
    items: List[Dict[str, Any]],
    bonds: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[PruneCandidate]:
    """
    Detect orphan items (not connected via any bond).
    """
    candidates: List[PruneCandidate] = []

    # Find all items connected by bonds
    connected_ids: Set[str] = set()
    for bond in bonds:
        connected_ids.update(bond.get("input_item_ids", []))
        if bond.get("output_item_id"):
            connected_ids.add(bond["output_item_id"])

    # Find items mentioned in events (e.g., as evidence sources)
    active_ids: Set[str] = set()
    for event in events:
        refs = event.get("refs", {})
        # Check various ref fields
        if refs.get("item_id"):
            active_ids.add(refs["item_id"])
        if refs.get("subject_item_id"):
            active_ids.add(refs["subject_item_id"])
        if refs.get("input_item_ids"):
            active_ids.update(refs["input_item_ids"])
        if refs.get("output_item_id"):
            active_ids.add(refs["output_item_id"])

    # Orphans: not connected and not recently active
    for item in items:
        item_id = item.get("id", "")
        item_title = item.get("title", "Untitled")

        if item_id not in connected_ids:
            if item_id not in active_ids:
                candidates.append(PruneCandidate(
                    item_id=item_id,
                    item_title=item_title[:50],
                    reason="orphan",
                    details="No bonds and no recent activity",
                    priority=0.5,
                    related_ids=[],
                ))
            else:
                # Connected via events but no bonds - lower priority orphan
                candidates.append(PruneCandidate(
                    item_id=item_id,
                    item_title=item_title[:50],
                    reason="orphan",
                    details="No bonds (but has event activity)",
                    priority=0.3,
                    related_ids=[],
                ))

    return candidates


def _detect_low_entropy(
    items: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
) -> List[PruneCandidate]:
    """
    Detect low-entropy items (never used as evidence sources).

    These are items that exist but never contributed evidence shards
    to any suggestion.
    """
    candidates: List[PruneCandidate] = []

    # Find items that have been used as evidence sources
    evidence_source_ids: Set[str] = set()
    for event in events:
        if event.get("name") == "bond.suggestions.presented":
            suggestions = event.get("refs", {}).get("suggestions", [])
            for s in suggestions:
                shards = s.get("evidence_shards", [])
                for shard in shards:
                    source_id = shard.get("source_id", "")
                    if source_id.startswith("it_"):
                        evidence_source_ids.add(source_id)

    # Find items never used as evidence
    for item in items:
        item_id = item.get("id", "")
        item_title = item.get("title", "Untitled")
        item_type = item.get("type", "Q")

        # Only flag Q items as low-entropy (M items are outputs, expected behavior)
        if item_type == "Q" and item_id not in evidence_source_ids:
            # Check if item has enough content to potentially be evidence
            body = item.get("body", "")
            if len(body) > 20:  # Has substantial content
                candidates.append(PruneCandidate(
                    item_id=item_id,
                    item_title=item_title[:50],
                    reason="low_entropy",
                    details="Has content but never used as evidence source",
                    priority=0.4,
                    related_ids=[],
                ))

    return candidates


def create_prune_plan(candidates: List[PruneCandidate]) -> PrunePlan:
    """
    Create a prune plan from candidates.

    The plan is a proposal only - it does NOT execute archiving.

    Args:
        candidates: List of PruneCandidate objects

    Returns:
        PrunePlan ready for review
    """
    plan_id = f"pp_{uuid.uuid4().hex[:24].upper()}"
    created_at = datetime.utcnow().isoformat() + "Z"

    # Generate summary
    reason_counts = defaultdict(int)
    for c in candidates:
        reason_counts[c.reason] += 1

    summary_parts = []
    for reason, count in sorted(reason_counts.items()):
        summary_parts.append(f"{count} {reason}")
    summary = f"Plan to archive {len(candidates)} items: {', '.join(summary_parts)}"

    return PrunePlan(
        plan_id=plan_id,
        candidates=candidates,
        created_at=created_at,
        status="proposed",
        summary=summary,
    )


def format_prune_plan_report(plan: PrunePlan) -> str:
    """
    Format prune plan as human-readable report.
    """
    if not plan.candidates:
        return "No prune candidates detected."

    lines = [
        "=" * 60,
        "PRUNE PLAN",
        "=" * 60,
        "",
        f"Plan ID: {plan.plan_id}",
        f"Created: {plan.created_at}",
        f"Status: {plan.status}",
        f"Summary: {plan.summary}",
        "",
        f"Candidates ({len(plan.candidates)}):",
        "",
    ]

    # Group by reason
    by_reason: Dict[str, List[PruneCandidate]] = defaultdict(list)
    for c in plan.candidates:
        by_reason[c.reason].append(c)

    for reason, group in sorted(by_reason.items()):
        lines.append(f"--- {reason.upper()} ({len(group)}) ---")
        for c in group[:10]:  # Show first 10 per category
            lines.append(f"  [{c.priority:.1f}] {c.item_id}")
            lines.append(f"       {c.item_title}")
            lines.append(f"       {c.details}")
        if len(group) > 10:
            lines.append(f"  ... and {len(group) - 10} more")
        lines.append("")

    lines.append("=" * 60)
    lines.append("Note: This is a plan only. No items have been archived.")
    lines.append("To archive, items would have status set to 'archived'.")
    lines.append("=" * 60)

    return "\n".join(lines)


def detect_and_plan(data_dir: Path) -> PrunePlan:
    """
    Convenience function: detect candidates and create plan.
    """
    candidates = detect_prune_candidates(data_dir)
    return create_prune_plan(candidates)


def apply_structured_novelty_protection(
    candidates: List[PruneCandidate],
    thread_model: Dict[str, Any],
    cohort_stats: Optional[Dict[str, Any]] = None,
) -> List[PruneCandidate]:
    """
    Protect items that are "structured novelty" from pruning.

    S09: Uses MDL structure-vs-noise gate to identify items that
    should be protected from archiving.

    Items that pass the gate with "structured" bucket are marked with:
    - protected_by_mdl: True
    - mdl_reason: explanation

    Args:
        candidates: List of PruneCandidate objects
        thread_model: Current thread context (handles, entities)
        cohort_stats: Optional stats for calibration

    Returns:
        Candidates with protection applied
    """
    from .mdl_scoring import structure_vs_noise_gate

    for candidate in candidates:
        # Create minimal artifact from candidate
        artifact = {
            "id": candidate.item_id,
            "title": candidate.item_title,
        }

        gate_result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        # If item passes gate as "structured", protect it
        if gate_result["allowed"] and gate_result["bucket"] == "structured":
            # Store protection in candidate details
            candidate.details += f" [MDL PROTECTED: {gate_result['reason']}]"
            # Lower priority so it's less likely to be pruned
            candidate.priority = max(0.0, candidate.priority - 0.3)

    return candidates


def detect_and_plan_with_mdl(
    data_dir: Path,
    thread_model: Optional[Dict[str, Any]] = None,
) -> PrunePlan:
    """
    Detect candidates, apply MDL protection, and create plan.

    S09: Enhanced version that protects structured novelty items.

    Args:
        data_dir: Path to data directory
        thread_model: Optional thread context (uses empty dict if None)

    Returns:
        PrunePlan with MDL protection applied
    """
    candidates = detect_prune_candidates(data_dir)

    if thread_model is not None:
        candidates = apply_structured_novelty_protection(candidates, thread_model)

    return create_prune_plan(candidates)
