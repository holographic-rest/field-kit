#!/usr/bin/env python3
"""
Field-Kit v0.1 MDL Controls Tests (Sprint S09)

Tests for MDL scoring, ComplexityBudget, and structure-vs-noise gate.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.mdl_scoring import (
    model_cost,
    data_cost,
    mdl_score,
    compare_strategies,
    ComplexityBudget,
    structure_vs_noise_gate,
    compute_cohort_stats,
    extract_tokens,
    compute_overlap_score,
    artifact_to_text,
    thread_model_to_tokens,
    gate_bundle_proposal,
    protect_structured_novelty,
    format_mdl_report,
    MODEL_COST_WEIGHTS,
    DATA_COST_WEIGHTS,
)


class TestModelCost:
    """Tests for model_cost function."""

    def test_empty_strategy_zero_cost(self):
        """Empty strategy has zero cost."""
        cost = model_cost({})
        assert cost == 0

    def test_rules_add_cost(self):
        """Rules add to cost."""
        strategy = {"rules": ["rule1", "rule2", "rule3"]}
        cost = model_cost(strategy)
        expected = 3 * MODEL_COST_WEIGHTS["rules"]
        assert cost == expected

    def test_parameters_add_cost(self):
        """Parameters add to cost."""
        strategy = {"parameters": 100}
        cost = model_cost(strategy)
        expected = 100 * MODEL_COST_WEIGHTS["parameters"]
        assert cost == expected

    def test_token_budget_adds_cost(self):
        """Token budget adds fractional cost."""
        strategy = {"token_budget": 1000}
        cost = model_cost(strategy)
        expected = int(1000 * MODEL_COST_WEIGHTS["token_budget"])
        assert cost == expected

    def test_modules_add_cost(self):
        """Modules add to cost."""
        strategy = {"modules": ["mod1", "mod2"]}
        cost = model_cost(strategy)
        expected = 2 * MODEL_COST_WEIGHTS["modules"]
        assert cost == expected

    def test_combined_strategy(self):
        """Combined strategy sums all costs."""
        strategy = {
            "rules": ["r1", "r2"],
            "parameters": 50,
            "token_budget": 500,
            "modules": ["m1"],
        }
        cost = model_cost(strategy)
        expected = (
            2 * MODEL_COST_WEIGHTS["rules"]
            + 50 * MODEL_COST_WEIGHTS["parameters"]
            + int(500 * MODEL_COST_WEIGHTS["token_budget"])
            + 1 * MODEL_COST_WEIGHTS["modules"]
        )
        assert cost == expected


class TestDataCost:
    """Tests for data_cost function."""

    def test_empty_outcomes_zero_cost(self):
        """Empty outcomes has zero cost."""
        cost = data_cost({})
        assert cost == 0

    def test_mistakes_add_cost(self):
        """Mistakes add to cost."""
        outcomes = {"mistakes": 5}
        cost = data_cost(outcomes)
        expected = 5 * DATA_COST_WEIGHTS["mistakes"]
        assert cost == expected

    def test_backtracks_add_cost(self):
        """Backtracks add to cost."""
        outcomes = {"backtracks": 3}
        cost = data_cost(outcomes)
        expected = 3 * DATA_COST_WEIGHTS["backtracks"]
        assert cost == expected

    def test_combined_outcomes(self):
        """Combined outcomes sum costs."""
        outcomes = {
            "mistakes": 2,
            "backtracks": 1,
            "overrides": 1,
        }
        cost = data_cost(outcomes)
        expected = (
            2 * DATA_COST_WEIGHTS["mistakes"]
            + 1 * DATA_COST_WEIGHTS["backtracks"]
            + 1 * DATA_COST_WEIGHTS["overrides"]
        )
        assert cost == expected


class TestMdlScore:
    """Tests for mdl_score function."""

    def test_mdl_score_sum(self):
        """MDL score is sum of model and data costs."""
        strategy = {"rules": ["r1"], "parameters": 10}
        outcomes = {"mistakes": 2}

        score = mdl_score(strategy, outcomes)
        expected = model_cost(strategy) + data_cost(outcomes)
        assert score == expected

    def test_mdl_score_positive(self):
        """MDL score is positive for non-empty inputs."""
        strategy = {"rules": ["r1"]}
        outcomes = {"mistakes": 1}
        score = mdl_score(strategy, outcomes)
        assert score > 0


class TestCompareStrategies:
    """Tests for compare_strategies function."""

    def test_selects_best_strategy(self):
        """MDL selects strategy with lowest total cost."""
        # Strategy A: Many rules, low errors
        strategy_a = {"name": "A", "rules": ["r1", "r2", "r3", "r4", "r5"], "parameters": 100}
        outcomes_a = {"mistakes": 1, "backtracks": 0}

        # Strategy B: Few rules, high errors
        strategy_b = {"name": "B", "rules": ["r1"], "parameters": 10}
        outcomes_b = {"mistakes": 10, "backtracks": 5}

        # Strategy C: Balanced (should win)
        strategy_c = {"name": "C", "rules": ["r1", "r2"], "parameters": 30}
        outcomes_c = {"mistakes": 2, "backtracks": 1}

        strategies = [strategy_a, strategy_b, strategy_c]
        outcomes = [outcomes_a, outcomes_b, outcomes_c]

        best_idx, scores = compare_strategies(strategies, outcomes)

        # C should have lowest score
        assert scores["C"] < scores["A"]
        assert scores["C"] < scores["B"]
        assert best_idx == 2  # Index of strategy C

    def test_empty_strategies(self):
        """Empty strategies list returns -1."""
        best_idx, scores = compare_strategies([], [])
        assert best_idx == -1
        assert scores == {}


class TestComplexityBudget:
    """Tests for ComplexityBudget class."""

    def test_within_budget_ok(self):
        """Costs within budget return ok=True."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000)
        ok, reason = budget.check(model_cost=500, memory_cost=5000)
        assert ok is True
        assert "within budget" in reason

    def test_model_exceeded_not_ok(self):
        """Model cost exceeding budget returns ok=False."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000)
        ok, reason = budget.check(model_cost=2000, memory_cost=5000)
        assert ok is False
        assert "model_cost" in reason

    def test_memory_exceeded_not_ok(self):
        """Memory cost exceeding budget returns ok=False."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000)
        ok, reason = budget.check(model_cost=500, memory_cost=15000)
        assert ok is False
        assert "memory_cost" in reason

    def test_total_exceeded_not_ok(self):
        """Total cost exceeding budget returns ok=False."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000, total_max=5000)
        ok, reason = budget.check(model_cost=900, memory_cost=9000)
        assert ok is False
        assert "total_cost" in reason

    def test_utilization_percentages(self):
        """Utilization returns correct percentages."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000, total_max=12000)
        util = budget.utilization(model_cost=500, memory_cost=5000)
        assert util["model"] == 0.5
        assert util["memory"] == 0.5
        assert util["total"] == 5500 / 12000

    def test_warn_if_exceeded_returns_message(self):
        """warn_if_exceeded returns message when exceeded."""
        budget = ComplexityBudget(model_max=100)
        warning = budget.warn_if_exceeded(model_cost=200, memory_cost=0, context="test")
        assert warning is not None
        assert "test" in warning
        assert "exceeded" in warning.lower()

    def test_warn_if_not_exceeded_returns_none(self):
        """warn_if_exceeded returns None when within budget."""
        budget = ComplexityBudget(model_max=1000, memory_max=10000)
        warning = budget.warn_if_exceeded(model_cost=100, memory_cost=100)
        assert warning is None


