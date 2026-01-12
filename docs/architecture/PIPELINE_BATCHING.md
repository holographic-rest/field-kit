# Pipeline & Batching Architecture

> **Sprint S08 — December 2024**

This document describes the pipeline and batching infrastructure implemented in Sprint S08, inspired by GPipe microbatching and Deep Speech 2's Batch Dispatch pattern.

---

## Overview

Field-Kit now includes a batching layer that can process multiple requests together for improved throughput. The design prioritizes:

1. **Identity-safe**: If batching disabled, behavior is identical to serial processing
2. **Synchronous**: No background threads or async queues (single-process)
3. **Deterministic**: Fixed batch sizes produce predictable batches
4. **Zero dependencies**: Uses only Python stdlib

---

## Research Foundation

### GPipe (Essay #10)
- Microbatching splits work into small batches for pipeline overlap
- Key insight: smaller batches enable pipelining without large memory overhead
- We adopt microbatch collection with size + timeout triggers

### Deep Speech 2 (Essay #22)
- Batch Dispatch pattern for low-latency serving
- Collect requests until batch_size reached or timeout exceeded
- Process batch, then return results to individual callers
- Achieves throughput while bounding latency

---

## Components

### Microbatcher (`src/fieldkit/pipeline.py`)

Collects requests into batches for efficient processing.

```python
from fieldkit.pipeline import Microbatcher

batcher = Microbatcher(batch_size=5, timeout_ms=50)

# Add requests
batcher.add(request1)
batcher.add(request2)

# Check if ready to flush
batch = batcher.flush_if_ready()
if batch:
    results = process_batch(batch)

# Force flush remaining
remaining = batcher.force_flush()
```

**Flush triggers:**
- `batch_size` requests collected
- `timeout_ms` elapsed since first request

### batch_dispatch

Convenience wrapper for batched function execution:

```python
from fieldkit.pipeline import batch_dispatch

def process_batch(requests):
    return [process(r) for r in requests]

# Dispatch 100 requests in batches of 10
results = batch_dispatch(process_batch, requests, batch_size=10)
```

Results are returned in the same order as input requests.

### measure_batch_dispatch

Same as batch_dispatch but also returns metrics:

```python
from fieldkit.pipeline import measure_batch_dispatch, format_metrics_report

results, metrics = measure_batch_dispatch(fn, requests, batch_size=5)
print(format_metrics_report(metrics))
```

Metrics include:
- `total_requests`: Number of requests processed
- `batches_dispatched`: Number of batches sent
- `avg_batch_size`: Average requests per batch
- `total_time_ms`: Total processing time
- `avg_latency_per_request_ms`: Average latency per request
- `throughput_per_sec`: Requests processed per second

---

## Pipeline Stages (Interfaces)

S08 defines pipeline stage interfaces for future extension:

```
candidate_generation  →  candidate_scoring  →  response_assembly  →  writeback
```

Currently these are interface-only; actual processing remains in existing modules. Future sprints may implement full stage-based pipelines.

---

## Integration: batch_suggest

The hololink pipeline now exposes batched suggestion:

```python
from fieldkit.hololink_pipeline import batch_suggest, batch_suggest_with_metrics

# Process multiple hololink requests in batches
requests = [
    {"item_a": item1, "item_b": item2},
    {"item_a": item3, "item_b": item4},
    # ...
]

results = batch_suggest(requests, batch_size=5)

# Or with metrics
results, metrics = batch_suggest_with_metrics(requests, batch_size=5)
```

---

## Benchmarks

Run the benchmark script to compare serial vs batched:

```bash
python3 tests/benchmark_throughput.py --data-dir prototype/data_dogfood --n 20
```

Example output:
```
================================================================================
THROUGHPUT BENCHMARK RESULTS
================================================================================

Mode                                  Requests     Total ms     Avg ms    Req/sec
--------------------------------------------------------------------------------
serial                                      20        16.40       0.82     1219.2
batched (batch_size=3)                      20        15.58       0.78     1283.9
batched (batch_size=5)                      20        14.41       0.72     1387.8
batched (batch_size=10)                     20        14.52       0.73     1377.6
================================================================================
```

**Analysis**: In local fast scenarios, batching provides ~5-12% improvement. When processing involves I/O or LLM calls, batching provides more substantial benefits.

---

## Design Decisions

### Why synchronous?
- Simpler to reason about and debug
- No race conditions or thread safety concerns
- Identity-safe: same behavior whether batching enabled or not
- Sufficient for current throughput requirements

### Why not async queues?
- Sprint requirement: "Do NOT implement multi-threaded queues unless absolutely necessary"
- Async adds complexity without proportional benefit for current use cases
- Can extend to async in future if needed

### Batch size selection
- Too small: Overhead exceeds benefit
- Too large: Latency increases for waiting requests
- Default of 4-5 works well for most scenarios
- Benchmark with actual workload to tune

---

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/pipeline.py` | Microbatcher, batch_dispatch, metrics |
| `src/fieldkit/hololink_pipeline.py` | batch_suggest integration |
| `tests/test_pipeline.py` | Unit tests (28 tests) |
| `tests/benchmark_throughput.py` | Throughput benchmark script |

---

## Future Work

1. **Full pipeline stages**: Implement actual stage processing with queues between stages
2. **Async support**: Add asyncio-based batching for I/O-heavy workloads
3. **Dynamic batch sizing**: Adjust batch size based on load and latency targets
4. **Pipeline visualization**: Show batch flow through stages

---

## See Also

- [POINTER_NAVIGATION.md](POINTER_NAVIGATION.md) — Pointer-based navigation (uses batching)
- [SESSION_STATE.md](SESSION_STATE.md) — Session continuity
- Research essays: GPipe (#10), Deep Speech 2 (#22)
