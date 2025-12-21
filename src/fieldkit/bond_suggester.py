"""
Field-Kit v0.1 Bond Suggester

Generates content-specific bond suggestions with VARIED language.

Two modes:
1. OpenAI mode (if OPENAI_API_KEY set): Single API call for 4 diverse suggestions
2. Fallback mode: Deterministic but with VARIED surface language

Key requirements:
- Each suggestion quotes a VERBATIM handle from item content
- 4 suggestions use 4 DIFFERENT intents (not the same 4 every time)
- Surface language VARIES per content (not always Define/Trace/Map/Operationalize)
- No "test case that validates" without test-ish words in handle
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import re
import os
import json
import hashlib


# === Handle Dataclass ===

@dataclass
class Handle:
    """A handle extracted from Item content."""
    text: str  # Exact substring from item body/title
    kind: str  # bullet | phrase | entity | heading | sentence
    weight: float  # Ranking score
    source: str  # body | title


# Test-ish words that allow "test case" suggestions
TEST_WORDS = {
    "test", "testing", "tests", "validate", "validation", "validates",
    "verify", "verification", "verifies", "metric", "metrics",
    "evaluation", "evaluate", "unit test", "unit-test", "unit",
    "acceptance", "assert", "assertion", "check", "criteria",
    "spec", "specs", "specification", "requirement", "requirements",
}

# Named entities / domain terms to recognize
DOMAIN_ENTITIES = {
    "field", "item", "bond", "episode", "network", "event", "ledger",
    "holologue", "monologue", "dialogue", "qdpi", "canon", "vault",
    "entrance way", "the entrance way", "gibsey", "rag", "microservices",
    "gpus", "linear algebra", "agents", "operator", "prompt",
}

# 12 intent types from bond ontology (use varied selection)
ALL_INTENT_TYPES = [
    "clarifies", "expands", "grounds_in", "derives_from",
    "bridges", "compares", "forks", "exemplifies",
    "qualifies", "revises", "answers", "contradicts",
]

# Map intent to recipe_id for traceability
INTENT_TO_RECIPE = {
    "clarifies": "clarify_to_testable_claim",
    "expands": "expand_to_checklist",
    "grounds_in": "ground_in_experiment",
    "derives_from": "derive_min_schema",
    "bridges": "architecture_map",
    "compares": "compare_with_criteria",
    "forks": "debate_two_options",
    "exemplifies": "ground_in_experiment",
    "qualifies": "decision_with_reasons",
    "revises": "clarify_to_testable_claim",
    "answers": "clarify_to_testable_claim",
    "contradicts": "peer_review_objections",
}

# VARIED sentence patterns - 40+ options grouped by semantic operation
# Each pattern has {quote} placeholder for handle and {num} for numeric constraint
SENTENCE_PATTERNS = {
    "clarify": [
        'Break down "{quote}" into {num} distinct concepts and define each precisely.',
        'Spell out what "{quote}" means in concrete, testable terms.',
        'Pin down "{quote}": what exactly does it claim and what would falsify it?',
        'Make "{quote}" explicit with {num} specific examples.',
        'State precisely what "{quote}" asserts and its boundary conditions.',
    ],
    "expand": [
        'Flesh out "{quote}" with {num} supporting details.',
        'Develop "{quote}" further: add {num} sub-points that elaborate.',
        'Build out "{quote}" into a {num}-item checklist.',
        'Extend "{quote}" to cover {num} additional cases or scenarios.',
        'Enrich "{quote}" with {num} concrete examples from this domain.',
    ],
    "ground": [
        'Ground "{quote}" in practice: propose {num} ways to observe it.',
        'Demonstrate "{quote}" with {num} concrete scenarios.',
        'Illustrate "{quote}" step by step in {num} phases.',
        'Apply "{quote}" to a real case: show {num} inputs and outputs.',
        'Put "{quote}" into action: list {num} specific steps.',
    ],
    "derive": [
        'Extract {num} rules from "{quote}" as MUST/MUST NOT constraints.',
        'Derive the structure of "{quote}" with {num} key properties.',
        'Pull out {num} patterns from "{quote}" and formalize each.',
        'Identify {num} invariants that "{quote}" implies.',
        'Distill "{quote}" into {num} testable requirements.',
    ],
    "bridge": [
        'Connect "{quote}" to {num} related concepts: what do they share?',
        'Link "{quote}" upstream and downstream: {num} dependencies.',
        'Map "{quote}" onto {num} other parts of the architecture.',
        'Show how "{quote}" interacts with {num} neighboring components.',
        'Tie "{quote}" to {num} other concepts and explain the flow.',
    ],
    "compare": [
        'Contrast "{quote}" with {num} alternatives: pros and cons.',
        'Weigh "{quote}" against {num} other approaches.',
        'Compare "{quote}" on {num} criteria: which wins and why?',
        'Stack "{quote}" up against {num} competing options.',
        'Evaluate "{quote}" alongside {num} alternatives with scores.',
    ],
    "fork": [
        'Fork "{quote}" into {num} possible directions to explore.',
        'Branch "{quote}" into {num} alternative interpretations.',
        'Consider {num} ways "{quote}" could evolve differently.',
        'Explore {num} divergent paths from "{quote}".',
        'Open up {num} choices within "{quote}" for decision.',
    ],
    "exemplify": [
        'Give {num} examples of "{quote}" in action.',
        'Show {num} instances where "{quote}" applies.',
        'Provide {num} concrete cases that embody "{quote}".',
        'Illustrate "{quote}" with {num} specific scenarios.',
        'Concretize "{quote}" through {num} real examples.',
    ],
    "qualify": [
        'Add {num} constraints that bound "{quote}".',
        'Limit the scope of "{quote}" with {num} conditions.',
        'Narrow "{quote}" down by specifying {num} boundaries.',
        'Qualify "{quote}" with {num} edge cases to exclude.',
        'Refine "{quote}" by adding {num} precision conditions.',
    ],
    "revise": [
        'Rework "{quote}" into {num} sharper statements.',
        'Reframe "{quote}" from {num} different perspectives.',
        'Update "{quote}" with {num} clarifications.',
        'Sharpen "{quote}" by addressing {num} ambiguities.',
        'Reformulate "{quote}" as {num} more precise claims.',
    ],
}

# Map semantic operations to intent types
OPERATION_TO_INTENT = {
    "clarify": "clarifies",
    "expand": "expands",
    "ground": "grounds_in",
    "derive": "derives_from",
    "bridge": "bridges",
    "compare": "compares",
    "fork": "forks",
    "exemplify": "exemplifies",
    "qualify": "qualifies",
    "revise": "revises",
}


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _score_by_word_count(quote: str, base_score: float) -> float:
    """Boost score for multi-word spans (>= 3 words)."""
    wc = _word_count(quote)
    if wc >= 5:
        return min(base_score + 0.15, 1.0)
    elif wc >= 3:
        return min(base_score + 0.08, 1.0)
    elif wc == 2:
        return base_score
    else:
        return max(base_score - 0.10, 0.1)


# === Handle Extraction ===

def extract_handles(title: str, body: Optional[str]) -> List[Handle]:
    """
    Extract 8-20 candidate handles from Item content.

    Prefers:
    - Bullet labels and colon clauses (structured content)
    - Multi-word spans (>= 3 words)
    - Named entities and capitalized phrases
    """
    handles = []
    seen_texts = set()

    def add_handle(text: str, kind: str, weight: float, source: str) -> bool:
        """Add handle if valid and not duplicate."""
        text = text.strip()
        if not text or len(text) < 3:
            return False
        text_normalized = re.sub(r'\s+', ' ', text.lower())
        if text_normalized in seen_texts:
            return False
        if re.match(r'^page\s+\d+', text_normalized):
            return False
        if len(text) > 80:
            text = text[:80]

        # Apply word count boost
        adjusted_weight = _score_by_word_count(text, weight)

        seen_texts.add(text_normalized)
        handles.append(Handle(text=text, kind=kind, weight=adjusted_weight, source=source))
        return True

    lines = []
    if body:
        lines = [(i + 1, line) for i, line in enumerate(body.split('\n'))]

    # Extract from title
    if title:
        normalized_title = _normalize_title(title)
        if normalized_title and len(normalized_title) > 5:
            add_handle(normalized_title, "heading", 1.0, "title")

    # Extract headings
    for line_num, line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            heading = line_stripped.lstrip('#').strip()
            if heading and len(heading) > 3:
                add_handle(heading, "heading", 0.95, "body")
        if line_stripped.lower().startswith('title:'):
            title_text = line_stripped[6:].strip()
            title_text = re.sub(r'^[A-Z]+\s*[-–:]\s*', '', title_text)
            if title_text and len(title_text) > 5:
                add_handle(title_text, "heading", 0.9, "body")

    # Extract bullet labels
    for line_num, line in lines:
        line_stripped = line.strip()
        colon_match = re.match(r'^((?:What|How|Why|When|Where)\s+[^:]+):', line_stripped, re.IGNORECASE)
        if colon_match:
            phrase = colon_match.group(1).strip()
            add_handle(phrase, "bullet", 0.9, "body")
        bullet_match = re.match(r'^[-*•]\s+(?:\*\*)?([^:*]+)(?:\*\*)?\s*:', line_stripped)
        if bullet_match:
            label = bullet_match.group(1).strip()
            if len(label) > 3 and len(label) < 50:
                add_handle(label, "bullet", 0.85, "body")

    # Extract strong phrases
    full_text = (body or "") + "\n" + (title or "")
    for match in re.finditer(r'\*\*([^*]+)\*\*', full_text):
        phrase = match.group(1).strip()
        if len(phrase) > 3 and len(phrase) < 60:
            add_handle(phrase, "phrase", 0.8, "body")
    for match in re.finditer(r'["\']([^"\']+)["\']', full_text):
        phrase = match.group(1).strip()
        if len(phrase) > 5 and len(phrase) < 60:
            add_handle(phrase, "phrase", 0.75, "body")
    for match in re.finditer(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*\s*[+/&]\s*[a-zA-Z]+(?:\s+[a-zA-Z]+)*)', full_text):
        phrase = match.group(1).strip()
        if len(phrase) > 5 and len(phrase) < 50:
            add_handle(phrase, "phrase", 0.7, "body")

    # Extract named entities
    text_lower = full_text.lower()
    for entity in DOMAIN_ENTITIES:
        pattern = re.compile(re.escape(entity), re.IGNORECASE)
        for match in pattern.finditer(full_text):
            original = match.group()
            if len(original) > 2:
                add_handle(original, "entity", 0.85, "body")

    # Extract capitalized noun phrases
    for match in re.finditer(r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', full_text):
        phrase = match.group(0).strip()
        if len(phrase) > 5 and len(phrase) < 50:
            if phrase.lower() not in ['this document', 'this is', 'what is']:
                add_handle(phrase, "entity", 0.65, "body")

    # Extract sentence fragments if needed
    if len(handles) < 8:
        for line_num, line in lines[:10]:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.lower().startswith('title:'):
                continue
            if re.match(r'^page\s+\d+', line_stripped.lower()):
                continue
            for delim in [':', ',', ';', ' - ', ' – ']:
                if delim in line_stripped:
                    parts = line_stripped.split(delim)
                    if len(parts[0]) > 10 and len(parts[0]) < 60:
                        add_handle(parts[0], "sentence", 0.5, "body")
                    break

    handles.sort(key=lambda h: h.weight, reverse=True)
    return handles[:20]


def _normalize_title(title: str) -> str:
    """Normalize title by stripping PAGE/numeric prefixes."""
    if not title:
        return ""
    result = title.strip()
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^\d+\s*[-–_]\s*', '', result)
    return result.strip()


# === Diversity Selection ===

def select_diverse_handles(handles: List[Handle], count: int = 4) -> List[Handle]:
    """Select k diverse handles with variety of kinds."""
    if not handles:
        return []

    selected = []
    used_kinds = set()
    used_texts = set()
    priority_kinds = ["bullet", "phrase", "entity", "heading", "sentence"]

    for kind in priority_kinds:
        if len(selected) >= count:
            break
        for handle in handles:
            if handle.kind == kind and kind not in used_kinds:
                if not _overlaps_with_any(handle.text, used_texts):
                    selected.append(handle)
                    used_kinds.add(kind)
                    used_texts.add(handle.text.lower())
                    break

    for handle in handles:
        if len(selected) >= count:
            break
        if handle not in selected:
            if not _overlaps_with_any(handle.text, used_texts):
                selected.append(handle)
                used_texts.add(handle.text.lower())

    for handle in handles:
        if len(selected) >= count:
            break
        if handle not in selected:
            selected.append(handle)

    return selected[:count]


def _overlaps_with_any(text: str, used_texts: set) -> bool:
    """Check if text overlaps significantly with any used text."""
    text_lower = text.lower()
    text_words = set(text_lower.split())
    for used in used_texts:
        used_words = set(used.split())
        overlap = text_words & used_words
        if len(overlap) > 2 and len(overlap) / min(len(text_words), len(used_words)) > 0.6:
            return True
        if text_lower in used or used in text_lower:
            return True
    return False


# Alias for backward compatibility
def choose_top_handles(handles: List[Handle], k: int = 4) -> List[Handle]:
    """Alias for select_diverse_handles."""
    return select_diverse_handles(handles, count=k)


# === Content-Based Operation Selection ===

def _select_operations(handles: List[Handle], seed: int) -> List[str]:
    """
    Select 4 diverse operations based on handle content.

    Different handles produce different operation selections.
    """
    all_ops = list(SENTENCE_PATTERNS.keys())
    handle_text = " ".join(h.text.lower() for h in handles)

    selected = []

    # First pick: based on content semantics
    if any(w in handle_text for w in ["structure", "schema", "model", "pattern", "format"]):
        selected.append("derive")
    elif any(w in handle_text for w in ["flow", "step", "process", "through", "moves"]):
        selected.append("ground")
    elif any(w in handle_text for w in ["compare", "versus", "vs", "difference", "alternative"]):
        selected.append("compare")
    elif any(w in handle_text for w in ["what", "is", "means", "definition"]):
        selected.append("clarify")
    elif any(w in handle_text for w in ["how", "learn", "improve", "works"]):
        selected.append("ground")
    else:
        # Content-based hash for variety
        selected.append(all_ops[seed % len(all_ops)])

    # Fill remaining 3 with different operations
    remaining_ops = [op for op in all_ops if op not in selected]
    for i in range(3):
        if not remaining_ops:
            remaining_ops = [op for op in all_ops if op not in selected]
        pick_idx = (seed + i * 7 + len(handle_text)) % len(remaining_ops)
        op = remaining_ops.pop(pick_idx % len(remaining_ops))
        selected.append(op)

    return selected[:4]


def _compose_varied_sentence(
    handle: Handle,
    operation: str,
    seed: int,
    idx: int,
) -> Tuple[str, str]:
    """
    Compose a VARIED sentence for a handle + operation.

    Different content produces different sentence structures.
    Returns: (display_text, intent_type)
    """
    quote = handle.text
    patterns = SENTENCE_PATTERNS.get(operation, SENTENCE_PATTERNS["clarify"])

    # Select pattern based on seed and index (varies per content)
    pattern_idx = (seed + idx * 3) % len(patterns)
    pattern = patterns[pattern_idx]

    # Select numeric constraint based on content length and type
    if handle.kind in ["bullet", "heading"]:
        nums = [5, 6, 4, 3]
    elif handle.kind == "entity":
        nums = [3, 4, 5, 2]
    else:
        nums = [3, 4, 5, 6]
    num = nums[(seed + idx) % len(nums)]

    # Format sentence
    sentence = pattern.format(quote=quote, num=num)

    intent_type = OPERATION_TO_INTENT.get(operation, "clarifies")
    return sentence, intent_type


# === OpenAI Generation ===

def _try_openai_generation(
    handles: List[Handle],
    item_title: str,
    item_body: Optional[str],
) -> Optional[List[Dict[str, Any]]]:
    """
    Try to generate suggestions via OpenAI API.

    Returns None if no API key or API fails.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        import openai

        handle_quotes = [h.text for h in handles[:4]]

        system_prompt = """You generate exactly 4 bond suggestions for a knowledge item.

RULES:
1. Each suggestion is ONE sentence (12-25 words)
2. Each suggestion MUST quote one of the provided handles VERBATIM in double quotes
3. Use 4 DIFFERENT starting verbs (NOT all Define/Trace/Map/Operationalize)
4. Each suggestion asks for a DIFFERENT output shape (checklist vs schema vs examples vs risks)
5. If handle has no test-ish words, do NOT suggest "test case that validates"
6. Include a numeric constraint (e.g., "3 examples", "5 steps", "4 criteria")

Output JSON array with 4 objects:
[
  {"handle_quote": "exact quote", "display_text": "sentence", "intent_type": "clarifies|expands|grounds_in|derives_from|bridges|compares"},
  ...
]"""

        user_prompt = f"""Item title: {item_title}

Item body excerpt:
{(item_body or '')[:500]}

Handles to use (one per suggestion):
1. "{handle_quotes[0] if len(handle_quotes) > 0 else 'this content'}"
2. "{handle_quotes[1] if len(handle_quotes) > 1 else 'this content'}"
3. "{handle_quotes[2] if len(handle_quotes) > 2 else 'this content'}"
4. "{handle_quotes[3] if len(handle_quotes) > 3 else 'this content'}"

Generate 4 diverse suggestions as JSON array."""

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=600,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        suggestions = data if isinstance(data, list) else data.get("suggestions", [])

        if len(suggestions) < 4:
            return None

        results = []
        for s in suggestions[:4]:
            intent = s.get("intent_type", "clarifies")
            results.append({
                "display_text": s.get("display_text", ""),
                "prompt_text": s.get("display_text", ""),
                "intent_type": intent,
                "handle_quote": s.get("handle_quote", ""),
                "handle": s.get("handle_quote", ""),
                "intent": intent.replace("_", " ").title(),
                "recipe_id": INTENT_TO_RECIPE.get(intent, "clarify_to_testable_claim"),
            })

        return results

    except Exception as e:
        print(f"[bond_suggester] OpenAI generation failed: {e}")
        return None


