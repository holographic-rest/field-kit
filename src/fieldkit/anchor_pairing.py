"""
Field-Kit v0.1 Anchor Pairing Module (Sprint 2)

Uses embedding-based cosine similarity to pair handles from items A and B
with MMR-like diversity selection.

Pipeline:
1. Normalize handles (dedupe aliases like "One Thousand" vs "One Thousand and One Nights")
2. Embed all handles using HashEmbeddingBackend
3. Compute pairwise cosine similarity matrix
4. Build candidate pool from top-k + per-B coverage picks
5. Apply MMR diversity selection with coverage rule
6. Return pairs with debug info

DESIGN NOTES:
- Uses deterministic HashEmbeddingBackend (no network calls, stable across runs)
- MMR λ=0.7 balances similarity vs diversity
- Coverage rule ensures each B handle appears at most once in final pairs
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from .embeddings import (
    get_hash_embedder,
    HashEmbeddingBackend,
    Embedder,
    cosine_sim,
    pairwise_cosine_matrix,
    Vector,
    Matrix,
)


# =============================================================================
# Sprint 3b: Handle Validity Filter
# =============================================================================

# Tokens that indicate an incomplete phrase when at the end of a handle
BAD_HANDLE_TAILS = {
    # Prepositions/conjunctions that need following words
    "of", "and", "or", "to", "in", "for", "with", "on", "at", "from", "by",
    # Copula/auxiliaries that need predicates
    "is", "are", "was", "were", "be", "been", "being",
    # Incomplete verb forms
    "become", "becomes", "becoming",
    # Other incomplete tails
    "the", "a", "an", "that", "which", "who", "whom", "whose",
}

# Common stopwords for handle validation
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "this", "that", "these", "those", "it", "its", "i", "you", "he", "she",
    "we", "they", "my", "your", "his", "her", "our", "their",
}


def is_good_anchor_handle(handle: str) -> bool:
    """
    Check if a handle is suitable for use as an anchor in hololoop options.

    Sprint 3b: Prevents incomplete phrase handles like "the structure of"
    or "the narrator becomes" from being selected.

    Rules:
    - Reject if < 4 chars after stripping
    - Reject if all tokens are stopwords
    - Reject if last token is in BAD_HANDLE_TAILS
    - Reject if ends with punctuation-only fragments

    Args:
        handle: The handle text to validate

    Returns:
        True if handle is valid for anchor use
    """
    if not handle:
        return False

    # Strip whitespace
    handle = handle.strip()

    # Reject if too short
    if len(handle) < 4:
        return False

    # Reject if ends with punctuation-only fragments
    if handle.endswith("...") or handle.endswith("…"):
        # Check if there's content before the ellipsis
        stripped = handle.rstrip(".…, ")
        if len(stripped) < 4:
            return False
        handle = stripped

    # Tokenize (simple whitespace split)
    tokens = handle.lower().split()

    if not tokens:
        return False

    # Reject if all tokens are stopwords
    non_stop_tokens = [t for t in tokens if t not in STOPWORDS]
    if not non_stop_tokens:
        return False

    # Reject if last token is a bad tail
    last_token = tokens[-1].rstrip(".,;:!?")
    if last_token in BAD_HANDLE_TAILS:
        return False

    return True


# === HANDLE ALIAS NORMALIZATION ===
# Map short forms to their canonical full forms
HANDLE_ALIASES = {
    "one thousand": "One Thousand and One Nights",
    "one thousand and": "One Thousand and One Nights",
    "arabian nights": "One Thousand and One Nights",
    "1001 nights": "One Thousand and One Nights",
    "the author": "identity of The Author",
    "found text": "found text",  # Keep as-is
    "the big sleep": "The Big Sleep",
    "magical dominion": "Magical Dominion",
}


def _normalize_handle_text(text: str) -> str:
    """
    Normalize handle text for alias suppression.

    Expands known short forms to their canonical versions.
    """
    text_lower = text.lower().strip()

    # Check for exact alias matches
    if text_lower in HANDLE_ALIASES:
        return HANDLE_ALIASES[text_lower]

    # Check for prefix matches (e.g., "one thousand" as prefix)
    for alias, canonical in HANDLE_ALIASES.items():
        if text_lower == alias or text_lower.startswith(alias + " "):
            # Only replace if canonical is longer (more complete)
            if len(canonical) > len(text):
                return canonical

    return text


def normalize_handles(handles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize handles and deduplicate aliases.

    - Expands known short forms to canonical versions
    - Deduplicates handles that normalize to the same text
    - Preserves the handle with highest score when deduping

    Args:
        handles: List of handle dicts with "quote" and "score" keys

    Returns:
        Deduplicated list with normalized quotes
    """
    seen_normalized = {}  # normalized_quote -> best handle

    for h in handles:
        quote = h.get("quote", "")
        normalized = _normalize_handle_text(quote)
        normalized_key = normalized.lower()

        new_handle = {**h, "quote": normalized, "original_quote": quote}

        if normalized_key not in seen_normalized:
            seen_normalized[normalized_key] = new_handle
        else:
            # Keep handle with higher score
            existing = seen_normalized[normalized_key]
            if h.get("score", 0) > existing.get("score", 0):
                seen_normalized[normalized_key] = new_handle

    return list(seen_normalized.values())


