#!/usr/bin/env python3
"""
Field-Kit v0.1 Evaluation Harness (Sprint S02)

Offline evaluation harness for measuring hololink quality, evidence grounding,
and anti-soup metrics. Supports regression testing against baselines.

Usage:
    python3 tests/eval_harness.py --test-case tests/test_cases/golden_flow.json
    python3 tests/eval_harness.py --all
    python3 tests/eval_harness.py --all --verbose

Metrics computed:
- Ranking: MRR@K, Recall@K, Golden Flow Continuation Success Rate
- Grounding: Evidence Coverage Rate (ECR), Anchor Resolution Rate (ARR)
- Anti-soup: Top-K Redundancy Index (TRI), Hubness
"""

import sys
import json
import argparse
import tempfile
import shutil
import subprocess
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class SuggestionResult:
    """Result for a single suggestion."""
    index: int  # 1-indexed position
    prompt_text: str
    intent_type: Optional[str]
    is_acceptable: bool
    has_evidence: bool = False
    evidence_anchors_resolved: int = 0
    evidence_anchors_total: int = 0
    scales_present: Set[str] = field(default_factory=set)  # S04: scales in evidence
    graph_distance: Optional[int] = None  # S05: distance from subject


@dataclass
class TestCaseResult:
    """Result of running a single test case."""
    test_case_name: str
    suggestions: List[SuggestionResult]
    acceptable_targets: Set[Any]
    k: int
    data_dir: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_name": self.test_case_name,
            "suggestions": [
                {
                    "index": s.index,
                    "prompt_text": s.prompt_text[:50] + "..." if len(s.prompt_text) > 50 else s.prompt_text,
                    "intent_type": s.intent_type,
                    "is_acceptable": s.is_acceptable,
                    "has_evidence": s.has_evidence,
                }
                for s in self.suggestions
            ],
            "k": self.k,
            "error": self.error,
        }


