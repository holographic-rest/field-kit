"""
Field-Kit v0.1 Hololoop Engine (Queue Lattice v0.1 - Quality Pipeline)

Generates 4 hololoop options for connecting two Queue Items.

QUALITY REQUIREMENTS:
- Each sentence: 9-22 words, NO quotes, NO meta scaffolding
- BANNED openers: How does, Compare, Trace, Provide, Give me, Define
- BANNED phrases: opens a path, traces back, provides a foundation
- NO NEW FACTS: Banned claims lexicon unless licensed by item content
- QUESTION BIAS: At least 2/4 options should be questions
- Must include handle-derived anchor from A and B (integrated naturally)
- 4 options must be diverse (deduplicated via Jaccard threshold)

Pipeline:
1. Extract handles + cluster by neighborhood (context similarity)
2. Generate 20-40 candidates using varied human-sounding skeletons
3. Hard filter: banned patterns, word count, anchors, bridge test, licensing
4. Rank by clickability (question marks, hinge words, tension words)
5. Deduplicate and diversify (with question quota)
6. Optional: LLM rewrite for naturalness
7. Select top 4
"""

import hashlib
import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from .handles import extract_handles, choose_diverse_handles, strip_all_quotes
from .anchor_pairing import select_anchor_pairs, normalize_handles


# === Quote detection regex (CRITICAL) ===
# Sprint 3: Only block double quotes, allow apostrophes for contractions
DOUBLE_QUOTE_PATTERN = re.compile(r'["\u201c\u201d\u00ab\u00bb]')

# === BANNED OPENERS (case-insensitive, start of sentence) ===
BANNED_OPENERS = [
    r'^how\s+does\b',
    r'^how\s+do\b',
    r'^how\s+is\b',
    r'^compare\b',
    r'^trace\b',
    r'^provide\b',
    r'^give\s+me\b',
    r'^define\b',
    r'^explain\b',
    r'^describe\b',
    r'^list\b',
    r'^identify\b',
    r'^summarize\b',
    r'^outline\b',
    r'^analyze\b',
    r'^evaluate\b',
    r'^discuss\b',
    r'^what\s+is\s+the\s+relationship\b',
]

# === BANNED PHRASES (system-speak, anywhere in text) ===
BANNED_PHRASES = [
    r'opens\s+a\s+path',
    r'traces\s+back',
    r'provides\s+a\s+foundation',
    r'provides\s+foundation',
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
    r'relates\s+to',
    r'connect\s+with',
    r'leads\s+into',
    r'builds\s+upon',
    r'bridges\s+the\s+gap',
    r'serves\s+as',
    r'functions\s+as',
    r'acts\s+as',
    r'points\s+toward',
    r'feeds\s+into',
    r'ties\s+into',
    r'links\s+to',
]

# === NO NEW FACTS: Unlicensed inference tokens ===
# Sprint 3: Extended list of words/phrases that imply invented facts
# These are rejected unless they appear in item A or B text (case-insensitive)
UNLICENSED_INFERENCE_TOKENS = [
    # Template-specific problematic phrases
    "planted",
    "point back",
    "enters the picture",
    "hold together",
    # Temporal/causal inventions
    "always", "never", "before", "after", "appeared",
    "hiding", "alibi", "witness", "dictate", "resist",
    "could never be the same", "could never be the same again",
    "always there before", "was always", "had always", "will always", "must always",
    # Inference words
    "truth", "deny", "foundation",
]

# Legacy alias for backwards compatibility
BANNED_CLAIMS = UNLICENSED_INFERENCE_TOKENS

# === HINGE WORDS (human-sounding connectors) ===
HINGE_WORDS = ['if', 'unless', 'so', 'instead', 'or', 'but', 'yet', 'still',
               'even', 'though', 'because', 'since', 'while', 'when', 'whenever',
               'whereas', 'although', 'despite', 'until', 'once']

# === TENSION WORDS (increase clickability) ===
TENSION_WORDS = ['conflict', 'tension', 'contradiction', 'paradox', 'strange',
                 'unexpected', 'mystery', 'missing', 'lost',
                 'absence', 'void', 'invisible', 'unseen', 'forgotten',
                 'fail', 'collapse', 'break', 'rupture', 'trap']

# === IDENTITY TRIGGERS (for WH-question bias) ===
IDENTITY_TRIGGERS = ['author', 'identity', 'who', 'wrote', 'writer', 'narrator']

# === FIRST-PERSON CLAIM TRIGGERS (for WH-question frames) ===
FIRST_PERSON_TRIGGERS = [
    r"i\s+didn't\s+write",
    r"i\s+do\s+not\s+know",
    r"i\s+don't\s+know",
    r"i\s+am\s+not",
    r"i\s+cannot",
    r"i\s+can't",
]

# === QUESTION SKELETONS (prioritized for question bias) ===
# Sprint 3: Removed problematic templates, added natural reader questions
QUESTION_SKELETONS = {
    "wh_question": [
        "What does {a} make you suspect about {b}?",
        "What does {b} make you doubt about {a}?",
        "Why does {b} matter if {a} is true?",
        "What does {a} want from {b}?",
        "Where does {b} leave {a}?",
    ],
    "yes_no_question": [
        "Does {b} answer the question that {a} raises?",
        "Is {a} the reason {b} feels incomplete?",
        "Can {b} exist independently of {a}?",
        "Does accepting {a} mean accepting {b} as well?",
        "Is there a version of {b} that doesn't require {a}?",
    ],
    "conditional_question": [
        "If {a} is true, what does that mean for {b}?",
        "If {b} is true, what does that do to {a}?",
        "If {a} is a claim, why does {b} matter here?",
        "What happens to {b} if {a} turns out to be wrong?",
        "If {a} is the frame, is {b} the picture or the wall?",
    ],
}

