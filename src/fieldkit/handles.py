"""
Field-Kit v0.1 Handle Extraction

Extracts span-level handles from Item content for bond generation.

A handle is a verbatim substring from the Item that can anchor a bond.
Priority order:
1. Bullet labels (lines with ":" or starting with "-" or "*")
2. Colon clauses (What X is:, How X works:)
3. Named entities (The Entrance Way, Vault, QDPI)
4. Short noun phrases and proper nouns
5. Sentence fragments (only if better handles unavailable)

Returns at least 8 handles when possible.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import uuid


@dataclass
class Handle:
    """A handle extracted from Item content."""
    handle_id: str     # Unique ID for this handle
    quote: str         # Exact verbatim substring from item
    kind: str          # bullet | colon | entity | phrase | sentence
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


def extract_handles(text: str, title: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract 8-20 candidate handles from Item content.

    Args:
        text: The item body text
        title: Optional item title

    Returns:
        List of handle dicts with: handle_id, quote, kind, score

    Priority:
    1. Bullet labels (lines starting with - or * followed by label:)
    2. Colon clauses (What X is:, How X works:)
    3. Named entities (capitalized multi-word phrases)
    4. Short noun phrases (from bold/quoted text)
    5. Sentence fragments (fallback for prose)
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

        # Normalize for dedup
        quote_normalized = re.sub(r'\s+', ' ', quote.lower())
        if quote_normalized in seen_quotes:
            return False

        # Truncate very long quotes but keep them
        if len(quote) > 80:
            # Find a natural break point
            for delim in [',', ';', '—', '-', ' and ']:
                idx = quote[:80].rfind(delim)
                if idx > 40:
                    quote = quote[:idx].strip()
                    break
            else:
                quote = quote[:77].strip() + "..."

        seen_quotes.add(quote_normalized)
        handles.append({
            "handle_id": str(uuid.uuid4())[:8],
            "quote": quote,
            "kind": kind,
            "score": score,
            "source": source,
            "line_num": line_num,
        })
        return True

    # Combine text sources
    lines = []
    if text:
        lines = [(i + 1, line, "body") for i, line in enumerate(text.split('\n'))]

    # === 1. Extract bullet labels (highest priority) ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # Bullet with label: pattern (- **Label:** or - Label: or * Label:)
        bullet_match = re.match(r'^[-*•]\s*(?:\*\*)?([^:*\n]+?)(?:\*\*)?\s*:\s*(.*)$', line_stripped)
        if bullet_match:
            label = bullet_match.group(1).strip()
            rest = bullet_match.group(2).strip()

            # The label is a high-quality handle
            if len(label) >= 4 and len(label) <= 60:
                add_handle(label, "bullet", 0.95, source, line_num)

            # The rest of the bullet (after colon) is also valuable
            if rest and len(rest) >= 10 and len(rest) <= 80:
                add_handle(rest, "bullet", 0.85, source, line_num)

    # === 2. Extract colon clauses (What/How/Why patterns) ===
    for line_num, line, source in lines:
        line_stripped = line.strip()

        # What X is:, How X works:, Why X matters:
        colon_match = re.match(
            r'^((?:What|How|Why|When|Where|Which)\s+[^:]{3,50}):\s*(.*)$',
            line_stripped,
            re.IGNORECASE
        )
        if colon_match:
            clause = colon_match.group(1).strip()
            explanation = colon_match.group(2).strip()

            add_handle(clause, "colon", 0.92, source, line_num)

            # The explanation is also a handle candidate
            if explanation and len(explanation) >= 10 and len(explanation) <= 80:
                add_handle(explanation, "colon", 0.80, source, line_num)

    # === 3. Extract from title ===
    if title:
        normalized_title = _normalize_title(title)
        if normalized_title and len(normalized_title) >= 5:
            add_handle(normalized_title, "phrase", 0.88, "title", 0)

    # === 4. Extract named entities (capitalized multi-word) ===
    full_text = (text or "") + "\n" + (title or "")

    # Domain entities
    for entity in DOMAIN_ENTITIES:
        pattern = re.compile(r'\b' + re.escape(entity) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(full_text):
            original = match.group()
            if len(original) >= 4:
                add_handle(original, "entity", 0.75, "body", 0)

    # Capitalized noun phrases (The Entrance Way, QDPI Events)
    for match in re.finditer(r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})', full_text):
        phrase = match.group(0).strip()
        if len(phrase) >= 5 and len(phrase) <= 50:
            # Skip common words
            if phrase.lower() not in {'this document', 'this is', 'what is', 'how to'}:
                add_handle(phrase, "entity", 0.70, "body", 0)

    # All-caps acronyms/terms (QDPI, RAG, GPU)
    for match in re.finditer(r'\b([A-Z]{2,6})\b', full_text):
        term = match.group(1)
        if term not in {'THE', 'AND', 'FOR', 'BUT', 'NOT', 'ARE', 'WAS', 'HAS'}:
            add_handle(term, "entity", 0.65, "body", 0)

    # === 5. Extract short noun phrases (bold/quoted) ===
    # Bold phrases (**text**)
    for match in re.finditer(r'\*\*([^*]+)\*\*', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 4 and len(phrase) <= 60:
            add_handle(phrase, "phrase", 0.78, "body", 0)

    # Quoted phrases ("text" or 'text')
    for match in re.finditer(r'["\']([^"\']+)["\']', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 5 and len(phrase) <= 60:
            add_handle(phrase, "phrase", 0.72, "body", 0)

    # Compound phrases with + or / (memory + inference)
    for match in re.finditer(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*\s*[+/&]\s*[a-zA-Z]+(?:\s+[a-zA-Z]+)*)', full_text):
        phrase = match.group(1).strip()
        if len(phrase) >= 5 and len(phrase) <= 50:
            add_handle(phrase, "phrase", 0.68, "body", 0)

    # === 6. Sentence fragments (fallback for prose-only content) ===
    if len(handles) < 8:
        for line_num, line, source in lines[:15]:
            line_stripped = line.strip()

            # Skip empty, headers, PAGE lines
            if not line_stripped:
                continue
            if line_stripped.lower().startswith(('title:', 'page ')):
                continue
            if line_stripped.startswith('#'):
                continue
            if line_stripped.startswith(('-', '*', '•')):
                continue  # Already handled

            # Extract meaningful sentence fragments
            if len(line_stripped) >= 15 and len(line_stripped) <= 120:
                # Prefer first clause before punctuation
                for delim in ['—', ':', ';', ',', ' - ']:
                    if delim in line_stripped:
                        parts = line_stripped.split(delim, 1)
                        if len(parts[0]) >= 10 and len(parts[0]) <= 70:
                            add_handle(parts[0].strip(), "sentence", 0.45, source, line_num)
                            break
                else:
                    # No delimiter, use full sentence if short enough
                    if len(line_stripped) <= 70:
                        add_handle(line_stripped, "sentence", 0.40, source, line_num)

    # Sort by score descending
    handles.sort(key=lambda h: h["score"], reverse=True)

    # Return 8-20 handles
    return handles[:20]


def _normalize_title(title: str) -> str:
    """Normalize title by stripping PAGE/numeric prefixes."""
    if not title:
        return ""
    result = title.strip()
    # Strip "PAGE X – " patterns
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)
    # Strip "Title: " prefix
    result = re.sub(r'^Title:\s*', '', result, flags=re.IGNORECASE)
    # Strip leading numeric prefixes
    result = re.sub(r'^\d+\s*[-–_]\s*', '', result)
    return result.strip()


def select_diverse_handles(handles: List[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
    """
    Select diverse handles ensuring variety of kinds.

    Args:
        handles: List of handle dicts from extract_handles
        count: Number of handles to select (default 4)

    Returns:
        List of selected handle dicts
    """
    if not handles:
        return []

    if len(handles) <= count:
        return handles

    selected = []
    used_kinds = set()
    used_quotes = set()

    # Priority order for kinds
    priority_kinds = ["bullet", "colon", "entity", "phrase", "sentence"]

    # First pass: get one of each kind
    for kind in priority_kinds:
        if len(selected) >= count:
            break
        for handle in handles:
            if handle["kind"] == kind and kind not in used_kinds:
                if not _overlaps(handle["quote"], used_quotes):
                    selected.append(handle)
                    used_kinds.add(kind)
                    used_quotes.add(handle["quote"].lower())
                    break

    # Second pass: fill remaining with highest score
    for handle in handles:
        if len(selected) >= count:
            break
        if handle not in selected:
            if not _overlaps(handle["quote"], used_quotes):
                selected.append(handle)
                used_quotes.add(handle["quote"].lower())

    return selected[:count]


def _overlaps(quote: str, used_quotes: set) -> bool:
    """Check if quote overlaps significantly with used quotes."""
    quote_lower = quote.lower()
    quote_words = set(quote_lower.split())

    for used in used_quotes:
        used_words = set(used.split())
        overlap = quote_words & used_words
        if len(overlap) > 2 and len(overlap) / min(len(quote_words), len(used_words)) > 0.5:
            return True
        if quote_lower in used or used in quote_lower:
            return True

    return False


def debug_handles(text: str, title: Optional[str] = None) -> None:
    """Print selected handles for debugging."""
    handles = extract_handles(text, title)
    diverse = select_diverse_handles(handles)

    print(f"\n{'='*60}")
    print(f"HANDLE EXTRACTION DEBUG")
    print(f"{'='*60}")
    print(f"Title: {title[:50] if title else 'None'}...")
    print(f"Body length: {len(text) if text else 0} chars")
    print(f"\nExtracted {len(handles)} handles:")

    for i, h in enumerate(handles[:12], 1):
        marker = " <--" if h in diverse else ""
        print(f"  {i:2}. [{h['kind']:8}] {h['score']:.2f} | {h['quote'][:50]}...{marker}")

    print(f"\nSelected {len(diverse)} diverse handles:")
    for i, h in enumerate(diverse, 1):
        print(f"  {i}. [{h['kind']}] \"{h['quote']}\"")

    print(f"{'='*60}\n")
