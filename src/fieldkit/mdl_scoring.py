"""
Field-Kit v0.1 MDL Scoring & Controls (Sprint S09)

Implements Minimum Description Length (MDL) scoring and structure-vs-noise gates
to prevent the Field from saving noise or becoming too generic.

Key concepts from research:
- MDL (Essay #24): Learning/model selection as data compression
- Kolmogorov (Essay #26): Structure vs noise as compressibility
- Hinton (Essay #6): Description length budgets for weights
- Coffee Automaton (Essay #20): Apparent complexity measurement

Design principles:
- Uses gzip-based proxies (no external dependencies)
- Deterministic and inspectable
- Suggest-only (does not block actions)
- Integrates with existing governance layer (S06)

Definitions:
- DL(x) = gzip_bytes(json.dumps(x, sort_keys=True))
- "Too compressible" (generic) = very low DL relative to cohort
- "Too incompressible" (noise) = very high DL and low thread overlap
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set

# Import gzip_bytes from complexity module to avoid duplication
from .complexity import gzip_bytes, coarse_grain_snapshot, apparent_complexity


# === MDL Scoring Core ===

# Weight constants for model cost calculation
# These are approximate "bits" per unit - documented below
MODEL_COST_WEIGHTS = {
    "rules": 8,           # Each rule ~8 bits to encode
    "parameters": 4,      # Each param ~4 bits (assuming quantized)
    "token_budget": 0.1,  # Each token ~0.1 bits overhead
    "modules": 16,        # Each module ~16 bits to describe
}

# Weight constants for data cost calculation
DATA_COST_WEIGHTS = {
    "mistakes": 10,       # Each mistake ~10 bits to encode
    "backtracks": 8,      # Each backtrack ~8 bits
    "overrides": 12,      # Each override ~12 bits (explicit user correction)
    "ungrounded": 6,      # Each ungrounded suggestion ~6 bits
}


def model_cost(strategy: Dict[str, Any]) -> int:
    """
    Compute approximate model cost in "bits" for a strategy.

    Model cost captures the complexity of the strategy itself:
    - Number of rules/heuristics
    - Parameter count
    - Token budget consumed
    - Number of modules invoked

    The weights are heuristic approximations inspired by MDL theory:
    a simpler strategy should have lower model cost.

    Args:
        strategy: Dict with optional keys:
            - rules: List of rule names/descriptions
            - parameters: Number of parameters
            - token_budget: Token count used
            - modules: List of module names

    Returns:
        Approximate model cost in bits (higher = more complex)
    """
    cost = 0

    # Rules cost
    rules = strategy.get("rules", [])
    cost += len(rules) * MODEL_COST_WEIGHTS["rules"]

    # Parameters cost
    params = strategy.get("parameters", 0)
    cost += params * MODEL_COST_WEIGHTS["parameters"]

    # Token budget cost
    tokens = strategy.get("token_budget", 0)
    cost += int(tokens * MODEL_COST_WEIGHTS["token_budget"])

    # Modules cost
    modules = strategy.get("modules", [])
    cost += len(modules) * MODEL_COST_WEIGHTS["modules"]

    return cost


def data_cost(outcomes: Dict[str, Any]) -> int:
    """
    Compute approximate data cost in "bits" for outcomes.

    Data cost captures how well the strategy fits the data:
    - Mistakes (wrong predictions/suggestions)
    - Backtracks (user went back)
    - Overrides (explicit corrections)
    - Ungrounded ratio (suggestions without evidence)

    The key MDL insight: prefer strategies that minimize
    model_cost + data_cost, trading complexity for fit.

    Args:
        outcomes: Dict with optional keys:
            - mistakes: Number of wrong suggestions
            - backtracks: Number of user backtracks
            - overrides: Number of explicit overrides
            - ungrounded: Number of ungrounded suggestions
            - ungrounded_ratio: Ratio of ungrounded (0-1)

    Returns:
        Approximate data cost in bits (higher = worse fit)
    """
    cost = 0

    # Direct mistake counts
    cost += outcomes.get("mistakes", 0) * DATA_COST_WEIGHTS["mistakes"]
    cost += outcomes.get("backtracks", 0) * DATA_COST_WEIGHTS["backtracks"]
    cost += outcomes.get("overrides", 0) * DATA_COST_WEIGHTS["overrides"]
    cost += outcomes.get("ungrounded", 0) * DATA_COST_WEIGHTS["ungrounded"]

    # Handle ungrounded ratio if provided instead of count
    if "ungrounded_ratio" in outcomes and "total_suggestions" in outcomes:
        ratio = outcomes["ungrounded_ratio"]
        total = outcomes["total_suggestions"]
        ungrounded_count = int(ratio * total)
        cost += ungrounded_count * DATA_COST_WEIGHTS["ungrounded"]

    return cost


def mdl_score(strategy: Dict[str, Any], outcomes: Dict[str, Any]) -> int:
    """
    Compute total MDL score for a strategy given outcomes.

    MDL Score = model_cost(strategy) + data_cost(outcomes)

    Lower is better: prefer simpler strategies that fit well.

    This is the "crude two-part MDL" from Essay #24:
    L(H) + L(D|H) where H is the hypothesis/strategy.

    Args:
        strategy: Strategy description dict
        outcomes: Outcome measurements dict

    Returns:
        Total MDL score in bits
    """
    return model_cost(strategy) + data_cost(outcomes)


def compare_strategies(
    strategies: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
) -> Tuple[int, Dict[str, int]]:
    """
    Compare multiple strategies by MDL score.

    Args:
        strategies: List of strategy dicts
        outcomes: List of corresponding outcome dicts

    Returns:
        Tuple of (best_index, {name: score} dict)
    """
    if len(strategies) != len(outcomes):
        raise ValueError("strategies and outcomes must have same length")

    if not strategies:
        return -1, {}

    scores = {}
    for i, (strategy, outcome) in enumerate(zip(strategies, outcomes)):
        name = strategy.get("name", f"strategy_{i}")
        scores[name] = mdl_score(strategy, outcome)

    best_name = min(scores, key=scores.get)
    best_index = next(
        i for i, s in enumerate(strategies)
        if s.get("name", f"strategy_{i}") == best_name
    )

    return best_index, scores


# === Complexity Budget ===

@dataclass
class ComplexityBudget:
    """
    Complexity budget for controlling model and memory growth.

    From Essay #6: maintain explicit budgets to prevent runaway complexity.
    These are soft limits that generate warnings, not hard failures.

    Attributes:
        model_max: Maximum model cost in bits
        memory_max: Maximum memory cost in bits (Field size)
        total_max: Maximum total (model + memory) cost
    """
    model_max: int = 1000
    memory_max: int = 10000
    total_max: int = 12000

    def check(
        self,
        model_cost: int,
        memory_cost: int,
    ) -> Tuple[bool, str]:
        """
        Check if costs are within budget.

        Args:
            model_cost: Current model cost
            memory_cost: Current memory/Field cost

        Returns:
            Tuple of (ok, reason)
            ok is True if within all budgets
            reason explains any violation
        """
        total = model_cost + memory_cost

        violations = []

        if model_cost > self.model_max:
            violations.append(
                f"model_cost ({model_cost}) exceeds budget ({self.model_max})"
            )

        if memory_cost > self.memory_max:
            violations.append(
                f"memory_cost ({memory_cost}) exceeds budget ({self.memory_max})"
            )

        if total > self.total_max:
            violations.append(
                f"total_cost ({total}) exceeds budget ({self.total_max})"
            )

        if violations:
            return False, "; ".join(violations)

        return True, "within budget"

    def warn_if_exceeded(
        self,
        model_cost: int,
        memory_cost: int,
        context: str = "",
    ) -> Optional[str]:
        """
        Return warning message if any budget exceeded, else None.

        This is a non-blocking helper for governance integration.
        """
        ok, reason = self.check(model_cost, memory_cost)
        if not ok:
            prefix = f"[{context}] " if context else ""
            return f"{prefix}Budget exceeded: {reason}"
        return None

    def utilization(
        self,
        model_cost: int,
        memory_cost: int,
    ) -> Dict[str, float]:
        """
        Compute budget utilization percentages.

        Returns:
            Dict with model, memory, total utilization (0-1 scale, can exceed 1)
        """
        return {
            "model": model_cost / self.model_max if self.model_max > 0 else 0,
            "memory": memory_cost / self.memory_max if self.memory_max > 0 else 0,
            "total": (model_cost + memory_cost) / self.total_max if self.total_max > 0 else 0,
        }


def compute_memory_cost(data_dir) -> int:
    """
    Compute memory cost for a Field directory.

    Uses apparent_complexity from complexity.py as proxy.

    Args:
        data_dir: Path to data directory

    Returns:
        Memory cost in bytes (gzip of coarse-grained snapshot)
    """
    return apparent_complexity(data_dir)


# === Structure vs Noise Gate ===

# Default thresholds for the gate
DEFAULT_GATE_THRESHOLDS = {
    "dl_low_ratio": 0.3,    # Reject if DL < median * 0.3 (too simple)
    "dl_high_ratio": 2.5,   # Reject if DL > median * 2.5 (too random)
    "min_overlap": 0.1,     # Minimum thread token overlap to allow
    "default_median_dl": 100,  # Default median DL if no cohort stats
}


def extract_tokens(text: str) -> Set[str]:
    """
    Extract normalized tokens from text.

    Uses simple word extraction with lowercasing.
    """
    if not text:
        return set()

    # Extract words, normalize
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    return set(words)


def compute_overlap_score(
    artifact_tokens: Set[str],
    thread_tokens: Set[str],
) -> float:
    """
    Compute overlap score between artifact and thread model tokens.

    Returns Jaccard-style overlap: intersection / union (0-1).
    """
    if not artifact_tokens or not thread_tokens:
        return 0.0

    intersection = artifact_tokens & thread_tokens
    union = artifact_tokens | thread_tokens

    if not union:
        return 0.0

    return len(intersection) / len(union)


def artifact_to_text(artifact: Dict[str, Any]) -> str:
    """
    Extract text content from an artifact for tokenization.

    Handles various artifact shapes (items, proposals, etc).
    """
    text_parts = []

    # Common text fields
    for key in ["title", "body", "summary", "prompt_text", "content", "description"]:
        val = artifact.get(key)
        if val and isinstance(val, str):
            text_parts.append(val)

    # Handle nested structures
    if "constituent_ids" in artifact:
        text_parts.append(" ".join(artifact["constituent_ids"]))

    return " ".join(text_parts)


def thread_model_to_tokens(thread_model: Dict[str, Any]) -> Set[str]:
    """
    Extract tokens from a thread model.

    Thread model may contain:
    - handles: List of handle dicts with "quote" field
    - entities: List of entity strings
    - open_questions: List of question strings
    - keywords: List of keyword strings
    """
    all_tokens: Set[str] = set()

    # Handles
    handles = thread_model.get("handles", [])
    for h in handles:
        if isinstance(h, dict):
            quote = h.get("quote", "")
            all_tokens.update(extract_tokens(quote))
        elif isinstance(h, str):
            all_tokens.update(extract_tokens(h))

    # Entities
    entities = thread_model.get("entities", [])
    for e in entities:
        all_tokens.update(extract_tokens(str(e)))

    # Open questions
    questions = thread_model.get("open_questions", [])
    for q in questions:
        all_tokens.update(extract_tokens(str(q)))

    # Keywords
    keywords = thread_model.get("keywords", [])
    for k in keywords:
        all_tokens.add(k.lower() if isinstance(k, str) else str(k).lower())

    return all_tokens


def structure_vs_noise_gate(
    artifact: Dict[str, Any],
    thread_model: Dict[str, Any],
    *,
    cohort_stats: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Gate to filter noise and generic boilerplate from being saved.

    From Essay #26 (Kolmogorov): Structure vs noise is compressibility.
    - Keep artifacts that are compressible given the thread model
    - Reject artifacts that are too simple (generic) or too random (noise)

    The gate uses:
    1. Description length (DL) via gzip compression
    2. Token overlap with thread model (handles, entities)

    Decision rules:
    - Reject if DL < low_threshold AND overlap low (boilerplate)
    - Reject if DL > high_threshold AND overlap low (noise)
    - Allow if overlap high OR DL in midband

    Args:
        artifact: The artifact to evaluate (item, proposal, etc)
        thread_model: Current thread context (handles, entities, questions)
        cohort_stats: Optional stats from recent artifacts (median_dl, etc)
        thresholds: Optional custom thresholds

    Returns:
        Dict with:
        - allowed: bool - whether artifact passes gate
        - reason: str - explanation
        - bucket: "too_simple" | "too_random" | "structured"
        - dl_artifact: int - description length of artifact
        - overlap_score: float - overlap with thread model
    """
    # Use provided thresholds or defaults
    thresh = {**DEFAULT_GATE_THRESHOLDS, **(thresholds or {})}

    # Compute description length
    dl_artifact = gzip_bytes(artifact)

    # Extract tokens
    artifact_text = artifact_to_text(artifact)
    artifact_tokens = extract_tokens(artifact_text)
    thread_tokens = thread_model_to_tokens(thread_model)

    # Compute overlap score
    overlap_score = compute_overlap_score(artifact_tokens, thread_tokens)

    # Get cohort median DL
    if cohort_stats and "median_dl" in cohort_stats:
        median_dl = cohort_stats["median_dl"]
    else:
        median_dl = thresh["default_median_dl"]

    # Compute thresholds
    dl_low = median_dl * thresh["dl_low_ratio"]
    dl_high = median_dl * thresh["dl_high_ratio"]
    min_overlap = thresh["min_overlap"]

    # Decision logic
    result = {
        "dl_artifact": dl_artifact,
        "overlap_score": round(overlap_score, 4),
        "median_dl": median_dl,
        "dl_low_threshold": round(dl_low, 1),
        "dl_high_threshold": round(dl_high, 1),
    }

    # High overlap = structured, allow regardless of DL
    if overlap_score >= min_overlap * 2:  # Strong overlap
        result["allowed"] = True
        result["bucket"] = "structured"
        result["reason"] = f"High thread overlap ({overlap_score:.2%})"
        return result

    # Too simple (low DL, low overlap) = generic boilerplate
    if dl_artifact < dl_low and overlap_score < min_overlap:
        result["allowed"] = False
        result["bucket"] = "too_simple"
        result["reason"] = (
            f"Too simple (DL={dl_artifact} < {dl_low:.0f}) "
            f"with low overlap ({overlap_score:.2%})"
        )
        return result

    # Too random (high DL, low overlap) = noise
    if dl_artifact > dl_high and overlap_score < min_overlap:
        result["allowed"] = False
        result["bucket"] = "too_random"
        result["reason"] = (
            f"Too random (DL={dl_artifact} > {dl_high:.0f}) "
            f"with low overlap ({overlap_score:.2%})"
        )
        return result

    # Midband DL or acceptable overlap = structured
    result["allowed"] = True
    result["bucket"] = "structured"

    if overlap_score >= min_overlap:
        result["reason"] = f"Acceptable overlap ({overlap_score:.2%}) with thread model"
    else:
        result["reason"] = f"Midband complexity (DL={dl_artifact} in [{dl_low:.0f}, {dl_high:.0f}])"

    return result