# === STATEMENT SKELETONS (for remaining slots) ===
STATEMENT_SKELETONS = {
    "conditional": [
        "If {a} is what it claims then {b} becomes the real question",
        "Unless {a} can explain itself {b} remains the only clue",
        "Suppose {a} is a distraction and {b} is the actual point",
        "If {a} turns out to be misdirection {b} starts to look different",
    ],
    "contrast": [
        "{a} says one thing but {b} suggests something else entirely",
        "The more you focus on {a} the stranger {b} becomes",
        "{b} seems to contradict everything {a} established",
        "Reading {a} makes {b} feel like a different kind of problem",
    ],
    "implication": [
        "Accepting {a} means accepting something uncomfortable about {b}",
        "The presence of {a} suggests {b} is not accidental",
        "{b} follows from {a} in ways worth examining",
        "Once you see {a} clearly {b} starts to look deliberate",
    ],
    "framing": [
        "Through the lens of {a} everything about {b} looks intentional",
        "{a} as a frame turns {b} into evidence",
        "Seeing {b} through {a} changes what counts as coincidence",
        "{a} makes {b} feel like a choice rather than an accident",
    ],
}

# === RETURN SKELETONS (B→A direction) ===
# Sprint 3: Removed "planted", "point back", "enters the picture"
RETURN_QUESTION_SKELETONS = {
    "wh_question": [
        # Sprint 3b: Replaced "was trying to do" and "circling back"
        "What does {b} suggest about {a}?",
        "Why does {b} matter next to {a}?",
        "What was {a} hiding that {b} reveals?",
        "What does {b} make you reconsider about {a}?",
        "Where does {a} fit once you've seen {b}?",
    ],
    "yes_no_question": [
        "Does {b} answer any of the questions {a} raised?",
        "Is {b} the key to understanding {a} or just more noise?",
        "Can {b} stand on its own or does it need {a}?",
        "Does {b} make {a} more or less believable?",
        "Is {b} the solution or just another symptom of {a}?",
    ],
    "conditional_question": [
        "If {b} is the answer, then what was {a} really asking?",
        "What does {a} look like from the perspective of {b}?",
        "Would {a} still matter if {b} had come first?",
        "If {b} takes over, does {a} become irrelevant?",
        "If {b} is true, what does that say about {a}?",
    ],
}

