#!/usr/bin/env python3
"""
Field-Kit v0.1 Throughput Benchmark (Sprint S08)

Benchmarks serial vs batched processing for hololink generation.

Usage:
    python3 tests/benchmark_throughput.py --data-dir prototype/data_dogfood --n 20
    python3 tests/benchmark_throughput.py --help

What this measures:
- Serial: Process N requests one at a time
- Batched: Process N requests using batch_dispatch with configurable batch size

Expected outcome:
- In local/fast scenarios, batching overhead may not help much
- When calls involve I/O or LLM, batching provides real benefit
- This establishes the baseline and infrastructure for future optimization
"""

import sys
import json
import time
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.hololink_pipeline import (
    generate_hololink_options,
    batch_suggest,
    batch_suggest_with_metrics,
)
from fieldkit.suggestion_engine import generate_bond_suggestions_with_evidence


def load_items(data_dir: Path, limit: int = 10) -> list:
    """Load items from data directory."""
    items_file = data_dir / "items.jsonl"
    items = []

    if items_file.exists():
        with open(items_file) as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
                    if len(items) >= limit:
                        break

    return items


def create_test_requests(items: list, n: int) -> list:
    """Create test requests from items."""
    requests = []

    if len(items) < 2:
        # Create synthetic items if not enough
        items = [
            {"id": "it_bench_1", "title": "Benchmark Item A", "body": "This is test content for benchmarking."},
            {"id": "it_bench_2", "title": "Benchmark Item B", "body": "Another test item for performance testing."},
        ]

    for i in range(n):
        idx_a = i % len(items)
        idx_b = (i + 1) % len(items)
        requests.append({
            "item_a": items[idx_a],
            "item_b": items[idx_b],
        })

    return requests


def benchmark_serial(requests: list) -> dict:
    """
    Benchmark serial processing (one request at a time).
    """
    start = time.time()

    results = []
    for req in requests:
        result = generate_hololink_options(req["item_a"], req["item_b"])
        results.append(result)

    end = time.time()
    total_ms = (end - start) * 1000

    return {
        "mode": "serial",
        "requests": len(requests),
        "total_ms": total_ms,
        "avg_ms": total_ms / len(requests) if requests else 0,
        "throughput": len(requests) / (total_ms / 1000) if total_ms > 0 else 0,
    }


def benchmark_batched(requests: list, batch_size: int) -> dict:
    """
    Benchmark batched processing.
    """
    start = time.time()

    results, metrics = batch_suggest_with_metrics(requests, batch_size=batch_size)

    end = time.time()
    total_ms = (end - start) * 1000

    return {
        "mode": f"batched (batch_size={batch_size})",
        "requests": len(requests),
        "batches": metrics["batches_dispatched"],
        "total_ms": total_ms,
        "avg_ms": total_ms / len(requests) if requests else 0,
        "throughput": len(requests) / (total_ms / 1000) if total_ms > 0 else 0,
    }


def benchmark_suggestion_engine_serial(items: list, n: int, data_dir: str) -> dict:
    """
    Benchmark suggestion engine in serial mode.
    """
    start = time.time()

    results = []
    for i in range(n):
        item = items[i % len(items)]
        result = generate_bond_suggestions_with_evidence(item, data_dir=data_dir)
        results.append(result)

    end = time.time()
    total_ms = (end - start) * 1000

    return {
        "mode": "suggestion_engine_serial",
        "requests": n,
        "total_ms": total_ms,
        "avg_ms": total_ms / n if n > 0 else 0,
        "throughput": n / (total_ms / 1000) if total_ms > 0 else 0,
    }


def format_results_table(results: list) -> str:
    """Format benchmark results as table."""
    lines = [
        "=" * 80,
        "THROUGHPUT BENCHMARK RESULTS",
        "=" * 80,
        "",
        f"{'Mode':<35} {'Requests':>10} {'Total ms':>12} {'Avg ms':>10} {'Req/sec':>10}",
        "-" * 80,
    ]

    for r in results:
        lines.append(
            f"{r['mode']:<35} {r['requests']:>10} {r['total_ms']:>12.2f} {r['avg_ms']:>10.2f} {r['throughput']:>10.1f}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark throughput for hololink generation"
    )
    parser.add_argument(
        "--data-dir", "-d",
        type=Path,
        default=Path("prototype/data_dogfood"),
        help="Data directory to load items from",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=20,
        help="Number of requests to benchmark",
    )
    parser.add_argument(
        "--batch-sizes",
        type=str,
        default="3,5,10",
        help="Comma-separated batch sizes to test",
    )
    parser.add_argument(
        "--include-suggestions",
        action="store_true",
        help="Also benchmark suggestion_engine",
    )

    args = parser.parse_args()

    print(f"Loading items from {args.data_dir}...")
    items = load_items(args.data_dir, limit=args.n)
    print(f"Loaded {len(items)} items")

    # Create test requests
    requests = create_test_requests(items, args.n)
    print(f"Created {len(requests)} test requests")
    print()

    results = []

    # Benchmark serial
    print("Running serial benchmark...")
    serial_result = benchmark_serial(requests)
    results.append(serial_result)

    # Benchmark batched with different batch sizes
    batch_sizes = [int(x.strip()) for x in args.batch_sizes.split(",")]
    for batch_size in batch_sizes:
        print(f"Running batched benchmark (batch_size={batch_size})...")
        batched_result = benchmark_batched(requests, batch_size)
        results.append(batched_result)

    # Optional: benchmark suggestion engine
    if args.include_suggestions and items:
        print("Running suggestion_engine benchmark...")
        sugg_result = benchmark_suggestion_engine_serial(items, min(args.n, 10), str(args.data_dir))
        results.append(sugg_result)

    # Print results
    print()
    print(format_results_table(results))

    # Analysis
    print()
    print("ANALYSIS")
    print("-" * 80)

    serial_ms = serial_result["total_ms"]
    for r in results[1:]:
        if "batched" in r["mode"]:
            improvement = (serial_ms - r["total_ms"]) / serial_ms * 100 if serial_ms > 0 else 0
            if improvement > 0:
                print(f"  {r['mode']}: {improvement:.1f}% faster than serial")
            else:
                print(f"  {r['mode']}: {abs(improvement):.1f}% slower than serial (overhead)")

    print()
    print("NOTE: In local/fast scenarios, batching overhead may exceed benefits.")
    print("      Batching shows value when calls involve I/O or LLM.")


if __name__ == "__main__":
    main()
