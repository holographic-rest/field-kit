"""
Field-Kit v0.1 Sanity Checks (Sprint S01)

Pre-activation sanity checks inspired by CS231n debugging discipline.
All checks operate in warn-mode by default: log warnings but don't fail.

Check boundaries:
1. Candidate sets (not empty, valid structure)
2. Probability scores (normalized 0-1, sum to 1 if distribution)
3. IDs (canonical format, no duplicates)
4. Events (valid schema, required fields)

Usage:
    from fieldkit.sanity_checks import SanityChecker

    checker = SanityChecker(mode="warn")  # or "strict" to raise
    checker.check_candidates(candidates)
    checker.check_probabilities(scores)
    checker.check_id_format(item_id)

See: docs/architecture/ARCHITECTURE_SANITY_CHECKS.md for full design notes.
"""

from typing import List, Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a sanity check."""
    passed: bool
    check_name: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed


class SanityChecker:
    """
    Centralized sanity checker with configurable mode.

    Modes:
    - "warn": Log warnings, don't raise (default)
    - "strict": Raise ValueError on failure
    - "silent": Don't log, just return results
    """

    # Canonical ID patterns
    ID_PATTERNS = {
        "item": re.compile(r"^it_[A-Za-z0-9_]{4,}$"),
        "bond": re.compile(r"^bd_[A-Za-z0-9_]{4,}$"),
        "episode": re.compile(r"^ep_[A-Za-z0-9_]{4,}$"),
        "network": re.compile(r"^nt_[A-Za-z0-9_]{4,}$"),
        "holologue": re.compile(r"^hl_[A-Za-z0-9_]{4,}$"),
    }

    # Valid event names (canonical)
    CANONICAL_EVENTS = {
        "app.first_run.started",
        "episode.created",
        "credits.delta",
        "store.commit",
        "tutorial.started",
        "item.created",
        "item.updated",
        "bond.suggestions.presented",
        "bond.draft_created",
        "bond.run_requested",
        "bond.executed",
        "holologue.run_requested",
        "holologue.completed",
        "bond.proposals.presented",
        "ledger.opened",
    }

    def __init__(self, mode: str = "warn"):
        if mode not in ("warn", "strict", "silent"):
            raise ValueError(f"Invalid mode: {mode}. Use 'warn', 'strict', or 'silent'")
        self.mode = mode
        self.results: List[CheckResult] = []

    def _handle_failure(self, result: CheckResult) -> CheckResult:
        """Handle a failed check based on mode."""
        self.results.append(result)

        if self.mode == "strict":
            raise ValueError(f"Sanity check failed: {result.check_name} - {result.message}")
        elif self.mode == "warn":
            logger.warning(f"[SANITY] {result.check_name}: {result.message}")

        return result

    def _handle_pass(self, result: CheckResult) -> CheckResult:
        """Handle a passed check."""
        self.results.append(result)
        if self.mode == "warn":
            logger.debug(f"[SANITY] {result.check_name}: PASS")
        return result

    def check_candidates(
        self,
        candidates: List[Any],
        min_count: int = 1,
        context: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """
        Check that candidate set is valid.

        Args:
            candidates: List of candidates
            min_count: Minimum required count (default 1)
            context: Optional context for debugging

        Returns:
            CheckResult
        """
        ctx = context or {}

        if candidates is None:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="candidates_not_none",
                message="Candidate set is None",
                context=ctx,
            ))

        if len(candidates) < min_count:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="candidates_min_count",
                message=f"Candidate set has {len(candidates)} items, need >= {min_count}",
                context={**ctx, "count": len(candidates), "min": min_count},
            ))

        return self._handle_pass(CheckResult(
            passed=True,
            check_name="candidates_valid",
            message=f"Candidate set OK ({len(candidates)} items)",
            context={**ctx, "count": len(candidates)},
        ))

    def check_probabilities(
        self,
        scores: List[float],
        sum_to_one: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """
        Check that probability scores are normalized.

        Args:
            scores: List of probability values
            sum_to_one: If True, check scores sum to ~1.0
            context: Optional context for debugging

        Returns:
            CheckResult
        """
        ctx = context or {}

        if not scores:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="probabilities_empty",
                message="Probability list is empty",
                context=ctx,
            ))

        # Check range [0, 1]
        out_of_range = [s for s in scores if s < 0 or s > 1]
        if out_of_range:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="probabilities_range",
                message=f"Scores out of [0,1] range: {out_of_range[:5]}...",
                context={**ctx, "out_of_range": out_of_range[:5]},
            ))

        # Check sum if required
        if sum_to_one:
            total = sum(scores)
            if abs(total - 1.0) > 0.01:
                return self._handle_failure(CheckResult(
                    passed=False,
                    check_name="probabilities_sum",
                    message=f"Scores sum to {total:.4f}, expected ~1.0",
                    context={**ctx, "sum": total},
                ))

        return self._handle_pass(CheckResult(
            passed=True,
            check_name="probabilities_valid",
            message=f"Probabilities OK ({len(scores)} scores)",
            context={**ctx, "count": len(scores)},
        ))

    def check_id_format(
        self,
        id_value: str,
        id_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """
        Check that ID follows canonical format.

        Args:
            id_value: The ID string to check
            id_type: Optional type hint ("item", "bond", etc.)
            context: Optional context for debugging

        Returns:
            CheckResult
        """
        ctx = context or {}

        if not id_value:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="id_not_empty",
                message="ID is empty",
                context=ctx,
            ))

        # If type specified, check specific pattern
        if id_type and id_type in self.ID_PATTERNS:
            pattern = self.ID_PATTERNS[id_type]
            if not pattern.match(id_value):
                return self._handle_failure(CheckResult(
                    passed=False,
                    check_name="id_format",
                    message=f"ID '{id_value}' doesn't match {id_type} pattern",
                    context={**ctx, "id": id_value, "type": id_type},
                ))
        else:
            # Check against any known pattern
            matched = any(p.match(id_value) for p in self.ID_PATTERNS.values())
            if not matched:
                return self._handle_failure(CheckResult(
                    passed=False,
                    check_name="id_format_any",
                    message=f"ID '{id_value}' doesn't match any canonical pattern",
                    context={**ctx, "id": id_value},
                ))

        return self._handle_pass(CheckResult(
            passed=True,
            check_name="id_valid",
            message=f"ID '{id_value}' is valid",
            context={**ctx, "id": id_value},
        ))

    def check_event(
        self,
        event: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """
        Check that event has valid schema.

        Args:
            event: Event dict to validate
            context: Optional context for debugging

        Returns:
            CheckResult
        """
        ctx = context or {}

        required_fields = ["name", "ts"]
        missing = [f for f in required_fields if f not in event]

        if missing:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="event_required_fields",
                message=f"Event missing required fields: {missing}",
                context={**ctx, "missing": missing, "event": event},
            ))

        event_name = event.get("name", "")
        if event_name not in self.CANONICAL_EVENTS:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="event_canonical_name",
                message=f"Event name '{event_name}' not in canonical set",
                context={**ctx, "name": event_name},
            ))

        return self._handle_pass(CheckResult(
            passed=True,
            check_name="event_valid",
            message=f"Event '{event_name}' is valid",
            context={**ctx, "name": event_name},
        ))

    def check_no_duplicates(
        self,
        items: List[Any],
        key_fn: Optional[Callable[[Any], str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CheckResult:
        """
        Check for duplicates in a list.

        Args:
            items: List of items to check
            key_fn: Function to extract key from each item (default: str)
            context: Optional context for debugging

        Returns:
            CheckResult
        """
        ctx = context or {}
        key_fn = key_fn or str

        seen: Set[str] = set()
        duplicates: List[str] = []

        for item in items:
            key = key_fn(item)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

        if duplicates:
            return self._handle_failure(CheckResult(
                passed=False,
                check_name="no_duplicates",
                message=f"Found {len(duplicates)} duplicates: {duplicates[:5]}...",
                context={**ctx, "duplicates": duplicates[:10]},
            ))

        return self._handle_pass(CheckResult(
            passed=True,
            check_name="no_duplicates",
            message=f"No duplicates in {len(items)} items",
            context={**ctx, "count": len(items)},
        ))

    def summary(self) -> Dict[str, Any]:
        """Get summary of all checks run."""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "mode": self.mode,
            "failures": [
                {"check": r.check_name, "message": r.message}
                for r in self.results if not r.passed
            ],
        }

    def reset(self):
        """Clear results for new check sequence."""
        self.results = []


# Convenience functions for quick checks
_default_checker = SanityChecker(mode="warn")


def validate_candidate_set(candidates: List[Any], min_count: int = 1) -> bool:
    """Quick validate candidates (raises in strict mode, warns otherwise)."""
    result = _default_checker.check_candidates(candidates, min_count)
    return result.passed


def validate_probabilities(scores: List[float], sum_to_one: bool = False) -> bool:
    """Quick validate probabilities."""
    result = _default_checker.check_probabilities(scores, sum_to_one)
    return result.passed


def validate_id(id_value: str, id_type: Optional[str] = None) -> bool:
    """Quick validate ID format."""
    result = _default_checker.check_id_format(id_value, id_type)
    return result.passed


def validate_event(event: Dict[str, Any]) -> bool:
    """Quick validate event schema."""
    result = _default_checker.check_event(event)
    return result.passed
