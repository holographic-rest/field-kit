"""
Field-Kit v0.1 Hololoop Engine (Queue Lattice PASS 2 - Content Quality)

Generates 4 hololoop options for connecting two Queue Items.

PASS 2 CRITICAL REQUIREMENTS:
- NO quotation marks around handles in user-facing text
- Handles appear as PLAIN TEXT substrings (not quoted)
- Each hololink = ONE sentence that naturally bridges A and B
- 4 options must be meaningfully different
- No generic boilerplate ("How does X lead into Y" - max 1)

Pipeline:
1. Choose 4 diverse (handle_a, handle_b) pairs
2. Generate MANY candidates (12-30)
3. HARD FILTER: must contain handles verbatim, no quotes, one sentence
4. RANK + DIVERSIFY: prefer concrete verbs, different frames
5. Pick top 4
"""

import hashlib
import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .handles import extract_handles, choose_diverse_handles, strip_all_quotes


# === Quote detection regex (CRITICAL) ===
QUOTE_PATTERN = re.compile(r'["\'\u201c\u201d\u2018\u2019\u00ab\u00bb]')

# === Banned boilerplate patterns ===
BANNED_PATTERNS = [
    r'provide\s+evidence',
    r'validate\s+',
    r'operationalize\s+',
    r'test\s+case',
    r'checklist',
    r'schema\s+for',
    r'in\s+this\s+context',
    r'explain\s+why\s+it\s+matters',
    r'walk\s+me\s+through',
    r'give\s+me\s+a\s+',
    r'derive\s+a\s+',
    r'expand\s+.*\s+into\s+a\s+\d+',
]

# === Sentence frames for heuristic generation ===
# These are INTERNAL frames - never shown to user
# Each frame generates natural sentences with handles as plain text
SENTENCE_FRAMES = {
    "causality": [
        "{handle_a} sets the stage for {handle_b}",
        "Without {handle_a} there would be no {handle_b}",
        "{handle_b} emerges from the logic of {handle_a}",
        "{handle_a} makes {handle_b} possible",
    ],
    "tension": [
        "The tension between {handle_a} and {handle_b} drives the narrative",
        "{handle_a} conflicts with {handle_b} in unexpected ways",
        "Where {handle_a} ends, {handle_b} begins to resist",
        "{handle_b} challenges what {handle_a} established",
    ],
    "identity": [
        "If {handle_a} is true, what does that make {handle_b}",
        "{handle_a} redefines {handle_b} as something else entirely",
        "Through {handle_a}, {handle_b} becomes a different kind of question",
        "{handle_b} transforms when viewed through {handle_a}",
    ],
    "stakes": [
        "What {handle_a} risks, {handle_b} inherits",
        "The stakes of {handle_a} become visible in {handle_b}",
        "{handle_b} reveals what {handle_a} was hiding",
        "Following {handle_a} leads inevitably to {handle_b}",
    ],
    "framing": [
        "{handle_a} reframes {handle_b} as deliberate design",
        "Viewing {handle_b} through the lens of {handle_a} changes everything",
        "{handle_a} as a frame makes {handle_b} feel intentional",
        "The {handle_a} perspective turns {handle_b} into evidence",
    ],
    "reversal": [
        "{handle_b} inverts the logic of {handle_a}",
        "What if {handle_a} is actually caused by {handle_b}",
        "{handle_a} in reverse reveals {handle_b}",
        "Reading {handle_b} backward illuminates {handle_a}",
    ],
    "question": [
        "Does {handle_a} explain why {handle_b} matters",
        "If {handle_a} fails, does {handle_b} still hold",
        "Can {handle_b} exist without {handle_a}",
        "What happens to {handle_b} when {handle_a} is removed",
    ],
    "implication": [
        "{handle_a} implies something specific about {handle_b}",
        "The presence of {handle_a} suggests {handle_b} is no accident",
        "{handle_b} follows from {handle_a} in ways worth tracing",
        "Accepting {handle_a} commits us to {handle_b}",
    ],
}


@dataclass
class HololinkCandidate:
    """A candidate hololink between two items."""
    handle_a: str
    handle_b: str
    forward_text: str
    return_text: str
    frame: str  # Internal frame type (never shown to user)
    score: float
    source: str  # "heuristic" | "llm"


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _contains_quotes(text: str) -> bool:
    """Check if text contains any quotation marks."""
    return bool(QUOTE_PATTERN.search(text))


def _contains_banned_pattern(text: str) -> bool:
    """Check if text contains banned boilerplate patterns."""
    text_lower = text.lower()
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _is_single_sentence(text: str) -> bool:
    """Check if text is approximately one sentence."""
    # Count sentence-ending punctuation
    endings = len(re.findall(r'[.!?]', text))
    # One sentence should have at most one ending punctuation
    return endings <= 1


