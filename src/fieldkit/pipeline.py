"""
Field-Kit v0.1 Pipeline & Batching (Sprint S08)

Implements GPipe-style microbatching for improved throughput.

Key concepts from research:
- GPipe (Essay #10): Microbatching splits work into small batches for pipeline overlap
- Deep Speech 2 (Essay #22): Batch Dispatch keeps latency low while improving throughput

This module provides:
- Microbatcher: Collects requests and flushes when batch_size or timeout reached
- batch_dispatch: Convenience wrapper for batched function execution
- Pipeline stage interfaces (for future extension)

Design principles:
- Synchronous and explicit (no background threads)
- Identity-safe (if batching disabled, behavior identical)
- No new dependencies
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from collections import deque


T = TypeVar('T')
R = TypeVar('R')


# === Pipeline Stages (interfaces only) ===

STAGES = [
    "candidate_generation",  # Graph + embeddings
    "candidate_scoring",     # Pointer ranking
    "response_assembly",     # Templated + citations
    "writeback",             # Events + Vault + bonds
]


@dataclass
class PipelineStage:
    """
    A pipeline stage definition.

    For now, stages are just names with optional configuration.
    Future: add queues and workers.
    """
    name: str
    enabled: bool = True
    batch_size: int = 4
    timeout_ms: int = 50

    def process(self, inputs: List[Any]) -> List[Any]:
        """
        Process a batch of inputs.

        Override in subclasses for real processing.
        Default: identity function.
        """
        return inputs


# === Microbatcher ===

@dataclass
class BatchedRequest(Generic[T]):
    """
    A request with its batch metadata.
    """
    request_id: int
    data: T
    added_at_ms: float


class Microbatcher(Generic[T]):
    """
    Collects requests into batches for efficient processing.

    GPipe-inspired microbatching:
    - Collects requests until batch_size reached OR timeout exceeded
    - flush_if_ready() returns batch when ready
    - force_flush() returns current batch immediately

    Usage:
        batcher = Microbatcher(batch_size=5, timeout_ms=50)
        batcher.add(request1)
        batcher.add(request2)
        # ... in a loop:
        batch = batcher.flush_if_ready()
        if batch:
            results = process_batch(batch)
    """

    def __init__(self, batch_size: int = 4, timeout_ms: int = 50):
        """
        Initialize microbatcher.

        Args:
            batch_size: Maximum requests per batch
            timeout_ms: Maximum time to wait for batch_size before flushing
        """
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self._queue: deque[BatchedRequest[T]] = deque()
        self._request_counter = 0
        self._first_add_time: Optional[float] = None

    def add(self, request: T) -> int:
        """
        Add a request to the batch queue.

        Returns:
            Request ID for result correlation
        """
        now_ms = time.time() * 1000

        if self._first_add_time is None:
            self._first_add_time = now_ms

        self._request_counter += 1
        req = BatchedRequest(
            request_id=self._request_counter,
            data=request,
            added_at_ms=now_ms,
        )
        self._queue.append(req)

        return req.request_id

    def flush_if_ready(self, now_ms: Optional[float] = None) -> Optional[List[BatchedRequest[T]]]:
        """
        Return batch if batch_size reached or timeout exceeded.

        Args:
            now_ms: Current time in milliseconds (default: now)

        Returns:
            List of BatchedRequest if ready, None otherwise
        """
        if len(self._queue) == 0:
            return None

        if now_ms is None:
            now_ms = time.time() * 1000

        # Check batch size
        if len(self._queue) >= self.batch_size:
            return self._flush_batch(self.batch_size)

        # Check timeout
        if self._first_add_time is not None:
            elapsed = now_ms - self._first_add_time
            if elapsed >= self.timeout_ms:
                return self._flush_batch(len(self._queue))

        return None

    def force_flush(self) -> List[BatchedRequest[T]]:
        """
        Force flush all pending requests.

        Returns:
            List of all pending BatchedRequests
        """
        return self._flush_batch(len(self._queue))

    def _flush_batch(self, count: int) -> List[BatchedRequest[T]]:
        """
        Flush up to count items from queue.
        """
        batch = []
        for _ in range(min(count, len(self._queue))):
            batch.append(self._queue.popleft())

        # Reset timer if queue empty
        if len(self._queue) == 0:
            self._first_add_time = None
        else:
            # Update first add time to oldest remaining request
            self._first_add_time = self._queue[0].added_at_ms

        return batch

    def pending_count(self) -> int:
        """Return number of pending requests."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0


# === Batch Dispatch ===

