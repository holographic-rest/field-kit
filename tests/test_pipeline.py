#!/usr/bin/env python3
"""
Field-Kit v0.1 Pipeline Tests (Sprint S08)

Tests for Microbatcher, batch_dispatch, and pipeline utilities.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.pipeline import (
    Microbatcher,
    BatchedRequest,
    batch_dispatch,
    batch_dispatch_with_index,
    measure_batch_dispatch,
    BatchMetrics,
    format_metrics_report,
    PipelineStage,
    STAGES,
)


class TestMicrobatcher:
    """Tests for Microbatcher class."""

    def test_add_returns_request_id(self):
        """Test that add() returns incrementing request IDs."""
        batcher = Microbatcher(batch_size=5)
        id1 = batcher.add("request_1")
        id2 = batcher.add("request_2")
        id3 = batcher.add("request_3")

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

    def test_flush_when_batch_size_reached(self):
        """Test that flush_if_ready returns batch when batch_size reached."""
        batcher = Microbatcher(batch_size=3, timeout_ms=1000)

        batcher.add("a")
        batcher.add("b")
        assert batcher.flush_if_ready() is None  # Not yet full

        batcher.add("c")
        batch = batcher.flush_if_ready()

        assert batch is not None
        assert len(batch) == 3
        assert [b.data for b in batch] == ["a", "b", "c"]

    def test_flush_when_timeout_exceeded(self):
        """Test that flush_if_ready returns batch when timeout exceeded."""
        batcher = Microbatcher(batch_size=10, timeout_ms=10)

        batcher.add("a")
        batcher.add("b")

        # Simulate time passing
        future_ms = time.time() * 1000 + 50  # 50ms in future
        batch = batcher.flush_if_ready(now_ms=future_ms)

        assert batch is not None
        assert len(batch) == 2

    def test_flush_if_ready_returns_none_when_empty(self):
        """Test that flush_if_ready returns None when queue is empty."""
        batcher = Microbatcher(batch_size=5)
        assert batcher.flush_if_ready() is None

    def test_force_flush_returns_all(self):
        """Test that force_flush returns all pending requests."""
        batcher = Microbatcher(batch_size=100, timeout_ms=10000)

        batcher.add("a")
        batcher.add("b")
        batcher.add("c")

        batch = batcher.force_flush()

        assert len(batch) == 3
        assert batcher.is_empty()

    def test_force_flush_empty_queue(self):
        """Test force_flush on empty queue returns empty list."""
        batcher = Microbatcher(batch_size=5)
        batch = batcher.force_flush()
        assert batch == []

    def test_pending_count(self):
        """Test pending_count returns correct count."""
        batcher = Microbatcher(batch_size=10)

        assert batcher.pending_count() == 0

        batcher.add("a")
        assert batcher.pending_count() == 1

        batcher.add("b")
        batcher.add("c")
        assert batcher.pending_count() == 3

        batcher.force_flush()
        assert batcher.pending_count() == 0

    def test_is_empty(self):
        """Test is_empty returns correct state."""
        batcher = Microbatcher(batch_size=5)

        assert batcher.is_empty()

        batcher.add("a")
        assert not batcher.is_empty()

        batcher.force_flush()
        assert batcher.is_empty()

    def test_batched_request_contains_metadata(self):
        """Test that BatchedRequest contains correct metadata."""
        batcher = Microbatcher(batch_size=2)

        before = time.time() * 1000
        batcher.add({"key": "value"})
        after = time.time() * 1000

        batch = batcher.flush_if_ready()
        assert batch is None  # Not full yet

        batcher.add("second")
        batch = batcher.flush_if_ready()

        assert batch is not None
        req = batch[0]
        assert isinstance(req, BatchedRequest)
        assert req.request_id == 1
        assert req.data == {"key": "value"}
        assert before <= req.added_at_ms <= after + 1000  # Allow some slack

    def test_multiple_batches(self):
        """Test multiple batch flushes work correctly."""
        batcher = Microbatcher(batch_size=2, timeout_ms=10000)

        # First batch
        batcher.add("a")
        batcher.add("b")
        batch1 = batcher.flush_if_ready()
        assert len(batch1) == 2

        # Second batch
        batcher.add("c")
        batcher.add("d")
        batch2 = batcher.flush_if_ready()
        assert len(batch2) == 2

        assert [b.data for b in batch1] == ["a", "b"]
        assert [b.data for b in batch2] == ["c", "d"]

    def test_partial_flush_resets_timer(self):
        """Test that partial flush updates first_add_time correctly."""
        batcher = Microbatcher(batch_size=2, timeout_ms=50)

        batcher.add("a")
        batcher.add("b")
        batcher.add("c")  # This one stays

        batch = batcher.flush_if_ready()
        assert len(batch) == 2
        assert batcher.pending_count() == 1

        # Timer should be reset to "c"'s add time
        assert batcher._first_add_time is not None


class TestBatchDispatch:
    """Tests for batch_dispatch function."""

    def test_basic_dispatch(self):
        """Test basic batch dispatch works."""
        def process(batch):
            return [x * 2 for x in batch]

        requests = [1, 2, 3, 4, 5]
        results = batch_dispatch(process, requests, batch_size=2)

        assert results == [2, 4, 6, 8, 10]

    def test_empty_requests(self):
        """Test batch_dispatch with empty requests."""
        def process(batch):
            return batch

        results = batch_dispatch(process, [], batch_size=5)
        assert results == []

    def test_single_request(self):
        """Test batch_dispatch with single request."""
        def process(batch):
            return [f"processed_{x}" for x in batch]

        results = batch_dispatch(process, ["only_one"], batch_size=5)
        assert results == ["processed_only_one"]

    def test_exact_batch_size(self):
        """Test when requests exactly match batch_size."""
        call_count = [0]

        def process(batch):
            call_count[0] += 1
            return batch

        requests = [1, 2, 3, 4]
        results = batch_dispatch(process, requests, batch_size=4)

        assert results == [1, 2, 3, 4]
        assert call_count[0] == 1  # Only one batch

    def test_multiple_batches(self):
        """Test that multiple batches are processed."""
        batches_seen = []

        def process(batch):
            batches_seen.append(list(batch))
            return batch

        requests = [1, 2, 3, 4, 5, 6, 7]
        results = batch_dispatch(process, requests, batch_size=3)

        assert results == [1, 2, 3, 4, 5, 6, 7]
        assert batches_seen == [[1, 2, 3], [4, 5, 6], [7]]

    def test_preserves_order(self):
        """Test that batch_dispatch preserves request order."""
        def process(batch):
            # Reverse within batch to test order preservation
            return list(reversed(batch))

        requests = ["a", "b", "c", "d"]
        results = batch_dispatch(process, requests, batch_size=2)

        # Each batch reversed: [b, a] + [d, c]
        assert results == ["b", "a", "d", "c"]

    def test_identity_when_batch_size_larger_than_requests(self):
        """Test identity behavior when batch_size > len(requests)."""
        def process(batch):
            return batch

        requests = [1, 2, 3]
        results = batch_dispatch(process, requests, batch_size=100)

        assert results == [1, 2, 3]


class TestBatchDispatchWithIndex:
    """Tests for batch_dispatch_with_index function."""

    def test_returns_indexed_results(self):
        """Test that results include original indices."""
        def process(batch):
            return [x.upper() for x in batch]

        requests = ["a", "b", "c"]
        results = batch_dispatch_with_index(process, requests, batch_size=2)

        assert results == [(0, "A"), (1, "B"), (2, "C")]

    def test_empty_requests(self):
        """Test with empty requests."""
        def process(batch):
            return batch

        results = batch_dispatch_with_index(process, [], batch_size=5)
        assert results == []


class TestMeasureBatchDispatch:
    """Tests for measure_batch_dispatch function."""

    def test_returns_results_and_metrics(self):
        """Test that measure_batch_dispatch returns tuple."""
        def process(batch):
            return [x + 1 for x in batch]

        results, metrics = measure_batch_dispatch(
            process, [1, 2, 3, 4], batch_size=2
        )

        assert results == [2, 3, 4, 5]
        assert isinstance(metrics, BatchMetrics)

    def test_metrics_values(self):
        """Test that metrics contain expected values."""
        def process(batch):
            return batch

        results, metrics = measure_batch_dispatch(
            process, [1, 2, 3, 4, 5], batch_size=2
        )

        assert metrics.total_requests == 5
        assert metrics.batches_dispatched == 3  # [1,2], [3,4], [5]
        assert metrics.avg_batch_size == 5 / 3
        assert metrics.total_time_ms >= 0
        assert metrics.throughput_per_sec > 0

    def test_empty_requests_metrics(self):
        """Test metrics for empty requests."""
        def process(batch):
            return batch

        results, metrics = measure_batch_dispatch(process, [], batch_size=5)

        assert results == []
        assert metrics.total_requests == 0
        assert metrics.batches_dispatched == 0
        assert metrics.throughput_per_sec == 0.0


class TestBatchMetrics:
    """Tests for BatchMetrics class."""

    def test_to_dict(self):
        """Test BatchMetrics.to_dict()."""
        metrics = BatchMetrics(
            total_requests=10,
            batches_dispatched=3,
            avg_batch_size=3.33,
            total_time_ms=100.0,
            avg_latency_per_request_ms=10.0,
            throughput_per_sec=100.0,
        )

        d = metrics.to_dict()

        assert d["total_requests"] == 10
        assert d["batches_dispatched"] == 3
        assert d["throughput_per_sec"] == 100.0


class TestFormatMetricsReport:
    """Tests for format_metrics_report function."""

    def test_produces_readable_output(self):
        """Test that format_metrics_report produces readable output."""
        metrics = BatchMetrics(
            total_requests=10,
            batches_dispatched=3,
            avg_batch_size=3.33,
            total_time_ms=100.0,
            avg_latency_per_request_ms=10.0,
            throughput_per_sec=100.0,
        )

        report = format_metrics_report(metrics)

        assert "BATCH DISPATCH METRICS" in report
        assert "Total Requests" in report
        assert "10" in report
        assert "100.0" in report or "100.00" in report


class TestPipelineStage:
    """Tests for PipelineStage class."""

    def test_default_process_is_identity(self):
        """Test that default process() is identity function."""
        stage = PipelineStage(name="test_stage")
        inputs = [{"a": 1}, {"b": 2}]
        outputs = stage.process(inputs)
        assert outputs == inputs

    def test_stage_attributes(self):
        """Test PipelineStage attributes."""
        stage = PipelineStage(
            name="custom",
            enabled=False,
            batch_size=8,
            timeout_ms=100,
        )

        assert stage.name == "custom"
        assert stage.enabled is False
        assert stage.batch_size == 8
        assert stage.timeout_ms == 100


class TestStagesConstant:
    """Tests for STAGES constant."""

    def test_stages_defined(self):
        """Test that pipeline stages are defined."""
        assert len(STAGES) == 4
        assert "candidate_generation" in STAGES
        assert "candidate_scoring" in STAGES
        assert "response_assembly" in STAGES
        assert "writeback" in STAGES


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
        TestMicrobatcher,
        TestBatchDispatch,
        TestBatchDispatchWithIndex,
        TestMeasureBatchDispatch,
        TestBatchMetrics,
        TestFormatMetricsReport,
        TestPipelineStage,
        TestStagesConstant,
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
