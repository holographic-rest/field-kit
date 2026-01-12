"""
Field-Kit v0.1 Hololink Generation Pipeline (Queue Lattice)

Generates hololink candidates for connecting two Queue Items.

Pipeline steps:
1. get_handles: Extract handles from both items (3-7 per item)
2. generate_candidates: Create 24-40 candidate hololinks
3. hard_filter: Remove candidates that fail validation
4. rank: Score candidates by quality
5. diversify: Select 4 diverse options

A hololink is a one-way navigational sentence from Item A to Item B.
A hololoop is a bidirectional bond with forward (A→B) and return (B→A) hololinks.
"""

import hashlib
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .handles import extract_handles, choose_diverse_handles


@dataclass
class HololinkCandidate:
    """A candidate hololink between two items."""
    handle_a: str       # Handle from Item A used in this link
    handle_b: str       # Handle from Item B used in this link
    forward_text: str   # A→B sentence
    return_text: str    # B→A sentence
    intent: str         # Internal intent type (extends|supports|contrasts|elaborates)
    score: float        # Quality score (0-1)
    source: str         # "template" | "llm"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle_a": self.handle_a,
            "handle_b": self.handle_b,
            "forward_text": self.forward_text,
            "return_text": self.return_text,
            "intent": self.intent,
            "score": self.score,
            "source": self.source,
        }


# === Template sets for candidate generation ===
# Each template uses {handle_a} and {handle_b} - both must appear in each sentence

INTENT_TEMPLATES = {
    "extends": [
        ('How does "{handle_a}" lead into "{handle_b}"?', '"{handle_b}" builds on "{handle_a}"'),
        ('"{handle_a}" extends toward "{handle_b}"', '"{handle_b}" follows from "{handle_a}"'),
        ('From "{handle_a}" to "{handle_b}"', '"{handle_b}" continues from "{handle_a}"'),
    ],
    "supports": [
        ('"{handle_a}" provides foundation for "{handle_b}"', '"{handle_b}" draws from "{handle_a}"'),
        ('"{handle_a}" grounds "{handle_b}"', '"{handle_b}" relies on "{handle_a}"'),
        ('Understanding "{handle_a}" helps with "{handle_b}"', '"{handle_b}" connects back to "{handle_a}"'),
    ],
    "contrasts": [
        ('Compare "{handle_a}" with "{handle_b}"', 'How "{handle_b}" differs from "{handle_a}"'),
        ('"{handle_a}" versus "{handle_b}"', '"{handle_b}" as alternative to "{handle_a}"'),
        ('Tension between "{handle_a}" and "{handle_b}"', '"{handle_b}" challenges "{handle_a}"'),
    ],
    "elaborates": [
        ('"{handle_a}" unpacks into "{handle_b}"', '"{handle_b}" elaborates on "{handle_a}"'),
        ('"{handle_a}" details "{handle_b}"', '"{handle_b}" expands "{handle_a}"'),
        ('Exploring "{handle_a}" through "{handle_b}"', '"{handle_b}" deepens "{handle_a}"'),
    ],
}


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


# === Pipeline Step 1: Get Handles ===

def get_handles_for_item(item: Dict[str, Any], k: int = 5) -> List[Dict[str, Any]]:
    """
    Get handles for an item, preferring stored handles over extraction.

    Args:
        item: Item dict with optional "handles" field
        k: Number of handles to return (3-7, default 5)

    Returns:
        List of handle dicts with quote, kind, starred
    """
    # Use stored handles if available
    if item.get("handles"):
        handles = item["handles"]
        # Return starred first, then rest
        starred = [h for h in handles if h.get("starred")]
        unstarred = [h for h in handles if not h.get("starred")]
        result = (starred + unstarred)[:k]
        return result

    # Extract handles from content
    text = item.get("body") or ""
    title = item.get("title")
    extracted = extract_handles(text, title)
    selected = choose_diverse_handles(extracted, k=k)

    return selected


# === Pipeline Step 2: Generate Candidates ===