def _contains_handle_verbatim(text: str, handle: str) -> bool:
    """Check if handle appears as plain substring (case-insensitive)."""
    return handle.lower() in text.lower()


def _token_jaccard(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def _generate_heuristic_candidates(
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
) -> List[HololinkCandidate]:
    """
    Generate heuristic candidates using sentence frames.

    Each candidate uses handles as PLAIN TEXT (no quotes).
    """
    candidates = []

    # Use up to 5 handles from each item
    ha_list = [h["quote"] for h in handles_a[:5]]
    hb_list = [h["quote"] for h in handles_b[:5]]

    if not ha_list or not hb_list:
        return candidates

    # Generate candidates from each frame
    for frame_name, templates in SENTENCE_FRAMES.items():
        # Use different handle pairs for variety
        for i, template in enumerate(templates[:2]):  # 2 templates per frame
            # Rotate through handles
            ha = ha_list[i % len(ha_list)]
            hb = hb_list[(i + 1) % len(hb_list)]

            # Generate forward text (A→B)
            forward_text = template.format(handle_a=ha, handle_b=hb)

            # Generate return text (B→A) - swap handles and adjust template
            return_template = templates[(i + 1) % len(templates)]
            return_text = return_template.format(handle_a=hb, handle_b=ha)

            candidates.append(HololinkCandidate(
                handle_a=ha,
                handle_b=hb,
                forward_text=forward_text,
                return_text=return_text,
                frame=frame_name,
                score=0.5,
                source="heuristic",
            ))

    return candidates


def _try_llm_generation(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
) -> Tuple[List[HololinkCandidate], str]:
    """
    Try to generate candidates via OpenAI API.

    CRITICAL: Prompts model to NOT use quotation marks.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return [], ""

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    warning = ""

    try:
        import openai

        # Prepare handle lists
        quotes_a = [h["quote"] for h in handles_a[:5]]
        quotes_b = [h["quote"] for h in handles_b[:5]]

        system_prompt = """You generate hololink sentences connecting two items.

CRITICAL RULES - MUST FOLLOW:
1. NEVER use quotation marks (" or ' or " or ") anywhere in your output
2. Include handles as PLAIN TEXT within the sentence (no quotes around them)
3. Each hololink must be exactly ONE sentence (10-25 words)
4. Each sentence must contain at least one handle from A AND one from B
5. Be specific to the content - no generic templates
6. Generate diverse options using different frames:
   - Causality: what enables what
   - Tension: what conflicts with what
   - Identity: what redefines what
   - Stakes: what reveals hidden risks
   - Framing: what makes what look intentional
   - Reversal: what inverts the logic

BANNED patterns (do not use):
- "How does X lead into Y"
- "Provide evidence", "Validate", "Operationalize"
- "Test case", "Checklist", "Schema for"
- "Walk me through", "Explain why it matters"

GOOD examples (NO QUOTES):
- If The Author cant be located, why does the narrator become a collector
- Scheherazade in reverse turns the mystery into a captivity mechanism
- Giallo framing makes confusion feel intentional

BAD examples (HAS QUOTES - FORBIDDEN):
- "The Author" leads into "mystery"
- How does "X" connect to "Y"

Output JSON:
{
  "candidates": [
    {
      "handle_a": "handle from A (plain text)",
      "handle_b": "handle from B (plain text)",
      "forward_text": "sentence from A to B with both handles as plain text",
      "return_text": "sentence from B to A with both handles as plain text",
      "frame": "causality|tension|identity|stakes|framing|reversal"
    }
  ]
}

Generate 8 diverse candidates."""

        # Truncate bodies
        body_a = (item_a.get("body") or "")[:600]
        body_b = (item_b.get("body") or "")[:600]

        user_prompt = f"""Item A:
Title: {item_a.get("title", "")}
Body: {body_a}

Handles from A (use as PLAIN TEXT, no quotes): {json.dumps(quotes_a)}

Item B:
Title: {item_b.get("title", "")}
Body: {body_b}

Handles from B (use as PLAIN TEXT, no quotes): {json.dumps(quotes_b)}

Generate 8 candidates. REMEMBER: NO quotation marks anywhere in forward_text or return_text."""

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
        except openai.BadRequestError as e:
            if "model" in str(e).lower():
                warning = f"Invalid model '{model}', falling back to gpt-4o-mini"
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.8,
                    max_tokens=1200,
                    response_format={"type": "json_object"},
                )
            else:
                raise

        content = response.choices[0].message.content
        data = json.loads(content)

        candidates = []
        for c in data.get("candidates", [])[:10]:
            # Strip any quotes that might have slipped through
            forward = strip_all_quotes(c.get("forward_text", ""))
            return_ = strip_all_quotes(c.get("return_text", ""))

            candidates.append(HololinkCandidate(
                handle_a=strip_all_quotes(c.get("handle_a", "")),
                handle_b=strip_all_quotes(c.get("handle_b", "")),
                forward_text=forward,
                return_text=return_,
                frame=c.get("frame", "unknown"),
                score=0.7,  # LLM candidates start higher
                source="llm",
            ))

        return candidates, warning

    except ImportError:
        return [], "openai package not installed"
    except Exception as e:
        print(f"[hololoop_engine] LLM generation failed: {e}")
        return [], str(e)


def _hard_filter(candidates: List[HololinkCandidate]) -> List[HololinkCandidate]:
    """
    Apply hard filters to remove invalid candidates.

    CRITICAL filters:
    - Must NOT contain quotation marks
    - Must contain handles verbatim (as plain substrings)
    - Must be single sentence
    - Must not contain banned patterns
    """
    filtered = []

    for c in candidates:
        # CRITICAL: No quotation marks
        if _contains_quotes(c.forward_text) or _contains_quotes(c.return_text):
            continue

        # Must contain handles verbatim
        if not _contains_handle_verbatim(c.forward_text, c.handle_a):
            continue
        if not _contains_handle_verbatim(c.forward_text, c.handle_b):
            continue
        if not _contains_handle_verbatim(c.return_text, c.handle_a):
            continue
        if not _contains_handle_verbatim(c.return_text, c.handle_b):
            continue

        # Must be single sentence
        if not _is_single_sentence(c.forward_text):
            continue
        if not _is_single_sentence(c.return_text):
            continue

        # No banned boilerplate
        if _contains_banned_pattern(c.forward_text):
            continue
        if _contains_banned_pattern(c.return_text):
            continue

        # Length checks
        if len(c.forward_text) < 15 or len(c.forward_text) > 150:
            continue
        if len(c.return_text) < 15 or len(c.return_text) > 150:
            continue

        filtered.append(c)

    return filtered


def _rank_candidates(candidates: List[HololinkCandidate]) -> List[HololinkCandidate]:
    """
    Score and rank candidates by quality.
    """
    for c in candidates:
        score = c.score

        # LLM source bonus
        if c.source == "llm":
            score += 0.1

        # Prefer longer handles (more specific)
        if len(c.handle_a) >= 15:
            score += 0.05
        if len(c.handle_b) >= 15:
            score += 0.05

        # Prefer medium-length sentences (20-60 chars)
        fwd_len = len(c.forward_text)
        if 20 <= fwd_len <= 60:
            score += 0.05
        elif fwd_len > 100:
            score -= 0.05

        # Penalty for "How does" pattern
        if c.forward_text.lower().startswith("how does"):
            score -= 0.15
        if c.return_text.lower().startswith("how does"):
            score -= 0.15

        c.score = min(score, 1.0)

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _diversify(candidates: List[HololinkCandidate], k: int = 4) -> List[HololinkCandidate]:
    """
    Select k diverse candidates.

    Ensures variety in:
    - Frames (causality, tension, identity, etc.)
    - Handles used
    - Sentence structure

    Constraint: At most 1 "How does" pattern in final 4.
    """
    if len(candidates) <= k:
        return candidates

    selected = []
    used_frames = set()
    used_handle_pairs = set()
    how_does_count = 0
    max_how_does = 1

    # First pass: one of each frame type
    for c in candidates:
        if len(selected) >= k:
            break

        # Check "How does" limit
        is_how_does = (
            c.forward_text.lower().startswith("how does") or
            c.return_text.lower().startswith("how does")
        )
        if is_how_does and how_does_count >= max_how_does:
            continue

        # Prefer unseen frames
        if c.frame not in used_frames:
            handle_pair = f"{c.handle_a[:15]}|{c.handle_b[:15]}"
            if handle_pair not in used_handle_pairs:
                selected.append(c)
                used_frames.add(c.frame)
                used_handle_pairs.add(handle_pair)
                if is_how_does:
                    how_does_count += 1

    # Second pass: fill with remaining diverse options
    for c in candidates:
        if len(selected) >= k:
            break
        if c in selected:
            continue

        # Check "How does" limit
        is_how_does = (
            c.forward_text.lower().startswith("how does") or
            c.return_text.lower().startswith("how does")
        )
        if is_how_does and how_does_count >= max_how_does:
            continue

        # Check for similar content
        handle_pair = f"{c.handle_a[:15]}|{c.handle_b[:15]}"
        if handle_pair in used_handle_pairs:
            continue

        # Check for near-duplicate sentences
        is_duplicate = False
        for s in selected:
            if _token_jaccard(c.forward_text, s.forward_text) > 0.5:
                is_duplicate = True
                break
        if is_duplicate:
            continue

        selected.append(c)
        used_handle_pairs.add(handle_pair)
        if is_how_does:
            how_does_count += 1

    return selected[:k]


def generate_hololoop_options(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Generate 4 hololoop options for connecting items A and B.

    PASS 2 Pipeline:
    1. Extract handles from both items
    2. Generate many candidates (heuristic + LLM)
    3. Hard filter (no quotes, handles verbatim, single sentence)
    4. Rank and diversify
    5. Pick top 4

    Args:
        item_a: First Queue Item dict
        item_b: Second Queue Item dict
        return_debug: Include debug info in response

    Returns:
        Dict with:
        - options: List of 4 hololoop option dicts
        - source: "llm" | "heuristic" | "mixed"
        - debug: Optional debug info
    """
    # Step 1: Extract handles
    handles_a = extract_handles(
        item_a.get("body") or "",
        item_a.get("title")
    )
    handles_b = extract_handles(
        item_b.get("body") or "",
        item_b.get("title")
    )

    # Select diverse handles
    selected_a = choose_diverse_handles(handles_a, k=5)
    selected_b = choose_diverse_handles(handles_b, k=5)

    # Ensure we have at least 2 handles from each item
    if len(selected_a) < 2:
        title = strip_all_quotes(item_a.get("title", "this content")[:40])
        selected_a.append({"quote": title, "kind": "heading"})
    if len(selected_b) < 2:
        title = strip_all_quotes(item_b.get("title", "this content")[:40])
        selected_b.append({"quote": title, "kind": "heading"})

    # Step 2: Generate candidates
    candidates = []

    # Try LLM first
    llm_candidates, warning = _try_llm_generation(item_a, item_b, selected_a, selected_b)
    candidates.extend(llm_candidates)

    # Always add heuristic candidates as fallback/supplement
    heuristic_candidates = _generate_heuristic_candidates(selected_a, selected_b)
    candidates.extend(heuristic_candidates)

    # Step 3: Hard filter
    filtered = _hard_filter(candidates)

    # Step 4: Rank
    ranked = _rank_candidates(filtered)

    # Step 5: Diversify and pick 4
    final = _diversify(ranked, k=4)

    # Determine source
    if any(c.source == "llm" for c in final):
        source = "llm" if all(c.source == "llm" for c in final) else "mixed"
    else:
        source = "heuristic"

    # Format as options
    options = []
    for i, c in enumerate(final, 1):
        options.append({
            "option_index": i,
            "link_text_forward": c.forward_text,
            "link_text_return": c.return_text,
            "handle_a_used": c.handle_a,
            "handle_b_used": c.handle_b,
            "frame": c.frame,  # Internal only
        })

    # Pad with fallback if needed
    while len(options) < 4:
        idx = len(options)
        ha = selected_a[idx % len(selected_a)]["quote"]
        hb = selected_b[idx % len(selected_b)]["quote"]

        # Simple fallback sentences (no quotes!)
        fallback_frames = [
            ("The logic of {a} leads toward {b}", "{b} follows from what {a} established"),
            ("What {a} reveals about {b}", "{b} casts new light on {a}"),
            ("{a} and {b} share hidden structure", "From {b} back to {a}"),
            ("{a} opens a path to {b}", "{b} traces back to {a}"),
        ]
        frame = fallback_frames[idx % len(fallback_frames)]

        options.append({
            "option_index": len(options) + 1,
            "link_text_forward": frame[0].format(a=ha, b=hb),
            "link_text_return": frame[1].format(a=ha, b=hb),
            "handle_a_used": ha,
            "handle_b_used": hb,
            "frame": "fallback",
        })

    result = {
        "options": options[:4],
        "source": source,
        "warning": warning or None,
        "item_a_id": item_a.get("id"),
        "item_b_id": item_b.get("id"),
    }

    if return_debug:
        result["debug"] = {
            "handles_a": [h["quote"] for h in selected_a],
            "handles_b": [h["quote"] for h in selected_b],
            "candidates_generated": len(candidates),
            "candidates_filtered": len(filtered),
            "candidates_ranked": len(ranked),
            "extraction_tags_a": [h.get("extraction_tag", "") for h in selected_a],
            "extraction_tags_b": [h.get("extraction_tag", "") for h in selected_b],
        }

    return result


def options_to_bond_create_params(
    option: Dict[str, Any],
    item_a_id: str,
    item_b_id: str,
) -> Dict[str, Any]:
    """
    Convert a hololoop option to parameters for creating a Bond.
    """
    return {
        "input_item_ids": [item_a_id, item_b_id],
        "prompt_text": f"Hololoop: {item_a_id} ↔ {item_b_id}",
        "bond_kind": "hololoop",
        "link_text_forward": option["link_text_forward"],
        "link_text_return": option["link_text_return"],
    }
