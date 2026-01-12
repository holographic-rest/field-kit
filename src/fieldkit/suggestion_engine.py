"""
Field-Kit v0.1 Suggestion Engine

Generates item-conditioned bond suggestions with genuine variety.

Two modes:
1. OpenAI mode (if OPENAI_API_KEY set): ONE API call returning JSON for all 4 suggestions
2. Fallback mode: Smarter deterministic method with varied sentence structures

Key requirements (from spec):
- Each suggestion quotes a VERBATIM handle from item content
- 4 suggestions use 4 DIFFERENT intents
- Surface language VARIES (not always Define/Trace/Connect/Test)
- No "test case that validates" without test-ish words in handle
- prompt_text is ONE sentence (max one semicolon)
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import re

from .handles import extract_handles, choose_diverse_handles, normalize_for_anchor


# === Intent types (4 core categories) ===
INTENTS = ["clarify", "concretize", "connect", "test"]

# Test-ish words that justify test/validation suggestions
TEST_WORDS = {
    "test", "tests", "testing", "validate", "validates", "validation",
    "verify", "verifies", "verification", "assert", "assertion",
    "check", "checks", "checking", "spec", "specs", "specification",
    "requirement", "requirements", "acceptance", "unit", "integration",
    "metric", "metrics", "evaluation", "criteria", "criterion",
}

# Leading verbs to reject for anti-generic detection
GENERIC_LEADING_VERBS = {"define", "trace", "connect", "test", "map", "operationalize"}


# === Sentence pattern pools (50+ diverse patterns) ===

CLARIFY_PATTERNS = [
    'What exactly does "{handle}" mean in concrete, testable terms?',
    'Unpack "{handle}": what are its 3 core components?',
    'Spell out "{handle}" with 3 specific examples.',
    'Pin down the meaning of "{handle}" using observable behaviors.',
    'What would falsify the claim embedded in "{handle}"?',
    'Break "{handle}" into 4 testable sub-claims.',
    'Make "{handle}" precise: what conditions must hold?',
    'Clarify the scope of "{handle}": what is in and what is out?',
    'State "{handle}" as a MUST/MUST NOT rule with 3 examples.',
    'What assumptions does "{handle}" depend on?',
]

CONCRETIZE_PATTERNS = [
    'Walk through "{handle}" step by step, showing 5 concrete states.',
    'Give 4 real examples where "{handle}" applies.',
    'Sketch a scenario that instantiates "{handle}" end-to-end.',
    'Show "{handle}" in action with inputs, processing, and outputs.',
    'Turn "{handle}" into a 6-step implementation checklist.',
    'Ground "{handle}" in a specific use case with named components.',
    'Illustrate "{handle}" with a before/after comparison.',
    'Flesh out "{handle}" with 5 concrete acceptance criteria.',
    'Operationalize "{handle}" as a sequence of observable events.',
    'Make "{handle}" tangible: what would a user see/do?',
]

CONNECT_PATTERNS = [
    'How does "{handle}" relate to 3 other concepts in this document?',
    'Map "{handle}" to upstream and downstream dependencies.',
    'What depends on "{handle}" and what does it depend on?',
    'Bridge "{handle}" to 2 adjacent architectural layers.',
    'Show how "{handle}" interacts with 3 neighboring components.',
    'Link "{handle}" to its preconditions and postconditions.',
    'Connect "{handle}" to 3 observable events in the system.',
    'Where does "{handle}" fit in the overall data flow?',
    'Relate "{handle}" to 2 constraints that govern it.',
    'What happens if "{handle}" fails or is missing?',
]

TEST_PATTERNS = [
    'Propose 4 test cases that would verify "{handle}".',
    'What are 3 edge cases that could break "{handle}"?',
    'Design a minimal experiment to validate "{handle}".',
    'List 4 specific assertions that confirm "{handle}" works.',
    'What metrics would prove "{handle}" is succeeding?',
    'Identify 3 failure modes for "{handle}" and how to detect them.',
    'Write 4 acceptance criteria for "{handle}" as checkboxes.',
    'What would a regression test for "{handle}" check?',
    'How would you know if "{handle}" stopped working?',
    'Create a 5-point scoring rubric for "{handle}".',
]

PATTERN_POOLS = {
    "clarify": CLARIFY_PATTERNS,
    "concretize": CONCRETIZE_PATTERNS,
    "connect": CONNECT_PATTERNS,
    "test": TEST_PATTERNS,
}


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _has_test_words(text: str) -> bool:
    """Check if text contains test-ish words."""
    text_lower = text.lower()
    return any(tw in text_lower for tw in TEST_WORDS)


def _extract_first_word(text: str) -> str:
    """Extract first word (lowercase) from text."""
    words = text.split()
    return words[0].lower() if words else ""


def _validate_suggestions(
    suggestions: List[Dict[str, Any]],
    item_text: str,
) -> Tuple[bool, List[str]]:
    """
    Validate suggestions meet all hard constraints.

    Returns: (is_valid, list_of_errors)
    """
    errors = []
    item_text_lower = item_text.lower()

    # Check we have exactly 4
    if len(suggestions) != 4:
        errors.append(f"Expected 4 suggestions, got {len(suggestions)}")

    # Check each suggestion
    intents_used = set()
    leading_verbs = []

    for i, s in enumerate(suggestions):
        handle = s.get("handle_quote", "")
        prompt = s.get("prompt_text", "")
        intent = s.get("intent", "")

        # Handle must exist in item text (case-insensitive)
        if handle.lower() not in item_text_lower:
            errors.append(f"Suggestion {i+1}: handle_quote not in item text")

        # Prompt must contain handle verbatim
        if handle and handle.lower() not in prompt.lower():
            errors.append(f"Suggestion {i+1}: prompt doesn't contain handle verbatim")

        # Prompt must be one sentence (max one semicolon, no multi-paragraph)
        if prompt.count('\n\n') > 0:
            errors.append(f"Suggestion {i+1}: prompt has multiple paragraphs")
        if prompt.count(';') > 1:
            errors.append(f"Suggestion {i+1}: prompt has more than one semicolon")

        # Track intents
        if intent in intents_used:
            errors.append(f"Suggestion {i+1}: duplicate intent '{intent}'")
        intents_used.add(intent)

        # Track leading verbs
        first_word = _extract_first_word(prompt)
        leading_verbs.append(first_word)

    # Check for same leading verb patterns
    if len(set(leading_verbs)) < 3:
        errors.append("Too many suggestions share the same leading verb pattern")

    # Check for generic leading verb set
    verb_set = set(leading_verbs)
    if verb_set <= GENERIC_LEADING_VERBS and len(verb_set) >= 3:
        errors.append("All prompts use generic Define/Trace/Connect/Test verbs")

    return len(errors) == 0, errors


def _try_openai_generation(
    item_title: str,
    item_body: Optional[str],
    handles: List[Dict[str, Any]],
) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Try to generate suggestions via OpenAI API.

    Returns: (suggestions or None, warning_message)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, ""

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    warning = ""

    try:
        import openai

        # Prepare handle quotes for prompt (top 10)
        handle_quotes = [h["quote"] for h in handles[:10]]

        # Build system prompt
        system_prompt = """You generate exactly 4 bond prompt suggestions for a knowledge item.