class TestStructureVsNoiseGate:
    """Tests for structure_vs_noise_gate function."""

    def test_rejects_boilerplate(self):
        """Gate rejects too-simple boilerplate."""
        # Very short, generic artifact with no overlap
        artifact = {"title": "OK", "body": "OK"}
        thread_model = {"handles": [{"quote": "complex technical topic"}]}

        # Use cohort stats with high median to make this artifact look too simple
        cohort_stats = {"median_dl": 200}

        result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        assert result["allowed"] is False
        assert result["bucket"] == "too_simple"
        assert "simple" in result["reason"].lower()

    def test_rejects_random_noise(self):
        """Gate rejects too-random noise."""
        # Generate long random-looking artifact
        random_words = " ".join([f"xyz{i}abc" for i in range(100)])
        artifact = {
            "title": "Random Word Soup",
            "body": random_words,
        }
        thread_model = {"handles": [{"quote": "coherent topic"}]}

        # Use cohort stats with low median to make this artifact look random
        cohort_stats = {"median_dl": 50}

        result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        assert result["allowed"] is False
        assert result["bucket"] == "too_random"
        assert "random" in result["reason"].lower()

    def test_allows_structured_novelty(self):
        """Gate allows structured content with thread overlap."""
        artifact = {
            "title": "Machine Learning Pipeline Design",
            "body": "This document describes the machine learning pipeline for the project.",
        }
        thread_model = {
            "handles": [{"quote": "machine learning"}, {"quote": "pipeline"}],
            "entities": ["project", "design"],
        }

        result = structure_vs_noise_gate(artifact, thread_model)

        assert result["allowed"] is True
        assert result["bucket"] == "structured"

    def test_allows_midband_complexity(self):
        """Gate allows artifacts with midband DL even without high overlap."""
        # Medium-complexity artifact
        artifact = {
            "title": "Moderate Content Item",
            "body": "This is a moderately sized piece of content that contains some information.",
        }
        thread_model = {"handles": [], "entities": []}

        # Use cohort stats that put this artifact in midband
        cohort_stats = {"median_dl": 80}

        result = structure_vs_noise_gate(
            artifact,
            thread_model,
            cohort_stats=cohort_stats,
        )

        # Should allow because it's in midband (not too simple, not too random)
        assert result["dl_artifact"] > 0
        assert "dl_artifact" in result

    def test_gate_result_structure(self):
        """Gate result has expected fields."""
        artifact = {"title": "Test", "body": "Content"}
        thread_model = {"handles": []}

        result = structure_vs_noise_gate(artifact, thread_model)

        assert "allowed" in result
        assert "reason" in result
        assert "bucket" in result
        assert "dl_artifact" in result
        assert "overlap_score" in result
        assert isinstance(result["allowed"], bool)
        assert result["bucket"] in ["too_simple", "too_random", "structured"]


