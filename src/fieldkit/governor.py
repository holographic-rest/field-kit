"""
Field-Kit v0.1 Memory Governor (Sprint S06)

Governance layer that observes Field state and suggests actions based on
complexity metrics. All actions are suggest-only (no automatic execution).

Key concepts:
- Observe: Compute metrics from data_dir
- Suggest: Recommend action based on thresholds
- Rationale: Explain why action is recommended

Actions:
- "bundle": Consolidate related items/bonds (high complexity, clusters detected)
- "prune": Archive stale/orphaned items (high duplicate/orphan rate)
- "branch": Encourage exploration (too sparse, low entropy)
- "continue": No action needed (healthy state)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from .complexity import (
    compute_all_metrics,
    coarse_grain_snapshot,
    format_metrics_report,
)


@dataclass
class GovernanceThresholds:
    """
    Thresholds for governance decisions.

    Conservative defaults - when uncertain, prefer "continue".
    """
    # Bundle thresholds
    complexity_high: int = 800  # bytes - bundle if above
    hubness_high: float = 0.7   # fraction - bundle if above
    avg_degree_high: float = 4.0  # bundle if above

    # Prune thresholds
    duplicate_rate_high: float = 0.15  # prune if above
    orphan_rate_high: float = 0.4  # prune if above

    # Branch thresholds (encourage exploration)
    entropy_ratio_low: float = 0.5  # branch if below
    bond_ratio_low: float = 0.2  # branch if bonds/items below

    # Minimum data requirements
    min_items_for_action: int = 5  # don't suggest actions for tiny Fields
    min_bonds_for_bundle: int = 3  # need enough bonds to bundle


@dataclass
class GovernanceObservation:
    """
    Result of governance observation.
    """
    timestamp: str
    data_dir: str
    metrics: Dict[str, Any]
    thresholds: Dict[str, Any]
    action: str  # "bundle" | "prune" | "branch" | "continue"
    rationale: str
    confidence: float  # 0.0 to 1.0
    details: List[str] = field(default_factory=list)  # Supporting observations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "data_dir": self.data_dir,
            "metrics_summary": {
                "apparent_complexity": self.metrics.get("apparent_complexity"),
                "branching_factor": self.metrics.get("branching_factor"),
                "hubness": self.metrics.get("hubness"),
                "duplicate_rate": self.metrics.get("duplicate_rate"),
                "entropy_ratio": self.metrics.get("entropy_ratio"),
                "is_soupy": self.metrics.get("is_soupy"),
                "is_sparse": self.metrics.get("is_sparse"),
            },
            "thresholds": self.thresholds,
            "action": self.action,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "details": self.details,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class ComplexityGovernor:
    """
    Observes Field state and suggests governance actions.

    Usage:
        governor = ComplexityGovernor()
        observation = governor.observe(data_dir)
        print(observation.action)  # "bundle", "prune", "branch", or "continue"
        print(observation.rationale)
    """

    def __init__(self, thresholds: Optional[GovernanceThresholds] = None):
        self.thresholds = thresholds or GovernanceThresholds()

    def observe(self, data_dir: Path) -> GovernanceObservation:
        """
        Observe a data directory and suggest governance action.

        Returns:
            GovernanceObservation with action and rationale
        """
        data_dir = Path(data_dir)
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Compute all metrics
        metrics = compute_all_metrics(data_dir)
        snapshot = metrics.get("snapshot", {})
        counts = snapshot.get("counts", {})
        graph_stats = snapshot.get("graph_stats", {})

        # Extract key values
        item_count = counts.get("items", 0)
        bond_count = counts.get("bonds", 0)
        complexity = metrics.get("apparent_complexity", 0)
        hubness = metrics.get("hubness", 0)
        duplicate_rate = metrics.get("duplicate_rate", 0)
        orphan_rate = graph_stats.get("orphan_rate", 0)
        avg_degree = graph_stats.get("avg_degree", 0)
        entropy_ratio = metrics.get("entropy_ratio", 0)
        is_soupy = metrics.get("is_soupy", False)
        is_sparse = metrics.get("is_sparse", False)

        # Compute bond ratio
        bond_ratio = bond_count / item_count if item_count > 0 else 0

        # Threshold dict for observation
        threshold_dict = {
            "complexity_high": self.thresholds.complexity_high,
            "hubness_high": self.thresholds.hubness_high,
            "duplicate_rate_high": self.thresholds.duplicate_rate_high,
            "orphan_rate_high": self.thresholds.orphan_rate_high,
            "entropy_ratio_low": self.thresholds.entropy_ratio_low,
            "bond_ratio_low": self.thresholds.bond_ratio_low,
            "min_items_for_action": self.thresholds.min_items_for_action,
        }

        # Decision logic
        action, rationale, confidence, details = self._decide_action(
            item_count=item_count,
            bond_count=bond_count,
            complexity=complexity,
            hubness=hubness,
            duplicate_rate=duplicate_rate,
            orphan_rate=orphan_rate,
            avg_degree=avg_degree,
            entropy_ratio=entropy_ratio,
            bond_ratio=bond_ratio,
            is_soupy=is_soupy,
            is_sparse=is_sparse,
        )

        return GovernanceObservation(
            timestamp=timestamp,
            data_dir=str(data_dir),
            metrics=metrics,
            thresholds=threshold_dict,
            action=action,
            rationale=rationale,
            confidence=confidence,
            details=details,
        )

    def _decide_action(
        self,
        item_count: int,
        bond_count: int,
        complexity: int,
        hubness: float,
        duplicate_rate: float,
        orphan_rate: float,
        avg_degree: float,
        entropy_ratio: float,
        bond_ratio: float,
        is_soupy: bool,
        is_sparse: bool,
    ) -> Tuple[str, str, float, List[str]]:
        """
        Decide governance action based on metrics.

        Returns:
            Tuple of (action, rationale, confidence, details)
        """
        details: List[str] = []

        # Not enough data for action
        if item_count < self.thresholds.min_items_for_action:
            return (
                "continue",
                f"Field is small ({item_count} items). Keep exploring before governance.",
                0.9,
                [f"Item count {item_count} < threshold {self.thresholds.min_items_for_action}"],
            )

        # Check if we have enough scale for definitive state assertions
        # Minimum scale: at least 3 bonds for bundle, or 10+ items for confident state
        has_min_scale_for_state = bond_count >= self.thresholds.min_bonds_for_bundle or item_count >= 10

        # BUNDLE signals
        bundle_signals = []
        bundle_score = 0.0

        if complexity > self.thresholds.complexity_high:
            bundle_signals.append(f"High complexity ({complexity} bytes)")
            bundle_score += 0.3

        if hubness > self.thresholds.hubness_high:
            bundle_signals.append(f"High hubness ({hubness:.1%})")
            bundle_score += 0.4

        if avg_degree > self.thresholds.avg_degree_high:
            bundle_signals.append(f"High avg degree ({avg_degree:.1f})")
            bundle_score += 0.3

        # Only assert "soup state" if we have minimum scale
        if is_soupy:
            if has_min_scale_for_state:
                bundle_signals.append("Soup state detected")
            else:
                # Softer language for small datasets
                bundle_signals.append("Early soup-like indicators (normal at small scale)")
            bundle_score += 0.2

        # PRUNE signals
        prune_signals = []
        prune_score = 0.0

        if duplicate_rate > self.thresholds.duplicate_rate_high:
            prune_signals.append(f"High duplicate rate ({duplicate_rate:.1%})")
            prune_score += 0.4

        if orphan_rate > self.thresholds.orphan_rate_high:
            prune_signals.append(f"High orphan rate ({orphan_rate:.1%})")
            prune_score += 0.4

        # BRANCH signals (encourage exploration)
        branch_signals = []
        branch_score = 0.0

        if entropy_ratio < self.thresholds.entropy_ratio_low and entropy_ratio > 0:
            branch_signals.append(f"Low entropy ratio ({entropy_ratio:.1%})")
            branch_score += 0.3

        if bond_ratio < self.thresholds.bond_ratio_low:
            branch_signals.append(f"Low bond ratio ({bond_ratio:.2f})")
            branch_score += 0.3

        # Only assert "sparse" if we have minimum scale
        if is_sparse:
            if has_min_scale_for_state:
                branch_signals.append("Sparse graph detected")
            else:
                branch_signals.append("Graph still forming (expected at small scale)")
            branch_score += 0.3

        # Decision: highest score wins, with tie-breakers
        # Priority: bundle > prune > branch > continue
        # This is conservative: bundle/prune only if clear signal

        min_score_for_action = 0.4  # Need at least this much signal

        if bundle_score >= min_score_for_action and bundle_score >= max(prune_score, branch_score):
            # Bundle if we have enough bonds
            if bond_count >= self.thresholds.min_bonds_for_bundle:
                # Collect all details for action
                details.extend(bundle_signals)
                details.extend(prune_signals)
                details.extend(branch_signals)
                return (
                    "bundle",
                    f"Consider bundling: {'; '.join(bundle_signals)}.",
                    min(0.9, bundle_score),
                    details,
                )
            else:
                # Not enough bonds - will fall through to continue
                pass

        if prune_score >= min_score_for_action and prune_score >= branch_score:
            # Collect all details for action
            details.extend(bundle_signals)
            details.extend(prune_signals)
            details.extend(branch_signals)
            return (
                "prune",
                f"Consider pruning: {'; '.join(prune_signals)}.",
                min(0.9, prune_score),
                details,
            )

        if branch_score >= min_score_for_action:
            # Collect all details for action
            details.extend(bundle_signals)
            details.extend(prune_signals)
            details.extend(branch_signals)
            return (
                "branch",
                f"Consider branching: {'; '.join(branch_signals)}.",
                min(0.9, branch_score),
                details,
            )

        # No clear signal or blocked by minimums - continue
        # For CONTINUE action, use softer observations
        continue_details = []

        # Add informational notes about what was observed but not acted on
        if bundle_score > 0 and bond_count < self.thresholds.min_bonds_for_bundle:
            continue_details.append(
                f"Bundle indicators present but below minimum scale ({bond_count} bonds, need {self.thresholds.min_bonds_for_bundle})"
            )
        if hubness > self.thresholds.hubness_high and not has_min_scale_for_state:
            continue_details.append(f"Hubness elevated ({hubness:.1%}) - typical for early-stage Fields")

        if not continue_details:
            continue_details.append("No significant governance signals detected")

        return (
            "continue",
            "Field appears healthy. Continue normal operation.",
            0.8,
            continue_details,
        )

    def format_report(self, observation: GovernanceObservation) -> str:
        """
        Format observation as human-readable report.
        """
        lines = [
            "=" * 60,
            "GOVERNANCE REPORT",
            "=" * 60,
            "",
            f"Timestamp: {observation.timestamp}",
            f"Data Dir: {observation.data_dir}",
            "",
            "--- Recommended Action ---",
            f"  Action: {observation.action.upper()}",
            f"  Confidence: {observation.confidence:.0%}",
            f"  Rationale: {observation.rationale}",
            "",
        ]

        if observation.details:
            lines.append("--- Supporting Observations ---")
            for detail in observation.details:
                lines.append(f"  - {detail}")
            lines.append("")

        # Add metrics summary
        metrics = observation.metrics
        lines.append("--- Key Metrics ---")
        lines.append(f"  Items: {metrics.get('snapshot', {}).get('counts', {}).get('items', 0)}")
        lines.append(f"  Bonds: {metrics.get('snapshot', {}).get('counts', {}).get('bonds', 0)}")
        lines.append(f"  Complexity: {metrics.get('apparent_complexity', 0)} bytes")
        lines.append(f"  Hubness: {metrics.get('hubness', 0):.1%}")
        lines.append(f"  Duplicate Rate: {metrics.get('duplicate_rate', 0):.1%}")
        lines.append(f"  Entropy Ratio: {metrics.get('entropy_ratio', 0):.1%}")
        lines.append("")

        # Add thresholds
        lines.append("--- Thresholds ---")
        for key, value in observation.thresholds.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


def observe_and_report(data_dir: Path, thresholds: Optional[GovernanceThresholds] = None) -> str:
    """
    Convenience function: observe data_dir and return formatted report.
    """
    governor = ComplexityGovernor(thresholds)
    observation = governor.observe(data_dir)
    return governor.format_report(observation)


def observe_and_json(data_dir: Path, thresholds: Optional[GovernanceThresholds] = None) -> str:
    """
    Convenience function: observe data_dir and return JSON.
    """
    governor = ComplexityGovernor(thresholds)
    observation = governor.observe(data_dir)
    return observation.to_json()