def compute_cohort_stats(
    artifacts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute cohort statistics from a list of artifacts.

    Used to calibrate the structure-vs-noise gate.

    Args:
        artifacts: List of artifact dicts

    Returns:
        Dict with median_dl, mean_dl, min_dl, max_dl
    """
    if not artifacts:
        return {
            "median_dl": DEFAULT_GATE_THRESHOLDS["default_median_dl"],
            "mean_dl": DEFAULT_GATE_THRESHOLDS["default_median_dl"],
            "min_dl": 0,
            "max_dl": 0,
            "count": 0,
        }

    dls = [gzip_bytes(a) for a in artifacts]
    dls.sort()

    n = len(dls)
    median_dl = dls[n // 2] if n % 2 == 1 else (dls[n // 2 - 1] + dls[n // 2]) / 2

    return {
        "median_dl": median_dl,
        "mean_dl": sum(dls) / n,
        "min_dl": min(dls),
        "max_dl": max(dls),
        "count": n,
    }


# === Integration Helpers ===

def gate_bundle_proposal(
    proposal: Dict[str, Any],
    thread_model: Dict[str, Any],
    cohort_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply structure-vs-noise gate to a bundle proposal.

    Marks proposal as blocked_by_mdl if rejected.

    Args:
        proposal: Bundle proposal dict
        thread_model: Current thread context
        cohort_stats: Optional cohort statistics

    Returns:
        Updated proposal with gate_result field
    """
    gate_result = structure_vs_noise_gate(
        proposal,
        thread_model,
        cohort_stats=cohort_stats,
    )

    proposal["gate_result"] = gate_result

    if not gate_result["allowed"]:
        proposal["blocked_by_mdl"] = True
        proposal["mdl_reason"] = gate_result["reason"]

    return proposal


def protect_structured_novelty(
    prune_candidates: List[Dict[str, Any]],
    thread_model: Dict[str, Any],
    cohort_stats: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Protect items that are "structured novelty" from pruning.

    Items that pass the structure gate with "structured" bucket
    are marked as protected.

    Args:
        prune_candidates: List of prune candidate dicts
        thread_model: Current thread context
        cohort_stats: Optional cohort statistics

    Returns:
        Updated candidates with protected field
    """
    for candidate in prune_candidates:
        # Create a minimal artifact from candidate
        artifact = {
            "id": candidate.get("item_id", ""),
            "title": candidate.get("item_title", ""),
        }

        gate_result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        if gate_result["allowed"] and gate_result["bucket"] == "structured":
            candidate["protected_by_mdl"] = True
            candidate["mdl_reason"] = gate_result["reason"]

    return prune_candidates


def format_mdl_report(
    strategy: Dict[str, Any],
    outcomes: Dict[str, Any],
    budget: Optional[ComplexityBudget] = None,
    memory_cost: int = 0,
) -> str:
    """
    Format MDL scoring results as a human-readable report.

    Args:
        strategy: Strategy dict
        outcomes: Outcomes dict
        budget: Optional complexity budget
        memory_cost: Current memory cost

    Returns:
        Formatted report string
    """
    m_cost = model_cost(strategy)
    d_cost = data_cost(outcomes)
    total = mdl_score(strategy, outcomes)

    lines = [
        "=" * 50,
        "MDL SCORE REPORT",
        "=" * 50,
        "",
        f"Strategy: {strategy.get('name', 'unnamed')}",
        "",
        "--- Model Cost Breakdown ---",
        f"  Rules: {len(strategy.get('rules', []))} x {MODEL_COST_WEIGHTS['rules']} = {len(strategy.get('rules', [])) * MODEL_COST_WEIGHTS['rules']} bits",
        f"  Parameters: {strategy.get('parameters', 0)} x {MODEL_COST_WEIGHTS['parameters']} = {strategy.get('parameters', 0) * MODEL_COST_WEIGHTS['parameters']} bits",
        f"  Tokens: {strategy.get('token_budget', 0)} x {MODEL_COST_WEIGHTS['token_budget']} = {int(strategy.get('token_budget', 0) * MODEL_COST_WEIGHTS['token_budget'])} bits",
        f"  Modules: {len(strategy.get('modules', []))} x {MODEL_COST_WEIGHTS['modules']} = {len(strategy.get('modules', [])) * MODEL_COST_WEIGHTS['modules']} bits",
        f"  TOTAL MODEL COST: {m_cost} bits",
        "",
        "--- Data Cost Breakdown ---",
        f"  Mistakes: {outcomes.get('mistakes', 0)} x {DATA_COST_WEIGHTS['mistakes']} = {outcomes.get('mistakes', 0) * DATA_COST_WEIGHTS['mistakes']} bits",
        f"  Backtracks: {outcomes.get('backtracks', 0)} x {DATA_COST_WEIGHTS['backtracks']} = {outcomes.get('backtracks', 0) * DATA_COST_WEIGHTS['backtracks']} bits",
        f"  Overrides: {outcomes.get('overrides', 0)} x {DATA_COST_WEIGHTS['overrides']} = {outcomes.get('overrides', 0) * DATA_COST_WEIGHTS['overrides']} bits",
        f"  TOTAL DATA COST: {d_cost} bits",
        "",
        f"==> MDL SCORE: {total} bits (lower is better)",
        "",
    ]

    if budget:
        lines.append("--- Budget Check ---")
        utilization = budget.utilization(m_cost, memory_cost)
        ok, reason = budget.check(m_cost, memory_cost)
        lines.append(f"  Model: {utilization['model']:.1%} of {budget.model_max}")
        lines.append(f"  Memory: {utilization['memory']:.1%} of {budget.memory_max}")
        lines.append(f"  Total: {utilization['total']:.1%} of {budget.total_max}")
        lines.append(f"  Status: {'OK' if ok else 'EXCEEDED'} - {reason}")
        lines.append("")

    lines.append("=" * 50)
    return "\n".join(lines)
