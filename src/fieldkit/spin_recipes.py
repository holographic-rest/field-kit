"""
Field-Kit v0.1 Spin Recipes

Static recipe registry for generating content-shaped suggestions and proposals.

Recipes are static data records (not persisted objects). Each recipe has:
- recipe_id: unique identifier
- category: "monologue" | "dialogue" | "holologue" | "proposal_generator"
- output_shape: expected QDPI type of output ("M", "D", "H")
- template: prompt template with placeholders
- intent_type: classification for UI/analytics
- display_templates: list of natural language variations for UI chips (6-14 words)

Placeholders:
- {{item_title}}: title of the input Item
- {{item_body}}: body of the input Item (if any)
- {{anchor_phrase}}: extracted noun-ish phrase from title
- {{content_topic}}: derived topic from body fingerprint
- {{body_excerpt}}: first meaningful excerpt from body
- {{selected_items}}: for Holologue, comma-separated titles
- {{artifact_kind}}: for Holologue, the target artifact type
- {{holologue_output_title}}: for proposals after Holologue
- {{holologue_output_body}}: for proposals after Holologue

Sprint G2: Suggestions now have two separate texts:
- display_text: natural language (6-14 words) for UI chips
- prompt_text: structured prompt with item grounding
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re


@dataclass
class SpinRecipe:
    """A static recipe for generating prompts."""
    recipe_id: str
    category: str  # monologue, dialogue, holologue, proposal_generator
    output_shape: str  # M, D, H
    template: str
    intent_type: str
    description: str = ""
    # Natural language display templates for UI chips (6-14 words)
    # Use {{content_topic}} to reference the item's topic
    display_templates: List[str] = field(default_factory=list)


# === Monologue Recipes (Q → M) ===
# 8 recipes from spec

MONOLOGUE_RECIPES = [
    SpinRecipe(
        recipe_id="clarify_to_testable_claim",
        category="monologue",
        output_shape="M",
        template="Rewrite '{{anchor_phrase}}' as a single falsifiable claim that could be tested.",
        intent_type="clarifies",
        description="Transforms ambiguous phrase into testable claim",
        display_templates=[
            "What testable claim does {{content_topic}} actually make?",
            "Turn {{content_topic}} into something I can verify.",
            "Make {{content_topic}} falsifiable and concrete.",
        ],
    ),
    SpinRecipe(
        recipe_id="expand_to_checklist",
        category="monologue",
        output_shape="M",
        template="Expand '{{anchor_phrase}}' into a 5-item checklist of things to verify.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="expands",
        description="Creates verification checklist from concept",
        display_templates=[
            "Make a checklist to validate {{content_topic}}.",
            "What should I verify about {{content_topic}}?",
            "Turn {{content_topic}} into actionable checkboxes.",
        ],
    ),
    SpinRecipe(
        recipe_id="ground_in_experiment",
        category="monologue",
        output_shape="M",
        template="Propose a minimal experiment to probe '{{anchor_phrase}}'.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="grounds_in",
        description="Suggests concrete experiment",
        display_templates=[
            "Design a quick experiment to test {{content_topic}}.",
            "What's the smallest test for {{content_topic}}?",
            "How would I validate {{content_topic}} empirically?",
        ],
    ),
    SpinRecipe(
        recipe_id="derive_min_schema",
        category="monologue",
        output_shape="M",
        template="Derive the minimal JSON schema for '{{anchor_phrase}}'.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="derives",
        description="Extracts data structure from concept",
        display_templates=[
            "What's the data model for {{content_topic}}?",
            "Define the structure of {{content_topic}}.",
            "What schema would capture {{content_topic}}?",
        ],
    ),
    SpinRecipe(
        recipe_id="decision_with_reasons",
        category="monologue",
        output_shape="M",
        template="Write a 5-bullet decision note for '{{anchor_phrase}}' with clear yes/no recommendation.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="grounds_in",
        description="Creates decision record with rationale",
        display_templates=[
            "Should I proceed with {{content_topic}}? Give reasons.",
            "Make a yes/no decision about {{content_topic}}.",
            "What's the verdict on {{content_topic}}?",
        ],
    ),
    SpinRecipe(
        recipe_id="compare_with_criteria",
        category="monologue",
        output_shape="M",
        template="Compare two approaches to '{{anchor_phrase}}' across 3 weighted criteria.",
        intent_type="grounds_in",
        description="Structured comparison framework",
        display_templates=[
            "Compare approaches to {{content_topic}} with criteria.",
            "What are the tradeoffs for {{content_topic}}?",
            "Score different options for {{content_topic}}.",
        ],
    ),
    SpinRecipe(
        recipe_id="risk_register",
        category="monologue",
        output_shape="M",
        template="List top 5 risks for '{{anchor_phrase}}' with likelihood and impact scores.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="grounds_in",
        description="Risk assessment table",
        display_templates=[
            "What could go wrong with {{content_topic}}?",
            "List the risks and failure modes for {{content_topic}}.",
            "What would break first in {{content_topic}}?",
        ],
    ),
    SpinRecipe(
        recipe_id="implementation_plan",
        category="monologue",
        output_shape="M",
        template="Create a step-by-step implementation plan for '{{anchor_phrase}}'.",
        intent_type="expands",
        description="Actionable implementation steps",
        display_templates=[
            "Turn {{content_topic}} into a step-by-step build plan.",
            "How do I actually implement {{content_topic}}?",
            "What are the concrete steps for {{content_topic}}?",
        ],
    ),
    # === Sprint G: Diverse Suggestion Recipes ===
    # 4 distinct output shapes for content-shaped suggestions
    # Display templates are SHORT chip labels (5-8 words max)
    SpinRecipe(
        recipe_id="spec_fragment_rules",
        category="monologue",
        output_shape="M",
        template="""Extract spec rules from '{{anchor_phrase}}'.

