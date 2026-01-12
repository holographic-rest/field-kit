#!/usr/bin/env python3
"""
Field-Kit v0.1 Regression Suite (Sprint S02)

Runs the evaluation harness and compares against baseline scores.
Fails if key metrics drop beyond tolerance thresholds.

Usage:
    python3 tests/regression_suite.py
    python3 tests/regression_suite.py --update-baselines
    python3 tests/regression_suite.py --data-dir prototype/data_dogfood

Exit codes:
    0 - All tests passed
    1 - One or more tests failed
    2 - Error running tests
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import EvalHarness, MetricsResult


@dataclass
class RegressionThreshold:
    """Threshold for a metric regression check."""
    metric: str
    tolerance: float  # Max drop allowed from baseline
    critical: bool = False  # If True, any drop fails the test


# Default thresholds - see REGRESSION_THRESHOLDS.md for rationale
DEFAULT_THRESHOLDS = [
    RegressionThreshold("mrr_at_k", tolerance=0.1, critical=False),
    RegressionThreshold("recall_at_k", tolerance=0.1, critical=False),
    RegressionThreshold("golden_flow_continuation", tolerance=0.0, critical=True),  # Must not drop
    RegressionThreshold("ecr", tolerance=0.0, critical=False),  # Currently 0, can only go up
    RegressionThreshold("tri_at_k", tolerance=0.2, critical=False),  # Higher is worse, but allow variation
]


@dataclass
class RegressionResult:
    """Result of a single regression check."""
    test_case: str
    metric: str
    baseline: float
    current: float
    threshold: float
    passed: bool
    critical: bool
    message: str


class RegressionSuite:
    """
    Regression test suite for Field-Kit evaluation.

    Compares current metrics against baseline scores and fails
    if key metrics drop beyond tolerance thresholds.
    """

    def __init__(
        self,
        baselines_path: Path = None,
        thresholds: List[RegressionThreshold] = None,
    ):
        self.baselines_path = baselines_path or Path(__file__).parent / "baselines" / "baseline_scores.json"
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.harness = EvalHarness()

    def load_baselines(self) -> Dict[str, Any]:
        """Load baseline scores from JSON file."""
        if not self.baselines_path.exists():
            return {}

        with open(self.baselines_path) as f:
            return json.load(f)

    def run_regression(
        self,
        data_dir: Path = None,
    ) -> Tuple[List[RegressionResult], bool]:
        """
        Run regression tests.

        Args:
            data_dir: Optional data directory (uses golden flow if None)

        Returns:
            Tuple of (list of RegressionResults, overall_passed)
        """
        baselines = self.load_baselines()
        if not baselines:
            print("Warning: No baseline scores found. Run --update-baselines first.")
            return [], False

        results = []
        overall_passed = True

        # Run all test cases
        test_cases = self.harness.load_test_cases()

        for case in test_cases:
            name = case.get("name", "unknown")

            # Get baseline for this test case
            baseline_data = baselines.get("test_cases", {}).get(name, {})
            baseline_metrics = baseline_data.get("system", {})

            if not baseline_metrics:
                print(f"Warning: No baseline for test case '{name}', skipping")
                continue

            # Run current test
            result = self.harness.run_test_case(case, data_dir)
            current_metrics = self.harness.compute_metrics(result)

            # Check each threshold
            for threshold in self.thresholds:
                metric = threshold.metric
                baseline_value = baseline_metrics.get(metric, 0.0)
                current_value = getattr(current_metrics, metric, 0.0)

                if current_value is None:
                    current_value = 0.0
                if baseline_value is None:
                    baseline_value = 0.0

                # Check for regression
                drop = baseline_value - current_value

                if threshold.critical:
                    passed = drop <= 0  # Any drop fails
                else:
                    passed = drop <= threshold.tolerance

                if not passed:
                    overall_passed = False

                message = ""
                if not passed:
                    if threshold.critical:
                        message = f"CRITICAL: {metric} dropped from {baseline_value:.4f} to {current_value:.4f}"
                    else:
                        message = f"{metric} dropped by {drop:.4f} (tolerance: {threshold.tolerance})"

                results.append(RegressionResult(
                    test_case=name,
                    metric=metric,
                    baseline=baseline_value,
                    current=current_value,
                    threshold=threshold.tolerance,
                    passed=passed,
                    critical=threshold.critical,
                    message=message,
                ))

        self.harness.cleanup()
        return results, overall_passed

    def update_baselines(self):
        """Update baseline scores with current system metrics."""
        print("Updating baselines...")
        self.harness.generate_baseline_scores(self.baselines_path)
        self.harness.cleanup()
        print("Baselines updated.")

    def generate_report(self, results: List[RegressionResult], overall_passed: bool) -> str:
        """Generate a human-readable regression report."""
        lines = [
            "=" * 70,
            "FIELD-KIT REGRESSION SUITE",
            "=" * 70,
            "",
        ]

        # Group by test case
        by_case = {}
        for r in results:
            if r.test_case not in by_case:
                by_case[r.test_case] = []
            by_case[r.test_case].append(r)

        for case, case_results in sorted(by_case.items()):
            case_passed = all(r.passed for r in case_results)
            status = "PASS" if case_passed else "FAIL"
            lines.append(f"[{status}] {case}")

            for r in case_results:
                if not r.passed:
                    lines.append(f"      {r.message}")

        lines.append("")
        lines.append("-" * 70)

        # Summary
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        critical_failures = sum(1 for r in results if not r.passed and r.critical)

        lines.append(f"Total checks: {len(results)}")
        lines.append(f"Passed: {passed_count}")
        lines.append(f"Failed: {failed_count}")
        if critical_failures > 0:
            lines.append(f"Critical failures: {critical_failures}")

        lines.append("")
        if overall_passed:
            lines.append("REGRESSION SUITE PASSED")
        else:
            lines.append("REGRESSION SUITE FAILED")
        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Field-Kit Regression Suite")
    parser.add_argument(
        "--update-baselines",
        action="store_true",
        help="Update baseline scores with current system metrics",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data directory to use (default: run golden flow)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    suite = RegressionSuite()

    if args.update_baselines:
        suite.update_baselines()
        return 0

    results, passed = suite.run_regression(args.data_dir)

    if not results:
        print("No regression results. Run --update-baselines first.")
        return 2

    print(suite.generate_report(results, passed))

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
