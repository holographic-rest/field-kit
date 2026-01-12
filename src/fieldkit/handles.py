"""
Field-Kit v0.1 Handle Extraction (Queue Lattice PASS 2)

Extracts short, diverse handles from Item content for hololoop generation.

A handle is a verbatim substring (plain text, NO quotes) that anchors a hololink.

PASS 2 Requirements:
- Handles must be SHORT (≤40 chars preferred, max 60)
- Handles appear as PLAIN TEXT in hololinks (never quoted)
- Strip PAGE X boilerplate
- Deduplicate
- Return 3-7 handles per item

Priority order:
1. Title line (normalized)
2. Named entities / key noun phrases (The Author, Scheherazade, Giallo)
3. Bullet headers / emphasized phrases
4. First sentence fragments as fallback

Returns up to 15 handles with choose_diverse_handles() for variety.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import uuid
import hashlib


@dataclass
class Handle:
    """A handle extracted from Item content."""
    handle_id: str     # Unique ID for this handle
    quote: str         # Exact verbatim substring from item (NO quotes added)
    kind: str          # bullet | colon | entity | phrase | sentence | heading
    score: float       # Ranking score (0-1)
    source: str        # body | title
    line_num: int      # Line number in source (0 for title)
    extraction_tag: str = ""  # Debug: how this handle was extracted


# === Domain entities to recognize ===
DOMAIN_ENTITIES = {
    "field", "item", "bond", "episode", "network", "event", "ledger",
    "holologue", "monologue", "dialogue", "qdpi", "canon", "vault",
    "entrance way", "the entrance way", "gibsey", "rag", "microservices",
    "gpus", "linear algebra", "agents", "operator", "prompt",
    "infrastructure", "architecture", "stack", "layer",
}

# === Full noun phrase patterns to preserve (high priority) ===
# These should NOT be truncated - extract complete phrases
FULL_PHRASE_PATTERNS = [
    r"One Thousand and One Nights",
    r"Scheherazade in reverse",
    r"identity of [Tt]he [A-Z][a-z]+",
    r"The [A-Z][a-z]+ [A-Z][a-z]+",  # The Big Sleep, The Author Mystery
    r"[A-Z][a-z]+ [A-Z][a-z]+ in [a-z]+",  # X Y in reverse/context
    r"found text",
    r"giallo",
    r"Magical Dominion",
    r"collector and curator",
]

# === First-person claim patterns (trigger WH-question frames) ===
FIRST_PERSON_PATTERNS = [
    r"I didn't write this",
    r"I do not know the identity",
    r"I don't know",
    r"I am not",
    r"I cannot",
]


def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _score_by_word_count(quote: str, base_score: float) -> float:
    """
    Boost score for multi-word spans (>= 3 words).
    Multi-word spans are more content-specific and make better handles.
    """
    wc = _word_count(quote)
    if wc >= 6:
        return min(base_score + 0.20, 1.0)  # Strong boost for 6+ words
    elif wc >= 4:
        return min(base_score + 0.15, 1.0)  # Good boost for 4-5 words
    elif wc >= 3:
        return min(base_score + 0.10, 1.0)  # Moderate boost for 3 words
    elif wc == 2:
        return base_score  # No change for 2 words
    else:
        return max(base_score - 0.15, 0.1)  # Penalty for single words


def strip_all_quotes(s: str) -> str:
    """
    Remove ALL quotation marks from string.

    PASS 2 CRITICAL: Handles must NEVER contain quotation marks.
    They appear as plain text in hololinks.
    """
    if not s:
        return ""
    # Remove all quote characters: ", ', ", ", ', ', «, »
    return re.sub(r'["\'\u201c\u201d\u2018\u2019\u00ab\u00bb]', '', s)


def normalize_for_anchor(s: str) -> str:
    """
    Normalize a string for use as anchor phrase.
    Strips "PAGE X – ..." prefixes, "Title: " prefixes, quotes, and leading/trailing punctuation.
    """
    if not s:
        return ""
    result = s.strip()
    # Strip "PAGE X – " or "PAGE X: " patterns
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)
    # Strip "Title: " prefix
    result = re.sub(r'^Title:\s*', '', result, flags=re.IGNORECASE)
    # CRITICAL: Strip all quotation marks
    result = strip_all_quotes(result)
    # Strip leading/trailing punctuation (but keep internal)
    result = re.sub(r'^[^\w]+', '', result)
    result = re.sub(r'[^\w]+$', '', result)
    # Strip leading numeric prefixes like "1 – " or "2. "
    result = re.sub(r'^\d+\s*[-–_.]\s*', '', result)
    return result.strip()


def extract_handles(text: str, title: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract up to 15 candidate handles from Item content.

    PASS 2 Requirements:
    - Handles must be SHORT (≤40 chars preferred, max 60)
    - Handles contain NO quotation marks (stripped)
    - Return 3-7 diverse handles per item

    Args:
        text: The item body text
        title: Optional item title

    Returns:
        List of handle dicts with: handle_id, quote, kind, score, source, line_num, extraction_tag

    Priority:
    1. Title line (normalized, short)
    2. Named entities / capitalized noun phrases (The Author, Scheherazade)
    3. Bullet labels and colon clauses
    4. Bold/emphasized phrases
    5. First sentence fragments (fallback)
    """
    handles = []
    seen_quotes = set()

    def add_handle(quote: str, kind: str, score: float, source: str, line_num: int = 0, tag: str = "") -> bool:
        """Add handle if valid and not duplicate. CRITICAL: Strips all quotes."""
        quote = quote.strip()
        if not quote or len(quote) < 4:
            return False

        # CRITICAL: Strip ALL quotation marks
        quote = strip_all_quotes(quote)

        # Skip PAGE patterns
        if re.match(r'^page\s+\d+', quote.lower()):
            return False

        # Skip Title: prefix lines
        if quote.lower().startswith('title:'):
            return False

        # Normalize for dedup (lowercase, collapse whitespace)
        quote_normalized = re.sub(r'\s+', ' ', quote.lower())
        if quote_normalized in seen_quotes:
            return False

        # Skip very short single-word handles unless they're entities
        if _word_count(quote) == 1 and kind not in ('entity',) and len(quote) < 6:
            return False

        # PASS 2: Prefer SHORT handles (≤40 chars)
        # Truncate long handles to find natural break points
        if len(quote) > 40:
            # Find a natural break point before 40 chars
            for delim in [',', ';', '—', ' - ', ' and ']:
                idx = quote[:40].rfind(delim)
                if idx > 15:
                    quote = quote[:idx].strip()
                    break
            else:
                # No good break point - try word boundary
                if len(quote) > 60:
                    words = quote.split()
                    truncated = []
                    length = 0
                    for w in words:
                        if length + len(w) + 1 > 40:
                            break
                        truncated.append(w)
                        length += len(w) + 1
                    if truncated:
                        quote = ' '.join(truncated)

        # Final length check - reject if still too long
        if len(quote) > 60:
            return False

        # Strip trailing punctuation
        quote = re.sub(r'[,;:.\-–—]+$', '', quote).strip()

        if len(quote) < 4:
            return False

        # Apply word count boost to score (prefer multi-word spans)
        adjusted_score = _score_by_word_count(quote, score)

        # Bonus for ideal length (15-35 chars)
        if 15 <= len(quote) <= 35:
            adjusted_score = min(adjusted_score + 0.05, 1.0)

        seen_quotes.add(quote_normalized)
        handles.append({
            "handle_id": str(uuid.uuid4())[:8],
            "quote": quote,
            "kind": kind,
            "score": adjusted_score,
            "source": source,
            "line_num": line_num,
            "extraction_tag": tag,
        })
        return True

    # Combine text sources
    lines = []
    if text:
        lines = [(i + 1, line, "body") for i, line in enumerate(text.split('\n'))]

    full_text = (text or "") + "\n" + (title or "")

    # === 1. Extract from title FIRST (highest priority) ===
    if title:
        normalized_title = normalize_for_anchor(title)
        if normalized_title and len(normalized_title) >= 4:
            add_handle(normalized_title, "heading", 0.98, "title", 0, "title_normalized")

    # === 1.5. Extract FULL NOUN PHRASES (highest priority, no truncation) ===
    # These are important literary/thematic phrases that must be preserved whole
    for pattern in FULL_PHRASE_PATTERNS:
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            phrase = match.group(0).strip()
            if 4 <= len(phrase) <= 60:
                add_handle(phrase, "entity", 0.96, "body", 0, "full_phrase_pattern")

    # === 1.6. Extract first-person claim phrases (for WH-question triggers) ===
    for pattern in FIRST_PERSON_PATTERNS:
        for match in re.finditer(pattern, full_text, re.IGNORECASE):
            phrase = match.group(0).strip()
            if 4 <= len(phrase) <= 40:
                add_handle(phrase, "phrase", 0.92, "body", 0, "first_person_claim")

    # === 2. Named entities - CRITICAL for literary/creative content ===
    # Look for capitalized phrases: The Author, Scheherazade, Giallo, Magical Dominion
    # Pattern: "The X" or multi-word capitalized phrases
    for match in re.finditer(r'\b(The\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', full_text):
        phrase = match.group(1).strip()
        if 6 <= len(phrase) <= 40:
            add_handle(phrase, "entity", 0.95, "body", 0, "the_phrase")

    # Single capitalized terms that look like names/concepts (not common words)
    common_words = {'This', 'That', 'These', 'Those', 'What', 'When', 'Where', 'Which', 'While', 'Although', 'However', 'Therefore', 'Perhaps', 'Maybe', 'Indeed', 'Actually', 'Simply', 'Really', 'Just'}
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b', full_text):
        phrase = match.group(1).strip()
        if phrase not in common_words and 4 <= len(phrase) <= 35:
            # Extra validation: should not be at start of sentence (after period)
            start = match.start()
            if start > 0 and full_text[start-1] not in '.!?\n':
                add_handle(phrase, "entity", 0.90, "body", 0, "capitalized_phrase")

    # === 3. Extract colon clauses (What/How/Why patterns) ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # "What X is:", "How X works:", "Why X matters:", etc.
        colon_match = re.match(
            r'^((?:What|How|Why|When|Where|Which)\s+[^:]{3,40}):\s*(.*)$',
            line_stripped,
            re.IGNORECASE
        )
        if colon_match:
            clause = colon_match.group(1).strip()
            add_handle(clause, "colon", 0.88, source, line_num, "wh_clause")

    # === 4. Extract bullet labels ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # Bullet with label pattern: "- **Label:** content" or "- Label: content"
        bullet_match = re.match(
            r'^[-*•]\s*(?:\*\*)?([^:*\n]{4,40})(?:\*\*)?\s*:\s*(.*)$',
            line_stripped
        )
        if bullet_match:
            label = bullet_match.group(1).strip()
            if len(label) >= 4:
                add_handle(label, "bullet", 0.85, source, line_num, "bullet_label")

        # Plain bullet lines (substantial content) - extract key phrase
        elif line_stripped.startswith(('-', '*', '•')):
            content = line_stripped.lstrip('-*•').strip()
            # Extract first meaningful phrase (before comma or dash)
            for delim in [',', ' - ', '—', ';']:
                if delim in content:
                    first_part = content.split(delim, 1)[0].strip()
                    if 8 <= len(first_part) <= 40:
                        add_handle(first_part, "bullet", 0.75, source, line_num, "bullet_first_phrase")
                    break
            else:
                if 8 <= len(content) <= 40:
                    add_handle(content, "bullet", 0.70, source, line_num, "bullet_content")

    # === 5. Extract headings from body ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # Markdown headings
        if line_stripped.startswith('#'):
            heading = line_stripped.lstrip('#').strip()
            heading = normalize_for_anchor(heading)
            if heading and len(heading) >= 4:
                add_handle(heading, "heading", 0.92, source, line_num, "md_heading")

        # "Title: X" lines in body
        if line_stripped.lower().startswith('title:'):
            title_text = line_stripped[6:].strip()
            title_text = normalize_for_anchor(title_text)
            if title_text and len(title_text) >= 4:
                add_handle(title_text, "heading", 0.90, source, line_num, "title_line")

    # === 6. Extract bold phrases (strip the markdown) ===
    for match in re.finditer(r'\*\*([^*]+)\*\*', full_text):
        phrase = strip_all_quotes(match.group(1).strip())
        if 6 <= len(phrase) <= 40:
            add_handle(phrase, "phrase", 0.78, "body", 0, "bold_phrase")

    # === 7. Extract content from quoted phrases (extract CONTENT, not the quotes) ===
    for match in re.finditer(r'["\'\u201c\u201d]([^"\'\u201c\u201d]+)["\'\u201c\u201d]', full_text):
        phrase = match.group(1).strip()  # Get content inside quotes
        if 6 <= len(phrase) <= 40:
            add_handle(phrase, "phrase", 0.75, "body", 0, "quoted_content")

    # === 8. Sentence fragments (fallback for prose-only content) ===
    if len(handles) < 8:
        for line_num, line, source in lines[:15]:
            line_stripped = line.strip()

            # Skip empty, headers, PAGE lines, already-processed bullets
            if not line_stripped:
                continue
            if line_stripped.lower().startswith(('title:', 'page ')):
                continue
            if line_stripped.startswith('#'):
                continue
            if line_stripped.startswith(('-', '*', '•')):
                continue

            # Extract first meaningful phrase (before punctuation)
            if len(line_stripped) >= 15:
                for delim in ['—', ':', ';', ',', ' - ', ' – ']:
                    if delim in line_stripped:
                        parts = line_stripped.split(delim, 1)
                        first_part = strip_all_quotes(parts[0].strip())
                        if 10 <= len(first_part) <= 40:
                            add_handle(first_part, "sentence", 0.50, source, line_num, "first_clause")
                            break

    # Sort by score descending
    handles.sort(key=lambda h: h["score"], reverse=True)

    # Return up to 15 handles (PASS 2: fewer but better)
    return handles[:15]


