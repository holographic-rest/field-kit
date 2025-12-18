"""
Field-Kit v0.1 Spin Recipes

Static recipe registry for generating content-shaped suggestions and proposals.

Recipes are static data records (not persisted objects). Each recipe has:
- recipe_id: unique identifier
- category: "monologue" | "dialogue" | "holologue" | "proposal_generator"
- output_shape: expected QDPI type of output ("M", "D", "H")
- template: prompt template with placeholders
- intent_type: classification for UI/analytics

Placeholders:
- {{item_title}}: title of the input Item
- {{item_body}}: body of the input Item (if any)
- {{anchor_phrase}}: extracted noun-ish phrase from title
- {{selected_items}}: for Holologue, comma-separated titles
- {{artifact_kind}}: for Holologue, the target artifact type
- {{holologue_output_title}}: for proposals after Holologue
- {{holologue_output_body}}: for proposals after Holologue
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
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
    ),
    SpinRecipe(
        recipe_id="expand_to_checklist",
        category="monologue",
        output_shape="M",
        template="Expand '{{anchor_phrase}}' into a 5-item checklist of things to verify.",
        intent_type="expands",
        description="Creates verification checklist from concept",
    ),
    SpinRecipe(
        recipe_id="ground_in_experiment",
        category="monologue",
        output_shape="M",
        template="Propose a minimal experiment to probe '{{anchor_phrase}}'.",
        intent_type="grounds_in",
        description="Suggests concrete experiment",
    ),
    SpinRecipe(
        recipe_id="derive_min_schema",
        category="monologue",
        output_shape="M",
        template="Derive the minimal JSON schema for '{{anchor_phrase}}'.",
        intent_type="derives",
        description="Extracts data structure from concept",
    ),
    SpinRecipe(
        recipe_id="decision_with_reasons",
        category="monologue",
        output_shape="M",
        template="Write a 5-bullet decision note for '{{anchor_phrase}}' with clear yes/no recommendation.",
        intent_type="grounds_in",
        description="Creates decision record with rationale",
    ),
    SpinRecipe(
        recipe_id="compare_with_criteria",
        category="monologue",
        output_shape="M",
        template="Compare two approaches to '{{anchor_phrase}}' across 3 weighted criteria.",
        intent_type="grounds_in",
        description="Structured comparison framework",
    ),
    SpinRecipe(
        recipe_id="risk_register",
        category="monologue",
        output_shape="M",
        template="List top 5 risks for '{{anchor_phrase}}' with likelihood and impact scores.",
        intent_type="grounds_in",
        description="Risk assessment table",
    ),
    SpinRecipe(
        recipe_id="implementation_plan",
        category="monologue",
        output_shape="M",
        template="Create a step-by-step implementation plan for '{{anchor_phrase}}'.",
        intent_type="expands",
        description="Actionable implementation steps",
    ),
]


# === Dialogue Recipes (Q → D) ===
# 6 recipes from spec

DIALOGUE_RECIPES = [
    SpinRecipe(
        recipe_id="peer_review_objections",
        category="dialogue",
        output_shape="D",
        template="Play a skeptical peer reviewer for '{{anchor_phrase}}'. List 3 objections, then respond to each.",
        intent_type="critiques",
        description="Self-critical review dialogue",
    ),
    SpinRecipe(
        recipe_id="debate_two_options",
        category="dialogue",
        output_shape="D",
        template="Stage a debate between two options for '{{anchor_phrase}}'. Give each side 2 arguments.",
        intent_type="forks",
        description="Point-counterpoint dialogue",
    ),
    SpinRecipe(
        recipe_id="refine_prompt_with_constraints",
        category="dialogue",
        output_shape="D",
        template="Refine the prompt about '{{anchor_phrase}}' by asking 3 clarifying questions and proposing improved versions.",
        intent_type="clarifies",
        description="Iterative prompt refinement",
    ),
    SpinRecipe(
        recipe_id="adversarial_test_cases",
        category="dialogue",
        output_shape="D",
        template="Generate 3 adversarial test cases for '{{anchor_phrase}}' and explain why each might break it.",
        intent_type="critiques",
        description="Adversarial testing dialogue",
    ),
    SpinRecipe(
        recipe_id="rubric_and_scoring",
        category="dialogue",
        output_shape="D",
        template="Create a rubric for evaluating '{{anchor_phrase}}' with 4 criteria, then score a hypothetical example.",
        intent_type="grounds_in",
        description="Evaluation rubric creation",
    ),
    SpinRecipe(
        recipe_id="multi_role_negotiation",
        category="dialogue",
        output_shape="D",
        template="Simulate a negotiation about '{{anchor_phrase}}' between 3 stakeholders with different priorities.",
        intent_type="forks",
        description="Multi-stakeholder negotiation",
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

def extract_anchor_phrase(title: str, body: Optional[str] = None) -> str:
    """
    Extract a short anchor phrase from an Item title.

    v0.1 algorithm (deterministic):
    1. If title <= 30 chars, use whole title
    2. Otherwise, take first noun-ish phrase (up to first punctuation or conjunction)
    3. Fallback: first 30 chars + "..."

    The anchor phrase must appear verbatim in rendered prompts.
    """
    if not title:
        return "this item"

    title = title.strip()

    # Rule 1: Short titles - use whole thing
    if len(title) <= 30:
        return title

    # Rule 2: Extract up to first major punctuation or conjunction
    # Split on: comma, semicolon, colon, dash, "and", "or", "but"
    pattern = r'^([^,;:\-–—]+?)(?:\s*[,;:\-–—]|\s+(?:and|or|but)\s)'
    match = re.match(pattern, title, re.IGNORECASE)

    if match:
        phrase = match.group(1).strip()
        if len(phrase) >= 5:  # Ensure we got something meaningful
            return phrase

    # Rule 3: Fallback - first 30 chars
    return title[:30].rstrip() + "..."


# === Template Rendering ===

def render_template(
    template: str,
    item_title: Optional[str] = None,
    item_body: Optional[str] = None,
    anchor_phrase: Optional[str] = None,
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

# Diverse selection of recipes for suggestions (4 with different output shapes)
SUGGESTION_RECIPE_IDS = [
    "expand_to_checklist",        # M - expands
    "ground_in_experiment",       # M - grounds_in (experiment)
    "derive_min_schema",          # M - derives (schema)
    "decision_with_reasons",      # M - grounds_in (decision)
]


def generate_suggestions_for_item(
    item_title: str,
    item_body: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate exactly 4 content-shaped suggestions for an Item.

    Each suggestion includes:
    - prompt_text: rendered prompt with anchor phrase verbatim
    - intent_type: from recipe
    - recipe_id: for traceability

    Requirements from spec:
    - Exactly 4 suggestions
    - Diverse output shapes/intents
    - Anchor phrase appears verbatim in prompt
    """
    anchor = extract_anchor_phrase(item_title, item_body)

    suggestions = []
    for recipe_id in SUGGESTION_RECIPE_IDS:
        recipe = RECIPE_BY_ID[recipe_id]
        prompt_text = render_template(
            recipe.template,
            item_title=item_title,
            item_body=item_body,
            anchor_phrase=anchor,
        )
        suggestions.append({
            "prompt_text": prompt_text,
            "intent_type": recipe.intent_type,
            "recipe_id": recipe.recipe_id,
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

    Each proposal includes:
    - prompt_text: rendered prompt referencing the Holologue output
    - intent_type: from recipe
    - recipe_id: for traceability

    Requirements from spec:
    - Exactly 4 proposals
    - Diverse follow-on intents
    - Reference the Holologue output artifact
    """
    anchor = extract_anchor_phrase(holologue_output_title, holologue_output_body)

    proposals = []
    for recipe_id in PROPOSAL_RECIPE_IDS:
        recipe = RECIPE_BY_ID[recipe_id]
        # For proposals, we use the holologue output as the "item"
        prompt_text = render_template(
            recipe.template,
            item_title=holologue_output_title,
            item_body=holologue_output_body,
            anchor_phrase=anchor,
            holologue_output_title=holologue_output_title,
            holologue_output_body=holologue_output_body,
        )
        proposals.append({
            "prompt_text": prompt_text,
            "intent_type": recipe.intent_type,
            "recipe_id": recipe.recipe_id,
        })

    return proposals
