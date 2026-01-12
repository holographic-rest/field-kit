# Field-Kit Evaluation & Regression Testing

This directory contains the evaluation harness and regression test suite for Field-Kit.

## Quick Start

```bash
# Run regression suite
python3 src/cli.py eval:regression

# View evaluation dashboard
python3 src/cli.py eval:dashboard

# Update baselines (after intentional changes)
python3 src/cli.py eval:regression --update-baselines
```

## Directory Structure

```
tests/
├── eval_harness.py         # Core evaluation engine
├── regression_suite.py     # Regression test runner
├── test_cases/             # Test case definitions
│   ├── README.md           # Test case schema documentation
│   └── *.json              # Individual test cases
├── baselines/
│   └── baseline_scores.json # Baseline metrics for regression
├── README.md               # This file
└── REGRESSION_THRESHOLDS.md # Threshold rationale
```

## Components

### Evaluation Harness (`eval_harness.py`)

The core evaluation engine that:
- Loads and runs test cases
- Computes metrics (MRR@K, Recall@K, ECR, TRI, hubness)
- Compares against baselines (lexical, random, recency)
- Generates reports

```bash
# Direct usage
python3 tests/eval_harness.py
python3 tests/eval_harness.py --data-dir prototype/data_dogfood
```

### Regression Suite (`regression_suite.py`)

Automated regression testing that:
- Runs all test cases through eval harness
- Compares against stored baseline scores
- Fails if metrics drop beyond tolerance thresholds
- Provides detailed pass/fail report

```bash
# Run regression tests
python3 tests/regression_suite.py

# Update baselines
python3 tests/regression_suite.py --update-baselines
```

### Test Cases

JSON files defining evaluation scenarios. See `test_cases/README.md` for schema.

Current test cases:
- `golden_flow.json` - Q-stage golden flow (all suggestions acceptable)
- `m_golden_flow_second_item.json` - M-stage with no suggestions
- `q_synthetic_field_overview.json` - Intent-type based acceptability
- `q_synthetic_strict_intent.json` - Strict intent matching
- `q_synthetic_top1_only.json` - Only top-1 acceptable

## Metrics

| Metric | Description | Range | Goal |
|--------|-------------|-------|------|
| MRR@K | Mean Reciprocal Rank at K | 0-1 | Higher is better |
| Recall@K | Fraction of acceptable in top-k | 0-1 | Higher is better |
| ECR | Evidence Coverage Rate | 0-1 | Higher is better* |
| TRI | Top-K Redundancy Index | 0-1 | Lower is better |
| Hubness | Fraction hitting common targets | 0-1 | Lower is better |

*ECR is currently 0 as evidence shards are not yet implemented.

## CLI Commands

### `eval:regression`

Run the regression suite against stored baselines.

```bash
python3 src/cli.py eval:regression
python3 src/cli.py eval:regression --update-baselines
python3 src/cli.py eval:regression --data-dir prototype/data_dogfood
```

### `eval:dashboard`

Display evaluation metrics dashboard.

```bash
python3 src/cli.py eval:dashboard
python3 src/cli.py eval:dashboard --data-dir prototype/data_dogfood
```

## Adding New Test Cases

1. Create a JSON file in `test_cases/` following the schema
2. Run `python3 tests/eval_harness.py` to verify
3. Run `python3 tests/regression_suite.py --update-baselines` to add to baselines
4. Commit the new test case and updated baselines

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Error running tests |