def choose_diverse_handles(handles: List[Dict[str, Any]], k: int = 8) -> List[Dict[str, Any]]:
    """
    Choose k diverse handles ensuring variety of kinds.

    Prioritizes:
    - Different kinds (colon, bullet, heading, entity, phrase, sentence)
    - Non-overlapping content
    - Higher scores within each kind

    Args:
        handles: List of handle dicts from extract_handles
        k: Number of handles to select (default 8)

    Returns:
        List of k selected handle dicts
    """
    if not handles:
        return []

    if len(handles) <= k:
        return handles

    selected = []
    used_kinds = set()
    used_quotes = set()

    # Priority order for kinds (structured content first)
    priority_kinds = ["colon", "bullet", "heading", "entity", "phrase", "sentence"]

    # First pass: get one of each kind (max k)
    for kind in priority_kinds:
        if len(selected) >= k:
            break
        for handle in handles:
            if handle["kind"] == kind and kind not in used_kinds:
                if not _overlaps(handle["quote"], used_quotes):
                    selected.append(handle)
                    used_kinds.add(kind)
                    used_quotes.add(handle["quote"].lower())
                    break

    # Second pass: fill remaining with highest score (non-overlapping)
    for handle in handles:
        if len(selected) >= k:
            break
        if handle not in selected:
            if not _overlaps(handle["quote"], used_quotes):
                selected.append(handle)
                used_quotes.add(handle["quote"].lower())

    return selected[:k]


