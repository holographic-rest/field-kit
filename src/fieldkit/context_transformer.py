"""
Field-Kit v0.1 Context Transformer

3-stage pipeline for generating content-grounded Bond suggestions:
1. ENCODER: Extract span-level anchors from Item content
2. DECODER: Generate one-sentence Bonds with verbatim quotes
3. VALIDATOR: Reject generic patterns, retry once, fallback to deterministic

Anchors are span-level meaning units with metadata:
- anchor_text: short handle (3-8 words)
- quote: verbatim excerpt from source (8-20 words)
- source_kind: heading | bullet_label | bold | sentence | fallback
- line_span: optional (start_line, end_line) for debug

Bond operations (one each):
- CLARIFY: define meaning/scope
- MAP: show architecture position
- TRACE: walk through flow
- TEST: validate correctness
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import re


# === Anchor Dataclass ===

@dataclass
class Anchor:
    """A span-level meaning unit extracted from Item content."""
    anchor_text: str  # Short handle (3-8 words)
    quote: str  # Verbatim excerpt (8-20 words)
    source_kind: str  # heading | bullet_label | bold | sentence | fallback
    line_span: Optional[Tuple[int, int]] = None  # (start_line, end_line)
    score: float = 0.0  # Ranking score for selection


# === Source Kind Weights ===
# Higher = more important
SOURCE_KIND_WEIGHTS = {
    "heading": 1.0,
    "bullet_label": 0.9,
    "bold": 0.85,
    "sentence": 0.6,
    "fallback": 0.3,
}

# Domain nouns that boost relevance
DOMAIN_NOUNS = {
    "field", "item", "bond", "episode", "network", "event", "ledger",
    "holologue", "monologue", "dialogue", "qdpi", "canon", "vault",
    "entrance", "proposal", "suggestion", "anchor", "prompt", "artifact",
    "system", "layer", "architecture", "flow", "state", "user",
}


# === Stage 1: ENCODER ===

def extract_anchors(title: str, body: Optional[str] = None) -> List[Anchor]:
    """
    ENCODER: Extract 8-20 candidate anchors from Item content.

    Extracts span-level meaning units from:
    1. Headings (markdown # or standalone title-like lines)
    2. Bullet labels (esp **Label:** or Label:)
    3. Bold phrases (**text**)
    4. Short colon-phrases
    5. Short noun phrases
    6. (fallback) First 1-2 sentences

    Each anchor includes:
    - anchor_text: short handle for display
    - quote: verbatim 8-20 word excerpt
    - source_kind: classification
    - line_span: optional debug info
    - score: for ranking (populated by rank_anchors)

    Returns 8-20 anchors, deterministically ordered.
    """
    anchors = []
    seen_texts = set()

    def add_anchor(
        anchor_text: str,
        quote: str,
        source_kind: str,
        line_num: Optional[int] = None
    ) -> bool:
        """Add anchor if valid and not duplicate. Returns True if added."""
        anchor_text = anchor_text.strip()
        quote = quote.strip()

        # Validate anchor_text (3-8 words, 5-60 chars)
        words = anchor_text.split()
        if len(words) < 2 or len(words) > 10:
            return False
        if len(anchor_text) < 5 or len(anchor_text) > 70:
            return False

        # Validate quote (8-20 words, or close)
        quote_words = quote.split()
        if len(quote_words) < 4:  # Allow slightly shorter for headings
            quote = anchor_text  # Use anchor as quote if too short
        elif len(quote_words) > 25:
            quote = " ".join(quote_words[:20])

        # Skip duplicates (case-insensitive on anchor_text)
        anchor_lower = anchor_text.lower()
        if anchor_lower in seen_texts:
            return False

        # Skip junk patterns
        if _is_junk_pattern(anchor_text):
            return False

        seen_texts.add(anchor_lower)
        line_span = (line_num, line_num) if line_num else None
        anchors.append(Anchor(
            anchor_text=anchor_text,
            quote=quote,
            source_kind=source_kind,
            line_span=line_span,
        ))
        return True

    # Parse body into lines
    lines = []
    if body:
        lines = [(i + 1, line.strip()) for i, line in enumerate(body.split('\n')) if line.strip()]

    # Priority 1: Title: line in body
    for line_num, line in lines:
        if line.lower().startswith('title:'):
            title_text = line[6:].strip()
            # Strip "FIELD – " or similar prefixes
            title_text = re.sub(r'^[A-Z]+\s*[-–:]\s*', '', title_text)
            if title_text and not _is_junk_pattern(title_text):
                add_anchor(title_text, _get_context_quote(lines, line_num), "heading", line_num)

    # Priority 2: Provided title (normalized)
    if title:
        normalized = _normalize_title(title)
        if normalized and not _is_junk_pattern(normalized):
            # Find quote from first meaningful body line
            quote = normalized
            if lines:
                for _, line in lines[:5]:
                    if not line.lower().startswith('title:') and len(line) > 20:
                        quote = _extract_quote(line)
                        break
            add_anchor(normalized, quote, "heading")

    # Priority 3: Markdown headings
    for line_num, line in lines:
        if line.startswith('#'):
            heading = line.lstrip('#').strip()
            if heading and not _is_junk_pattern(heading):
                quote = _get_context_quote(lines, line_num)
                add_anchor(heading, quote, "heading", line_num)

    # Priority 4: Bold phrases (**text**)
    for line_num, line in lines:
        bold_matches = re.findall(r'\*\*([^*]+)\*\*', line)
        for bold in bold_matches:
            bold = bold.strip()
            if bold.endswith(':'):
                bold = bold[:-1]  # Remove trailing colon for anchor
            if bold and len(bold) > 4:
                add_anchor(bold, _extract_quote(line), "bold", line_num)

    # Priority 5: Bullet labels (- **Label:** or - Label:)
    for line_num, line in lines:
        # Match "- **Label:** ..." or "- Label: ..."
        bullet_match = re.match(r'^[-*•]\s+(?:\*\*)?([^:*]+)(?:\*\*)?\s*:\s*(.+)?$', line)
        if bullet_match:
            label = bullet_match.group(1).strip()
            rest = bullet_match.group(2) or ""
            if label and len(label) > 3:
                quote = f"{label}: {rest}".strip() if rest else label
                add_anchor(label, _extract_quote(line), "bullet_label", line_num)

    # Priority 6: Colon-phrases (What X is:, How X works:)
    for line_num, line in lines:
        colon_match = re.match(r'^((?:What|How|Why|When|Where)\s+[^:]+):\s*(.+)?$', line, re.IGNORECASE)
        if colon_match:
            phrase = colon_match.group(1).strip()
            rest = colon_match.group(2) or ""
            quote = f"{phrase}: {rest}" if rest else phrase
            add_anchor(phrase, _extract_quote(line), "sentence", line_num)

    # Priority 7: Noun phrases from sentences (capitalize noun phrases)
    if len(anchors) < 12:
        for line_num, line in lines[:15]:  # First 15 lines
            # Skip already-processed patterns
            if any([
                line.startswith('#'),
                line.lower().startswith('title:'),
                re.match(r'^[-*•]', line),
                '**' in line,
            ]):
                continue

            # Extract capitalized noun phrases
            cap_phrases = re.findall(r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})', line)
            for phrase in cap_phrases:
                if len(phrase) > 5 and phrase.lower() not in ['this', 'what', 'how', 'the']:
                    add_anchor(phrase, _extract_quote(line), "sentence", line_num)

    # Priority 8: Fallback - first 1-2 meaningful sentences
    if len(anchors) < 8:
        for line_num, line in lines[:5]:
            if line.lower().startswith('title:'):
                continue
            if len(line) > 30:
                # Extract first noun phrase or short sentence
                first_clause = line.split(',')[0].split(';')[0]
                if len(first_clause) > 10:
                    words = first_clause.split()[:6]
                    anchor_text = " ".join(words)
                    if not _is_junk_pattern(anchor_text):
                        add_anchor(anchor_text, _extract_quote(line), "fallback", line_num)

    return anchors[:20]  # Cap at 20


def _normalize_title(title: str) -> str:
    """Normalize title by stripping PAGE/numeric prefixes."""
    if not title:
        return ""
    result = title.strip()
    # Strip "PAGE X – " or "PAGE X: " patterns
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)
    # Strip leading numeric prefixes
    result = re.sub(r'^\d+\s*[-–_]\s*', '', result)
    return result.strip()


def _is_junk_pattern(text: str) -> bool:
    """Check if text matches a junk pattern to filter out."""
    text_lower = text.lower()
    junk_starters = [
        "this document describes",
        "this is a document",
        "this is meant to be",
        "the following",
        "page 1", "page 2", "page 3",
        "give me a test case that validates",
        "explain this",
        "walk me through",
        "tell me about",
        "help me understand",
    ]
    for junk in junk_starters:
        if text_lower.startswith(junk):
            return True
    # Skip pure numbers or PAGE patterns
    if re.match(r'^(page\s*)?\d+\.?$', text, re.IGNORECASE):
        return True
    return False


def _extract_quote(line: str, max_words: int = 18) -> str:
    """Extract a verbatim quote from a line (8-20 words)."""
    # Remove markdown formatting for cleaner quote
    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
    clean = re.sub(r'^[-*•#]+\s*', '', clean)
    clean = clean.strip()

    words = clean.split()
    if len(words) <= max_words:
        return clean
    return " ".join(words[:max_words])


def _get_context_quote(lines: List[Tuple[int, str]], target_line: int) -> str:
    """Get quote from lines near the target line."""
    # Find the line and next few lines for context
    quote_parts = []
    found = False
    for line_num, line in lines:
        if line_num == target_line:
            found = True
        if found:
            quote_parts.append(line)
            if len(" ".join(quote_parts).split()) >= 12:
                break
    return _extract_quote(" ".join(quote_parts))


# === Anchor Ranking ===

def rank_anchors(anchors: List[Anchor], title: str, body: Optional[str]) -> List[Anchor]:
    """
    Rank anchors by relevance using heuristic scoring.

    Scoring factors:
    1. source_kind weight (heading > bullet_label > bold > sentence > fallback)
    2. Length sweet spot (prefer 6-12 word quotes)
    3. Domain noun presence (boost if contains Field-Kit terminology)
    4. Quote quality (verbatim, non-generic)

    Returns anchors sorted by score descending.
    """
    all_text = ((title or "") + " " + (body or "")).lower()

    for anchor in anchors:
        score = 0.0

        # 1. Source kind weight
        score += SOURCE_KIND_WEIGHTS.get(anchor.source_kind, 0.3)

        # 2. Length sweet spot (6-12 words is ideal)
        word_count = len(anchor.quote.split())
        if 8 <= word_count <= 15:
            score += 0.3
        elif 5 <= word_count <= 20:
            score += 0.15

        # 3. Domain noun presence
        anchor_lower = anchor.anchor_text.lower()
        domain_matches = sum(1 for noun in DOMAIN_NOUNS if noun in anchor_lower)
        score += min(domain_matches * 0.15, 0.45)  # Cap at 0.45

        # 4. Quote quality - boost if quote has structure
        if ':' in anchor.quote:
            score += 0.1
        if any(c in anchor.quote for c in ['–', '—', '+']):
            score += 0.05

        # 5. Penalty for generic starters
        if anchor.anchor_text.lower().startswith(('the ', 'a ', 'an ')):
            score -= 0.1

        anchor.score = score

    # Sort by score descending
    return sorted(anchors, key=lambda a: a.score, reverse=True)


# === Stage 2: DECODER ===

# Operations for Bond generation (one each)
OPERATIONS = [
    {
        "op": "CLARIFY",
        "intent": "clarifies",
        "template": 'Define what "{anchor}" means in {domain} and list 3 concrete examples.',
    },
    {
        "op": "MAP",
        "intent": "derives",
        "template": 'Show where "{anchor}" fits in the architecture with 4 connecting components.',
    },
    {
        "op": "TRACE",
        "intent": "grounds_in",
        "template": 'Trace how "{anchor}" flows through the system in 6 numbered steps.',
    },
    {
        "op": "TEST",
        "intent": "critiques",
        "template": 'Give 3 test cases that validate "{anchor}" works correctly.',
    },
]


@dataclass
class BondSuggestion:
    """A generated Bond suggestion with content grounding."""
    display_text: str  # One sentence for UI (<=180 chars preferred, max 240)
    prompt_text: str  # Full prompt with context for execution
    intent_type: str  # clarifies | derives | grounds_in | critiques
    operation: str  # CLARIFY | MAP | TRACE | TEST
    anchor_text: str  # The anchor this bond is grounded in
    quote: str  # Verbatim quote from Item
    source_kind: str  # Source classification of anchor


def generate_bonds(
    anchors: List[Anchor],
    item_title: str,
    item_body: Optional[str] = None,
) -> List[BondSuggestion]:
    """
    DECODER: Generate 4 one-sentence Bonds from top 4 ranked anchors.

    Each Bond:
    - Is one sentence, <=180 chars preferred (max 240)
    - Includes verbatim quote from Item
    - Requests concrete artifact with numeric constraint
    - Uses one of: CLARIFY, MAP, TRACE, TEST

    Returns exactly 4 BondSuggestions.
    """
    if not anchors:
        # Fallback if no anchors
        anchors = [Anchor(
            anchor_text=item_title or "this content",
            quote=item_title or "this content",
            source_kind="fallback",
        )]

    # Rank and select top 4 anchors
    ranked = rank_anchors(anchors, item_title, item_body)
    top_4 = ranked[:4]

    # Pad if we have fewer than 4 anchors
    while len(top_4) < 4:
        top_4.append(top_4[0] if top_4 else Anchor(
            anchor_text="this content",
            quote="this content",
            source_kind="fallback",
        ))

    # Extract domain context for templates
    domain = _extract_domain(item_title, item_body)

    bonds = []
    for i, (anchor, op_info) in enumerate(zip(top_4, OPERATIONS)):
        # Generate display_text from template
        display_text = op_info["template"].format(
            anchor=anchor.anchor_text,
            domain=domain,
        )

        # Ensure display_text is <=240 chars
        if len(display_text) > 240:
            display_text = display_text[:237] + "..."

        # Generate full prompt_text with context
        prompt_text = f"""{display_text}

Context from "{item_title}":
> {anchor.quote}"""

        bonds.append(BondSuggestion(
            display_text=display_text,
            prompt_text=prompt_text,
            intent_type=op_info["intent"],
            operation=op_info["op"],
            anchor_text=anchor.anchor_text,
            quote=anchor.quote,
            source_kind=anchor.source_kind,
        ))

    return bonds


def _extract_domain(title: str, body: Optional[str]) -> str:
    """Extract domain context phrase from title/body."""
    # Look for domain-specific terms
    text = ((title or "") + " " + (body or "")[:200]).lower()

    if "field" in text:
        return "the Field"
    if "holologue" in text:
        return "Holologue"
    if "bond" in text:
        return "Bond operations"
    if "item" in text:
        return "Item management"
    if "episode" in text:
        return "Episode context"
    if "architect" in text:
        return "the architecture"
    if "system" in text:
        return "the system"

    return "this context"


# === Stage 3: VALIDATOR ===

# Banned patterns that indicate generic, non-grounded bonds
BANNED_PATTERNS = [
    r"^give me a test case that validates",
    r"^explain this",
    r"^walk me through",
    r"^tell me about",
    r"^help me understand",
    r"^describe the",
    r"^what is",
    r"^can you explain",
    r"^please provide",
]


def validate_bond(bond: BondSuggestion, item_body: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    VALIDATOR: Check if a Bond meets content-grounding requirements.

    Requirements:
    1. Must contain verbatim substring >=6 chars from Item
    2. Must include domain noun from Item
    3. Must include numeric constraint (3, 4, 6, etc.)
    4. Must NOT start with banned patterns

    Returns (is_valid, reason) tuple.
    """
    display = bond.display_text.lower()

    # Check 1: Banned patterns
    for pattern in BANNED_PATTERNS:
        if re.match(pattern, display, re.IGNORECASE):
            return False, f"Starts with banned pattern: {pattern}"

    # Check 2: Verbatim substring >=6 chars
    if item_body:
        body_lower = item_body.lower()
        # Check if anchor_text or a 6+ char substring appears in body
        anchor_lower = bond.anchor_text.lower()
        if len(anchor_lower) >= 6:
            if anchor_lower not in body_lower:
                # Try first 10 chars
                if anchor_lower[:10] not in body_lower:
                    return False, "Anchor not verbatim from Item"

    # Check 3: Numeric constraint
    has_numeric = bool(re.search(r'\b\d+\b', bond.display_text))
    if not has_numeric:
        return False, "Missing numeric constraint"

    # Check 4: Domain noun presence (lenient - just needs one)
    has_domain_noun = any(
        noun in display
        for noun in ["anchor", "define", "show", "trace", "test", "list", "give",
                     "component", "step", "example", "case", "architecture"]
    )
    if not has_domain_noun:
        return False, "Missing action/domain noun"

    # Check 5: Length bounds
    if len(bond.display_text) > 240:
        return False, "Exceeds 240 char limit"

    return True, None


def validate_bonds(
    bonds: List[BondSuggestion],
    item_body: Optional[str],
) -> List[BondSuggestion]:
    """
    Validate all bonds and retry invalid ones.

    For each invalid bond:
    1. Try regenerating with fallback template
    2. If still invalid, use deterministic fallback

    Returns 4 valid BondSuggestions.
    """
    valid_bonds = []

    for bond in bonds:
        is_valid, reason = validate_bond(bond, item_body)

        if is_valid:
            valid_bonds.append(bond)
        else:
            # Retry with deterministic fallback
            fallback = _create_fallback_bond(bond)
            valid_bonds.append(fallback)

    return valid_bonds


def _create_fallback_bond(original: BondSuggestion) -> BondSuggestion:
    """Create a deterministic fallback bond from an invalid one."""
    # Use simpler, guaranteed-valid template
    fallback_templates = {
        "CLARIFY": 'Define "{anchor}" with 3 concrete examples from this context.',
        "MAP": 'Show how "{anchor}" connects to 4 other components.',
        "TRACE": 'List 6 steps showing how "{anchor}" flows through the system.',
        "TEST": 'Provide 3 test cases that verify "{anchor}" works correctly.',
    }

    template = fallback_templates.get(
        original.operation,
        'Explain "{anchor}" with 3 specific examples.'
    )

    display_text = template.format(anchor=original.anchor_text)

    return BondSuggestion(
        display_text=display_text,
        prompt_text=f"{display_text}\n\nContext:\n> {original.quote}",
        intent_type=original.intent_type,
        operation=original.operation,
        anchor_text=original.anchor_text,
        quote=original.quote,
        source_kind=original.source_kind,
    )


# === Main Pipeline ===

def transform_context(
    item_title: str,
    item_body: Optional[str] = None,
) -> List[BondSuggestion]:
    """
    Run the full Context Transformer pipeline.

    1. ENCODER: Extract anchors from Item
    2. DECODER: Generate 4 bonds from top anchors
    3. VALIDATOR: Ensure all bonds are content-grounded

    Returns exactly 4 valid BondSuggestions.
    """
    # Stage 1: ENCODER
    anchors = extract_anchors(item_title, item_body)

    # Stage 2: DECODER
    bonds = generate_bonds(anchors, item_title, item_body)

    # Stage 3: VALIDATOR
    valid_bonds = validate_bonds(bonds, item_body)

    return valid_bonds


def suggestions_to_legacy_format(bonds: List[BondSuggestion]) -> List[Dict[str, Any]]:
    """
    Convert BondSuggestions to legacy format for compatibility.

    Returns list of dicts with:
    - display_text: for UI chips
    - prompt_text: for Bond execution
    - intent_type: classification
    - recipe_id: derived from operation
    """
    # Map operations to legacy recipe_ids
    op_to_recipe = {
        "CLARIFY": "clarify_to_testable_claim",
        "MAP": "architecture_map",
        "TRACE": "interaction_trace",
        "TEST": "spec_fragment_rules",
    }

    return [
        {
            "display_text": bond.display_text,
            "prompt_text": bond.prompt_text,
            "intent_type": bond.intent_type,
            "recipe_id": op_to_recipe.get(bond.operation, "clarify_to_testable_claim"),
        }
        for bond in bonds
    ]


# === For Holologue Proposals ===

def transform_holologue_context(
    holologue_title: str,
    holologue_body: Optional[str] = None,
    selected_item_titles: Optional[List[str]] = None,
) -> List[BondSuggestion]:
    """
    Generate 4 content-grounded proposals after Holologue completion.

    Uses the Holologue output as source for anchor extraction,
    with optional boost for terms from selected input items.

    Returns exactly 4 valid BondSuggestions.
    """
    # Extract anchors from Holologue output
    anchors = extract_anchors(holologue_title, holologue_body)

    # If we have selected items, boost anchors that reference them
    if selected_item_titles:
        selected_text = " ".join(selected_item_titles).lower()
        for anchor in anchors:
            if any(word in selected_text for word in anchor.anchor_text.lower().split()):
                anchor.score += 0.2

    # Generate and validate bonds
    bonds = generate_bonds(anchors, holologue_title, holologue_body)
    valid_bonds = validate_bonds(bonds, holologue_body)

    return valid_bonds
