"""
Field-Kit v0.1 Pointer Scorer

Scores candidates and produces selection probabilities.

Implements the core insight from Pointer Networks:
- Output is a probability distribution over the candidate set
- Not generating text, but selecting from existing objects

v0.1 uses heuristic scoring; later versions can train on click data.
"""

import math
from typing import List, Dict, Any, Optional, Tuple

from .candidate_set import Candidate


def score_candidates(
    candidates: List[Candidate],
    subject_embedding: Optional[List[float]] = None,
    candidate_embeddings: Optional[List[List[float]]] = None,
) -> List[Candidate]:
    """
    Score candidates and assign selection probabilities.

    Args:
        candidates: List of candidates to score
        subject_embedding: Optional embedding of subject item
        candidate_embeddings: Optional embeddings for candidates

    Returns:
        Candidates with updated scores and probabilities
    """
    if not candidates:
        return candidates

    # If embeddings available, use cosine similarity
    if subject_embedding and candidate_embeddings:
        candidates = _score_with_embeddings(
            candidates, subject_embedding, candidate_embeddings
        )
    else:
        # Heuristic scoring
        candidates = _score_heuristic(candidates)

    # Convert scores to probabilities (softmax)
    candidates = _apply_softmax(candidates, temperature=1.0)

    # Update ranks
    sorted_candidates = sorted(candidates, key=lambda c: c.probability, reverse=True)
    for i, c in enumerate(sorted_candidates):
        c.rank = i + 1

    return candidates


def _score_heuristic(candidates: List[Candidate]) -> List[Candidate]:
    """
    Heuristic scoring based on available features.

    Factors:
    - Evidence presence (has evidence shards)
    - Handle quality (multi-word handles preferred)
    - Source quality (LLM > template)
    - Diversity bonus
    """
    for c in candidates:
        score = 0.5  # Base score

        # Evidence bonus
        if c.has_evidence():
            score += 0.15
            # More evidence = slightly better
            score += min(len(c.evidence_shards) * 0.05, 0.1)

        # Handle quality
        if c.handle_quote:
            word_count = len(c.handle_quote.split())
            if word_count >= 5:
                score += 0.1
            elif word_count >= 3:
                score += 0.05

        # Source quality
        if c.source == "llm":
            score += 0.1
        elif c.source == "heuristic":
            score += 0.05

        # Intent diversity (penalize if same as previous)
        # This is handled at selection time in diversify step

        # Recency bonus if available
        if c.recency is not None:
            score += c.recency * 0.1

        # Graph distance penalty if available
        if c.graph_distance is not None:
            # Closer is better
            if c.graph_distance <= 1:
                score += 0.1
            elif c.graph_distance <= 2:
                score += 0.05

        c.score = min(max(score, 0.0), 1.0)

    return candidates


def _score_with_embeddings(
    candidates: List[Candidate],
    subject_embedding: List[float],
    candidate_embeddings: List[List[float]],
) -> List[Candidate]:
    """
    Score using cosine similarity with embeddings.

    This is the "real" pointer network approach where
    attention scores (similarities) become the output distribution.
    """
    for i, c in enumerate(candidates):
        if i < len(candidate_embeddings):
            similarity = _cosine_similarity(
                subject_embedding, candidate_embeddings[i]
            )
            # Scale similarity to [0.3, 0.9] range
            c.score = 0.3 + (similarity + 1.0) * 0.3

            # Still apply evidence bonus
            if c.has_evidence():
                c.score = min(c.score + 0.1, 1.0)
        else:
            # Fallback to heuristic for missing embeddings
            c.score = 0.5 if c.has_evidence() else 0.4

    return candidates


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def _apply_softmax(
    candidates: List[Candidate],
    temperature: float = 1.0,
) -> List[Candidate]:
    """
    Apply softmax to convert scores to probabilities.

    Args:
        candidates: Candidates with scores
        temperature: Softmax temperature (higher = more uniform)

    Returns:
        Candidates with updated probabilities
    """
    if not candidates:
        return candidates

    # Get scores and apply temperature
    scores = [c.score / temperature for c in candidates]

    # Subtract max for numerical stability
    max_score = max(scores)
    exp_scores = [math.exp(s - max_score) for s in scores]

    # Normalize
    total = sum(exp_scores)
    if total == 0:
        # Uniform distribution fallback
        prob = 1.0 / len(candidates)
        for c in candidates:
            c.probability = prob
    else:
        for c, exp_s in zip(candidates, exp_scores):
            c.probability = exp_s / total

    return candidates


def select_top_k(
    candidates: List[Candidate],
    k: int = 4,
    diversify: bool = True,
) -> List[Candidate]:
    """
    Select top-k candidates, optionally with diversity.

    Args:
        candidates: Scored candidates
        k: Number to select
        diversify: If True, ensure intent variety

    Returns:
        Top-k candidates
    """
    if len(candidates) <= k:
        return candidates

    if not diversify:
        # Pure probability ranking
        sorted_candidates = sorted(
            candidates, key=lambda c: c.probability, reverse=True
        )
        return sorted_candidates[:k]

    # Diversified selection
    selected = []
    used_intents = set()
    remaining = list(candidates)

    # First pass: one of each intent type
    intent_order = ["clarify", "concretize", "connect", "test",
                   "clarifies", "expands", "grounds_in", "bridges"]

    for intent in intent_order:
        if len(selected) >= k:
            break
        for c in sorted(remaining, key=lambda x: x.probability, reverse=True):
            if c.intent_type == intent and intent not in used_intents:
                selected.append(c)
                used_intents.add(intent)
                remaining.remove(c)
                break

    # Second pass: fill with highest probability
    for c in sorted(remaining, key=lambda x: x.probability, reverse=True):
        if len(selected) >= k:
            break
        selected.append(c)

    # Update ranks
    for i, c in enumerate(selected):
        c.rank = i + 1

    return selected


def get_pointer_distribution(candidates: List[Candidate]) -> Dict[str, float]:
    """
    Get the pointer distribution as a dict.

    Useful for logging and debugging.
    """
    return {
        c.candidate_id: c.probability
        for c in sorted(candidates, key=lambda x: x.probability, reverse=True)
    }


def format_pointer_output(candidates: List[Candidate]) -> str:
    """
    Format candidates for CLI display with probabilities.

    Shows rank, probability, title, and evidence.
    """
    lines = []
    for c in sorted(candidates, key=lambda x: x.rank):
        prob_pct = f"{c.probability * 100:.1f}%"
        title = c.title[:60] + "..." if len(c.title) > 60 else c.title
        lines.append(f"  {c.rank}. [{prob_pct}] {title}")

        # Show evidence
        if c.evidence_shards:
            for shard in c.evidence_shards[:2]:  # Max 2 shards
                span = shard.text_span[:50] + "..." if len(shard.text_span) > 50 else shard.text_span
                lines.append(f"     WHY: \"{span}\"")

    return "\n".join(lines)