HARD RULES - FOLLOW EXACTLY:
1. Each suggestion is ONE sentence (12-30 words, max one semicolon)
2. Each suggestion MUST quote one of the provided handles VERBATIM in double quotes
3. Use 4 DIFFERENT intents: clarify, concretize, connect, test
4. Use 4 DIFFERENT starting verbs (NOT all Define/Trace/Connect/Test)
5. If handle has no test-ish words (test/validate/verify/spec/metric), do NOT suggest "test case that validates"
6. Include a numeric constraint in each prompt (e.g., "3 examples", "5 steps", "4 criteria")
7. Each prompt requests a DIFFERENT output shape (checklist vs schema vs examples vs risks)

Output JSON object with "suggestions" array:
{
  "suggestions": [
    {
      "intent": "clarify|concretize|connect|test",
      "handle_quote": "exact quote from handles list",
      "prompt_text": "one sentence prompt with handle in quotes",
      "why": "short rationale (<= 12 words)"
    },
    ...
  ]
}"""

        # Truncate body to first 1500 chars
        body_excerpt = (item_body or "")[:1500]
        if len(item_body or "") > 1500:
            body_excerpt += "..."

        user_prompt = f"""Item title: {item_title}

Item body (first 1500 chars):
{body_excerpt}

Available handles to use (MUST quote one verbatim per suggestion):
{json.dumps(handle_quotes, indent=2)}

