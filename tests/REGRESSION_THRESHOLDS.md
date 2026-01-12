# Regression Thresholds Rationale

This document explains the regression thresholds used in `regression_suite.py`.

## Current Thresholds

| Metric | Tolerance | Critical | Rationale |
|--------|-----------|----------|-----------|
| `mrr_at_k` | 0.1 | No | Allow 10% drop; ranking may vary with data changes |
| `recall_at_k` | 0.1 | No | Allow 10% drop; same rationale as MRR |
| `golden_flow_continuation` | 0.0 | Yes | Must not drop; core quality signal |
| `ecr` | 0.0 | No | Currently 0; can only go up when evidence implemented |
| `tri_at_k` | 0.2 | No | Higher tolerance; proxy metric with natural variance |

## Threshold Philosophy

### Critical Metrics

Metrics marked as `critical: True` have **zero tolerance** for regression. Any drop triggers immediate failure. These protect core functionality.

**golden_flow_continuation**: The primary quality signal. If the golden flow continuation rate drops, it means the system is no longer surfacing the expected next steps. This is a hard requirement.

### Non-Critical Metrics

Non-critical metrics have **tolerance ranges** that allow for natural variance while catching significant regressions.

**mrr_at_k, recall_at_k (tolerance: 0.1)**: Ranking metrics can vary slightly with:
- Changes to suggestion ordering algorithms
- New items in the corpus
- Modified TF-IDF or similarity weights

A 10% tolerance catches meaningful regressions while ignoring noise.

**ecr (tolerance: 0.0)**: Evidence Coverage Rate is currently 0% because evidence shards aren't implemented yet. When evidence is added, this can only improve (go up). Zero tolerance means we catch any accidental removal of evidence functionality.

**tri_at_k (tolerance: 0.2)**: Top-K Redundancy Index measures lexical diversity. This proxy metric has more variance because:
- It uses token overlap as a diversity proxy
- Suggestion content changes affect TRI
- Higher tolerance (20%) prevents false alarms

## Updating Thresholds

If you need to adjust thresholds:

1. Document the reason in this file
2. Update `DEFAULT_THRESHOLDS` in `regression_suite.py`
3. Run the suite to verify the change
4. Commit with a clear message explaining the adjustment

## When to Override

Consider tightening thresholds when:
- A metric becomes more stable and reliable
- You have higher confidence in the measurement
- The feature is mature and should not regress

Consider loosening thresholds when:
- A metric is inherently noisy
- The underlying implementation is being actively developed
- External factors (LLM responses, etc.) add variance

## Baseline Updates

Run `--update-baselines` after intentional changes:
- New ranking algorithm
- Modified suggestion logic
- Added test cases
- Improved metrics implementation

Never update baselines to hide regressions. Investigate failures first.
