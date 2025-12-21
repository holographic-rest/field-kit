"""
Field-Kit v0.1 Handle Extraction (Span-First, Structure-Aware)

Extracts span-level handles from Item content for bond generation.

A handle is a verbatim substring from the Item that can anchor a bond.
Priority order:
1. Bullet headers / colon clauses (structured content)
2. Multi-word spans (>= 3 words) - avoid single nouns
3. Named entities and capitalized phrases
4. Sentence fragments (only if better handles unavailable)

Returns up to 20 handles with choose_diverse_handles() for variety.
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
    quote: str         # Exact verbatim substring from item
    kind: str          # bullet | colon | entity | phrase | sentence | heading
    score: float       # Ranking score (0-1)
    source: str        # body | title
    line_num: int      # Line number in source (0 for title)


# === Domain entities to recognize ===
DOMAIN_ENTITIES = {
    "field", "item", "bond", "episode", "network", "event", "ledger",
    "holologue", "monologue", "dialogue", "qdpi", "canon", "vault",
    "entrance way", "the entrance way", "gibsey", "rag", "microservices",
    "gpus", "linear algebra", "agents", "operator", "prompt",
    "infrastructure", "architecture", "stack", "layer",
}


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


def normalize_for_anchor(s: str) -> str:
    """
    Normalize a string for use as anchor phrase.
    Strips "PAGE X – ..." prefixes, "Title: " prefixes, and leading/trailing punctuation.
    """
    if not s:
        return ""
    result = s.strip()
    # Strip "PAGE X – " or "PAGE X: " patterns
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)
    # Strip "Title: " prefix
    result = re.sub(r'^Title:\s*', '', result, flags=re.IGNORECASE)
    # Strip leading/trailing punctuation (but keep internal)
    result = re.sub(r'^[^\w]+', '', result)
    result = re.sub(r'[^\w]+$', '', result)
    # Strip leading numeric prefixes like "1 – " or "2. "
    result = re.sub(r'^\d+\s*[-–_.]\s*', '', result)
    return result.strip()


def extract_handles(text: str, title: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract up to 20 candidate handles from Item content.

    Args:
        text: The item body text
        title: Optional item title

    Returns:
        List of handle dicts with: handle_id, quote, kind, score, source, line_num

    Priority (span-first, structure-aware):
    1. Bullet labels and colon clauses (highest value for structure)
    2. Multi-word spans from title/headings (>= 3 words)
    3. Named entities and capitalized phrases
    4. Quoted/bold text
    5. Sentence fragments (fallback for prose-only content)
    """
    handles = []
    seen_quotes = set()

    def add_handle(quote: str, kind: str, score: float, source: str, line_num: int = 0) -> bool:
        """Add handle if valid and not duplicate."""
        quote = quote.strip()
        if not quote or len(quote) < 4:
            return False

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

        # Truncate very long quotes but keep them
        original_quote = quote
        if len(quote) > 100:
            # Find a natural break point
            for delim in [',', ';', '—', '-', ' and ', '.']:
                idx = quote[:100].rfind(delim)
                if idx > 40:
                    quote = quote[:idx].strip()
                    break
            else:
                quote = quote[:97].strip() + "..."

        # Apply word count boost to score (prefer multi-word spans)
        adjusted_score = _score_by_word_count(quote, score)

        seen_quotes.add(quote_normalized)
        handles.append({
            "handle_id": str(uuid.uuid4())[:8],
            "quote": quote,
            "kind": kind,
            "score": adjusted_score,
            "source": source,
            "line_num": line_num,
        })
        return True

    # Combine text sources
    lines = []
    if text:
        lines = [(i + 1, line, "body") for i, line in enumerate(text.split('\n'))]

    # === 1. Extract colon clauses (What/How/Why patterns) - HIGHEST PRIORITY ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # "What X is:", "How X works:", "Why X matters:", etc.
        colon_match = re.match(
            r'^((?:What|How|Why|When|Where|Which)\s+[^:]{3,70}):\s*(.*)$',
            line_stripped,
            re.IGNORECASE
        )
        if colon_match:
            clause = colon_match.group(1).strip()
            explanation = colon_match.group(2).strip()

            # The full clause is a high-quality handle
            add_handle(clause, "colon", 0.98, source, line_num)

            # The explanation is also valuable if it's substantial
            if explanation and len(explanation) >= 15 and len(explanation) <= 120:
                add_handle(explanation, "colon", 0.92, source, line_num)

    # === 2. Extract bullet labels (lines with - or * followed by label:) ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # Bullet with label pattern: "- **Label:** content" or "- Label: content"
        bullet_match = re.match(
            r'^[-*•]\s*(?:\*\*)?([^:*\n]+?)(?:\*\*)?\s*:\s*(.*)$',
            line_stripped
        )
        if bullet_match:
            label = bullet_match.group(1).strip()
            rest = bullet_match.group(2).strip()

            # The label is a high-quality handle
            if len(label) >= 4 and len(label) <= 80:
                add_handle(label, "bullet", 0.95, source, line_num)

            # The rest of the bullet (after colon) is also valuable
            if rest and len(rest) >= 15 and len(rest) <= 120:
                add_handle(rest, "bullet", 0.88, source, line_num)

        # Plain bullet lines (substantial content)
        elif line_stripped.startswith(('-', '*', '•')):
            content = line_stripped.lstrip('-*•').strip()
            if len(content) >= 20 and len(content) <= 120:
                add_handle(content, "bullet", 0.75, source, line_num)

    # === 3. Extract from title (multi-word spans) ===
    if title:
        normalized_title = normalize_for_anchor(title)
        if normalized_title and len(normalized_title) >= 8:
            add_handle(normalized_title, "heading", 0.90, "title", 0)

    # === 4. Extract headings from body ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # Markdown headings
        if line_stripped.startswith('#'):
            heading = line_stripped.lstrip('#').strip()
            if heading and len(heading) >= 8 and len(heading) <= 100:
                add_handle(heading, "heading", 0.85, source, line_num)

        # "Title: X" lines in body
        if line_stripped.lower().startswith('title:'):
            title_text = line_stripped[6:].strip()
            # Strip any leading identifiers
            title_text = re.sub(r'^[A-Z]+\s*[-–:]\s*', '', title_text)
            if title_text and len(title_text) >= 8:
                add_handle(title_text, "heading", 0.88, source, line_num)

    # === 5. Extract named entities ===
    full_text = (text or "") + "\n" + (title or "")

    # Domain entities (multi-word preferred)
    for entity in DOMAIN_ENTITIES:
        if ' ' in entity:  # Prefer multi-word entities
            pattern = re.compile(r'\b' + re.escape(entity) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(full_text):
                original = match.group()
                if len(original) >= 5:
                    add_handle(original, "entity", 0.80, "body", 0)

    # Capitalized noun phrases (The Entrance Way, QDPI Events)
    for match in re.finditer(r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})', full_text):
        phrase = match.group(0).strip()
        if len(phrase) >= 8 and len(phrase) <= 60:
            # Skip common patterns
            if phrase.lower() not in {'this document', 'this is', 'what is', 'how to', 'the item'}:
                add_handle(phrase, "entity", 0.72, "body", 0)

    # === 6. Extract bold/quoted phrases ===
    # Bold phrases (**text**)
    for match in re.finditer(r'\*\*([^*]+)\*\*', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 8 and len(phrase) <= 80:
            add_handle(phrase, "phrase", 0.78, "body", 0)

    # Quoted phrases ("text" or 'text')
    for match in re.finditer(r'["\']([^"\']+)["\']', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 8 and len(phrase) <= 80:
            add_handle(phrase, "phrase", 0.75, "body", 0)

    # Compound phrases with + or / (memory + inference, RAG / agents)
    for match in re.finditer(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*\s*[+/&]\s*[a-zA-Z]+(?:\s+[a-zA-Z]+)*)', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 8 and len(phrase) <= 60:
            add_handle(phrase, "phrase", 0.70, "body", 0)

    # === 7. Sentence fragments (fallback for prose-only content) ===
    if len(handles) < 10:
        for line_num, line, source in lines[:20]:
            line_stripped = line.strip()

            # Skip empty, headers, PAGE lines, already-processed bullets
            if not line_stripped:
                continue
            if line_stripped.lower().startswith(('title:', 'page ')):
                continue
            if line_stripped.startswith('#'):
                continue
            if line_stripped.startswith(('-', '*', '•')):
                continue  # Already handled

            # Extract meaningful sentence fragments
            if len(line_stripped) >= 20 and len(line_stripped) <= 150:
                # Prefer first clause before punctuation
                for delim in ['—', ':', ';', ',', ' - ']:
                    if delim in line_stripped:
                        parts = line_stripped.split(delim, 1)
                        if len(parts[0]) >= 15 and len(parts[0]) <= 80:
                            add_handle(parts[0].strip(), "sentence", 0.50, source, line_num)
                            break
                else:
                    # No delimiter found, use full sentence if appropriate length
                    if len(line_stripped) <= 80:
                        add_handle(line_stripped, "sentence", 0.45, source, line_num)

    # Sort by score descending
    handles.sort(key=lambda h: h["score"], reverse=True)

    # Return up to 20 handles
    return handles[:20]


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