Output format:
## Rules
- MUST: (list 4-6 requirements)
- MUST NOT: (list 3-4 anti-patterns)

## Tests
- Test 1: How to verify each MUST
- Test 2: How to detect each MUST NOT violation

Context:
{{body_excerpt}}""",
        intent_type="derives",
        description="Extracts MUST/MUST NOT rules with tests",
        display_templates=[
            "Extract spec rules",
            "Define MUST/MUST NOT constraints",
            "Write testable requirements",
        ],
    ),
    SpinRecipe(
        recipe_id="architecture_map",
        category="monologue",
        output_shape="M",
        template="""Map the architecture of '{{anchor_phrase}}'.

Output format:
## Architecture Map
| Layer | Responsibility | Inputs | Outputs |
|-------|---------------|--------|---------|
(4-6 rows)

## Key Interfaces
- Interface 1: what connects to what
- Interface 2: data flow direction

Context:
{{body_excerpt}}""",
        intent_type="derives",
        description="Creates architecture map table",
        display_templates=[
            "Map the architecture layers",
            "Create layer responsibility table",
            "Show system structure",
        ],
    ),
    SpinRecipe(
        recipe_id="interaction_trace",
        category="monologue",
        output_shape="M",
        template="""Trace a single interaction through '{{anchor_phrase}}'.

Output format:
## Interaction Trace
1. User/System action
2. First response
3. Processing step
... (10-14 steps total)

## State Changes
- Before: initial state
- After: final state

Context:
{{body_excerpt}}""",
        intent_type="grounds_in",
        description="Traces interaction through system",
        display_templates=[
            "Trace interaction step-by-step",
            "Walk through the flow",
            "Show state changes",
        ],
    ),
    SpinRecipe(
        recipe_id="learning_loop_metrics",
        category="monologue",
        output_shape="M",
        template="""Define learning signals for '{{anchor_phrase}}'.

Output format:
## Learning Loop
- Signal 1: what to observe
- Signal 2: what indicates success
- Signal 3: what indicates failure

## Metrics
| Metric | How to measure | Target |
|--------|---------------|--------|
(3-5 rows)

## Feedback Path
How the system improves over time