@dataclass
class AnchorPair:
    """A paired anchor from items A and B."""
    handle_a: str
    handle_b: str
    similarity: float
    mmr_score: float = 0.0
    index_a: int = 0
    index_b: int = 0


def _embed_handles(
    handles: List[Dict[str, Any]],
    embedder: Embedder,
) -> Tuple[List[str], Matrix]:
    """
    Embed handle quotes and return (quotes, embeddings).
    """
    quotes = [h.get("quote", "") for h in handles]
    embeddings = embedder.embed_texts(quotes)
    return quotes, embeddings


def _build_similarity_matrix(
    vecs_a: Matrix,
    vecs_b: Matrix,
) -> Matrix:
    """
    Build pairwise cosine similarity matrix.

    Result[i][j] = cosine_sim(vecs_a[i], vecs_b[j])
    """
    return pairwise_cosine_matrix(vecs_a, vecs_b)


def _get_top_k_pairs(
    sim_matrix: Matrix,
    quotes_a: List[str],
    quotes_b: List[str],
    k: int = 12,
) -> List[AnchorPair]:
    """
    Get top-k pairs by similarity score.
    """
    # Flatten matrix to list of (sim, i, j)
    pairs = []
    for i, row in enumerate(sim_matrix):
        for j, sim in enumerate(row):
            pairs.append((sim, i, j))

    # Sort by similarity descending
    pairs.sort(key=lambda x: x[0], reverse=True)

    # Take top k
    result = []
    for sim, i, j in pairs[:k]:
        result.append(AnchorPair(
            handle_a=quotes_a[i],
            handle_b=quotes_b[j],
            similarity=sim,
            index_a=i,
            index_b=j,
        ))

    return result


def _get_coverage_picks(
    sim_matrix: Matrix,
    quotes_a: List[str],
    quotes_b: List[str],
    existing_pairs: List[AnchorPair],
) -> List[AnchorPair]:
    """
    Get one representative pair for each B handle not yet covered.

    For each uncovered B, pick the A handle with highest similarity.
    """
    covered_b = set(p.handle_b.lower() for p in existing_pairs)

    result = []
    for j, hb in enumerate(quotes_b):
        if hb.lower() in covered_b:
            continue

        # Find best A for this B
        best_i = 0
        best_sim = sim_matrix[0][j] if sim_matrix else 0.0

        for i in range(len(quotes_a)):
            if sim_matrix[i][j] > best_sim:
                best_sim = sim_matrix[i][j]
                best_i = i

        result.append(AnchorPair(
            handle_a=quotes_a[best_i],
            handle_b=hb,
            similarity=best_sim,
            index_a=best_i,
            index_b=j,
        ))

    return result


def _pair_to_vec(pair: AnchorPair, vecs_a: Matrix, vecs_b: Matrix) -> Vector:
    """
    Get concatenated vector representation of a pair for MMR diversity.
    """
    vec_a = vecs_a[pair.index_a]
    vec_b = vecs_b[pair.index_b]
    return vec_a + vec_b  # Simple concatenation


def _mmr_select(
    candidates: List[AnchorPair],
    vecs_a: Matrix,
    vecs_b: Matrix,
    num_pairs: int = 4,
    lambda_: float = 0.7,
) -> List[AnchorPair]:
    """
    Select pairs using Maximal Marginal Relevance (MMR).

    MMR balances:
    - Relevance: similarity between A and B handles (sim_ab)
    - Diversity: dissimilarity from already selected pairs

    Score = λ * sim_ab - (1-λ) * max_sim_to_selected

    Args:
        candidates: Pool of candidate pairs
        vecs_a: Embeddings of A handles
        vecs_b: Embeddings of B handles
        num_pairs: Number of pairs to select
        lambda_: Balance parameter (higher = prefer similarity)

    Returns:
        Selected pairs with MMR scores
    """
    if len(candidates) <= num_pairs:
        return candidates

    selected = []
    selected_vecs = []  # Pair vectors of selected items
    remaining = list(candidates)

    # Track which B handles are used (coverage rule)
    used_b_handles = set()

    while len(selected) < num_pairs and remaining:
        best_score = float('-inf')
        best_idx = 0

        for idx, pair in enumerate(remaining):
            # Relevance: similarity between A and B
            relevance = pair.similarity

            # Diversity: max similarity to any selected pair
            if selected_vecs:
                pair_vec = _pair_to_vec(pair, vecs_a, vecs_b)
                max_sim_to_selected = max(
                    cosine_sim(pair_vec, sv) for sv in selected_vecs
                )
            else:
                max_sim_to_selected = 0.0

            # MMR score
            mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim_to_selected

            # Coverage penalty: prefer unused B handles
            if pair.handle_b.lower() in used_b_handles:
                mmr_score -= 0.15  # Penalty for reusing B handle

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        # Select best
        chosen = remaining.pop(best_idx)
        chosen.mmr_score = best_score
        selected.append(chosen)
        selected_vecs.append(_pair_to_vec(chosen, vecs_a, vecs_b))
        used_b_handles.add(chosen.handle_b.lower())

    return selected