RETURN_STATEMENT_SKELETONS = {
    "conditional": [
        "But {b} only matters if {a} is taken seriously first",
        "Unless {b} addresses what {a} raised nothing changes",
        "If {b} is the response then {a} was a more serious question",
        "Suppose {b} is what {a} was pointing toward all along",
    ],
    "contrast": [
        "{b} refuses the terms that {a} tried to set",
        "Against {a} the case for {b} becomes strangely compelling",
        "{a} thought it was finished but {b} reopens everything",
        "The silence around {b} speaks to what {a} left out",
    ],
    "implication": [
        "{b} contains implications that reach back to reshape {a}",
        "Accepting {b} means reconsidering what {a} promised",
        "{b} draws conclusions that {a} deliberately avoided",
        "Once you see {b} clearly {a} can never look the same",
    ],
    "framing": [
        "{b} reframes {a} as something more deliberate than it seemed",
        "Through {b} the gaps in {a} start to look like choices",
        "The {b} perspective makes {a} complicit in new ways",
        "Seen from {b} the structure of {a} changes meaning",
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
    forward_word_count: int = 0
    return_word_count: int = 0
    is_question: bool = False  # Whether forward_text is a question
    # Sprint 3: Evidence spans
    evidence_span_a: Optional[str] = None  # Context around handle_a in item A
    evidence_span_b: Optional[str] = None  # Context around handle_b in item B


def _hash_content(text: str) -> int:
    """Generate deterministic hash for content-based selection."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


# =============================================================================
# Sprint 3: Evidence Span Helpers
# =============================================================================

def normalize_for_search(text: str) -> str:
    """
    Normalize text for case-insensitive handle searching.

    - Lowercase
    - Collapse whitespace
    - Does NOT destroy display text (returns a search-friendly version)
    """
    return re.sub(r'\s+', ' ', text.lower().strip())


def find_best_span(text: str, handle: str, window: int = 120) -> Optional[str]:
    """
    Find the best evidence span containing the handle in the source text.

    Extracts ±window characters around the first occurrence of handle.

    Args:
        text: Source text to search in
        handle: Handle to find
        window: Characters to include before/after match (default 120)

    Returns:
        Evidence span string, or None if handle not found
    """
    if not text or not handle:
        return None

    text_normalized = normalize_for_search(text)
    handle_normalized = normalize_for_search(handle)

    # Try exact match first
    pos = text_normalized.find(handle_normalized)

    # If not found, try first few words of handle
    if pos < 0 and ' ' in handle_normalized:
        words = handle_normalized.split()
        for n in range(len(words), 1, -1):
            partial = ' '.join(words[:n])
            pos = text_normalized.find(partial)
            if pos >= 0:
                break

    if pos < 0:
        return None

    # Extract span from ORIGINAL text (preserve case/formatting)
    # Map position back to original text
    start = max(0, pos - window)
    end = min(len(text), pos + len(handle) + window)

    # Adjust to word boundaries if possible
    if start > 0:
        # Find previous space
        space_pos = text.rfind(' ', 0, start)
        if space_pos > start - 20:
            start = space_pos + 1

    if end < len(text):
        # Find next space
        space_pos = text.find(' ', end)
        if space_pos > 0 and space_pos < end + 20:
            end = space_pos

    span = text[start:end].strip()

    # Add ellipsis if truncated
    if start > 0:
        span = "..." + span
    if end < len(text):
        span = span + "..."

    return span


def _contains_quotes(text: str) -> bool:
    """
    Check if text contains double quotation marks.

    Sprint 3: Allow apostrophes for contractions (didn't, doesn't, can't).
    Only block double quotes used to wrap/quote handles.
    """
    return bool(DOUBLE_QUOTE_PATTERN.search(text))


def _has_banned_opener(text: str) -> bool:
    """Check if text starts with a banned opener."""
    text_lower = text.lower().strip()
    for pattern in BANNED_OPENERS:
        if re.match(pattern, text_lower):
            return True
    return False


def _has_banned_phrase(text: str) -> bool:
    """Check if text contains banned system-speak phrases."""
    text_lower = text.lower()
    for pattern in BANNED_PHRASES:
        if re.search(pattern, text_lower):
            return True
    return False


def _check_unlicensed_claims(
    text: str,
    content_a: str,
    content_b: str,
) -> Tuple[bool, List[str]]:
    """
    Sprint 3: NO NEW FACTS filter with token tracking.

    Check if text contains unlicensed inference tokens that are not
    present in item A or B content.

    Args:
        text: Candidate text to check
        content_a: Item A body text
        content_b: Item B body text

    Returns:
        Tuple of (has_unlicensed, blocked_tokens)
        - has_unlicensed: True if any unlicensed token found
        - blocked_tokens: List of tokens that were blocked
    """
    text_lower = text.lower()
    combined_content = (content_a + " " + content_b).lower()
    blocked = []

    for token in UNLICENSED_INFERENCE_TOKENS:
        token_lower = token.lower()
        # Check if token appears in the candidate text
        if token_lower in text_lower:
            # Check if it's licensed by appearing in source content
            if token_lower not in combined_content:
                blocked.append(token)

    return (len(blocked) > 0, blocked)


def _has_unlicensed_claim(text: str, content_a: str, content_b: str) -> bool:
    """
    NO NEW FACTS filter: Check if text contains banned claims
    that are not licensed (present) in item A or B content.

    Returns True if text has an unlicensed claim (should be rejected).
    """
    has_unlicensed, _ = _check_unlicensed_claims(text, content_a, content_b)
    return has_unlicensed


def _is_single_sentence(text: str) -> bool:
    """Check if text is approximately one sentence."""
    # Count sentence-ending punctuation
    endings = len(re.findall(r'[.!?]', text))
    # One sentence should have at most one ending punctuation
    return endings <= 1


def _is_question(text: str) -> bool:
    """Check if text is a question."""
    return '?' in text


def _is_wh_question(text: str) -> bool:
    """Check if text is a WH-question (Who/What/Why/How/Which/Where/When)."""
    text_lower = text.lower().strip()
    return bool(re.match(r'^(who|what|why|how|which|where|when)\b', text_lower))


def _has_identity_trigger(handles: List[Dict[str, Any]], content: str) -> bool:
    """Check if handles or content contain identity triggers."""
    combined = content.lower()
    for h in handles:
        combined += " " + h.get("quote", "").lower()

    for trigger in IDENTITY_TRIGGERS:
        if trigger in combined:
            return True
    return False


def _has_first_person_claim(content: str) -> bool:
    """Check if content has first-person claim triggers."""
    content_lower = content.lower()
    for pattern in FIRST_PERSON_TRIGGERS:
        if re.search(pattern, content_lower):
            return True
    return False


def _contains_anchor(text: str, anchor: str) -> bool:
    """
    Check if anchor appears in text (case-insensitive substring match).
    Also matches partial anchors (first 3+ significant words).
    """
    text_lower = text.lower()
    anchor_lower = anchor.lower()

    # Direct substring match
    if anchor_lower in text_lower:
        return True

    # Try matching first few words of anchor
    anchor_words = anchor_lower.split()
    if len(anchor_words) >= 2:
        # Try 2-word match
        partial = ' '.join(anchor_words[:2])
        if partial in text_lower:
            return True
        # Try 3-word match if available
        if len(anchor_words) >= 3:
            partial = ' '.join(anchor_words[:3])
            if partial in text_lower:
                return True

    return False


def _bridge_test(text: str, anchor_a: str, anchor_b: str) -> bool:
    """
    Bridge test: strip anchors and check if remaining text is generic.
    Returns True if the sentence passes (is NOT generic).
    """
    # Remove anchors from text
    stripped = text.lower()
    stripped = stripped.replace(anchor_a.lower(), ' ')
    stripped = stripped.replace(anchor_b.lower(), ' ')

    # Normalize whitespace
    stripped = ' '.join(stripped.split())

    # If remaining text is too short, it's generic
    remaining_words = [w for w in stripped.split() if len(w) > 2]
    if len(remaining_words) < 4:
        return False

    # Check for generic bridge patterns
    generic_bridges = [
        'leads to', 'connects to', 'relates to', 'opens a path',
        'traces back', 'the logic of', 'follows from', 'and share',
        'share hidden', 'casts new light', 'reveals about',
    ]

    for bridge in generic_bridges:
        if bridge in stripped:
            return False

    return True


def _token_jaccard(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts (word-level)."""
    # Remove common stop words for better similarity detection
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                  'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                  'from', 'as', 'into', 'through', 'during',
                  'above', 'below', 'between', 'under', 'again', 'further',
                  'then', 'once', 'here', 'there', 'when', 'where', 'why',
                  'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
                  'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                  'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or'}

    tokens1 = set(w.lower() for w in text1.split() if w.lower() not in stop_words)
    tokens2 = set(w.lower() for w in text2.split() if w.lower() not in stop_words)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def _clickability_score(text: str) -> float:
    """
    Score text by clickability factors:
    - Question marks (high bonus)
    - Hinge words (if, unless, so, etc.)
    - Tension words (conflict, mystery, etc.)
    """
    score = 0.0
    text_lower = text.lower()

    # Question marks are highly clickable
    if '?' in text:
        score += 0.35  # Increased from 0.25

    # WH-questions get extra bonus
    if _is_wh_question(text):
        score += 0.10

    # Hinge words add intrigue
    hinge_count = sum(1 for word in HINGE_WORDS if f' {word} ' in f' {text_lower} ')
    score += min(hinge_count * 0.08, 0.24)  # Max 0.24 from hinge words

    # Tension words increase engagement
    tension_count = sum(1 for word in TENSION_WORDS if word in text_lower)
    score += min(tension_count * 0.1, 0.3)  # Max 0.3 from tension words

    return min(score, 1.0)


def _cluster_handles_by_neighborhood(
    handles: List[Dict[str, Any]],
    content: str
) -> List[List[Dict[str, Any]]]:
    """
    Cluster handles by semantic neighborhood (context similarity).

    Handles that appear near each other in the content or share
    thematic overlap are grouped together.
    """
    if len(handles) <= 2:
        return [[h] for h in handles]

    content_lower = content.lower()

    # Build proximity map: which handles appear within N chars of each other
    proximity_threshold = 200  # chars
    clusters = []
    assigned = set()

    for i, h1 in enumerate(handles):
        if i in assigned:
            continue

        cluster = [h1]
        assigned.add(i)

        h1_quote = h1["quote"].lower()
        h1_pos = content_lower.find(h1_quote)

        for j, h2 in enumerate(handles[i+1:], i+1):
            if j in assigned:
                continue

            h2_quote = h2["quote"].lower()
            h2_pos = content_lower.find(h2_quote)

            # Check proximity in content
            if h1_pos >= 0 and h2_pos >= 0:
                if abs(h1_pos - h2_pos) <= proximity_threshold:
                    cluster.append(h2)
                    assigned.add(j)
                    continue

            # Check word overlap (thematic similarity)
            h1_words = set(h1_quote.split())
            h2_words = set(h2_quote.split())
            overlap = h1_words & h2_words
            if len(overlap) >= 1 and len(overlap) / min(len(h1_words), len(h2_words)) > 0.3:
                cluster.append(h2)
                assigned.add(j)

        clusters.append(cluster)

    # Add any remaining handles as single-item clusters
    for i, h in enumerate(handles):
        if i not in assigned:
            clusters.append([h])

    return clusters


def _select_neighborhood_pairs(
    clusters_a: List[List[Dict[str, Any]]],
    clusters_b: List[List[Dict[str, Any]]],
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
) -> List[Tuple[str, str]]:
    """
    Select handle pairs that respect neighborhood clustering.

    Ensures "Scheherazade" pairs with "One Thousand and One Nights"
    rather than randomly with unrelated concepts.
    """
    pairs = []

    # Strategy 1: Pair cluster representatives first
    for cluster_a in clusters_a:
        for cluster_b in clusters_b:
            # Use highest-scored handle from each cluster
            best_a = max(cluster_a, key=lambda h: h.get("score", 0))
            best_b = max(cluster_b, key=lambda h: h.get("score", 0))

            pair_key = (best_a["quote"], best_b["quote"])
            if pair_key not in pairs:
                pairs.append(pair_key)

    # Strategy 2: Add cross-cluster pairs for variety
    for h_a in handles_a[:5]:
        for h_b in handles_b[:5]:
            pair_key = (h_a["quote"], h_b["quote"])
            if pair_key not in pairs:
                pairs.append(pair_key)

    # Limit total pairs
    return pairs[:20]


def _generate_heuristic_candidates(
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
    content_a: str = "",
    content_b: str = "",
    need_wh_questions: bool = False,
    preselected_pairs: Optional[List[Tuple[str, str]]] = None,
) -> List[HololinkCandidate]:
    """
    Generate heuristic candidates using varied sentence skeletons.

    Prioritizes question skeletons for question bias requirement.

    Args:
        handles_a: Handles from item A
        handles_b: Handles from item B
        content_a: Body text of item A
        content_b: Body text of item B
        need_wh_questions: Whether to prioritize WH-questions
        preselected_pairs: Optional list of (handle_a, handle_b) pairs from anchor_pairing
    """
    candidates = []

    # Get handle quotes
    ha_list = [h["quote"] for h in handles_a[:7]]
    hb_list = [h["quote"] for h in handles_b[:7]]

    if not ha_list or not hb_list:
        return candidates

    # Use preselected pairs if provided, otherwise fall back to neighborhood clustering
    if preselected_pairs:
        pairs = preselected_pairs
    else:
        # Cluster handles by neighborhood (legacy fallback)
        clusters_a = _cluster_handles_by_neighborhood(handles_a[:7], content_a)
        clusters_b = _cluster_handles_by_neighborhood(handles_b[:7], content_b)
        pairs = _select_neighborhood_pairs(clusters_a, clusters_b, handles_a[:7], handles_b[:7])

    # Generate QUESTION candidates first (for question bias)
    for frame_name, templates in QUESTION_SKELETONS.items():
        return_templates = RETURN_QUESTION_SKELETONS.get(frame_name, templates)

        for pair_idx, (ha, hb) in enumerate(pairs[:6]):
            fwd_template = templates[pair_idx % len(templates)]
            ret_template = return_templates[pair_idx % len(return_templates)]

            forward_text = fwd_template.format(a=ha, b=hb)
            return_text = ret_template.format(a=ha, b=hb)

            candidates.append(HololinkCandidate(
                handle_a=ha,
                handle_b=hb,
                forward_text=forward_text,
                return_text=return_text,
                frame=frame_name,
                score=0.6,  # Slightly higher base for questions
                source="heuristic",
                forward_word_count=_word_count(forward_text),
                return_word_count=_word_count(return_text),
                is_question=True,
            ))

    # Generate STATEMENT candidates
    for frame_name, templates in STATEMENT_SKELETONS.items():
        return_templates = RETURN_STATEMENT_SKELETONS.get(frame_name, templates)

        for pair_idx, (ha, hb) in enumerate(pairs[:5]):
            fwd_template = templates[pair_idx % len(templates)]
            ret_template = return_templates[pair_idx % len(return_templates)]

            forward_text = fwd_template.format(a=ha, b=hb)
            return_text = ret_template.format(a=ha, b=hb)

            candidates.append(HololinkCandidate(
                handle_a=ha,
                handle_b=hb,
                forward_text=forward_text,
                return_text=return_text,
                frame=frame_name,
                score=0.5,
                source="heuristic",
                forward_word_count=_word_count(forward_text),
                return_word_count=_word_count(return_text),
                is_question=False,
            ))

    return candidates


def _try_llm_generation(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    handles_a: List[Dict[str, Any]],
    handles_b: List[Dict[str, Any]],
    need_wh_questions: bool = False,
) -> Tuple[List[HololinkCandidate], str]:
    """
    Try to generate candidates via OpenAI API with strict quality requirements.
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

        wh_instruction = ""
        if need_wh_questions:
            wh_instruction = "\n- At least 3 candidates MUST be WH-questions (Who/What/Why/How)"

        system_prompt = f"""You generate natural hololink sentences connecting two items.

STRICT REQUIREMENTS - MUST FOLLOW:
1. NEVER use quotation marks anywhere
2. Each sentence must be 9-22 words (count carefully!)
3. Include anchors from A and B as natural parts of the sentence (not quoted)
4. Write like a curious reader thinking aloud, not a system prompt
5. At least 5 of your 10 candidates MUST be questions (end with ?)
6. Do NOT invent temporal/causal facts (no "always", "never", "before", "after" unless in source){wh_instruction}

BANNED OPENERS (never start with):
- How does, Compare, Trace, Provide, Give me, Define, Explain, Describe, List

BANNED PHRASES (never use):
- opens a path, traces back, provides a foundation, relates to, connects to
- leads into, bridges the gap, serves as, functions as, ties into
- always there before, could never be the same, was hiding

GOOD EXAMPLES (natural reader questions):
- Who benefits if the author cant be located and the narrator becomes the collector
- What does Scheherazade in reverse mean for a story that traps its teller
- Is the giallo framing why every coincidence feels like a planted clue
- If identity of the author matters then why lead with found text

BAD EXAMPLES (system-speak or inventing facts):
- How does X relate to Y
- X was always there before Y
- Y could never be the same after X appeared

Generate EXACTLY 10 candidates. Each must use different handles and frames.

Output JSON:
{{
  "candidates": [
    {{
      "handle_a": "anchor from A (plain text)",
      "handle_b": "anchor from B (plain text)",
      "forward_text": "9-22 word sentence A→B with both anchors integrated naturally",
      "return_text": "9-22 word sentence B→A with both anchors integrated naturally",
      "frame": "question|conditional|contrast|implication|framing"
    }}
  ]
}}"""

        # Truncate bodies
        body_a = (item_a.get("body") or "")[:600]
        body_b = (item_b.get("body") or "")[:600]

        user_prompt = f"""Item A:
Title: {item_a.get("title", "")}
Body: {body_a}

Anchors from A (integrate naturally, no quotes): {json.dumps(quotes_a)}

Item B:
Title: {item_b.get("title", "")}
Body: {body_b}

Anchors from B (integrate naturally, no quotes): {json.dumps(quotes_b)}

Generate 10 candidates. At least 5 MUST be questions. Each sentence MUST be 9-22 words. Sound like a curious human reader, not a system."""

        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.85,
                max_tokens=2000,
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
                    temperature=0.85,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
            else:
                raise

        content = response.choices[0].message.content
        data = json.loads(content)

        candidates = []
        for c in data.get("candidates", [])[:12]:
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
                forward_word_count=_word_count(forward),
                return_word_count=_word_count(return_),
                is_question=_is_question(forward),
            ))

        return candidates, warning

    except ImportError:
        return [], "openai package not installed"
    except Exception as e:
        print(f"[hololoop_engine] LLM generation failed: {e}")
        return [], str(e)


def _try_llm_rewrite(
    candidates: List[HololinkCandidate],
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
) -> List[HololinkCandidate]:
    """
    Optional: Rewrite top candidates into more natural reader questions.
    Only modifies phrasing, not pairing/ranking logic.

    Returns original candidates if no API key or on failure.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return candidates

    if not candidates:
        return candidates

    try:
        import openai

        # Only rewrite top 4 candidates
        to_rewrite = candidates[:4]

        system_prompt = """You rewrite hololink sentences to sound more natural while preserving meaning.

RULES:
1. Keep both anchors (the key phrases from A and B) - do NOT remove them
2. Keep the sentence as a question if it was a question
3. Make it sound like a curious reader thinking aloud
4. 9-22 words
5. NO quotation marks
6. Do NOT add new facts or temporal claims (no "always", "before", "after")
7. Do NOT use system-speak (no "relates to", "connects to", "provides a foundation")

Return JSON with rewritten versions."""

        sentences_to_rewrite = []
        for c in to_rewrite:
            sentences_to_rewrite.append({
                "forward": c.forward_text,
                "return": c.return_text,
                "handle_a": c.handle_a,
                "handle_b": c.handle_b,
            })

        user_prompt = f"""Rewrite these hololink sentences to sound more natural:

{json.dumps(sentences_to_rewrite, indent=2)}

Return JSON:
{{
  "rewritten": [
    {{"forward": "...", "return": "..."}}
  ]
}}"""

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)
        rewritten = data.get("rewritten", [])

        # Apply rewrites
        for i, rw in enumerate(rewritten[:len(to_rewrite)]):
            if i < len(candidates):
                new_fwd = strip_all_quotes(rw.get("forward", ""))
                new_ret = strip_all_quotes(rw.get("return", ""))

                # Only use rewrite if it still contains both anchors
                if (new_fwd and new_ret and
                    _contains_anchor(new_fwd, candidates[i].handle_a) and
                    _contains_anchor(new_fwd, candidates[i].handle_b) and
                    _contains_anchor(new_ret, candidates[i].handle_a) and
                    _contains_anchor(new_ret, candidates[i].handle_b)):
                    candidates[i].forward_text = new_fwd
                    candidates[i].return_text = new_ret
                    candidates[i].forward_word_count = _word_count(new_fwd)
                    candidates[i].return_word_count = _word_count(new_ret)
                    candidates[i].is_question = _is_question(new_fwd)

        return candidates

    except Exception as e:
        # On any error, return original candidates
        print(f"[hololoop_engine] LLM rewrite failed: {e}")
        return candidates


def _hard_filter(
    candidates: List[HololinkCandidate],
    content_a: str,
    content_b: str,
) -> Tuple[List[HololinkCandidate], Dict[str, Any]]:
    """
    Apply hard filters to remove invalid candidates.

    Sprint 3: Returns filter stats including blocked tokens.

    FILTERS:
    1. No double quotation marks (apostrophes allowed)
    2. No banned openers
    3. No banned phrases
    4. No unlicensed claims (NO NEW FACTS)
    5. Word count 9-22
    6. Must contain both anchors (case-insensitive)
    7. Single sentence
    8. Bridge test (not generic when anchors stripped)

    Returns:
        Tuple of (filtered_candidates, filter_stats)
    """
    filtered = []
    all_blocked_tokens: Set[str] = set()
    rejection_reasons = {
        "quotes": 0,
        "banned_opener": 0,
        "banned_phrase": 0,
        "unlicensed_claim": 0,
        "word_count": 0,
        "missing_anchor": 0,
        "multi_sentence": 0,
        "bridge_test": 0,
    }

    for c in candidates:
        # 1. No quotation marks
        if _contains_quotes(c.forward_text) or _contains_quotes(c.return_text):
            rejection_reasons["quotes"] += 1
            continue

        # 2. No banned openers
        if _has_banned_opener(c.forward_text) or _has_banned_opener(c.return_text):
            rejection_reasons["banned_opener"] += 1
            continue

        # 3. No banned phrases
        if _has_banned_phrase(c.forward_text) or _has_banned_phrase(c.return_text):
            rejection_reasons["banned_phrase"] += 1
            continue

        # 4. No unlicensed claims (NO NEW FACTS) - Sprint 3: track blocked tokens
        has_unlicensed_fwd, blocked_fwd = _check_unlicensed_claims(
            c.forward_text, content_a, content_b
        )
        has_unlicensed_ret, blocked_ret = _check_unlicensed_claims(
            c.return_text, content_a, content_b
        )
        if has_unlicensed_fwd or has_unlicensed_ret:
            all_blocked_tokens.update(blocked_fwd)
            all_blocked_tokens.update(blocked_ret)
            rejection_reasons["unlicensed_claim"] += 1
            continue

        # 5. Word count 9-22
        fwd_wc = _word_count(c.forward_text)
        ret_wc = _word_count(c.return_text)
        if not (9 <= fwd_wc <= 22) or not (9 <= ret_wc <= 22):
            rejection_reasons["word_count"] += 1
            continue

        # 6. Must contain both anchors
        if not _contains_anchor(c.forward_text, c.handle_a):
            rejection_reasons["missing_anchor"] += 1
            continue
        if not _contains_anchor(c.forward_text, c.handle_b):
            rejection_reasons["missing_anchor"] += 1
            continue
        if not _contains_anchor(c.return_text, c.handle_a):
            rejection_reasons["missing_anchor"] += 1
            continue
        if not _contains_anchor(c.return_text, c.handle_b):
            rejection_reasons["missing_anchor"] += 1
            continue

        # 7. Single sentence
        if not _is_single_sentence(c.forward_text):
            rejection_reasons["multi_sentence"] += 1
            continue
        if not _is_single_sentence(c.return_text):
            rejection_reasons["multi_sentence"] += 1
            continue

        # 8. Bridge test
        if not _bridge_test(c.forward_text, c.handle_a, c.handle_b):
            rejection_reasons["bridge_test"] += 1
            continue
        if not _bridge_test(c.return_text, c.handle_a, c.handle_b):
            rejection_reasons["bridge_test"] += 1
            continue

        # Update metadata
        c.forward_word_count = fwd_wc
        c.return_word_count = ret_wc
        c.is_question = _is_question(c.forward_text)

        filtered.append(c)

    filter_stats = {
        "rejection_reasons": rejection_reasons,
        "blocked_tokens": sorted(all_blocked_tokens),
        "total_rejected": len(candidates) - len(filtered),
    }

    return filtered, filter_stats


def _rank_candidates(candidates: List[HololinkCandidate]) -> List[HololinkCandidate]:
    """
    Score and rank candidates by quality and clickability.
    """
    for c in candidates:
        score = c.score

        # LLM source bonus
        if c.source == "llm":
            score += 0.15

        # Clickability scoring (questions get higher scores)
        fwd_click = _clickability_score(c.forward_text)
        ret_click = _clickability_score(c.return_text)
        score += (fwd_click + ret_click) / 2 * 0.35

        # Prefer specific anchors (longer = more specific)
        if len(c.handle_a) >= 15:
            score += 0.05
        if len(c.handle_b) >= 15:
            score += 0.05

        # Ideal word count bonus (12-18 words is sweet spot)
        if 12 <= c.forward_word_count <= 18:
            score += 0.05
        if 12 <= c.return_word_count <= 18:
            score += 0.05

        c.score = min(score, 1.0)

    # Sort by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _diversify_with_question_quota(
    candidates: List[HololinkCandidate],
    k: int = 4,
    min_questions: int = 2,
    need_wh_question: bool = False,
) -> List[HololinkCandidate]:
    """
    Select k diverse candidates with question quota.

    Ensures:
    - At least min_questions options are questions
    - If need_wh_question, at least 1 is a WH-question
    - Options are not near-duplicates
    - Variety in frames and handle pairs
    """
    if len(candidates) <= k:
        return candidates

    selected = []
    used_frames = set()
    used_handle_pairs = set()
    jaccard_threshold = 0.35

    # Separate questions and statements
    questions = [c for c in candidates if c.is_question]
    wh_questions = [c for c in questions if _is_wh_question(c.forward_text)]
    statements = [c for c in candidates if not c.is_question]

    # First: ensure WH-question if needed
    if need_wh_question and wh_questions:
        for c in wh_questions:
            handle_pair = f"{c.handle_a[:20].lower()}|{c.handle_b[:20].lower()}"
            if handle_pair not in used_handle_pairs:
                selected.append(c)
                used_frames.add(c.frame)
                used_handle_pairs.add(handle_pair)
                break

    # Second: fill question quota
    for c in questions:
        if len(selected) >= k:
            break
        if len([s for s in selected if s.is_question]) >= min_questions:
            break
        if c in selected:
            continue

        handle_pair = f"{c.handle_a[:20].lower()}|{c.handle_b[:20].lower()}"
        if handle_pair in used_handle_pairs:
            continue

        # Check Jaccard
        is_duplicate = False
        for s in selected:
            fwd_sim = _token_jaccard(c.forward_text, s.forward_text)
            if fwd_sim > jaccard_threshold:
                is_duplicate = True
                break
        if is_duplicate:
            continue

        selected.append(c)
        used_frames.add(c.frame)
        used_handle_pairs.add(handle_pair)

    # Third: fill remaining with best candidates (prefer frame variety)
    all_remaining = [c for c in candidates if c not in selected]
    all_remaining.sort(key=lambda c: c.score, reverse=True)

    for c in all_remaining:
        if len(selected) >= k:
            break

        handle_pair = f"{c.handle_a[:20].lower()}|{c.handle_b[:20].lower()}"
        if handle_pair in used_handle_pairs:
            continue

        # Check Jaccard
        is_duplicate = False
        for s in selected:
            fwd_sim = _token_jaccard(c.forward_text, s.forward_text)
            ret_sim = _token_jaccard(c.return_text, s.return_text)
            if fwd_sim > jaccard_threshold or ret_sim > jaccard_threshold:
                is_duplicate = True
                break
        if is_duplicate:
            continue

        # Prefer new frames
        if c.frame in used_frames:
            remaining_new = [x for x in all_remaining
                           if x not in selected
                           and x.frame not in used_frames
                           and f"{x.handle_a[:20].lower()}|{x.handle_b[:20].lower()}" not in used_handle_pairs]
            if remaining_new:
                continue

        selected.append(c)
        used_frames.add(c.frame)
        used_handle_pairs.add(handle_pair)

    return selected[:k]


def generate_hololoop_options(
    item_a: Dict[str, Any],
    item_b: Dict[str, Any],
    return_debug: bool = False,
) -> Dict[str, Any]:
    """
    Generate 4 hololoop options for connecting items A and B.

    Quality Pipeline:
    1. Extract handles + cluster by neighborhood
    2. Generate candidates (questions prioritized)
    3. Hard filter (banned patterns, word count, anchors, licensing)
    4. Rank by clickability
    5. Diversify with question quota (min 2/4 questions)
    6. Optional LLM rewrite for naturalness
    7. Select top 4

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
    body_a = item_a.get("body") or ""
    body_b = item_b.get("body") or ""
    title_a = item_a.get("title") or ""
    title_b = item_b.get("title") or ""

    content_a = f"{title_a}\n{body_a}"
    content_b = f"{title_b}\n{body_b}"

    handles_a = extract_handles(body_a, title_a)
    handles_b = extract_handles(body_b, title_b)

    # Select diverse handles
    selected_a = choose_diverse_handles(handles_a, k=7)
    selected_b = choose_diverse_handles(handles_b, k=7)

    # Ensure we have at least 2 handles from each item
    if len(selected_a) < 2:
        title = strip_all_quotes(title_a[:40]) if title_a else "this content"
        selected_a.append({"quote": title, "kind": "heading", "score": 0.5})
    if len(selected_b) < 2:
        title = strip_all_quotes(title_b[:40]) if title_b else "this content"
        selected_b.append({"quote": title, "kind": "heading", "score": 0.5})

    # Check for identity triggers (need WH-questions)
    need_wh = (_has_identity_trigger(selected_a, content_a) or
               _has_identity_trigger(selected_b, content_b) or
               _has_first_person_claim(content_a) or
               _has_first_person_claim(content_b))

    # Step 1.5: Select anchor pairs using embedding similarity + MMR
    anchor_pairs, anchor_debug = select_anchor_pairs(
        selected_a,
        selected_b,
        num_pairs=6,  # Generate more pairs for candidate variety
        top_k=12,
        lambda_=0.7,
    )

    # Step 2: Generate candidates
    candidates = []

    # Try LLM first
    llm_candidates, warning = _try_llm_generation(
        item_a, item_b, selected_a, selected_b, need_wh_questions=need_wh
    )
    candidates.extend(llm_candidates)

    # Always add heuristic candidates (with anchor pairs from embedding similarity)
    heuristic_candidates = _generate_heuristic_candidates(
        selected_a, selected_b, body_a, body_b,
        need_wh_questions=need_wh,
        preselected_pairs=anchor_pairs if anchor_pairs else None,
    )
    candidates.extend(heuristic_candidates)

    # Step 3: Hard filter (includes licensing check)
    # Sprint 3: Now returns (filtered, filter_stats) with blocked tokens
    filtered, filter_stats = _hard_filter(candidates, content_a, content_b)

    # Sprint 3: Add evidence spans to filtered candidates
    for c in filtered:
        c.evidence_span_a = find_best_span(content_a, c.handle_a)
        c.evidence_span_b = find_best_span(content_b, c.handle_b)

    # Step 4: Rank
    ranked = _rank_candidates(filtered)

    # Step 5: Diversify with question quota
    final = _diversify_with_question_quota(
        ranked, k=4, min_questions=2, need_wh_question=need_wh
    )

    # Step 6: Optional LLM rewrite for naturalness
    if os.environ.get("OPENAI_API_KEY"):
        final = _try_llm_rewrite(final, item_a, item_b)

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
            "relation_type": c.frame,  # For bond creation
            # Sprint 3: Evidence spans
            "evidence_span_a": c.evidence_span_a,
            "evidence_span_b": c.evidence_span_b,
        })

    # Pad with high-quality question fallbacks if needed
    while len(options) < 4:
        idx = len(options)
        ha = selected_a[idx % len(selected_a)]["quote"]
        hb = selected_b[idx % len(selected_b)]["quote"]

        # Question-based fallbacks
        fallback_templates = [
            (f"What does {ha} want from {hb}?",
             f"What does {hb} reveal about {ha}?"),
            (f"Is {ha} the reason {hb} feels incomplete?",
             f"Does {hb} answer any questions that {ha} raised?"),
            (f"If {ha} is true, what does that make {hb}?",
             f"If {hb} is the answer, what was {ha} really asking?"),
            (f"Can {hb} exist independently of {ha}?",
             f"Can {ha} stand on its own without {hb}?"),
        ]
        fwd, ret = fallback_templates[idx % len(fallback_templates)]

        options.append({
            "option_index": len(options) + 1,
            "link_text_forward": fwd,
            "link_text_return": ret,
            "handle_a_used": ha,
            "handle_b_used": hb,
            "frame": "fallback",
            "relation_type": "fallback",
            # Sprint 3: Evidence spans for fallback
            "evidence_span_a": find_best_span(content_a, ha),
            "evidence_span_b": find_best_span(content_b, hb),
        })

    result = {
        "options": options[:4],
        "source": source,
        "warning": warning or None,
        "item_a_id": item_a.get("id"),
        "item_b_id": item_b.get("id"),
    }

    if return_debug:
        # Sprint 3: Build evidence span info for selected options
        evidence_info = []
        for opt in options[:4]:
            evidence_info.append({
                "handle_a": opt["handle_a_used"],
                "handle_b": opt["handle_b_used"],
                "evidence_span_a_present": opt.get("evidence_span_a") is not None,
                "evidence_span_b_present": opt.get("evidence_span_b") is not None,
            })

        result["debug"] = {
            "handles_a": [h["quote"] for h in selected_a],
            "handles_b": [h["quote"] for h in selected_b],
            "candidates_generated": len(candidates),
            "candidates_filtered": len(filtered),
            "candidates_ranked": len(ranked),
            "candidates_final": len(final),
            "need_wh_questions": need_wh,
            "question_count": sum(1 for c in final if c.is_question),
            "extraction_tags_a": [h.get("extraction_tag", "") for h in selected_a],
            "extraction_tags_b": [h.get("extraction_tag", "") for h in selected_b],
            # Sprint 2: Anchor pairing debug info
            "anchor_pairs": anchor_debug.get("selected_pairs", []),
            "anchor_sim_top_pairs": [
                (a, b, round(sim, 4))
                for a, b, sim in anchor_debug.get("top_k_pairs", [])[:5]
            ],
            "anchor_b_coverage": anchor_debug.get("used_b_handles", []),
            "anchor_normalization": anchor_debug.get("normalization_applied", {}),
            # Sprint 3: Evidence and licensing debug info
            "evidence_spans": evidence_info,
            "filter_stats": filter_stats,
            "blocked_tokens": filter_stats.get("blocked_tokens", []),
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
    relation = option.get("relation_type", "hololoop")
    return {
        "input_item_ids": [item_a_id, item_b_id],
        "prompt_text": f"Hololoop ({relation}): {item_a_id} ↔ {item_b_id}",
        "bond_kind": "hololoop",
        "link_text_forward": option["link_text_forward"],
        "link_text_return": option["link_text_return"],
        "intent_type": relation,
    }
