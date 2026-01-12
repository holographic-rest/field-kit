# S02: Observability & Evaluation Harness
**Days:** Dec 25-26 (2 days, lighter load due to holiday)  
**Theme:** Measure everything; establish regression tests

---

## Objective

Build an evaluation harness that can measure hololink quality, evidence grounding, and system health. Establish a regression test protocol so future changes don't break the golden path. Add metrics dashboard for fellowship narrative.

---

## Why This Matters for Fellowship Narrative

- **Demonstrates rigor**: Evaluation harness shows systematic approach, not just "it works on my machine"
- **Enables measurement**: Can prove improvements vs baseline (critical for research narrative)
- **Shows engineering discipline**: CS231n-style "measure, don't guess" approach
- **Prevents regressions**: Automated tests catch breakage before demo

---

## Inputs

### Research Documents
- `research/12-23-2025-research/evaluation/03_offline_eval_hololinks.md.md` - Eval harness design
- `research/27-essays/27_CS231n_convolutional_neural_networks_visual_recognition.md` - Sanity suite pattern
- `research/27-essays/23_scaling_laws_neural_LMs.md` - Measurement discipline
- `research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md` - MDL scoring

### Repo Modules
- `prototype/scripts/run_golden_flow.py` - Existing test
- `src/cli.py` - CLI for test execution
- `src/fieldkit/store_jsonl.py` - Data access

---

## Tasks

### Task 1: Create Eval Harness Structure
1. Create `tests/eval_harness.py` with:
   - `EvalHarness` class
   - `run_test_case(context, expected)` method
   - `compute_metrics(results)` method
   - `generate_report(metrics)` method
2. Create `tests/test_cases/` directory
3. Create `tests/test_cases/golden_flow.json` (serialize existing golden flow as test case)

### Task 2: Implement Core Metrics
1. Implement ranking metrics:
   - `MRR@K` (mean reciprocal rank of first acceptable link in top-K, binary relevance: acceptable=1, not=0)
   - `Golden Flow Continuation Success Rate`: % of golden flow steps where top-1 suggestion is acceptable (binary)
   - `Recall@10` (coverage of acceptable links in top-10, binary relevance)
2. Implement grounding metrics:
   - `Evidence Coverage Rate (ECR)`: % of hololinks with ≥1 evidence shard
   - `Anchor Resolution Rate (ARR)`: % of evidence shards that resolve to existing source span
   - `Evidence Trace Presence`: % of suggestions with ≥1 evidence shard (proxy for support)
3. Implement anti-soup metrics:
   - `Ungrounded Link Ratio (ULR)`: 1 - ECR (% of links with no evidence)
   - `Top-k Redundancy Index (TRI)`: Mean pairwise cosine similarity among top-k suggestions (embedding-based)
   - `Hubness`: Fraction of suggestions pointing to top-N nodes (by degree or selection frequency)

### Task 3: Create Test Cases (5 minimum, 10 stretch goal)
1. Convert golden flow to test case #1
2. Create 4-9 additional test cases covering:
   - Queue stage (1-3 cases)
   - Monologue stage (1-3 cases)
   - Dialogue stage (1-2 cases)
   - Holologue stage (0-1 case)
3. Each test case includes:
   - `context`: seed nodes, QDPI stage, working text
   - `candidate_pool`: available targets
   - `acceptable_targets`: set of target IDs that are acceptable (binary relevance)
   - `required_evidence_shards`: list of evidence shard IDs that should support links (optional)

### Task 4: Implement Baseline Comparisons
1. Create three baselines:
   - `LexicalOnlyBaseline`: FTS/BM25 only
   - `VectorOnlyBaseline`: ANN/embeddings only
   - `GraphOnlyBaseline`: Neighborhood expansion only
2. Run all test cases against baselines
3. Store baseline scores in `tests/baselines/baseline_scores.json` for comparison

### Task 5: Add Regression Protocol
1. Create `tests/regression_suite.py`:
   - Loads all test cases
   - Runs current system
   - Compares against baseline scores
   - Fails if key metrics drop beyond tolerance
2. Add CLI command: `python3 src/cli.py eval:regression`
3. Document tolerance thresholds in `tests/REGRESSION_THRESHOLDS.md`

### Task 6: Create Metrics Dashboard
1. Create `prototype/ui/metrics.html` (or add to existing UI):
   - Shows current metrics vs baselines
   - Plots complexity trends over time
   - Shows evidence coverage by stage
