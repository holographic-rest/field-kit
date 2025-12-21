"""
Field-Kit v0.1 Core Library

Private • Local only
"""

from .schemas import (
    Network, Episode, Item, Bond, QDPIEvent,
    Vec3, ActorRef, ErrorInfo,
    ItemProvenanceUser, ItemProvenanceBond, ItemProvenanceHolologue,
    generate_network_id, generate_episode_id, generate_item_id,
    generate_bond_id, generate_event_id, now_iso,
    SYSTEM_ACTOR, USER_ACTOR,
    CANONICAL_EVENT_NAMES,
)

from .store_jsonl import Store, get_store, reset_store, dict_to_item, dict_to_bond, dict_to_episode

from .qdpi import EventLogger, get_logger

from .spin_recipes import (
    SpinRecipe,
    get_recipe,
    get_recipes_by_category,
    normalize_title_for_anchor,
    extract_anchor_phrase,
    render_template,
    generate_suggestions_for_item,
    generate_proposals_for_holologue,
    RECIPE_BY_ID,
    ALL_RECIPES,
    MONOLOGUE_RECIPES,
    DIALOGUE_RECIPES,
    HOLOLOGUE_RECIPES,
)

from .context_transformer import (
    Anchor,
    BondSuggestion,
    extract_anchors,
    rank_anchors,
    generate_bonds,
    validate_bond,
    validate_bonds,
    transform_context,
    transform_holologue_context,
    suggestions_to_legacy_format,
)

from .handles import (
    Handle,
    extract_handles as extract_content_handles,
    select_diverse_handles as select_content_handles,
    debug_handles,
)

from .generation import (
    generate_bond_output,
    generate_holologue_output,
)

__all__ = [
    # Schemas
    "Network", "Episode", "Item", "Bond", "QDPIEvent",
    "Vec3", "ActorRef", "ErrorInfo",
    "ItemProvenanceUser", "ItemProvenanceBond", "ItemProvenanceHolologue",
    # ID generators
    "generate_network_id", "generate_episode_id", "generate_item_id",
    "generate_bond_id", "generate_event_id", "now_iso",
    # Actors
    "SYSTEM_ACTOR", "USER_ACTOR",
    # Constants
    "CANONICAL_EVENT_NAMES",
    # Store
    "Store", "get_store", "reset_store", "dict_to_item", "dict_to_bond", "dict_to_episode",
    # Events
    "EventLogger", "get_logger",
    # Spin Recipes
    "SpinRecipe",
    "get_recipe",
    "get_recipes_by_category",
    "normalize_title_for_anchor",
    "extract_anchor_phrase",
    "render_template",
    "generate_suggestions_for_item",
    "generate_proposals_for_holologue",
    "RECIPE_BY_ID",
    "ALL_RECIPES",
    "MONOLOGUE_RECIPES",
    "DIALOGUE_RECIPES",
    "HOLOLOGUE_RECIPES",
    # Context Transformer
    "Anchor",
    "BondSuggestion",
    "extract_anchors",
    "rank_anchors",
    "generate_bonds",
    "validate_bond",
    "validate_bonds",
    "transform_context",
    "transform_holologue_context",
    "suggestions_to_legacy_format",
    # Handle Extraction (content-specific bonds)
    "Handle",
    "extract_content_handles",
    "select_content_handles",
    "debug_handles",
    # Generation
    "generate_bond_output",
    "generate_holologue_output",
]
