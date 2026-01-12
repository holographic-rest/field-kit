# Evaluation Harness Design

Technical design document for the Field-Kit evaluation harness (Sprint S02).

## Overview

The evaluation harness provides offline testing and regression detection for Field-Kit's suggestion system. It measures ranking quality, grounding coverage, and diversity signals.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                          │
│              eval:regression  │  eval:dashboard             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    RegressionSuite                          │
│  - Load baselines                                           │
│  - Run test cases                                           │
│  - Compare against thresholds                               │
│  - Generate pass/fail report                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     EvalHarness                             │
│  - Load test cases from JSON                                │
│  - Execute against golden flow or data dirs                 │
│  - Compute metrics                                          │
│  - Run baseline comparators                                 │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ BaselineCompar  │ │ MetricsResult   │ │ Test Cases      │
│ - lexical       │ │ - mrr_at_k      │ │ - JSON schema   │
│ - random        │ │ - recall_at_k   │ │ - dynamic IDs   │
│ - recency       │ │ - ecr, tri, etc │ │ - golden flow   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Metrics

### Ranking Quality

**MRR@K (Mean Reciprocal Rank at K)**
- Measures where the first acceptable item appears
- `1/rank` of first acceptable in top-K suggestions
- Range: 0 to 1 (higher is better)

**Recall@K**
- Fraction of acceptable suggestions in top-K
- `|acceptable ∩ top_k| / |acceptable|`
- Range: 0 to 1 (higher is better)

**Golden Flow Continuation**
- Binary: 1 if top-1 is acceptable, 0 otherwise
- Critical metric for workflow continuation

### Grounding Coverage

**ECR (Evidence Coverage Rate)**
- Fraction of suggestions with evidence shards
- Currently 0% (evidence not implemented)
- Will increase as evidence system is built

**Evidence Trace Presence**
- Binary presence of any evidence
- Also 0% until evidence is implemented

### Diversity & Anti-Soup Signals

**TRI (Top-K Redundancy Index)**
- Measures lexical diversity in top-K
- Uses Jaccard similarity on word tokens
- Range: 0 to 1 (lower is better = more diverse)

**Hubness**
- Fraction of suggestions hitting common intent types
- Proxy for graph-based hubness detection
- Range: 0 to 1 (lower is better)

## Test Case Schema

```json
{
  "name": "string",
  "description": "string",
  "qdpi_stage": "Q" | "D" | "P" | "I" | "M",
  "seed": {
    "type": "golden_flow" | "data_dir",
    "path": "optional/path"
  },
  "subject_item_id": "item-uuid" | "dynamic:N",
  "k": 4,
  "acceptable_targets": {
    "type": "suggestion_indices" | "item_ids" | "intent_types",
    "values": []
  }
}
```

### Dynamic Item IDs

Test cases can use `dynamic:N` to reference items by their creation order in the golden flow:
- `dynamic:0` = first item created
- `dynamic:1` = second item created

This allows test cases to work without hardcoding UUIDs.

## Baseline Comparators

The harness compares the system against three baselines:

1. **Lexical**: Rank by token overlap with subject text
2. **Random**: Seeded random shuffle (reproducible)
3. **Recency**: Original presentation order

These provide context for whether the system's ranking adds value.

## Regression Testing

Thresholds defined in `regression_suite.py`:

```python
DEFAULT_THRESHOLDS = [
    RegressionThreshold("mrr_at_k", tolerance=0.1),
    RegressionThreshold("recall_at_k", tolerance=0.1),
    RegressionThreshold("golden_flow_continuation", tolerance=0.0, critical=True),
    RegressionThreshold("ecr", tolerance=0.0),
    RegressionThreshold("tri_at_k", tolerance=0.2),
]
```

See `tests/REGRESSION_THRESHOLDS.md` for rationale.

## Data Flow

1. **Test Case Loading**: JSON files parsed, dynamic IDs resolved
2. **Golden Flow Execution**: If seed type is `golden_flow`, run through demo flow
3. **Suggestion Retrieval**: Get `bond.suggestions.presented` events from QDPI log
4. **Metrics Computation**: Calculate all metrics for system and baselines
5. **Comparison**: Check against thresholds, generate report

## Limitations

### Current Limitations

1. **No evidence shards**: ECR is always 0
2. **TRI is approximate**: Uses Jaccard on tokens, not embeddings
3. **Hubness is proxied**: Uses intent type frequency, not graph degree
4. **Golden flow only**: Most test cases use golden flow seed

### Future Improvements

1. Add evidence shard generation and ECR measurement
2. Integrate embedding-based TRI when embeddings are available
3. Add graph-based hubness detection
4. Support more seed types (user scenarios, edge cases)

## Usage

### Run Evaluation

```bash
# Via CLI
python3 src/cli.py eval:dashboard
python3 src/cli.py eval:regression

# Direct script
python3 tests/eval_harness.py
python3 tests/regression_suite.py
```

### Add Test Case

1. Create JSON in `tests/test_cases/`
2. Follow schema in `test_cases/README.md`
3. Run `eval:regression --update-baselines`
4. Commit test case + updated baselines

### Debug Failures

1. Run `eval:dashboard` for current metrics
2. Check regression report for specific failures
3. Review threshold rationale in `REGRESSION_THRESHOLDS.md`
4. Investigate metric computation in `eval_harness.py`

## References

- Sprint S02: `docs/specs/S02_observability_eval.md`
- Research: `research/ML_spine_for_gibsey_QDPI.md`
- Test cases: `tests/test_cases/README.md`