Context:
{{body_excerpt}}""",
        intent_type="derives",
        description="Defines learning signals and metrics",
        display_templates=[
            "Define learning loop metrics",
            "Identify success signals",
            "Set up feedback path",
        ],
    ),
]


# === Dialogue Recipes (Q → D) ===
# 6 recipes from spec

DIALOGUE_RECIPES = [
    SpinRecipe(
        recipe_id="peer_review_objections",
        category="dialogue",
        output_shape="D",
        template="Play a skeptical peer reviewer for '{{anchor_phrase}}'. List 3 objections, then respond to each.\n\nContext from source:\n> {{body_excerpt}}",
        intent_type="critiques",
        description="Self-critical review dialogue",
        display_templates=[
            "What would a skeptic say about {{content_topic}}?",
            "Challenge {{content_topic}} with tough objections.",
            "Play devil's advocate on {{content_topic}}.",
        ],
    ),
    SpinRecipe(
        recipe_id="debate_two_options",
        category="dialogue",
        output_shape="D",
        template="Stage a debate between two options for '{{anchor_phrase}}'. Give each side 2 arguments.",
        intent_type="forks",
        description="Point-counterpoint dialogue",
        display_templates=[
            "Debate both sides of {{content_topic}}.",
            "What's the strongest case for and against {{content_topic}}?",
            "Stage an argument about {{content_topic}}.",
        ],
    ),
    SpinRecipe(
        recipe_id="refine_prompt_with_constraints",
        category="dialogue",
        output_shape="D",
        template="Refine the prompt about '{{anchor_phrase}}' by asking 3 clarifying questions and proposing improved versions.",
        intent_type="clarifies",
        description="Iterative prompt refinement",
        display_templates=[
            "What clarifying questions should I ask about {{content_topic}}?",
            "Help me sharpen {{content_topic}} with constraints.",
            "Refine {{content_topic}} into something more precise.",
        ],
    ),
    SpinRecipe(
        recipe_id="adversarial_test_cases",
        category="dialogue",
        output_shape="D",
        template="Generate 3 adversarial test cases for '{{anchor_phrase}}' and explain why each might break it.",
        intent_type="critiques",
        description="Adversarial testing dialogue",
        display_templates=[
            "What edge cases would break {{content_topic}}?",
            "Find the adversarial inputs for {{content_topic}}.",
            "Stress test {{content_topic}} with worst-case scenarios.",
        ],
    ),
    SpinRecipe(
        recipe_id="rubric_and_scoring",
        category="dialogue",
        output_shape="D",
        template="Create a rubric for evaluating '{{anchor_phrase}}' with 4 criteria, then score a hypothetical example.",
        intent_type="grounds_in",
        description="Evaluation rubric creation",
        display_templates=[
            "How would I score {{content_topic}} objectively?",
            "Create a rubric to evaluate {{content_topic}}.",
            "What criteria matter most for {{content_topic}}?",
        ],
    ),
    SpinRecipe(
        recipe_id="multi_role_negotiation",
        category="dialogue",
        output_shape="D",
        template="Simulate a negotiation about '{{anchor_phrase}}' between 3 stakeholders with different priorities.",
        intent_type="forks",
        description="Multi-stakeholder negotiation",
        display_templates=[
            "How would different stakeholders view {{content_topic}}?",
            "Simulate a negotiation about {{content_topic}}.",
            "What competing interests affect {{content_topic}}?",
        ],
    ),
]


# === Holologue Recipes (many → one) ===
# 6 recipes from spec

HOLOLOGUE_RECIPES = [
    SpinRecipe(
        recipe_id="holologue_plan_from_constellation",
        category="holologue",
        output_shape="H",
        template="Given the selected items ({{selected_items}}), synthesize a comprehensive {{artifact_kind}}.",
        intent_type="synthesizes",
        description="Synthesizes plan from multiple items",
    ),
    SpinRecipe(
        recipe_id="holologue_spec_fragment_rules",
        category="holologue",
        output_shape="H",
        template="Extract concrete spec rules from ({{selected_items}}) as a numbered list of requirements.",
        intent_type="derives",
        description="Derives spec from constellation",
    ),
    SpinRecipe(
        recipe_id="holologue_taxonomy_or_model",
        category="holologue",
        output_shape="H",
        template="Build a taxonomy or domain model from ({{selected_items}}) with clear hierarchies.",
        intent_type="synthesizes",
        description="Creates taxonomy from items",
    ),
    SpinRecipe(
        recipe_id="holologue_acceptance_checklist",
        category="holologue",
        output_shape="H",
        template="Derive an acceptance test checklist from ({{selected_items}}) with pass/fail criteria.",
        intent_type="derives",
        description="Creates acceptance criteria",
    ),
    SpinRecipe(
        recipe_id="holologue_translation_map",
        category="holologue",
        output_shape="H",
        template="Create a translation map between concepts in ({{selected_items}}).",
        intent_type="synthesizes",
        description="Maps concepts across items",
    ),
    SpinRecipe(
        recipe_id="holologue_meta_recompose_artifacts",
        category="holologue",
        output_shape="H",
        template="Recompose the artifacts in ({{selected_items}}) into a unified narrative.",
        intent_type="synthesizes",
        description="Combines artifacts into narrative",
    ),
]


# === Proposal Generator Recipes ===
# 2 recipes for generating follow-on prompts

PROPOSAL_GENERATOR_RECIPES = [
    SpinRecipe(
        recipe_id="proposal_pack_from_single_item",
        category="proposal_generator",
        output_shape="M",  # Generates prompts for M-type outputs
        template="Based on '{{item_title}}', suggest follow-on prompts.",
        intent_type="expands",
        description="Generates suggestions for single item",
    ),
    SpinRecipe(
        recipe_id="proposal_pack_from_holologue_output",
        category="proposal_generator",
        output_shape="M",  # Generates prompts for M-type outputs
        template="Based on the Holologue output '{{holologue_output_title}}', suggest follow-on prompts.",
        intent_type="expands",
        description="Generates proposals after Holologue",
    ),
]


# === Complete Recipe Registry ===

ALL_RECIPES: List[SpinRecipe] = (
    MONOLOGUE_RECIPES +
    DIALOGUE_RECIPES +
    HOLOLOGUE_RECIPES +
    PROPOSAL_GENERATOR_RECIPES
)

RECIPE_BY_ID: Dict[str, SpinRecipe] = {r.recipe_id: r for r in ALL_RECIPES}


def get_recipe(recipe_id: str) -> Optional[SpinRecipe]:
    """Get a recipe by ID."""
    return RECIPE_BY_ID.get(recipe_id)


def get_recipes_by_category(category: str) -> List[SpinRecipe]:
    """Get all recipes in a category."""
    return [r for r in ALL_RECIPES if r.category == category]


# === Anchor Phrase Extraction ===

def normalize_title_for_anchor(title: str) -> str:
    """
    Normalize a title by stripping PAGE prefixes and numeric patterns.

    Strips:
    - ^PAGE\s+\d+\s*[-–:]\s* (e.g., "PAGE 1 – ", "PAGE 2: ")
    - ^PAGE\s+\d+\s* (e.g., "PAGE 1 " with no delimiter)
    - ^\d+\s*[-–_]\s* (e.g., "01 - ", "1_")

    Returns empty string if result is empty after stripping.
    """
    if not title:
        return ""

    result = title.strip()

    # Strip "PAGE X – " or "PAGE X: " or "PAGE X - "
    result = re.sub(r'^PAGE\s+\d+\s*[-–:]\s*', '', result, flags=re.IGNORECASE)

    # Strip "PAGE X " (with just whitespace after)
    result = re.sub(r'^PAGE\s+\d+\s+', '', result, flags=re.IGNORECASE)

    # Strip leading numeric prefixes like "01 - " or "1_"
    result = re.sub(r'^\d+\s*[-–_]\s*', '', result)

    return result.strip()


def extract_anchor_phrase(title: str, body: Optional[str] = None) -> str:
    """
    Extract a short anchor phrase from an Item title and body.

    v0.1 algorithm (deterministic):
    1. If body contains a line starting with "Title:", use that text
    2. Else use normalized title (after removing PAGE/numeric prefixes)
    3. Else fall back to first meaningful phrase from body
    4. If title <= 40 chars, use whole thing; otherwise extract phrase

    The anchor phrase must appear verbatim in rendered prompts.
    The anchor phrase must NEVER start with "PAGE".
    """
    # Priority 1: Check for "Title:" line in body
    if body:
        for line in body.split('\n'):
            line = line.strip()
            if line.lower().startswith('title:'):
                # Extract text after "Title:"
                title_text = line[6:].strip()
                if title_text and not title_text.upper().startswith('PAGE'):
                    return title_text

    # Priority 2: Use normalized title (strips PAGE X patterns)
    if title:
        normalized = normalize_title_for_anchor(title)
        if normalized and not normalized.upper().startswith('PAGE'):
            # Apply length/phrase extraction rules to normalized title
            if len(normalized) <= 40:
                return normalized

            # Extract up to first major punctuation or conjunction
            pattern = r'^([^,;:\-–—]+?)(?:\s*[,;:\-–—]|\s+(?:and|or|but)\s)'
            match = re.match(pattern, normalized, re.IGNORECASE)

            if match:
                phrase = match.group(1).strip()
                if len(phrase) >= 5:
                    return phrase

            # Fallback for normalized title - first 40 chars
            return normalized[:40].rstrip() + "..."

    # Priority 3: Extract from body if title is unusable
    if body:
        # Find first non-empty, meaningful sentence/phrase
        for line in body.split('\n'):
            line = line.strip()
            # Skip empty lines, Title: lines, and PAGE lines
            if not line:
                continue
            if line.lower().startswith('title:'):
                continue
            if line.upper().startswith('PAGE'):
                continue
            # Skip purely numeric lines
            if re.match(r'^\d+\.?\s*$', line):
                continue

            # Take first ~40 chars of this line
            phrase = line[:40].rstrip()
            if len(phrase) >= 5:
                if len(line) > 40:
                    phrase += "..."
                return phrase

    # Ultimate fallback
    return "this item"


# === Handle Extraction (Context Engineering) ===
# Sprint G: Extract semantic "handles" from Item content for hyperlink-like suggestions

# Junk patterns to strip
JUNK_PATTERNS = [
    r'^PAGE\s+\d+\s*[-–:]\s*',  # "PAGE 1 – "
    r'^PAGE\s+\d+\s*$',          # "PAGE 1"
    r'^\d+\s*[-–_\.]\s*',        # "01 - ", "1."
    r'^This document describes\s*',  # Generic filler
    r'^This is a document about\s*',
    r'^This is meant to be\s*',
    r'^The following\s*',
]


def extract_handles(title: str, body: Optional[str] = None) -> List[str]:
    """
    Extract 6-12 semantic "handles" from Item content.

    Handles are short phrases (max ~70 chars) that represent the actual subjects
    of the item content. They should come from:
    1. Title: line if present
    2. Headings (markdown # or standalone title-like lines)
    3. Bullet items (the label portion before ":" or first 6-10 words)
    4. "Label: value" patterns (just the label)
    5. Noun-ish phrases from sentences

    Handles must NOT include:
    - "PAGE X" patterns
    - "This document describes..." filler
    - Empty or too-short phrases

    Returns:
        List of unique handles (6-12), stable order, deterministic output.
    """
    handles = []
    seen = set()

    def add_handle(h: str) -> bool:
        """Add handle if valid and not seen. Returns True if added."""
        if not h:
            return False
        h = h.strip()
        # Check for junk patterns
        for pattern in JUNK_PATTERNS:
            if re.match(pattern, h, re.IGNORECASE):
                return False
        # Skip if too short or too long
        if len(h) < 4 or len(h) > 70:
            return False
        # Skip if already seen (case-insensitive)
        h_lower = h.lower()
        if h_lower in seen:
            return False
        # Skip pure numbers or PAGE patterns
        if re.match(r'^(page\s*)?\d+\.?$', h, re.IGNORECASE):
            return False
        seen.add(h_lower)
        handles.append(h)
        return True

    # Combine title and body for processing
    lines = []
    if body:
        lines = [l.strip() for l in body.split('\n') if l.strip()]

    # Priority 1: Extract "Title:" line from body
    for line in lines:
        if line.lower().startswith('title:'):
            title_text = line[6:].strip()
            # Strip any junk from the title
            for pattern in JUNK_PATTERNS:
                title_text = re.sub(pattern, '', title_text, flags=re.IGNORECASE)
            if title_text:
                add_handle(title_text)

    # Priority 2: Use the provided title (normalized)
    if title:
        normalized_title = normalize_title_for_anchor(title)
        if normalized_title and not normalized_title.upper().startswith('PAGE'):
            add_handle(normalized_title)

    # Priority 3: Extract headings (markdown # or standalone title-like lines)
    for line in lines:
        # Skip Title: lines (already processed)
        if line.lower().startswith('title:'):
            continue
        # Markdown headings
        if line.startswith('#'):
            heading = line.lstrip('#').strip()
            add_handle(heading)
        # Standalone title-like lines (short, title-cased, no punctuation at end)
        elif len(line) < 60 and line[0].isupper() and not line.endswith(('.', ':', ',')):
            # Could be a heading - add if looks like one
            if not any(c in line for c in ['(', ')', '{', '}', '[', ']']):
                add_handle(line)

    # Priority 4: Extract from "Label: value" patterns
    for line in lines:
        if ':' in line and not line.lower().startswith('title:'):
            parts = line.split(':', 1)
            label = parts[0].strip()
            # Labels are typically short and descriptive
            if 3 < len(label) < 50:
                # Avoid URL-like patterns or common prefixes
                if not any(x in label.lower() for x in ['http', 'www', 'file', '//']):
                    add_handle(label)

    # Priority 5: Extract bullet items
    for line in lines:
        # Check for bullet patterns
        bullet_match = re.match(r'^[-*•]\s+(.+)$', line)
        if bullet_match:
            bullet_content = bullet_match.group(1)
            # If bullet has "Label: description" format, use the label
            if ':' in bullet_content:
                label = bullet_content.split(':')[0].strip()
                if 4 < len(label) < 40:
                    add_handle(label)
            else:
                # Use first 8 words of bullet
                words = bullet_content.split()[:8]
                phrase = ' '.join(words)
                if len(phrase) > 10:
                    # Trim at sentence end if present
                    if '.' in phrase:
                        phrase = phrase.split('.')[0]
                    add_handle(phrase)

    # Priority 6: Extract noun-ish phrases from sentences
    if len(handles) < 6:
        for line in lines[:10]:  # Only first 10 lines
            # Skip already processed patterns
            if any([line.startswith('#'), line.lower().startswith('title:'),
                    re.match(r'^[-*•]', line)]):
                continue
            # Look for "X is Y" patterns
            is_match = re.match(r'^(.+?)\s+is\s+', line, re.IGNORECASE)
            if is_match:
                subject = is_match.group(1).strip()
                if 5 < len(subject) < 50:
                    add_handle(subject)
            # Look for capitalized noun phrases (2-4 words)
            cap_phrases = re.findall(r'(?:the\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}', line)
            for phrase in cap_phrases:
                if 5 < len(phrase) < 40 and phrase.lower() not in ['this', 'what', 'how', 'the']:
                    add_handle(phrase)

    # Priority 7: Extract key acronyms/proper nouns
    if body and len(handles) < 8:
        all_text = (body or "") + " " + (title or "")
        acronyms = re.findall(r'\b[A-Z]{2,}[a-z]*\b', all_text)
        for a in acronyms:
            if a not in ['THE', 'AND', 'FOR', 'THIS', 'PAGE', 'MUST', 'NOT', 'WITH']:
                add_handle(a)

    # Return 6-12 handles
    return handles[:12]


# === Content Fingerprint Extraction ===

def extract_key_phrases(body: Optional[str], title: Optional[str] = None) -> List[str]:
    """
    Extract key phrases from Item body for content-shaped suggestions.

    Extracts:
    - Capitalized proper nouns (QDPI, Vault, Field, etc.)
    - Title: line content
    - Noun-ish phrases (2-4 words with capitals)
    - Technical terms (words with mixed case or acronyms)

    Returns list of 3-6 key phrases that should appear verbatim in suggestions.
    """
    phrases = []

    if not body and not title:
        return ["this content"]

    text = (body or "") + "\n" + (title or "")

    # Extract capitalized acronyms and proper nouns (2+ uppercase letters)
    acronyms = re.findall(r'\b[A-Z]{2,}[a-z]*\b', text)
    for a in acronyms:
        if a not in ['THE', 'AND', 'FOR', 'THIS', 'PAGE', 'MUST', 'NOT']:
            phrases.append(a)

    # Extract Title: line content if present
    for line in text.split('\n'):
        line = line.strip()
        if line.lower().startswith('title:'):
            title_text = line[6:].strip()
            if title_text:
                phrases.append(title_text)

    # Extract capitalized noun phrases (The X, X Y where X/Y are capitalized)
    cap_phrases = re.findall(r'(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}', text)
    for p in cap_phrases:
        p = p.strip()
        if len(p) > 4 and p not in ['This', 'What', 'How', 'The', 'PAGE']:
            if p not in phrases:
                phrases.append(p)

    # Extract key concept patterns: "X and Y", "X + Y"
    concept_patterns = re.findall(r'[a-zA-Z]+\s+(?:and|[+&])\s+[a-zA-Z]+', text)
    for p in concept_patterns:
        if len(p) > 6:
            phrases.append(p)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in phrases:
        p_lower = p.lower()
        if p_lower not in seen and len(p) > 2:
            seen.add(p_lower)
            unique.append(p)

    return unique[:8]  # Return up to 8 key phrases


def extract_content_fingerprint(title: str, body: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract a content fingerprint from an Item for display_text generation.

    Returns:
        Dict with:
        - content_topic: short topic phrase (for display_text placeholders)
        - body_excerpt: first meaningful excerpt from body (1-2 lines)
        - key_terms: list of distinctive terms from body (for content matching)
        - key_phrases: list of proper nouns and concept phrases for verbatim use
    """
    fingerprint = {
        "content_topic": "",
        "body_excerpt": "",
        "key_terms": [],
        "key_phrases": [],
    }

    # Extract key phrases (proper nouns, acronyms, concept phrases)
    fingerprint["key_phrases"] = extract_key_phrases(body, title)

    # Extract content_topic (prefer body content over title)
    if body:
        lines = []
        for line in body.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith('title:'):
                continue
            if line.upper().startswith('PAGE'):
                continue
            lines.append(line)

        if lines:
            # Use first meaningful line as topic, shortened
            first_line = lines[0]
            # Shorten to key noun phrase (first 30 chars or before comma/colon)
            topic = first_line
            for delim in [',', ':', ' - ', ' – ']:
                if delim in topic:
                    topic = topic.split(delim)[0]
                    break
            topic = topic[:35].strip()
            if len(first_line) > 35 and not topic.endswith('...'):
                topic += "..."
            fingerprint["content_topic"] = topic

            # Extract body excerpt (first 1-2 meaningful lines)
            excerpt_lines = lines[:2]
            fingerprint["body_excerpt"] = "\n".join(excerpt_lines)[:200]

            # Extract key terms (distinctive words > 5 chars)
            all_text = " ".join(lines[:4]).lower()
            words = re.findall(r'\b[a-z]{5,}\b', all_text)
            # Filter common words
            common = {'about', 'after', 'before', 'between', 'could', 'would',
                      'should', 'their', 'there', 'these', 'those', 'through',
                      'which', 'while', 'being', 'having', 'using', 'first',
                      'other', 'something', 'everything', 'anything'}
            fingerprint["key_terms"] = [w for w in words if w not in common][:10]

    # Fallback to title if no body content
    if not fingerprint["content_topic"]:
        fingerprint["content_topic"] = extract_anchor_phrase(title, body)

    if not fingerprint["body_excerpt"]:
        fingerprint["body_excerpt"] = title or "(no content)"

    return fingerprint


# === Template Rendering ===

def render_template(
    template: str,
    item_title: Optional[str] = None,
    item_body: Optional[str] = None,
    anchor_phrase: Optional[str] = None,
    content_topic: Optional[str] = None,
    body_excerpt: Optional[str] = None,
    selected_items: Optional[List[str]] = None,
    artifact_kind: Optional[str] = None,
    holologue_output_title: Optional[str] = None,
    holologue_output_body: Optional[str] = None,
) -> str:
    """
    Render a recipe template with provided values.

    Placeholders replaced:
    - {{item_title}}
    - {{item_body}}
    - {{anchor_phrase}}
    - {{content_topic}} (for display_text - short topic)
    - {{body_excerpt}} (for prompt_text - quoted context)
    - {{selected_items}} (comma-separated list)
    - {{artifact_kind}}
    - {{holologue_output_title}}
    - {{holologue_output_body}}
    """
    result = template

    if item_title is not None:
        result = result.replace("{{item_title}}", item_title)

    if item_body is not None:
        result = result.replace("{{item_body}}", item_body)

    if anchor_phrase is not None:
        result = result.replace("{{anchor_phrase}}", anchor_phrase)

    if content_topic is not None:
        result = result.replace("{{content_topic}}", content_topic)

    if body_excerpt is not None:
        result = result.replace("{{body_excerpt}}", body_excerpt)

    if selected_items is not None:
        items_str = ", ".join(selected_items)
        result = result.replace("{{selected_items}}", items_str)

    if artifact_kind is not None:
        result = result.replace("{{artifact_kind}}", artifact_kind)

    if holologue_output_title is not None:
        result = result.replace("{{holologue_output_title}}", holologue_output_title)

    if holologue_output_body is not None:
        result = result.replace("{{holologue_output_body}}", holologue_output_body)

    return result


# === Suggestion Generation (Item Context) ===

# Sprint G: 4 diverse output shapes for content-shaped suggestions
# Each produces a distinctly different artifact structure
SUGGESTION_RECIPE_IDS = [
    "spec_fragment_rules",        # MUST/MUST NOT rules + tests
    "architecture_map",           # Layer/Responsibility/Inputs/Outputs table
    "interaction_trace",          # 10-14 step walkthrough
    "learning_loop_metrics",      # Signals + metrics + feedback
]

# Sprint G: Hyperlink-like suggestion templates
# Each is ONE sentence, 8-18 words, includes "{{handle}}" placeholder
# Intents: clarify, map, trace, test
HYPERLINK_TEMPLATES = [
    {
        "intent": "clarify",
        "recipe_id": "clarify_to_testable_claim",
        "template": "Tell me what \"{{handle}}\" means in this context and why it matters.",
    },
    {
        "intent": "map",
        "recipe_id": "architecture_map",
        "template": "Show how \"{{handle}}\" fits into the architecture and what it connects to.",
    },
    {
        "intent": "trace",
        "recipe_id": "interaction_trace",
        "template": "Walk me through how \"{{handle}}\" flows through the system step by step.",
    },
    {
        "intent": "test",
        "recipe_id": "spec_fragment_rules",
        "template": "Give me a test case that validates \"{{handle}}\" is working correctly.",
    },
]


def generate_suggestions_for_item(
    item_title: str,
    item_body: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate exactly 4 content-shaped suggestions for an Item.

    Sprint G: Each suggestion is a hyperlink-like prompt that:
    - Is ONE sentence, 8-18 words
    - Includes exactly one handle phrase verbatim in quotes
    - Uses distinct intents (clarify, map, trace, test)

    Returns:
    - display_text: The hyperlink-like sentence (for UI chips)
    - prompt_text: Full prompt with context for Bond execution
    - intent_type: clarify, map, trace, or test
    - recipe_id: for traceability
    """
    # Extract handles from item content
    handles = extract_handles(item_title, item_body)

    # Fallback if no handles extracted
    if not handles:
        handles = [extract_anchor_phrase(item_title, item_body)]

    # Get fingerprint for context grounding
    fingerprint = extract_content_fingerprint(item_title, item_body)
    body_excerpt = fingerprint["body_excerpt"]

    suggestions = []
    for i, template_info in enumerate(HYPERLINK_TEMPLATES):
        # Pick a handle (cycle through available handles)
        handle = handles[i % len(handles)]

        # Generate hyperlink-like display text
        display_text = template_info["template"].replace("{{handle}}", handle)

        # Generate full prompt_text with context grounding
        prompt_text = f"""{display_text}

Context from "{item_title}":
> {body_excerpt}"""

        suggestions.append({
            "display_text": display_text,
            "prompt_text": prompt_text,
            "intent_type": template_info["intent"],
            "recipe_id": template_info["recipe_id"],
        })

    return suggestions


# === Proposal Generation (Holologue Context) ===

# Diverse selection of recipes for proposals after Holologue (4 with different intents)
PROPOSAL_RECIPE_IDS = [
    "expand_to_checklist",        # expands - create actionable checklist
    "derive_min_schema",          # derives - extract structure
    "risk_register",              # grounds_in - identify risks
    "peer_review_objections",     # critiques - challenge the output
]


def generate_proposals_for_holologue(
    holologue_output_title: str,
    holologue_output_body: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate exactly 4 content-shaped proposals after Holologue completion.

    Sprint G2: Each proposal now includes:
    - display_text: natural language for UI chips
    - prompt_text: rendered prompt referencing the Holologue output
    - intent_type: from recipe
    - recipe_id: for traceability

    Requirements from spec:
    - Exactly 4 proposals
    - Diverse follow-on intents
    - Reference the Holologue output artifact
    """
    anchor = extract_anchor_phrase(holologue_output_title, holologue_output_body)
    fingerprint = extract_content_fingerprint(holologue_output_title, holologue_output_body)
    content_topic = fingerprint["content_topic"]
    body_excerpt = fingerprint["body_excerpt"]

    proposals = []
    for i, recipe_id in enumerate(PROPOSAL_RECIPE_IDS):
        recipe = RECIPE_BY_ID[recipe_id]

        # Generate display_text from recipe's display_templates
        if recipe.display_templates:
            display_template = recipe.display_templates[i % len(recipe.display_templates)]
            display_text = render_template(
                display_template,
                content_topic=content_topic,
                anchor_phrase=anchor,
            )
        else:
            display_text = f"Process '{content_topic}'"

        # For proposals, we use the holologue output as the "item"
        prompt_text = render_template(
            recipe.template,
            item_title=holologue_output_title,
            item_body=holologue_output_body,
            anchor_phrase=anchor,
            content_topic=content_topic,
            body_excerpt=body_excerpt,
            holologue_output_title=holologue_output_title,
            holologue_output_body=holologue_output_body,
        )
        proposals.append({
            "display_text": display_text,
            "prompt_text": prompt_text,
            "intent_type": recipe.intent_type,
            "recipe_id": recipe.recipe_id,
        })

    return proposals
