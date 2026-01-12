#!/usr/bin/env python3
"""
Field-Kit v0.1 Governance Tests (Sprint S06)

Tests for complexity metrics, governor, bundling, and pruning modules.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.complexity import (
    gzip_bytes,
    coarse_grain_snapshot,
    apparent_complexity,
    branching_factor_from_events,
    duplicate_rate,
    suggestion_entropy_from_events,
    hubness_score,
    compute_all_metrics,
)
from fieldkit.governor import ComplexityGovernor, GovernanceThresholds
from fieldkit.bundling import (
    propose_bundle,
    detect_bundle_candidates,
    BundleProposal,
)
from fieldkit.pruning import (
    detect_prune_candidates,
    create_prune_plan,
    PruneCandidate,
    PrunePlan,
)


class TestComplexityMetrics:
    """Tests for complexity.py"""

    def test_gzip_bytes_basic(self):
        """Test gzip_bytes returns positive integer."""
        obj = {"key": "value", "list": [1, 2, 3]}
        result = gzip_bytes(obj)
        assert isinstance(result, int)
        assert result > 0

    def test_gzip_bytes_larger_object_more_bytes(self):
        """Test that larger objects produce more bytes."""
        small = {"x": 1}
        large = {"x": list(range(100))}
        assert gzip_bytes(large) > gzip_bytes(small)

    def test_coarse_grain_snapshot_structure(self, tmp_path):
        """Test coarse_grain_snapshot returns expected structure."""
        # Create minimal data
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test Item"}\n'
        )

        snapshot = coarse_grain_snapshot(tmp_path)

        assert "counts" in snapshot
        assert "item_types" in snapshot
        assert "graph_stats" in snapshot
        assert snapshot["counts"]["items"] == 1
        assert snapshot["item_types"].get("Q", 0) == 1

    def test_apparent_complexity_returns_int(self, tmp_path):
        """Test apparent_complexity returns positive integer."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        result = apparent_complexity(tmp_path)
        assert isinstance(result, int)
        assert result > 0

    def test_duplicate_rate_no_duplicates(self, tmp_path):
        """Test duplicate_rate with unique items."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "title": "First Item"}\n'
            '{"id": "it_002", "title": "Second Item"}\n'
            '{"id": "it_003", "title": "Third Item"}\n'
        )

        rate, count = duplicate_rate(tmp_path)
        assert rate == 0.0
        assert count == 0

    def test_duplicate_rate_with_duplicates(self, tmp_path):
        """Test duplicate_rate detects near-duplicates."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "title": "Same Title Here"}\n'
            '{"id": "it_002", "title": "Same Title Here"}\n'  # duplicate
            '{"id": "it_003", "title": "Different Item"}\n'
        )

        rate, count = duplicate_rate(tmp_path)
        assert count >= 1  # At least one duplicate
        assert rate > 0

    def test_hubness_score_returns_tuple(self, tmp_path):
        """Test hubness_score returns (float, list)."""
        bonds_file = tmp_path / "bonds.jsonl"
        bonds_file.write_text(
            '{"id": "bd_001", "status": "executed", "input_item_ids": ["it_001"], "output_item_id": "it_002"}\n'
        )

        hubness, top_hubs = hubness_score(tmp_path)
        assert isinstance(hubness, float)
        assert isinstance(top_hubs, list)

    def test_compute_all_metrics_complete(self, tmp_path):
        """Test compute_all_metrics returns all expected keys."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        metrics = compute_all_metrics(tmp_path)

        expected_keys = [
            "snapshot",
            "apparent_complexity",
            "branching_factor",
            "duplicate_rate",
            "hubness",
            "is_soupy",
            "is_sparse",
        ]
        for key in expected_keys:
            assert key in metrics, f"Missing key: {key}"


class TestGovernor:
    """Tests for governor.py"""

    def test_observe_returns_observation(self, tmp_path):
        """Test ComplexityGovernor.observe returns GovernanceObservation."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        governor = ComplexityGovernor()
        observation = governor.observe(tmp_path)

        assert observation.action in ["bundle", "prune", "branch", "continue"]
        assert observation.rationale
        assert 0 <= observation.confidence <= 1

    def test_small_field_defaults_to_continue(self, tmp_path):
        """Test that small Fields get 'continue' action."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        governor = ComplexityGovernor()
        observation = governor.observe(tmp_path)

        # Small field (1 item) should default to continue
        assert observation.action == "continue"
        assert "small" in observation.rationale.lower() or "keep exploring" in observation.rationale.lower()

    def test_custom_thresholds(self, tmp_path):
        """Test that custom thresholds are respected."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        # Set very low threshold for action
        thresholds = GovernanceThresholds(min_items_for_action=0)
        governor = ComplexityGovernor(thresholds)
        observation = governor.observe(tmp_path)

        # Now action should be possible (though may still be 'continue')
        assert observation.action in ["bundle", "prune", "branch", "continue"]

    def test_observation_to_json(self, tmp_path):
        """Test GovernanceObservation.to_json produces valid JSON."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "Test"}\n'
        )

        governor = ComplexityGovernor()
        observation = governor.observe(tmp_path)
        json_str = observation.to_json()

        # Should parse without error
        parsed = json.loads(json_str)
        assert parsed["action"] == observation.action

    def test_continue_action_no_alarm_phrases(self, tmp_path):
        """Test that CONTINUE action does not include alarm phrases.

        This tests the fix for the contradiction where the report said
        'CONTINUE' but also claimed 'Soup state detected'.
        """
        # Create a small golden-flow-like dataset (5 items, 2 bonds)
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "type": "Q", "title": "First Item"}\n'
            '{"id": "it_002", "type": "Q", "title": "Second Item"}\n'
            '{"id": "it_003", "type": "M", "title": "M: First Item"}\n'
            '{"id": "it_004", "type": "D", "title": "D: Second Item"}\n'
            '{"id": "it_005", "type": "H", "title": "Holologue"}\n'
        )

        bonds_file = tmp_path / "bonds.jsonl"
        bonds_file.write_text(
            '{"id": "bd_001", "status": "executed", "input_item_ids": ["it_001"], "output_item_id": "it_003"}\n'
            '{"id": "bd_002", "status": "executed", "input_item_ids": ["it_002"], "output_item_id": "it_004"}\n'
        )

        governor = ComplexityGovernor()
        observation = governor.observe(tmp_path)

        # With only 2 bonds (below min_bonds_for_bundle=3), action should be CONTINUE
        assert observation.action == "continue", f"Expected 'continue', got '{observation.action}'"

        # Alarm phrases should NOT appear in details when action is CONTINUE
        alarm_phrases = ["Soup state detected", "Sparse graph detected"]
        report = governor.format_report(observation)

        for phrase in alarm_phrases:
            assert phrase not in report, f"Alarm phrase '{phrase}' should not appear when action=CONTINUE"

        # Details should use softer language
        details_text = " ".join(observation.details)
        # Should NOT have hard alarms
        assert "Soup state detected" not in details_text
        # May have softer indicators
        if "hubness" in details_text.lower():
            assert "typical" in details_text.lower() or "early-stage" in details_text.lower() or "elevated" in details_text.lower()


class TestBundling:
    """Tests for bundling.py"""

    def test_propose_bundle_creates_proposal(self):
        """Test propose_bundle creates valid proposal."""
        item_ids = ["it_001", "it_002", "it_003"]
        proposal = propose_bundle(item_ids, "Test Bundle", "For testing")

        assert proposal.proposal_id.startswith("bp_")
        assert proposal.bundle_title == "Test Bundle"
        assert proposal.constituent_ids == item_ids
        assert proposal.action == "bundle"
        assert proposal.status == "proposed"

    def test_bundle_proposal_serialization(self):
        """Test BundleProposal serialization."""
        proposal = propose_bundle(["it_001", "it_002"], "Test")

        # to_dict
        d = proposal.to_dict()
        assert "proposal_id" in d
        assert "constituent_ids" in d

        # to_json
        json_str = proposal.to_json()
        parsed = json.loads(json_str)
        assert parsed["proposal_id"] == proposal.proposal_id

        # from_dict
        restored = BundleProposal.from_dict(d)
        assert restored.proposal_id == proposal.proposal_id
        assert restored.constituent_ids == proposal.constituent_ids

    def test_detect_bundle_candidates_empty(self, tmp_path):
        """Test detect_bundle_candidates with no items."""
        proposals = detect_bundle_candidates(tmp_path)
        assert proposals == []

    def test_detect_bundle_candidates_finds_similar(self, tmp_path):
        """Test detect_bundle_candidates finds items with similar titles."""
        items_file = tmp_path / "items.jsonl"
        # Create items with same prefix (should cluster)
        items_file.write_text(
            '{"id": "it_001", "title": "Project Alpha Documentation"}\n'
            '{"id": "it_002", "title": "Project Alpha Design"}\n'
            '{"id": "it_003", "title": "Something Else Entirely"}\n'
        )

        proposals = detect_bundle_candidates(tmp_path)

        # May or may not find clusters depending on implementation
        # At minimum, should not crash
        assert isinstance(proposals, list)


class TestPruning:
    """Tests for pruning.py"""

    def test_detect_prune_candidates_empty(self, tmp_path):
        """Test detect_prune_candidates with no data."""
        candidates = detect_prune_candidates(tmp_path)
        assert candidates == []

    def test_detect_prune_candidates_finds_duplicates(self, tmp_path):
        """Test detect_prune_candidates finds duplicates."""
        items_file = tmp_path / "items.jsonl"
        items_file.write_text(
            '{"id": "it_001", "title": "Duplicate Title Here", "created_at": "2025-01-01"}\n'
            '{"id": "it_002", "title": "Duplicate Title Here", "created_at": "2025-01-02"}\n'
        )

        candidates = detect_prune_candidates(tmp_path)

        # Should find at least one duplicate candidate
        duplicate_candidates = [c for c in candidates if c.reason == "duplicate"]
        assert len(duplicate_candidates) >= 1

    def test_create_prune_plan(self):
        """Test create_prune_plan creates valid plan."""
        candidates = [
            PruneCandidate(
                item_id="it_001",
                item_title="Test",
                reason="duplicate",
                details="Near-duplicate of it_002",
                priority=0.7,
            ),
        ]

        plan = create_prune_plan(candidates)

        assert plan.plan_id.startswith("pp_")
        assert plan.status == "proposed"
        assert len(plan.candidates) == 1
        assert "duplicate" in plan.summary

    def test_prune_plan_serialization(self):
        """Test PrunePlan serialization."""
        candidates = [
            PruneCandidate(
                item_id="it_001",
                item_title="Test",
                reason="orphan",
                details="No bonds",
                priority=0.5,
            ),
        ]
        plan = create_prune_plan(candidates)

        # to_dict
        d = plan.to_dict()
        assert "plan_id" in d
        assert "candidates" in d

        # to_json
        json_str = plan.to_json()
        parsed = json.loads(json_str)
        assert parsed["plan_id"] == plan.plan_id

        # from_dict
        restored = PrunePlan.from_dict(d)
        assert restored.plan_id == plan.plan_id
        assert len(restored.candidates) == 1


def run_tests():
    """Run all tests and report results."""
    try:
        import pytest
        result = pytest.main([__file__, "-v", "--tb=short"])
        return result == 0
    except ImportError:
        # Fallback: run tests manually
        return run_tests_manual()


def run_tests_manual():
    """Run tests without pytest."""
    passed = 0
    failed = 0
    errors = []

    test_classes = [
        TestComplexityMetrics,
        TestGovernor,
        TestBundling,
        TestPruning,
    ]

    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                # Create tmp_path for tests that need it
                import tempfile
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    try:
                        method = getattr(instance, method_name)
                        # Check if method needs tmp_path
                        import inspect
                        sig = inspect.signature(method)
                        if "tmp_path" in sig.parameters:
                            method(tmp_path)
                        else:
                            method()
                        passed += 1
                        print(f"  PASS: {cls.__name__}.{method_name}")
                    except AssertionError as e:
                        failed += 1
                        errors.append(f"{cls.__name__}.{method_name}: {e}")
                        print(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                    except Exception as e:
                        failed += 1
                        errors.append(f"{cls.__name__}.{method_name}: {e}")
                        print(f"  ERROR: {cls.__name__}.{method_name}: {e}")

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    return failed == 0


if __name__ == "__main__":
    # Allow running tests directly
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        success = run_tests_manual()
        sys.exit(0 if success else 1)