def select_anchor_pairs(
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
    embedder: Optional[Embedder] = None,
    num_pairs: int = 4,
    top_k: int = 12,
    lambda_: float = 0.7,
) -> Tuple[List[Tuple[str, str]], Dict[str, Any]]:
    """
    Select anchor pairs using embedding similarity with MMR diversity.

    Pipeline:
    1. Normalize handles (dedupe aliases)
    2. Sprint 3b: Filter to valid anchor handles (no bad tails)
    3. Embed all handles
    4. Compute pairwise cosine similarity matrix
    5. Build candidate pool: top-k + coverage picks
    6. Apply MMR selection with coverage rule

    Args:
        handles_a: Handles from item A (list of dicts with "quote", "score")
        handles_b: Handles from item B
        embedder: Optional embedder (defaults to HashEmbeddingBackend)
        num_pairs: Number of pairs to return (default 4)
        top_k: Size of top-k candidate pool (default 12)
        lambda_: MMR balance parameter (default 0.7)

    Returns:
        Tuple of:
        - pairs: List of (handle_a, handle_b) tuples
        - debug: Dict with similarity matrix, scores, etc.
    """
    # Use default embedder if not provided
    if embedder is None:
        embedder = get_hash_embedder(dim=256)

    # Step 1: Normalize handles
    norm_a = normalize_handles(handles_a)
    norm_b = normalize_handles(handles_b)

    # Handle edge cases
    if not norm_a or not norm_b:
        return [], {"error": "empty_handles"}

    # Step 1.5 (Sprint 3b): Filter to good anchor handles
    good_a = [h for h in norm_a if is_good_anchor_handle(h.get("quote", ""))]
    good_b = [h for h in norm_b if is_good_anchor_handle(h.get("quote", ""))]

    # Track filtering stats for debug
    handle_filter_stats = {
        "handles_a_total": len(norm_a),
        "handles_a_good": len(good_a),
        "handles_b_total": len(norm_b),
        "handles_b_good": len(good_b),
        "fallback_used": False,
    }

    # Fallback: if filtering leaves < 2 handles on either side, use original
    if len(good_a) < 2 or len(good_b) < 2:
        handle_filter_stats["fallback_used"] = True
        # Use original normalized handles
        working_a = norm_a
        working_b = norm_b
    else:
        working_a = good_a
        working_b = good_b

    # Step 2: Embed handles (use filtered working lists)
    quotes_a, vecs_a = _embed_handles(working_a, embedder)
    quotes_b, vecs_b = _embed_handles(working_b, embedder)

    # Step 3: Compute similarity matrix
    sim_matrix = _build_similarity_matrix(vecs_a, vecs_b)

    # Step 4: Build candidate pool
    top_k_pairs = _get_top_k_pairs(sim_matrix, quotes_a, quotes_b, k=top_k)
    coverage_pairs = _get_coverage_picks(sim_matrix, quotes_a, quotes_b, top_k_pairs)

    # Combine candidates (dedupe by pair key)
    seen = set()
    candidates = []
    for p in top_k_pairs + coverage_pairs:
        key = (p.handle_a.lower(), p.handle_b.lower())
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    # Step 5: MMR selection
    selected = _mmr_select(candidates, vecs_a, vecs_b, num_pairs, lambda_)

    # Format output
    pairs = [(p.handle_a, p.handle_b) for p in selected]

    debug = {
        "quotes_a": quotes_a,
        "quotes_b": quotes_b,
        "sim_matrix": sim_matrix,
        "top_k_pairs": [(p.handle_a, p.handle_b, p.similarity) for p in top_k_pairs],
        "coverage_pairs": [(p.handle_a, p.handle_b, p.similarity) for p in coverage_pairs],
        "candidates_count": len(candidates),
        "selected_pairs": [
            {
                "handle_a": p.handle_a,
                "handle_b": p.handle_b,
                "similarity": round(p.similarity, 4),
                "mmr_score": round(p.mmr_score, 4),
            }
            for p in selected
        ],
        "lambda": lambda_,
        "used_b_handles": list(set(p.handle_b for p in selected)),
        "normalization_applied": {
            "a_original": [h.get("original_quote", h.get("quote")) for h in norm_a],
            "a_normalized": quotes_a,
            "b_original": [h.get("original_quote", h.get("quote")) for h in norm_b],
            "b_normalized": quotes_b,
        },
        # Sprint 3b: Handle validity filter stats
        "handle_filter": handle_filter_stats,
        "rejected_handles_a": [
            h.get("quote", "") for h in norm_a
            if not is_good_anchor_handle(h.get("quote", ""))
        ],
        "rejected_handles_b": [
            h.get("quote", "") for h in norm_b
            if not is_good_anchor_handle(h.get("quote", ""))
        ],
    }

    return pairs, debug