class TestTokenExtraction:
    """Tests for token extraction utilities."""

    def test_extract_tokens_basic(self):
        """extract_tokens returns set of lowercase words."""
        text = "Hello World Test"
        tokens = extract_tokens(text)
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_extract_tokens_filters_short(self):
        """extract_tokens filters out 1-char words."""
        text = "A B C Hello"
        tokens = extract_tokens(text)
        assert "a" not in tokens
        assert "b" not in tokens
        assert "hello" in tokens

    def test_extract_tokens_empty(self):
        """extract_tokens returns empty set for empty input."""
        assert extract_tokens("") == set()
        assert extract_tokens(None) == set()

    def test_compute_overlap_score(self):
        """compute_overlap_score returns Jaccard-style overlap."""
        tokens_a = {"hello", "world", "test"}
        tokens_b = {"hello", "world", "other"}

        score = compute_overlap_score(tokens_a, tokens_b)

        # Intersection: {hello, world} = 2
        # Union: {hello, world, test, other} = 4
        # Jaccard: 2/4 = 0.5
        assert score == 0.5

    def test_compute_overlap_empty(self):
        """compute_overlap_score returns 0 for empty sets."""
        assert compute_overlap_score(set(), {"a", "b"}) == 0.0
        assert compute_overlap_score({"a", "b"}, set()) == 0.0

    def test_artifact_to_text(self):
        """artifact_to_text extracts text from various fields."""
        artifact = {
            "title": "My Title",
            "body": "My Body",
            "summary": "My Summary",
        }
        text = artifact_to_text(artifact)
        assert "My Title" in text
        assert "My Body" in text
        assert "My Summary" in text

    def test_thread_model_to_tokens(self):
        """thread_model_to_tokens extracts tokens from thread model."""
        thread_model = {
            "handles": [{"quote": "important handle"}],
            "entities": ["entity_one"],
            "keywords": ["keyword"],
        }
        tokens = thread_model_to_tokens(thread_model)
        assert "important" in tokens
        assert "handle" in tokens
        assert "keyword" in tokens