def generate_candidates(
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
) -> List[HololinkCandidate]:
    """
    Generate 24-40 hololink candidates from handle pairs.

    Uses templates and optionally LLM to create candidates.
    Each candidate pairs one handle from A with one from B.
    """
    candidates = []

    # Generate template-based candidates
    # For each intent type, try each template with different handle pairs
    intents = list(INTENT_TEMPLATES.keys())

    for intent in intents:
        templates = INTENT_TEMPLATES[intent]

        for t_idx, (fwd_template, ret_template) in enumerate(templates):
            # Pair handles systematically to get variety
            for i, ha in enumerate(handles_a[:4]):
                for j, hb in enumerate(handles_b[:4]):
                    # Use hash to deterministically select which pairs to use
                    pair_hash = _hash_content(f"{ha['quote']}{hb['quote']}{intent}{t_idx}")

                    # Only use about 25% of pairs to avoid explosion
                    if pair_hash % 4 != 0:
                        continue

                    handle_a_text = ha["quote"]
                    handle_b_text = hb["quote"]

                    try:
                        forward = fwd_template.format(handle_a=handle_a_text, handle_b=handle_b_text)
                        return_ = ret_template.format(handle_a=handle_a_text, handle_b=handle_b_text)

                        candidates.append(HololinkCandidate(
                            handle_a=handle_a_text,
                            handle_b=handle_b_text,
                            forward_text=forward,
                            return_text=return_,
                            intent=intent,
                            score=0.5,  # Base score, will be adjusted in ranking
                            source="template",
                        ))
                    except (KeyError, IndexError):
                        continue

    # Try LLM generation for additional candidates
    llm_candidates = _try_llm_generation(handles_a, handles_b, item_a, item_b)
    candidates.extend(llm_candidates)

    return candidates


def _try_llm_generation(
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
) -> List[HololinkCandidate]:
    """
    Try to generate additional candidates via LLM.

    Returns empty list if LLM not available.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    try:
        import openai

        # Prepare handle quotes
        quotes_a = [h["quote"] for h in handles_a[:5]]
        quotes_b = [h["quote"] for h in handles_b[:5]]

        system_prompt = """You generate hololink candidates connecting two items.

For each hololink:
- forward_text: Sentence from A→B that includes handles from BOTH items
- return_text: Sentence from B→A that includes handles from BOTH items
- intent: One of: extends, supports, contrasts, elaborates

CRITICAL:
1. Each sentence MUST quote handles from BOTH items (in double quotes)
2. Keep sentences 10-25 words
3. Generate 8 diverse candidates with different handle pairings

Output JSON:
{
  "candidates": [
    {
      "handle_a": "handle from A",
      "handle_b": "handle from B",
      "forward_text": "sentence with both handles",
      "return_text": "sentence with both handles",
      "intent": "extends|supports|contrasts|elaborates"
    }
  ]
}"""

        # Truncate bodies
        body_a = (item_a.get("body") or "")[:500]
        body_b = (item_b.get("body") or "")[:500]

        user_prompt = f"""Item A: {item_a.get("title", "")}
{body_a}

Handles from A: {json.dumps(quotes_a)}

Item B: {item_b.get("title", "")}
{body_b}

Handles from B: {json.dumps(quotes_b)}