# === Main API ===

def generate_suggestions(
    item_title: str,
    item_body: Optional[str] = None,
    other_item_titles: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate exactly 4 content-specific bond suggestions.

    Pipeline:
    1. Extract handles from content (prefers multi-word spans)
    2. Choose 4 diverse handles
    3. Try OpenAI generation if API key available
    4. Fall back to VARIED deterministic generation

    Each suggestion:
    - Quotes a VERBATIM handle from the item
    - Uses a DIFFERENT intent type
    - Has VARIED surface language (not same 4 verbs)
    - Is one sentence, no truncation

    Returns list of 4 dicts with:
    - display_text: Full sentence for UI (alias: prompt_text)
    - prompt_text: Full sentence for UI
    - intent_type: Bond intent
    - intent: Human-readable intent label
    - handle: Verbatim handle (alias: handle_quote)
    - handle_quote: Verbatim handle
    - recipe_id: For traceability
    """
    # Extract and select handles
    handles = extract_handles(item_title, item_body)
    diverse_handles = select_diverse_handles(handles, count=4)

    # Fallback if no handles
    if not diverse_handles:
        fallback_text = _normalize_title(item_title) or "this content"
        diverse_handles = [Handle(text=fallback_text, kind="heading", weight=1.0, source="title")]

    # Pad if insufficient
    while len(diverse_handles) < 4:
        diverse_handles.append(diverse_handles[0])

    # Try OpenAI generation first
    openai_result = _try_openai_generation(diverse_handles, item_title, item_body)
    if openai_result:
        # Add context to prompt_text
        for s in openai_result:
            if item_body:
                excerpt = item_body[:300].strip()
                if len(item_body) > 300:
                    excerpt += "..."
                s["prompt_text"] = f'{s["display_text"]}\n\nContext:\n> {excerpt}'
        return openai_result

    # Deterministic fallback with VARIED language
    seed = _hash_content(item_title + (item_body or ""))
    operations = _select_operations(diverse_handles, seed)

    suggestions = []
    for i, (handle, operation) in enumerate(zip(diverse_handles, operations)):
        display_text, intent_type = _compose_varied_sentence(handle, operation, seed, i)

        # Build prompt_text with context
        prompt_text = display_text
        if item_body:
            excerpt = item_body[:300].strip()
            if len(item_body) > 300:
                excerpt += "..."
            prompt_text = f"{display_text}\n\nContext:\n> {excerpt}"

        suggestions.append({
            "display_text": display_text,
            "prompt_text": prompt_text,
            "intent_type": intent_type,
            "intent": intent_type.replace("_", " ").title(),
            "handle": handle.text,
            "handle_quote": handle.text,
            "recipe_id": INTENT_TO_RECIPE.get(intent_type, "clarify_to_testable_claim"),
        })

    return suggestions


def get_handles_for_event(suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract handles and recipe_ids for event logging."""
    return {
        "handles": [s.get("handle", s.get("handle_quote", "")) for s in suggestions],
        "recipe_ids": [s["recipe_id"] for s in suggestions],
    }


def suggestions_to_legacy_format(suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert to legacy format for backward compatibility."""
    return [
        {
            "display_text": s["display_text"],
            "prompt_text": s["prompt_text"],
            "intent_type": s["intent_type"],
            "recipe_id": s["recipe_id"],
            "handle_quote": s.get("handle", s.get("handle_quote", "")),
        }
        for s in suggestions
    ]