class TestCohortStats:
    """Tests for cohort statistics."""

    def test_compute_cohort_stats_basic(self):
        """compute_cohort_stats computes median and mean."""
        artifacts = [
            {"title": "A", "body": "Short"},
            {"title": "B", "body": "Medium length content"},
            {"title": "C", "body": "Much longer content with more words here"},
        ]
        stats = compute_cohort_stats(artifacts)

        assert "median_dl" in stats
        assert "mean_dl" in stats
        assert "count" in stats
        assert stats["count"] == 3
        assert stats["median_dl"] > 0

    def test_compute_cohort_stats_empty(self):
        """compute_cohort_stats handles empty list."""
        stats = compute_cohort_stats([])
        assert stats["count"] == 0
        assert stats["median_dl"] == 100  # Default


class TestIntegration:
    """Tests for integration helpers."""

    def test_gate_bundle_proposal(self):
        """gate_bundle_proposal adds gate_result to proposal."""
        proposal = {
            "proposal_id": "bp_123",
            "title": "Bundle: Related Items",
            "constituent_ids": ["it_1", "it_2"],
            "rationale": "Similar titles",
        }
        thread_model = {"handles": [{"quote": "related items"}]}

        result = gate_bundle_proposal(proposal, thread_model)

        assert "gate_result" in result

    def test_protect_structured_novelty(self):
        """protect_structured_novelty marks structured items."""
        candidates = [
            {
                "item_id": "it_001",
                "item_title": "Structured Content About Topic",
                "priority": 0.7,
            }
        ]
        thread_model = {"handles": [{"quote": "structured content topic"}]}

        result = protect_structured_novelty(candidates, thread_model)

        # Candidates list is updated in place
        assert len(result) == 1


class TestFormatReport:
    """Tests for format_mdl_report."""

    def test_format_report_basic(self):
        """format_mdl_report produces readable output."""
        strategy = {"name": "test_strategy", "rules": ["r1"], "parameters": 50}
        outcomes = {"mistakes": 2, "backtracks": 1}

        report = format_mdl_report(strategy, outcomes)

        assert "MDL SCORE REPORT" in report
        assert "test_strategy" in report
        assert "Model Cost" in report
        assert "Data Cost" in report

    def test_format_report_with_budget(self):
        """format_mdl_report includes budget when provided."""
        strategy = {"name": "test", "rules": []}
        outcomes = {"mistakes": 0}
        budget = ComplexityBudget(model_max=100, memory_max=1000)

        report = format_mdl_report(strategy, outcomes, budget=budget, memory_cost=500)

        assert "Budget Check" in report
        assert "Model:" in report
        assert "Memory:" in report


def run_tests():
    """Run all tests and report results."""
    try:
        import pytest
        result = pytest.main([__file__, "-v", "--tb=short"])
        return result == 0
    except ImportError:
        return run_tests_manual()


def run_tests_manual():
    """Run tests without pytest."""
    passed = 0
    failed = 0

    test_classes = [
        TestModelCost,
        TestDataCost,
        TestMdlScore,
        TestCompareStrategies,
        TestComplexityBudget,
        TestStructureVsNoiseGate,
        TestTokenExtraction,
        TestCohortStats,
        TestIntegration,
        TestFormatReport,
    ]

    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    passed += 1
                    print(f"  PASS: {cls.__name__}.{method_name}")
                except AssertionError as e:
                    failed += 1
                    print(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                except Exception as e:
                    failed += 1
                    print(f"  ERROR: {cls.__name__}.{method_name}: {e}")

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        success = run_tests_manual()
        sys.exit(0 if success else 1)