Generate 8 diverse hololink candidates."""

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        candidates = []
        for c in data.get("candidates", [])[:10]:
            candidates.append(HololinkCandidate(
                handle_a=c.get("handle_a", ""),
                handle_b=c.get("handle_b", ""),
                forward_text=c.get("forward_text", ""),
                return_text=c.get("return_text", ""),
                intent=c.get("intent", "extends"),
                score=0.7,  # LLM candidates start with higher score
                source="llm",
            ))

        return candidates

    except Exception as e:
        print(f"[hololink_pipeline] LLM generation failed: {e}")
        return []


# === Pipeline Step 3: Hard Filter ===

def hard_filter(candidates: List[HololinkCandidate]) -> List[HololinkCandidate]:
    """
    Remove candidates that fail validation.

    Filters:
    - Empty or too short sentences
    - Missing handle references
    - Duplicate content
    """
    seen = set()
    filtered = []

    for c in candidates:
        # Check sentence lengths
        if len(c.forward_text) < 15 or len(c.return_text) < 15:
            continue
        if len(c.forward_text) > 200 or len(c.return_text) > 200:
            continue

        # Check for placeholder text
        fwd_lower = c.forward_text.lower()
        ret_lower = c.return_text.lower()
        if "item a" in fwd_lower or "item b" in fwd_lower:
            continue
        if "item a" in ret_lower or "item b" in ret_lower:
            continue

        # Check handles are present in sentences (at least one)
        ha_lower = c.handle_a.lower()
        hb_lower = c.handle_b.lower()

        # At least one handle should appear in forward (relaxed check)
        if ha_lower[:15] not in fwd_lower and hb_lower[:15] not in fwd_lower:
            continue

        # Deduplicate by content hash
        content_key = f"{c.forward_text[:50]}|{c.return_text[:50]}"
        if content_key in seen:
            continue
        seen.add(content_key)

        filtered.append(c)

    return filtered


# === Pipeline Step 4: Rank ===

def rank_candidates(candidates: List[HololinkCandidate]) -> List[HololinkCandidate]:
    """
    Score and rank candidates by quality.

    Scoring factors:
    - LLM source bonus
    - Handle length (multi-word preferred)
    - Sentence quality
    """
    for c in candidates:
        score = c.score  # Start with existing score

        # LLM source bonus
        if c.source == "llm":
            score += 0.1

        # Multi-word handle bonus
        if len(c.handle_a.split()) >= 3:
            score += 0.05
        if len(c.handle_b.split()) >= 3:
            score += 0.05

        # Sentence length sweet spot (20-60 chars)
        fwd_len = len(c.forward_text)
        if 20 <= fwd_len <= 60:
            score += 0.05
        elif fwd_len > 100:
            score -= 0.05

        # Intent diversity is handled in diversify step

        c.score = min(score, 1.0)

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


# === Pipeline Step 5: Diversify ===

def diversify(candidates: List[HololinkCandidate], k: int = 4) -> List[HololinkCandidate]:
    """
    Select k diverse candidates.

    Ensures variety in:
    - Intent types
    - Handles used
    - Sentence structure
    """
    if len(candidates) <= k:
        return candidates

    selected = []
    used_intents = set()
    used_handles = set()

    # First pass: get one of each intent type
    for intent in ["extends", "supports", "contrasts", "elaborates"]:
        if len(selected) >= k:
            break
        for c in candidates:
            if c.intent == intent and intent not in used_intents:
                # Prefer candidates with fresh handles
                handle_key = f"{c.handle_a[:20]}|{c.handle_b[:20]}"
                if handle_key not in used_handles:
                    selected.append(c)
                    used_intents.add(intent)
                    used_handles.add(handle_key)
                    break

    # Second pass: fill remaining with highest scoring, diverse options
    for c in candidates:
        if len(selected) >= k:
            break
        if c not in selected:
            handle_key = f"{c.handle_a[:20]}|{c.handle_b[:20]}"
            if handle_key not in used_handles:
                selected.append(c)
                used_handles.add(handle_key)

    # Final pass: just take top scores if still not enough
    for c in candidates:
        if len(selected) >= k:
            break
        if c not in selected:
            selected.append(c)

    return selected[:k]


# === Main Pipeline Entry Point ===

def generate_hololink_options(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Generate 4 hololink options for connecting items A and B.

    Pipeline: get_handles → generate_candidates → hard_filter → rank → diversify

    Args:
        item_a: First Queue Item dict
        item_b: Second Queue Item dict
        return_debug: Include debug info in response

    Returns:
        Dict with:
        - options: List of 4 hololink option dicts
        - source: "pipeline"
        - debug: Optional debug info
    """
    # Step 1: Get handles
    handles_a = get_handles_for_item(item_a, k=5)
    handles_b = get_handles_for_item(item_b, k=5)

    # Ensure we have at least 2 handles from each item
    if len(handles_a) < 2:
        title = item_a.get("title", "this content")[:50]
        handles_a.append({"quote": title, "kind": "heading", "starred": False})
    if len(handles_b) < 2:
        title = item_b.get("title", "this content")[:50]
        handles_b.append({"quote": title, "kind": "heading", "starred": False})

    # Step 2: Generate candidates
    candidates = generate_candidates(handles_a, handles_b, item_a, item_b)

    # Step 3: Hard filter
    filtered = hard_filter(candidates)

    # Step 4: Rank
    ranked = rank_candidates(filtered)

    # Step 5: Diversify
    final = diversify(ranked, k=4)

    # Format as options
    options = []
    for i, c in enumerate(final, 1):
        options.append({
            "option_index": i,
            "relation_type": c.intent,  # Intent is internal only
            "link_text_forward": c.forward_text,
            "link_text_return": c.return_text,
            "handle_a_used": c.handle_a,
            "handle_b_used": c.handle_b,
        })

    # Ensure we have 4 options (pad with fallback if needed)
    while len(options) < 4:
        idx = len(options) + 1
        ha = handles_a[min(idx - 1, len(handles_a) - 1)]["quote"]
        hb = handles_b[min(idx - 1, len(handles_b) - 1)]["quote"]
        intents = ["extends", "supports", "contrasts", "elaborates"]
        intent = intents[(idx - 1) % 4]
        templates = INTENT_TEMPLATES[intent][0]

        options.append({
            "option_index": idx,
            "relation_type": intent,
            "link_text_forward": templates[0].format(handle_a=ha, handle_b=hb),
            "link_text_return": templates[1].format(handle_a=ha, handle_b=hb),
            "handle_a_used": ha,
            "handle_b_used": hb,
        })

    result = {
        "options": options[:4],
        "source": "pipeline",
        "item_a_id": item_a.get("id"),
        "item_b_id": item_b.get("id"),
    }

    if return_debug:
        result["debug"] = {
            "handles_a": [h["quote"] for h in handles_a],
            "handles_b": [h["quote"] for h in handles_b],
            "candidates_generated": len(candidates),
            "candidates_filtered": len(filtered),
            "candidates_ranked": len(ranked),
        }

    return result