def batch_dispatch(
    fn: Callable[[List[T]], List[R]],
    requests: List[T],
    batch_size: int = 4,
    timeout_ms: int = 50,
) -> List[R]:
    """
    Dispatch requests through a function in batches.

    Convenience wrapper that:
    1. Groups requests into microbatches
    2. Calls fn(batch) on each microbatch
    3. Returns ordered results

    Args:
        fn: Function that processes a batch and returns results
        requests: List of requests to process
        batch_size: Maximum requests per batch
        timeout_ms: Maximum time to wait (not used in sync mode)

    Returns:
        List of results in same order as requests
    """
    if not requests:
        return []

    # For synchronous dispatch, just split into batches
    results: List[R] = []

    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        batch_results = fn(batch)
        results.extend(batch_results)

    return results


def batch_dispatch_with_index(
    fn: Callable[[List[T]], List[R]],
    requests: List[T],
    batch_size: int = 4,
) -> List[tuple[int, R]]:
    """
    Dispatch requests and return (index, result) pairs.

    Useful when you need to correlate results with original requests.
    """
    if not requests:
        return []

    results: List[tuple[int, R]] = []
    idx = 0

    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        batch_results = fn(batch)
        for r in batch_results:
            results.append((idx, r))
            idx += 1

    return results


# === Pipeline Stage Functions (interfaces) ===

def stage_candidate_generation(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Stage A: Generate candidates from items.

    Interface only - actual implementation in hololink_pipeline.py
    """
    # Each request should have item_a, item_b
    # Returns list of candidate sets
    return [{"candidates": [], "request": r} for r in requests]


def stage_candidate_scoring(
    requests: List[Dict[str, Any]],
    candidates: List[List[Any]],
) -> List[Dict[str, Any]]:
    """
    Stage B: Score candidates using pointer-style ranking.

    Interface only - actual implementation in pointer_scorer.py
    """
    return [{"scored": c, "request": r} for r, c in zip(requests, candidates)]


def stage_response_assembly(
    scored: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Stage C: Assemble responses with templates and citations.

    Interface only.
    """
    return [{"response": s} for s in scored]


def stage_writeback(
    responses: List[Dict[str, Any]],
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Stage D: Write events, update Vault, create bonds.

    Interface only.
    """
    return [{"written": True, "response": r} for r in responses]


# === Metrics ===

@dataclass
class BatchMetrics:
    """
    Metrics from a batch dispatch operation.
    """
    total_requests: int
    batches_dispatched: int
    avg_batch_size: float
    total_time_ms: float
    avg_latency_per_request_ms: float
    throughput_per_sec: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "batches_dispatched": self.batches_dispatched,
            "avg_batch_size": self.avg_batch_size,
            "total_time_ms": self.total_time_ms,
            "avg_latency_per_request_ms": self.avg_latency_per_request_ms,
            "throughput_per_sec": self.throughput_per_sec,
        }


def measure_batch_dispatch(
    fn: Callable[[List[T]], List[R]],
    requests: List[T],
    batch_size: int = 4,
) -> tuple[List[R], BatchMetrics]:
    """
    Dispatch with metrics collection.

    Returns:
        Tuple of (results, metrics)
    """
    if not requests:
        return [], BatchMetrics(
            total_requests=0,
            batches_dispatched=0,
            avg_batch_size=0.0,
            total_time_ms=0.0,
            avg_latency_per_request_ms=0.0,
            throughput_per_sec=0.0,
        )

    start = time.time()

    results: List[R] = []
    batches_dispatched = 0

    for i in range(0, len(requests), batch_size):
        batch = requests[i:i + batch_size]
        batch_results = fn(batch)
        results.extend(batch_results)
        batches_dispatched += 1

    end = time.time()
    total_time_ms = (end - start) * 1000

    metrics = BatchMetrics(
        total_requests=len(requests),
        batches_dispatched=batches_dispatched,
        avg_batch_size=len(requests) / batches_dispatched if batches_dispatched > 0 else 0.0,
        total_time_ms=total_time_ms,
        avg_latency_per_request_ms=total_time_ms / len(requests) if len(requests) > 0 else 0.0,
        throughput_per_sec=len(requests) / (total_time_ms / 1000) if total_time_ms > 0 else 0.0,
    )

    return results, metrics


def format_metrics_report(metrics: BatchMetrics) -> str:
    """
    Format metrics as human-readable report.
    """
    lines = [
        "=" * 50,
        "BATCH DISPATCH METRICS",
        "=" * 50,
        f"  Total Requests:      {metrics.total_requests}",
        f"  Batches Dispatched:  {metrics.batches_dispatched}",
        f"  Avg Batch Size:      {metrics.avg_batch_size:.1f}",
        f"  Total Time:          {metrics.total_time_ms:.2f} ms",
        f"  Avg Latency/Request: {metrics.avg_latency_per_request_ms:.2f} ms",
        f"  Throughput:          {metrics.throughput_per_sec:.1f} req/sec",
        "=" * 50,
    ]
    return "\n".join(lines)