Generate 4 diverse suggestions following all rules."""

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
        except openai.BadRequestError as e:
            # Invalid model, fallback to gpt-4o-mini
            if "model" in str(e).lower():
                warning = f"Invalid model '{model}', falling back to gpt-4o-mini"
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
            else:
                raise

        # Parse response
        content = response.choices[0].message.content
        data = json.loads(content)

        suggestions = data.get("suggestions", [])
        if not suggestions and isinstance(data, list):
            suggestions = data

        if len(suggestions) < 4:
            return None, "OpenAI returned fewer than 4 suggestions"

        # Normalize to our format
        results = []
        for s in suggestions[:4]:
            results.append({
                "intent": s.get("intent", "clarify"),
                "handle_quote": s.get("handle_quote", ""),
                "prompt_text": s.get("prompt_text", ""),
                "why": s.get("why", ""),
            })

        return results, warning

    except ImportError:
        return None, "openai package not installed"
    except Exception as e:
        print(f"[suggestion_engine] OpenAI generation failed: {e}")
        return None, str(e)


def _deterministic_fallback(
    item_title: str,
    item_body: Optional[str],
    handles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate suggestions deterministically with varied language.

    Key difference from previous impl: uses content-based seed to select
    different patterns for different items.
    """
    # Use content hash for deterministic but varied selection
    content = (item_title or "") + (item_body or "")
    seed = _hash_content(content)

    # Select 4 handles (or pad if needed)
    selected_handles = handles[:4]
    while len(selected_handles) < 4:
        fallback = {
            "quote": normalize_for_anchor(item_title) or "this content",
            "kind": "heading",
            "score": 0.5,
        }
        selected_handles.append(fallback)

    suggestions = []

    for i, intent in enumerate(INTENTS):
        handle = selected_handles[i]
        quote = handle["quote"]

        # Check if this handle has test words
        has_test = _has_test_words(quote)

        # Skip test intent if handle has no test words
        if intent == "test" and not has_test:
            # Use a concretize variant instead
            patterns = CONCRETIZE_PATTERNS
        else:
            patterns = PATTERN_POOLS[intent]

        # Select pattern based on seed + index (varies per item)
        pattern_idx = (seed + i * 7 + len(content) + hash(quote)) % len(patterns)
        pattern = patterns[pattern_idx]

        # Format prompt
        prompt_text = pattern.format(handle=quote)

        # Generate brief rationale
        why_options = [
            f"grounds the {intent} in item content",
            f"makes the claim testable",
            f"clarifies scope and boundaries",
            f"enables verification",
        ]
        why = why_options[i % len(why_options)]

        suggestions.append({
            "intent": intent,
            "handle_quote": quote,
            "prompt_text": prompt_text,
            "why": why,
        })

    return suggestions