# === S08: Batch Suggest (optional batching mode) ===

def batch_suggest(
    requests: List[Dict[str, Any]],
    batch_size: int = 4,
    return_debug: bool = False,
) -> List[Dict[str, Any]]:
    """
    Process multiple hololink requests in batches.

    S08: GPipe-style batching for improved throughput.

    Each request should have:
    - item_a: Dict with item data
    - item_b: Dict with item data

    Args:
        requests: List of request dicts
        batch_size: Batch size for dispatch (default 4)
        return_debug: Include debug info in responses

    Returns:
        List of results in same order as requests
    """
    from .pipeline import batch_dispatch

    def process_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of requests."""
        results = []
        for req in batch:
            item_a = req.get("item_a", {})
            item_b = req.get("item_b", {})
            result = generate_hololink_options(item_a, item_b, return_debug=return_debug)
            results.append(result)
        return results

    return batch_dispatch(process_batch, requests, batch_size=batch_size)


def batch_suggest_with_metrics(
    requests: List[Dict[str, Any]],
    batch_size: int = 4,
    return_debug: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process requests with metrics collection.

    Returns:
        Tuple of (results, metrics_dict)
    """
    from .pipeline import measure_batch_dispatch

    def process_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for req in batch:
            item_a = req.get("item_a", {})
            item_b = req.get("item_b", {})
            result = generate_hololink_options(item_a, item_b, return_debug=return_debug)
            results.append(result)
        return results

    results, metrics = measure_batch_dispatch(process_batch, requests, batch_size=batch_size)
    return results, metrics.to_dict()