2. Or create CLI command: `python3 src/cli.py eval:dashboard` that prints table

---

## Acceptance Criteria

- [ ] Eval harness runs all test cases (minimum 5, stretch goal 10)
- [ ] All core metrics compute correctly (MRR@K, Golden Flow Continuation Success Rate, ECR, ARR, Evidence Trace Presence, ULR, TRI, Hubness)
- [ ] Baseline comparisons exist (lexical/vector/graph) with scores stored in `tests/baselines/baseline_scores.json`
- [ ] Regression suite runs and fails on degradation
- [ ] Metrics dashboard exists (UI or CLI)
- [ ] Documentation: `tests/README.md` + `tests/REGRESSION_THRESHOLDS.md`

---

## Test Plan

### Test 1: Eval Harness Runs
```bash
python3 tests/eval_harness.py --test-case tests/test_cases/golden_flow.json
```
**Expected:** Runs test case and prints metrics

### Test 2: All Test Cases Load
```python
# In Python REPL
from tests.eval_harness import EvalHarness
harness = EvalHarness()
cases = harness.load_test_cases()
assert len(cases) >= 5  # Minimum 5, stretch goal 10
```
**Expected:** All test cases load without errors (minimum 5)

### Test 3: Metrics Compute
```python
# Mock results
results = {
    "suggestions": [
        {"target_id": "it_1", "is_acceptable": True, "has_evidence": True},
        {"target_id": "it_2", "is_acceptable": False, "has_evidence": False},
    ],
    "acceptable_targets": {"it_1"}
}
metrics = harness.compute_metrics(results)
assert "mrr@5" in metrics
assert "ecr" in metrics
assert "evidence_trace_presence" in metrics
assert metrics["ecr"] == 0.5  # 1 of 2 has evidence
```
**Expected:** All metrics compute correctly

### Test 4: Regression Suite
```bash
python3 src/cli.py eval:regression
```
**Expected:** Runs all tests, compares to baselines, exits 0 if passing

---

## Documentation Outputs

1. `tests/README.md` - How to run eval harness
2. `tests/REGRESSION_THRESHOLDS.md` - Tolerance values and rationale
3. `tests/test_cases/README.md` - Test case format specification
4. `docs/evaluation/EVAL_HARNESS_DESIGN.md` - Architecture of eval system

---

## Fallback Plan

If 10 test cases is too many:
- **Fallback:** Create 5 test cases (golden flow + 4 others)
- **Minimum deliverable:** Eval harness runs with at least 5 test cases
- **Document:** Plan to expand to 10 in post-fellowship work

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`prototype/scripts/run_golden_flow.py`, `src/cli.py`, `src/fieldkit/store_jsonl.py`)
- **Research docs:** All paths match actual files (including `.md.md` extension for eval doc)
- **Metrics changes:**
  - `nDCG@5` → `MRR@K` + `Golden Flow Continuation Success Rate` (binary relevance, no human labels)
  - `Support Precision` → `Evidence Trace Presence` + `Anchor Resolution Rate` (automatic checks)
  - Test cases: 5 minimum, 10 stretch goal (was 10 required)
- **Baseline storage:** Added explicit path `tests/baselines/baseline_scores.json` for baseline score storage

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S02: Observability & Evaluation Harness.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S02_observability_eval.md
Also read: research/12-23-2025-research/evaluation/03_offline_eval_hololinks.md.md

Your goal:
1. Create eval harness structure (tests/eval_harness.py)
2. Implement core metrics (MRR@K, Golden Flow Continuation Success Rate, ECR, ARR, Evidence Trace Presence, ULR, TRI, Hubness)
3. Create test cases (minimum 5, stretch goal 10; start with golden flow, add 4-9 more)
4. Implement baseline comparisons (lexical/vector/graph) and store scores in tests/baselines/baseline_scores.json
5. Add regression protocol (tests/regression_suite.py)
6. Create metrics dashboard (UI or CLI)

Constraints:
- DO NOT change existing functionality (only add measurement)
- Keep test cases simple (JSON files with context + acceptable_targets set, binary relevance)
- Metrics must be computable offline (no external services, no human labeling)
- Regression suite must be runnable via CLI
- Use binary relevance (acceptable/not) not graded relevance

After completion:
- Run eval harness on all test cases
- Document metrics in tests/README.md
- Create regression thresholds document
- Verify regression suite catches degradations

Start by creating the eval harness structure and implementing MRR@K.
```