@dataclass
class MetricsResult:
    """Computed metrics for a test case."""
    test_case_name: str
    # Ranking metrics
    mrr_at_k: float  # Reciprocal rank of first acceptable, 0 if none
    recall_at_k: float  # Fraction of acceptable in top-k
    golden_flow_continuation: float  # 1 if top-1 is acceptable, else 0
    # Grounding metrics
    ecr: float  # Evidence Coverage Rate: % with evidence
    arr: Optional[float]  # Anchor Resolution Rate: % of anchors resolved
    evidence_trace_presence: float  # Same as ECR for now
    # Anti-soup metrics
    tri_at_k: float  # Top-k Redundancy Index (lexical similarity)
    hubness: float  # Fraction hitting common targets
    # S04: Multi-scale metrics
    scale_count: int = 1  # Number of distinct scales present
    scales_present: List[str] = field(default_factory=list)  # Which scales
    # S05: Graph propagation metrics
    has_graph_distance: bool = False  # Any candidate has graph_distance set
    avg_graph_distance: Optional[float] = None  # Average distance (if available)
    # Meta
    k: int = 4
    total_suggestions: int = 0
    acceptable_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaselineComparator:
    """
    Baseline comparators for suggestion ranking.

    These provide simple baselines to compare against the actual system.
    Not intended to be good - just to provide a reference point.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def lexical_baseline(
        self,
        subject_text: str,
        suggestions: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Rank suggestions by token overlap with subject text.

        Returns indices sorted by overlap score (descending).
        """
        subject_tokens = set(subject_text.lower().split())

        scores = []
        for i, sug in enumerate(suggestions):
            prompt = sug.get("prompt_text", "")
            prompt_tokens = set(prompt.lower().split())
            overlap = len(subject_tokens & prompt_tokens)
            scores.append((i, overlap))

        # Sort by overlap descending, then by original index
        scores.sort(key=lambda x: (-x[1], x[0]))
        return [i for i, _ in scores]

    def random_baseline(
        self,
        suggestions: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Stable random ranking using seeded shuffle.

        Returns indices in random order (deterministic based on seed).
        """
        import random
        indices = list(range(len(suggestions)))
        rng = random.Random(self.seed)
        rng.shuffle(indices)
        return indices

    def recency_baseline(
        self,
        suggestions: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Rank by recency (original order, assuming most recent first).

        Since suggestions don't have timestamps, returns original order.
        """
        return list(range(len(suggestions)))

    def apply_ranking(
        self,
        suggestions: List[SuggestionResult],
        ranking: List[int],
    ) -> List[SuggestionResult]:
        """Reorder suggestions by ranking."""
        if not suggestions or not ranking:
            return suggestions
        return [suggestions[i] for i in ranking if i < len(suggestions)]


class EvalHarness:
    """
    Evaluation harness for Field-Kit hololink quality.

    Loads test cases, runs them against the current system,
    and computes metrics.
    """

    def __init__(self, test_cases_dir: Optional[Path] = None):
        self.test_cases_dir = test_cases_dir or Path(__file__).parent / "test_cases"
        self._temp_dirs: List[Path] = []

    def load_test_cases(self) -> List[Dict[str, Any]]:
        """Load all test cases from the test_cases directory."""
        cases = []
        for path in sorted(self.test_cases_dir.glob("*.json")):
            if path.name == "README.md":
                continue
            try:
                with open(path) as f:
                    case = json.load(f)
                    case["_path"] = str(path)
                    cases.append(case)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to load {path}: {e}")
        return cases

    def _setup_data_dir(self, test_case: Dict[str, Any]) -> Tuple[Path, List[str]]:
        """
        Set up the data directory for a test case.

        Returns:
            Tuple of (data_dir, list of created item IDs)
        """
        seed = test_case.get("seed", {})
        seed_type = seed.get("type", "golden_flow")

        if seed_type == "data_dir":
            # Use existing data directory
            data_dir = Path(seed.get("data_dir", "prototype/data"))
            return data_dir, self._get_item_ids(data_dir)

        elif seed_type == "golden_flow":
            # Run golden flow in a temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="eval_harness_"))
            self._temp_dirs.append(temp_dir)

            result = subprocess.run(
                ["python3", "prototype/scripts/run_golden_flow.py", "--fresh", "--data-dir", str(temp_dir)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Golden flow failed: {result.stderr}")

            return temp_dir, self._get_item_ids(temp_dir)

        elif seed_type == "synthetic":
            # Run setup steps in a temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="eval_harness_"))
            self._temp_dirs.append(temp_dir)

            # Initialize
            subprocess.run(
                ["python3", "src/cli.py", "--data-dir", str(temp_dir), "init"],
                capture_output=True,
            )

            # Run setup steps
            for step in seed.get("setup_steps", []):
                if step == "init":
                    continue  # Already done
                # Parse command
                parts = step.split()
                subprocess.run(
                    ["python3", "src/cli.py", "--data-dir", str(temp_dir)] + parts,
                    capture_output=True,
                )

            return temp_dir, self._get_item_ids(temp_dir)

        else:
            raise ValueError(f"Unknown seed type: {seed_type}")

    def _get_item_ids(self, data_dir: Path) -> List[str]:
        """Get list of item IDs from a data directory, ordered by creation."""
        items_file = data_dir / "items.jsonl"
        if not items_file.exists():
            return []

        items = []
        with open(items_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    items.append(item)

        # Sort by created_at if available
        items.sort(key=lambda x: x.get("created_at", ""))
        return [item["id"] for item in items]

    def _resolve_subject_item_id(self, test_case: Dict[str, Any], item_ids: List[str]) -> str:
        """Resolve the subject item ID, handling dynamic references."""
        subject = test_case.get("subject_item_id", "")

        if subject.startswith("dynamic:"):
            index = int(subject.split(":")[1])
            if index >= len(item_ids):
                raise ValueError(f"Dynamic index {index} out of range (only {len(item_ids)} items)")
            return item_ids[index]

        return subject

    def _get_suggestions(self, data_dir: Path, item_id: str) -> List[Dict[str, Any]]:
        """
        Get suggestions for an item from the system.

        Currently reads from events (bond.suggestions.presented).
        Future: call hololink_pipeline directly.
        """
        # Try both event file names
        events_file = data_dir / "qdpi_events.jsonl"
        if not events_file.exists():
            events_file = data_dir / "events.jsonl"
        if not events_file.exists():
            return []

        suggestions = []
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get("name") == "bond.suggestions.presented":
                        refs = event.get("refs", {})
                        if refs.get("item_id") == item_id:
                            suggestions = refs.get("suggestions", [])

        return suggestions

    def _evaluate_acceptability(
        self,
        suggestions: List[Dict[str, Any]],
        acceptable: Dict[str, Any],
    ) -> List[bool]:
        """Evaluate which suggestions are acceptable."""
        accept_type = acceptable.get("type", "suggestion_indices")
        accept_values = set(acceptable.get("values", []))

        results = []
        for i, sug in enumerate(suggestions):
            if accept_type == "suggestion_indices":
                # 1-indexed positions
                is_acceptable = (i + 1) in accept_values
            elif accept_type == "intent_types":
                # Check both intent and intent_type fields
                intent = sug.get("intent_type") or sug.get("intent", "")
                is_acceptable = intent in accept_values
            elif accept_type == "item_ids":
                target_id = sug.get("target_id", "")
                is_acceptable = target_id in accept_values
            else:
                is_acceptable = False
            results.append(is_acceptable)

        return results

    def run_test_case(
        self,
        test_case: Dict[str, Any],
        data_dir: Optional[Path] = None,
    ) -> TestCaseResult:
        """
        Run a single test case.

        Args:
            test_case: Test case definition
            data_dir: Optional pre-existing data directory

        Returns:
            TestCaseResult with suggestions and acceptability
        """
        name = test_case.get("name", "unknown")
        k = test_case.get("k", 4)

        try:
            # Setup data directory
            if data_dir is None:
                data_dir, item_ids = self._setup_data_dir(test_case)
            else:
                item_ids = self._get_item_ids(data_dir)

            # Resolve subject item ID
            subject_id = self._resolve_subject_item_id(test_case, item_ids)

            # Get suggestions
            suggestions = self._get_suggestions(data_dir, subject_id)

            # Evaluate acceptability
            acceptable = test_case.get("acceptable_targets", {})
            acceptability = self._evaluate_acceptability(suggestions, acceptable)

            # Build results
            suggestion_results = []
            for i, sug in enumerate(suggestions[:k]):
                # S03: Check for evidence shards
                evidence_shards = sug.get("evidence_shards", [])
                has_evidence = len(evidence_shards) > 0

                # S04: Extract scales from evidence shards
                shard_scales = set()
                for shard in evidence_shards:
                    scale = shard.get("scale", "local")
                    shard_scales.add(scale)

                # S05: Extract graph distance
                graph_dist = sug.get("graph_distance")

                suggestion_results.append(SuggestionResult(
                    index=i + 1,
                    prompt_text=sug.get("prompt_text", ""),
                    intent_type=sug.get("intent_type") or sug.get("intent"),
                    is_acceptable=acceptability[i] if i < len(acceptability) else False,
                    has_evidence=has_evidence,
                    evidence_anchors_total=len(evidence_shards),
                    evidence_anchors_resolved=sum(1 for s in evidence_shards if s.get("span_start", -1) >= 0),
                    scales_present=shard_scales,
                    graph_distance=graph_dist,
                ))

            return TestCaseResult(
                test_case_name=name,
                suggestions=suggestion_results,
                acceptable_targets=set(acceptable.get("values", [])),
                k=k,
                data_dir=str(data_dir),
            )

        except Exception as e:
            return TestCaseResult(
                test_case_name=name,
                suggestions=[],
                acceptable_targets=set(),
                k=k,
                error=str(e),
            )

    def compute_metrics(self, result: TestCaseResult) -> MetricsResult:
        """
        Compute all metrics for a test case result.

        Metrics:
        - mrr_at_k: Reciprocal rank of first acceptable, 0 if none
        - recall_at_k: Fraction of acceptable in top-k
        - golden_flow_continuation: 1 if top-1 is acceptable, else 0
        - ecr: Evidence Coverage Rate
        - arr: Anchor Resolution Rate
        - tri_at_k: Top-k Redundancy Index (lexical similarity)
        - hubness: Fraction hitting common targets
        """
        suggestions = result.suggestions
        k = result.k

        if result.error or not suggestions:
            return MetricsResult(
                test_case_name=result.test_case_name,
                mrr_at_k=0.0,
                recall_at_k=0.0,
                golden_flow_continuation=0.0,
                ecr=0.0,
                arr=None,
                evidence_trace_presence=0.0,
                tri_at_k=0.0,
                hubness=0.0,
                k=k,
                total_suggestions=0,
                acceptable_count=0,
            )

        # MRR@K: Reciprocal rank of first acceptable
        mrr = 0.0
        for i, s in enumerate(suggestions[:k]):
            if s.is_acceptable:
                mrr = 1.0 / (i + 1)
                break

        # Recall@K: Fraction of acceptable in top-k
        acceptable_in_k = sum(1 for s in suggestions[:k] if s.is_acceptable)
        total_acceptable = len(result.acceptable_targets)
        recall = acceptable_in_k / total_acceptable if total_acceptable > 0 else 0.0

        # Golden Flow Continuation: 1 if top-1 is acceptable
        gfc = 1.0 if suggestions and suggestions[0].is_acceptable else 0.0

        # ECR: Evidence Coverage Rate
        with_evidence = sum(1 for s in suggestions[:k] if s.has_evidence)
        ecr = with_evidence / len(suggestions[:k]) if suggestions else 0.0

        # ARR: Anchor Resolution Rate
        total_anchors = sum(s.evidence_anchors_total for s in suggestions[:k])
        resolved_anchors = sum(s.evidence_anchors_resolved for s in suggestions[:k])
        arr = resolved_anchors / total_anchors if total_anchors > 0 else None

        # TRI@K: Top-k Redundancy Index (lexical similarity)
        tri = self._compute_tri(suggestions[:k])

        # Hubness: Using intent type frequency as proxy
        hubness = self._compute_hubness(suggestions[:k])

        # S04: Aggregate scales across all suggestions
        all_scales: Set[str] = set()
        for s in suggestions[:k]:
            all_scales.update(s.scales_present)
        scales_list = sorted(all_scales)

        # S05: Compute graph distance metrics
        graph_distances = [s.graph_distance for s in suggestions[:k] if s.graph_distance is not None]
        has_graph_distance = len(graph_distances) > 0
        avg_graph_distance = sum(graph_distances) / len(graph_distances) if graph_distances else None

        return MetricsResult(
            test_case_name=result.test_case_name,
            mrr_at_k=round(mrr, 4),
            recall_at_k=round(recall, 4),
            golden_flow_continuation=gfc,
            ecr=round(ecr, 4),
            arr=round(arr, 4) if arr is not None else None,
            evidence_trace_presence=round(ecr, 4),
            tri_at_k=round(tri, 4),
            hubness=round(hubness, 4),
            scale_count=len(scales_list),
            scales_present=scales_list,
            has_graph_distance=has_graph_distance,
            avg_graph_distance=round(avg_graph_distance, 2) if avg_graph_distance is not None else None,
            k=k,
            total_suggestions=len(suggestions[:k]),
            acceptable_count=acceptable_in_k,
        )

    def _compute_tri(self, suggestions: List[SuggestionResult]) -> float:
        """
        Compute Top-k Redundancy Index using Jaccard similarity on tokens.

        Higher TRI = more redundancy (bad for diversity).
        """
        if len(suggestions) < 2:
            return 0.0

        def tokenize(text: str) -> Set[str]:
            return set(text.lower().split())

        token_sets = [tokenize(s.prompt_text) for s in suggestions]

        # Compute mean pairwise Jaccard similarity
        similarities = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                a, b = token_sets[i], token_sets[j]
                if a or b:
                    intersection = len(a & b)
                    union = len(a | b)
                    sim = intersection / union if union > 0 else 0.0
                    similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _compute_hubness(self, suggestions: List[SuggestionResult]) -> float:
        """
        Compute hubness as fraction of suggestions with repeated intent types.

        In future: use target ID frequency or graph degree.
        """
        if not suggestions:
            return 0.0

        intent_counts = Counter(s.intent_type for s in suggestions if s.intent_type)
        if not intent_counts:
            return 0.0

        # Most common intent
        most_common_count = intent_counts.most_common(1)[0][1]

        # Hubness = fraction with the most common intent
        return most_common_count / len(suggestions)

    def run_all_test_cases(self, verbose: bool = False) -> List[Tuple[TestCaseResult, MetricsResult]]:
        """Run all test cases and compute metrics."""
        cases = self.load_test_cases()
        results = []

        for case in cases:
            if verbose:
                print(f"Running: {case.get('name', 'unknown')}...")

            result = self.run_test_case(case)
            metrics = self.compute_metrics(result)
            results.append((result, metrics))

            if verbose:
                print(f"  MRR@{metrics.k}: {metrics.mrr_at_k}, Recall@{metrics.k}: {metrics.recall_at_k}")

        return results

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self._temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        self._temp_dirs = []

    def run_baselines(
        self,
        test_case: Dict[str, Any],
        result: TestCaseResult,
        data_dir: Path,
    ) -> Dict[str, MetricsResult]:
        """
        Run baseline comparators and compute their metrics.

        Returns dict mapping baseline name to MetricsResult.
        """
        comparator = BaselineComparator()
        baselines = {}

        if not result.suggestions:
            # No suggestions to rerank
            return {
                "lexical": self.compute_metrics(result),
                "random": self.compute_metrics(result),
                "recency": self.compute_metrics(result),
            }

        # Get subject item text for lexical baseline
        subject_id = self._resolve_subject_item_id(
            test_case,
            self._get_item_ids(data_dir)
        )
        subject_item = self._get_item(data_dir, subject_id)
        subject_text = subject_item.get("title", "") + " " + subject_item.get("body", "") if subject_item else ""

        # Get raw suggestions for reranking
        raw_suggestions = self._get_suggestions(data_dir, subject_id)

        # Lexical baseline
        lexical_ranking = comparator.lexical_baseline(subject_text, raw_suggestions)
        lexical_suggestions = comparator.apply_ranking(result.suggestions, lexical_ranking)
        lexical_result = TestCaseResult(
            test_case_name=result.test_case_name,
            suggestions=lexical_suggestions,
            acceptable_targets=result.acceptable_targets,
            k=result.k,
        )
        baselines["lexical"] = self.compute_metrics(lexical_result)

        # Random baseline
        random_ranking = comparator.random_baseline(raw_suggestions)
        random_suggestions = comparator.apply_ranking(result.suggestions, random_ranking)
        random_result = TestCaseResult(
            test_case_name=result.test_case_name,
            suggestions=random_suggestions,
            acceptable_targets=result.acceptable_targets,
            k=result.k,
        )
        baselines["random"] = self.compute_metrics(random_result)

        # Recency baseline (same as original order)
        baselines["recency"] = self.compute_metrics(result)

        return baselines

    def _get_item(self, data_dir: Path, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single item by ID."""
        items_file = data_dir / "items.jsonl"
        if not items_file.exists():
            return None

        with open(items_file) as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("id") == item_id:
                        return item
        return None

    def generate_baseline_scores(
        self,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generate baseline scores for all test cases.

        Args:
            output_path: Path to save JSON output

        Returns:
            Dict with baseline scores per test case
        """
        cases = self.load_test_cases()
        baseline_scores = {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "test_cases": {},
        }

        for case in cases:
            name = case.get("name", "unknown")
            print(f"Generating baselines for: {name}...")

            # Setup data dir
            data_dir, item_ids = self._setup_data_dir(case)

            # Run test case
            result = self.run_test_case(case, data_dir)

            # Compute baselines
            baselines = self.run_baselines(case, result, data_dir)

            # Store
            baseline_scores["test_cases"][name] = {
                "system": self.compute_metrics(result).to_dict(),
                "baselines": {k: v.to_dict() for k, v in baselines.items()},
            }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(baseline_scores, f, indent=2)
            print(f"Baseline scores saved to: {output_path}")

        return baseline_scores

    def generate_report(self, results: List[Tuple[TestCaseResult, MetricsResult]]) -> str:
        """Generate a human-readable report."""
        lines = [
            "=" * 70,
            "FIELD-KIT EVALUATION REPORT",
            "=" * 70,
            "",
        ]

        # Summary table
        lines.append("Test Case                          MRR@K  Recall@K  ECR    TRI    Scales")
        lines.append("-" * 78)

        for result, metrics in results:
            name = metrics.test_case_name[:32].ljust(32)
            mrr = f"{metrics.mrr_at_k:.3f}".ljust(6)
            recall = f"{metrics.recall_at_k:.3f}".ljust(9)
            ecr = f"{metrics.ecr:.3f}".ljust(6)
            tri = f"{metrics.tri_at_k:.3f}".ljust(6)
            scales = ",".join(metrics.scales_present) if metrics.scales_present else "-"
            lines.append(f"{name}  {mrr} {recall} {ecr} {tri} {scales}")

        lines.append("")

        # Aggregate metrics
        all_metrics = [m for _, m in results if m.total_suggestions > 0]
        if all_metrics:
            avg_mrr = sum(m.mrr_at_k for m in all_metrics) / len(all_metrics)
            avg_recall = sum(m.recall_at_k for m in all_metrics) / len(all_metrics)
            avg_ecr = sum(m.ecr for m in all_metrics) / len(all_metrics)
            avg_tri = sum(m.tri_at_k for m in all_metrics) / len(all_metrics)
            # S04: Scale coverage
            avg_scale_count = sum(m.scale_count for m in all_metrics) / len(all_metrics)
            all_scales_union: Set[str] = set()
            for m in all_metrics:
                all_scales_union.update(m.scales_present)

            lines.extend([
                "--- Aggregate Metrics ---",
                f"Avg MRR@K:    {avg_mrr:.4f}",
                f"Avg Recall@K: {avg_recall:.4f}",
                f"Avg ECR:      {avg_ecr:.4f}",
                f"Avg TRI:      {avg_tri:.4f}",
                f"Avg Scales:   {avg_scale_count:.2f} ({','.join(sorted(all_scales_union)) or '-'})",
                "",
            ])

        # Errors
        errors = [(r, m) for r, m in results if r.error]
        if errors:
            lines.append("--- Errors ---")
            for result, _ in errors:
                lines.append(f"  {result.test_case_name}: {result.error}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Field-Kit Evaluation Harness")
    parser.add_argument(
        "--test-case",
        type=Path,
        help="Run a single test case",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test cases",
    )
    parser.add_argument(
        "--generate-baselines",
        action="store_true",
        help="Generate baseline scores and save to tests/baselines/baseline_scores.json",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for results JSON",
    )
    args = parser.parse_args()

    harness = EvalHarness()

    try:
        if args.generate_baselines:
            # Generate baseline scores
            baselines_dir = Path(__file__).parent / "baselines"
            baselines_dir.mkdir(exist_ok=True)
            output_path = baselines_dir / "baseline_scores.json"
            harness.generate_baseline_scores(output_path)
            harness.cleanup()
            return

        if args.test_case:
            # Run single test case
            with open(args.test_case) as f:
                test_case = json.load(f)

            result = harness.run_test_case(test_case)
            metrics = harness.compute_metrics(result)

            print(harness.generate_report([(result, metrics)]))

            if args.output:
                with open(args.output, "w") as f:
                    json.dump({
                        "result": result.to_dict(),
                        "metrics": metrics.to_dict(),
                    }, f, indent=2)

        elif args.all:
            # Run all test cases
            results = harness.run_all_test_cases(verbose=args.verbose)
            print(harness.generate_report(results))

            if args.output:
                with open(args.output, "w") as f:
                    json.dump({
                        "results": [
                            {"result": r.to_dict(), "metrics": m.to_dict()}
                            for r, m in results
                        ]
                    }, f, indent=2)

        else:
            parser.print_help()

    finally:
        harness.cleanup()


if __name__ == "__main__":
    main()