def select_diverse_handles(handles: List[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
    """Alias for choose_diverse_handles with count parameter."""
    return choose_diverse_handles(handles, k=count)


def choose_top_handles(handles: List[Dict[str, Any]], k: int = 4) -> List[Dict[str, Any]]:
    """Alias for choose_diverse_handles."""
    return choose_diverse_handles(handles, k=k)


def _overlaps(quote: str, used_quotes: set) -> bool:
    """Check if quote overlaps significantly with used quotes."""
    quote_lower = quote.lower()
    quote_words = set(quote_lower.split())

    for used in used_quotes:
        used_words = set(used.split())
        overlap = quote_words & used_words
        # Significant overlap if > 60% of words shared
        if len(overlap) > 2 and len(overlap) / min(len(quote_words), len(used_words)) > 0.6:
            return True
        # Direct substring match
        if quote_lower in used or used in quote_lower:
            return True

    return False


def debug_handles(text: str, title: Optional[str] = None) -> None:
    """Print extracted and selected handles for debugging."""
    handles = extract_handles(text, title)
    diverse = choose_diverse_handles(handles, k=8)

    print(f"\n{'='*70}")
    print(f"HANDLE EXTRACTION DEBUG")
    print(f"{'='*70}")
    print(f"Title: {title[:60] if title else 'None'}...")
    print(f"Body length: {len(text) if text else 0} chars")
    print(f"\nExtracted {len(handles)} handles:")

    for i, h in enumerate(handles[:15], 1):
        marker = " <-- SELECTED" if h in diverse else ""
        wc = _word_count(h['quote'])
        print(f"  {i:2}. [{h['kind']:8}] {h['score']:.2f} ({wc}w) | {h['quote'][:55]}...{marker}")

    print(f"\nSelected {len(diverse)} diverse handles:")
    for i, h in enumerate(diverse, 1):
        print(f"  {i}. [{h['kind']}] \"{h['quote']}\"")

    print(f"{'='*70}\n")
