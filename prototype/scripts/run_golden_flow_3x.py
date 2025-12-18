#!/usr/bin/env python3
"""
Golden Flow 3x Runner

Runs the Golden Flow 3 times consecutively with fresh data directories.
If any run fails, exits nonzero.

This proves that the Golden Flow is repeatable and deterministic.

Usage:
    python prototype/scripts/run_golden_flow_3x.py
"""

import subprocess
import sys
from pathlib import Path


def run_golden_flow_once(run_number: int) -> bool:
    """Run Golden Flow once with --fresh flag."""
    print(f"\n{'=' * 60}")
    print(f"GOLDEN FLOW RUN {run_number}/3")
    print("=" * 60)

    script_path = Path(__file__).parent / "run_golden_flow.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--fresh"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Print just the summary
        lines = result.stdout.strip().split("\n")
        # Print last 5 lines (summary)
        for line in lines[-5:]:
            print(line)
        return True
    else:
        print(f"FAILED with exit code {result.returncode}")
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        return False


def main():
    """Run Golden Flow 3 times and report results."""
    print("=" * 60)
    print("GOLDEN FLOW 3x RUNNER")
    print("=" * 60)
    print("Running Golden Flow 3 times with fresh data each time...")

    results = []

    for i in range(1, 4):
        success = run_golden_flow_once(i)
        results.append(success)
        status = "PASS" if success else "FAIL"
        print(f"Run {i}: {status}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for i, success in enumerate(results, 1):
        status = "PASS" if success else "FAIL"
        print(f"  Run {i}: {status}")
        if not success:
            all_passed = False

    print()
    if all_passed:
        print("ALL 3 RUNS PASSED - Golden Flow is repeatable!")
        return 0
    else:
        print("SOME RUNS FAILED - Check logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
