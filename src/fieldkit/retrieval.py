"""
Field-Kit v0.1 Retrieval Module (Queue Lattice)

Local similarity-based retrieval for finding related items.

Uses token-based similarity (Jaccard/BM25-lite) - NO embeddings.
This is the "retrieval-first" approach for the Related Items panel.
"""

import re
import math
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter


def _tokenize(text: str) -> List[str]:
    """
    Tokenize text into lowercase words.

    Removes punctuation and short tokens.
    """
    if not text:
        return []

    # Lowercase and extract words
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())

    # Remove common stopwords
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again',
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
        'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this',
        'that', 'these', 'those', 'it', 'its', 'what', 'which', 'who', 'whom',
    }

    return [w for w in words if w not in stopwords and len(w) > 2]


def _get_item_text(item: Dict[str, Any]) -> str:
    """Get searchable text from an item."""
    parts = []

    title = item.get("title", "")
    if title:
        # Title is weighted 2x
        parts.append(title)
        parts.append(title)

    body = item.get("body", "")
    if body:
        parts.append(body)

    # Include handles if present
    handles = item.get("handles", [])
    for h in handles:
        quote = h.get("quote", "")
        if quote:
            parts.append(quote)
            if h.get("starred"):
                # Starred handles weighted 2x
                parts.append(quote)

    return " ".join(parts)


def jaccard_similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """
    Compute Jaccard similarity between two token sets.

    J(A,B) = |A ∩ B| / |A ∪ B|
    """
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)

    if union == 0:
        return 0.0

    return intersection / union


def bm25_score(
    query_tokens: List[str],
    doc_tokens: List[str],
    doc_freq: Dict[str, int],
    num_docs: int,
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """
    Compute BM25 score for a document given a query.

    BM25 is a probabilistic ranking function used by search engines.
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_len = len(doc_tokens)
    doc_counter = Counter(doc_tokens)
    score = 0.0

    for term in query_tokens:
        if term not in doc_counter:
            continue

        tf = doc_counter[term]
        df = doc_freq.get(term, 0)

        # IDF component
        idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1)

        # TF component with length normalization
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))

        score += idf * tf_norm

    return score


def compute_document_frequencies(items: List[Dict[str, Any]]) -> Tuple[Dict[str, int], float]:
    """
    Compute document frequencies for BM25.

    Returns: (doc_freq dict, avg_doc_len)
    """
    doc_freq: Dict[str, int] = {}
    total_len = 0

    for item in items:
        text = _get_item_text(item)
        tokens = _tokenize(text)
        total_len += len(tokens)

        # Count unique tokens per document
        seen = set()
        for token in tokens:
            if token not in seen:
                doc_freq[token] = doc_freq.get(token, 0) + 1
                seen.add(token)

    avg_doc_len = total_len / len(items) if items else 1.0
    return doc_freq, avg_doc_len


def find_related_items(
    query_item: Dict[str, Any],
    candidate_items: List[Dict[str, Any]],
    k: int = 5,
    method: str = "hybrid",
) -> List[Dict[str, Any]]:
    """
    Find items most related to the query item.

    Args:
        query_item: The item to find relations for
        candidate_items: Pool of items to search
        k: Number of related items to return
        method: "jaccard" | "bm25" | "hybrid"

    Returns:
        List of k items with their similarity scores, sorted by relevance.
        Each item dict includes "_similarity_score" field.
    """
    if not candidate_items:
        return []

    # Exclude the query item from candidates
    query_id = query_item.get("id")
    candidates = [i for i in candidate_items if i.get("id") != query_id]

    if not candidates:
        return []

    # Tokenize query
    query_text = _get_item_text(query_item)
    query_tokens = _tokenize(query_text)
    query_token_set = set(query_tokens)

    # Compute document frequencies for BM25
    doc_freq, avg_doc_len = compute_document_frequencies(candidates)
    num_docs = len(candidates)

    # Score each candidate
    scored = []
    for item in candidates:
        item_text = _get_item_text(item)
        item_tokens = _tokenize(item_text)
        item_token_set = set(item_tokens)

        if method == "jaccard":
            score = jaccard_similarity(query_token_set, item_token_set)
        elif method == "bm25":
            score = bm25_score(query_tokens, item_tokens, doc_freq, num_docs, avg_doc_len)
        else:  # hybrid
            jaccard_score = jaccard_similarity(query_token_set, item_token_set)
            bm25_score_val = bm25_score(query_tokens, item_tokens, doc_freq, num_docs, avg_doc_len)
            # Normalize BM25 score (typically 0-10 range) to 0-1
            bm25_norm = min(bm25_score_val / 10.0, 1.0)
            # Combine with equal weights
            score = 0.5 * jaccard_score + 0.5 * bm25_norm

        if score > 0:
            item_copy = dict(item)
            item_copy["_similarity_score"] = round(score, 4)
            scored.append(item_copy)

    # Sort by score descending
    scored.sort(key=lambda x: x["_similarity_score"], reverse=True)

    return scored[:k]


def find_best_target_for_hololoop(
    source_item: Dict[str, Any],
    candidate_items: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Find the best target item for a draft hololoop.

    Used for auto-linking when no Active Item is set.

    Returns the most related item, or None if no candidates.
    """
    related = find_related_items(source_item, candidate_items, k=1, method="hybrid")
    return related[0] if related else None