def generate_bond_suggestions(
    item_title: str,
    item_body: Optional[str] = None,
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Generate 4 item-conditioned bond suggestions.

    Pipeline:
    1. Extract handles from content (span-first, structure-aware)
    2. Choose 8 diverse handles as candidates
    3. Try OpenAI generation if API key available
    4. Fall back to smarter deterministic method
    5. Validate suggestions meet all constraints

    Args:
        item_title: Item title
        item_body: Item body text
        return_debug: If True, include debug info in response

    Returns:
        Dict with:
        - suggestions: List of 4 suggestion dicts
        - suggestion_source: "llm" | "fallback"
        - warning: Optional warning message
        - debug: Optional debug info (if return_debug=True)
          - candidate_handles: The 8 handles used as candidates
    """
    # Extract and select handles
    full_text = (item_title or "") + "\n" + (item_body or "")
    all_handles = extract_handles(item_body or "", item_title)
    candidate_handles = choose_diverse_handles(all_handles, k=8)

    # Pad if insufficient
    if len(candidate_handles) < 4:
        fallback = {
            "quote": normalize_for_anchor(item_title) or "this content",
            "kind": "heading",
            "score": 0.5,
        }
        while len(candidate_handles) < 4:
            candidate_handles.append(fallback)

    # Try OpenAI generation
    suggestions, warning = _try_openai_generation(item_title, item_body, candidate_handles)

    source = "llm" if suggestions else "fallback"

    if not suggestions:
        # Use deterministic fallback
        suggestions = _deterministic_fallback(item_title, item_body, candidate_handles)

    # Validate
    is_valid, errors = _validate_suggestions(suggestions, full_text)
    if not is_valid and source == "llm":
        # Fall back to deterministic if LLM output is invalid
        suggestions = _deterministic_fallback(item_title, item_body, candidate_handles)
        source = "fallback"
        warning = f"LLM suggestions invalid ({', '.join(errors)}), using fallback"

    result = {
        "suggestions": suggestions,
        "suggestion_source": source,
        "warning": warning or None,
    }

    if return_debug:
        result["debug"] = {
            "candidate_handles": [h["quote"] for h in candidate_handles],
            "all_handles_count": len(all_handles),
        }

    return result


def suggestions_to_legacy_format(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert to legacy format for backward compatibility with spin_recipes.

    Returns list of dicts with:
    - display_text
    - prompt_text
    - intent_type
    - recipe_id
    - handle_quote
    """
    suggestions = result.get("suggestions", [])

    # Map intent to recipe_id
    intent_to_recipe = {
        "clarify": "clarify_to_testable_claim",
        "concretize": "ground_in_experiment",
        "connect": "architecture_map",
        "test": "adversarial_test_cases",
    }

    legacy = []
    for s in suggestions:
        intent = s.get("intent", "clarify")
        prompt = s.get("prompt_text", "")
        handle = s.get("handle_quote", "")

        legacy.append({
            "display_text": prompt,
            "prompt_text": prompt,
            "intent_type": intent,
            "recipe_id": intent_to_recipe.get(intent, "clarify_to_testable_claim"),
            "handle_quote": handle,
        })

    return legacy


def generate_bond_suggestions_with_evidence(
    item: Dict[str, Any],
    return_debug: bool = False,
    data_dir: Optional[str] = None,
    session_state: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate bond suggestions with evidence shards (pointer-style).

    This is the S03 version that produces structured candidates with:
    - Evidence shards citing the handle location
    - Probabilities from pointer scorer
    - Structured candidate objects

    S04: Added multi-scale context aggregation. If data_dir is provided,
    attempts to add mid/far scale evidence from event history.

    S05: Added graph propagation reranking. Uses MPNN-style message passing
    to improve candidate scoring based on graph structure.

    S07: Added session_state parameter. If provided, uses state to bias
    evidence selection toward entities/open_questions in state.

    Args:
        item: The item dict with id, title, body
        return_debug: Include debug info
        data_dir: Optional data directory for multi-scale sampling
        session_state: Optional SessionState for continuity (S07)

    Returns:
        Dict with:
        - suggestions: List of suggestion dicts (legacy compatible)
        - candidates: List of Candidate objects (as dicts)
        - suggestion_source: "llm" | "fallback"
        - has_evidence: Count of suggestions with evidence
        - scales_present: Set of scales found in evidence (S04)
        - state_utilized: Whether session_state influenced results (S07)
    """
    from .candidate_set import (
        Candidate, EvidenceShard,
        generate_candidate_id, generate_shard_id,
        create_evidence_from_handle,
    )
    from .pointer_scorer import score_candidates, select_top_k

    item_title = item.get("title", "")
    item_body = item.get("body")
    item_id = item.get("id", "")

    # S07: Extract state influence keywords
    state_keywords = set()
    state_utilized = False
    if session_state is not None:
        try:
            from .session_state import get_state_influence_keywords
            state_keywords = get_state_influence_keywords(session_state)
            if state_keywords:
                state_utilized = True
        except ImportError:
            pass  # Session state module not available

    # Get base suggestions
    result = generate_bond_suggestions(item_title, item_body, return_debug)
    suggestions = result.get("suggestions", [])
    source = result.get("suggestion_source", "fallback")

    # S04: Sample multi-scale context if data_dir provided
    context_pack = None
    if data_dir:
        try:
            from .dilated_context import DilatedContextSampler
            sampler = DilatedContextSampler(data_dir)
            context_pack = sampler.sample(item_id)
        except Exception:
            pass  # Best effort - continue without multi-scale

    # Convert to candidates with evidence
    candidates = []
    for i, s in enumerate(suggestions):
        handle = s.get("handle_quote", "")
        prompt = s.get("prompt_text", "")
        intent = s.get("intent", "clarify")

        # Create candidate
        candidate = Candidate(
            candidate_id=generate_candidate_id(item_id, prompt[:50]),
            target_type="suggestion",
            target_id=None,
            title=prompt[:100] if len(prompt) > 100 else prompt,
            summary=prompt,
            intent_type=intent,
            handle_quote=handle,
            source=source,
            rank=i + 1,
        )

        # Create local evidence shard from the handle
        if handle:
            source_text = item_body or item_title
            if source_text:
                evidence = create_evidence_from_handle(item, handle)
                # Ensure scale and dilation_offset are set
                evidence.scale = "local"
                evidence.dilation_offset = 0
                candidate.evidence_shards.append(evidence)

        # S04: Try to add mid/far evidence from context pack
        # S07: Pass state keywords to bias evidence selection
        if context_pack and handle:
            _add_multiscale_evidence(candidate, context_pack, handle, state_keywords)

        candidates.append(candidate)

    # Score candidates and get probabilities
    candidates = score_candidates(candidates)

    # S05: Graph propagation reranking if data_dir provided
    if data_dir:
        try:
            from .graph_propagation import GraphReranker
            reranker = GraphReranker(data_dir, propagation_rounds=2, graph_weight=0.3)
            candidates = reranker.rerank(item_id, candidates, use_propagation=True)
        except Exception:
            pass  # Best effort - continue without graph reranking

    candidates = select_top_k(candidates, k=4, diversify=True)

    # Update suggestions with evidence data for backward compatibility
    enhanced_suggestions = []
    scales_present = set()

    for c in candidates:
        # Track scales present
        for es in c.evidence_shards:
            scales_present.add(es.scale)

        s = {
            "intent": c.intent_type,
            "handle_quote": c.handle_quote,
            "prompt_text": c.summary,
            "why": f"Based on \"{c.handle_quote[:30]}...\"" if len(c.handle_quote) > 30 else f"Based on \"{c.handle_quote}\"",
            # Add evidence fields
            "evidence_shards": [es.to_dict() for es in c.evidence_shards],
            "candidate_id": c.candidate_id,
            "probability": c.probability,
            "score": c.score,
            "rank": c.rank,
        }
        enhanced_suggestions.append(s)

    # Count evidence
    has_evidence = sum(1 for c in candidates if c.has_evidence())

    output = {
        "suggestions": enhanced_suggestions,
        "candidates": [c.to_dict() for c in candidates],
        "suggestion_source": source,
        "has_evidence": has_evidence,
        "scales_present": list(scales_present),  # S04
        "state_utilized": state_utilized,  # S07
        "warning": result.get("warning"),
    }

    if return_debug:
        output["debug"] = result.get("debug", {})

    return output


def _add_multiscale_evidence(
    candidate,
    context_pack,
    handle: str,
    state_keywords: Optional[set] = None,
) -> None:
    """
    Add mid/far scale evidence to a candidate (S04, S07).

    Best-effort: searches context items for matching keywords.

    S07: If state_keywords provided, prioritizes items matching those keywords.
    """
    from .candidate_set import EvidenceShard, generate_shard_id
    from .dilated_context import find_matching_text_in_item

    # Extract keywords from handle for matching
    keywords = handle.split()
    if len(keywords) > 3:
        keywords = keywords[:3]  # Use first 3 words

    # S07: Add state keywords to search terms if available
    if state_keywords:
        keywords = list(set(keywords) | set(list(state_keywords)[:3]))

    # Try to find mid-scale evidence
    for ctx_item in context_pack.mid_items[:3]:  # Check up to 3 mid items
        item_dict = {
            "id": ctx_item.item_id,
            "title": ctx_item.title,
            "body": ctx_item.body,
        }
        match = find_matching_text_in_item(item_dict, keywords)
        if match:
            text_span, span_start, span_end = match
            shard = EvidenceShard(
                shard_id=generate_shard_id(ctx_item.item_id, text_span),
                source_type="item",
                source_id=ctx_item.item_id,
                text_span=text_span,
                span_start=span_start,
                span_end=span_end,
                scale="mid",
                dilation_offset=ctx_item.dilation_offset,
            )
            candidate.evidence_shards.append(shard)
            break  # One mid shard is enough

    # Try to find far-scale evidence
    for ctx_item in context_pack.far_items[:3]:  # Check up to 3 far items
        item_dict = {
            "id": ctx_item.item_id,
            "title": ctx_item.title,
            "body": ctx_item.body,
        }
        match = find_matching_text_in_item(item_dict, keywords)
        if match:
            text_span, span_start, span_end = match
            shard = EvidenceShard(
                shard_id=generate_shard_id(ctx_item.item_id, text_span),
                source_type="item",
                source_id=ctx_item.item_id,
                text_span=text_span,
                span_start=span_start,
                span_end=span_end,
                scale="far",
                dilation_offset=ctx_item.dilation_offset,
            )
            candidate.evidence_shards.append(shard)
            break  # One far shard is enough
