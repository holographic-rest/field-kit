"""
Field-Kit v0.1 Candidate Set + Evidence Shard Schema

Implements pointer-style navigation with evidence citations.

Key concepts:
- EvidenceShard: Text span that supports a navigation decision
- Candidate: A navigation target (item) with evidence and score

Evidence shards don't need perfect span offsets in v0.1.
Set span_start/span_end to -1 if unknown.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import hashlib
import json


@dataclass
class EvidenceShard:
    """
    A text span that supports a navigation/suggestion.

    Follows W3C Web Annotation patterns for robustness.

    S04: Added dilation_offset for multi-scale context tracking.
    """
    shard_id: str              # Stable ID
    source_type: str           # "item" | "bond" | "prompt_template"
    source_id: str             # ID of source (item_id, bond_id, etc.)
    text_span: str             # The quoted text (max ~300 chars)
    span_start: int = -1       # Character offset in source (-1 if unknown)
    span_end: int = -1         # Character offset end (-1 if unknown)
    scale: str = "local"       # "local" | "mid" | "far" (distance from subject)
    dilation_offset: int = 0   # S04: Event offset (0=local, negative=past events)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "shard_id": self.shard_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "text_span": self.text_span,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "scale": self.scale,
            "dilation_offset": self.dilation_offset,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceShard":
        """Create from dict."""
        return cls(
            shard_id=d.get("shard_id", ""),
            source_type=d.get("source_type", "item"),
            source_id=d.get("source_id", ""),
            text_span=d.get("text_span", ""),
            span_start=d.get("span_start", -1),
            span_end=d.get("span_end", -1),
            scale=d.get("scale", "local"),
            dilation_offset=d.get("dilation_offset", 0),
        )


@dataclass
class Candidate:
    """
    A candidate navigation target with evidence and scoring.

    Implements pointer-style selection: the model selects from a
    candidate set rather than generating text.
    """
    candidate_id: str                          # Unique ID for this candidate
    target_type: str = "item"                  # "item" | "episode" | "bond"
    target_id: Optional[str] = None            # ID of target object (if pointer exists)
    title: str = ""                            # Display title
    summary: str = ""                          # Short description
    evidence_shards: List[EvidenceShard] = field(default_factory=list)

    # Scoring fields
    score: float = 0.5                         # Quality score (0-1)
    probability: float = 0.0                   # Selection probability
    rank: int = 0                              # Rank in list (1-indexed)

    # Optional metadata
    intent_type: str = ""                      # "clarify" | "concretize" | "connect" | "test"
    handle_quote: str = ""                     # Handle used in this candidate
    recency: Optional[float] = None            # Recency score
    graph_distance: Optional[int] = None       # Hops from subject

    # Source tracking
    source: str = "template"                   # "template" | "llm" | "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "candidate_id": self.candidate_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "title": self.title,
            "summary": self.summary,
            "evidence_shards": [s.to_dict() for s in self.evidence_shards],
            "score": self.score,
            "probability": self.probability,
            "rank": self.rank,
            "intent_type": self.intent_type,
            "handle_quote": self.handle_quote,
            "recency": self.recency,
            "graph_distance": self.graph_distance,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Candidate":
        """Create from dict."""
        evidence_shards = [
            EvidenceShard.from_dict(s) for s in d.get("evidence_shards", [])
        ]
        return cls(
            candidate_id=d.get("candidate_id", ""),
            target_type=d.get("target_type", "item"),
            target_id=d.get("target_id"),
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            evidence_shards=evidence_shards,
            score=d.get("score", 0.5),
            probability=d.get("probability", 0.0),
            rank=d.get("rank", 0),
            intent_type=d.get("intent_type", ""),
            handle_quote=d.get("handle_quote", ""),
            recency=d.get("recency"),
            graph_distance=d.get("graph_distance"),
            source=d.get("source", "template"),
        )

    def has_evidence(self) -> bool:
        """Check if candidate has any evidence shards."""
        return len(self.evidence_shards) > 0


def generate_shard_id(source_id: str, text_span: str) -> str:
    """Generate stable shard ID from source and text."""
    content = f"{source_id}:{text_span[:100]}"
    hash_hex = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"sh_{hash_hex.upper()}"


def generate_candidate_id(target_id: Optional[str], title: str) -> str:
    """Generate stable candidate ID."""
    content = f"{target_id or 'none'}:{title[:50]}"
    hash_hex = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"cd_{hash_hex.upper()}"


def create_evidence_from_item(
    item: Dict[str, Any],
    text_span: str,
    scale: str = "local",
) -> EvidenceShard:
    """
    Create an evidence shard from an item.

    Extracts the span from item body/title and creates shard.
    """
    item_id = item.get("id", "")
    body = item.get("body") or ""
    title = item.get("title") or ""
    full_text = title + "\n" + body

    # Try to find span position
    span_start = -1
    span_end = -1
    text_lower = full_text.lower()
    span_lower = text_span.lower()

    if span_lower in text_lower:
        span_start = text_lower.index(span_lower)
        span_end = span_start + len(text_span)

    # Truncate span if too long
    if len(text_span) > 300:
        text_span = text_span[:297] + "..."

    return EvidenceShard(
        shard_id=generate_shard_id(item_id, text_span),
        source_type="item",
        source_id=item_id,
        text_span=text_span,
        span_start=span_start,
        span_end=span_end,
        scale=scale,
    )


def create_evidence_from_handle(
    item: Dict[str, Any],
    handle_quote: str,
) -> EvidenceShard:
    """Create evidence shard from a handle quote in an item."""
    return create_evidence_from_item(item, handle_quote, scale="local")


def build_candidate_set(
    subject_item: Dict[str, Any],
    suggestions: List[Dict[str, Any]],
    store=None,
) -> List[Candidate]:
    """
    Build a candidate set from existing suggestions.

    Converts suggestion dicts to Candidate objects with evidence shards.

    Args:
        subject_item: The item for which suggestions were generated
        suggestions: List of suggestion dicts (from suggestion_engine)
        store: Optional store for looking up target items

    Returns:
        List of Candidate objects with evidence shards
    """
    candidates = []
    subject_id = subject_item.get("id", "")

    for i, s in enumerate(suggestions):
        handle = s.get("handle_quote") or s.get("handle") or ""
        prompt = s.get("prompt_text") or s.get("display_text") or ""
        intent = s.get("intent_type") or s.get("intent") or ""

        # Create candidate
        candidate = Candidate(
            candidate_id=generate_candidate_id(subject_id, prompt[:50]),
            target_type="suggestion",  # No specific target yet
            target_id=None,            # Would be set if we matched to an item
            title=prompt[:100] if len(prompt) > 100 else prompt,
            summary=prompt,
            intent_type=intent,
            handle_quote=handle,
            source=s.get("source", "template"),
            rank=i + 1,
        )

        # Create evidence shard from the handle
        if handle:
            evidence = create_evidence_from_handle(subject_item, handle)
            candidate.evidence_shards.append(evidence)

        candidates.append(candidate)

    return candidates


def candidates_to_legacy_format(candidates: List[Candidate]) -> List[Dict[str, Any]]:
    """
    Convert candidates back to legacy suggestion format.

    For backward compatibility with existing code paths.
    """
    legacy = []
    for c in candidates:
        legacy.append({
            "display_text": c.summary,
            "prompt_text": c.summary,
            "intent_type": c.intent_type,
            "handle_quote": c.handle_quote,
            "intent": c.intent_type,
            "recipe_id": _intent_to_recipe(c.intent_type),
            # Add evidence fields for eval harness
            "evidence_shards": [s.to_dict() for s in c.evidence_shards],
            "candidate_id": c.candidate_id,
            "probability": c.probability,
            "score": c.score,
            "rank": c.rank,
        })
    return legacy


def _intent_to_recipe(intent: str) -> str:
    """Map intent type to recipe_id."""
    mapping = {
        "clarify": "clarify_to_testable_claim",
        "clarifies": "clarify_to_testable_claim",
        "concretize": "ground_in_experiment",
        "grounds_in": "ground_in_experiment",
        "connect": "architecture_map",
        "bridges": "architecture_map",
        "test": "adversarial_test_cases",
        "expands": "expand_to_checklist",
        "derives_from": "derive_min_schema",
        "compares": "compare_with_criteria",
        "forks": "debate_two_options",
        "exemplifies": "ground_in_experiment",
        "qualifies": "decision_with_reasons",
        "revises": "clarify_to_testable_claim",
        "answers": "clarify_to_testable_claim",
        "contradicts": "peer_review_objections",
    }
    return mapping.get(intent.lower(), "clarify_to_testable_claim")
