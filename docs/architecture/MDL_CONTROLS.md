# MDL Controls Architecture

> **Sprint S09 — January 2025**

This document describes the Minimum Description Length (MDL) scoring and structure-vs-noise gates implemented in Sprint S09.

---

## Overview

MDL Controls help the Field avoid:
- **Saving noise**: Random, unstructured content that doesn't reduce future description length
- **Saving boilerplate**: Generic, too-compressible content that doesn't add value
- **Uncontrolled complexity**: System drift into "soup" where everything relates to everything

The design is based on four research essays:
- **Essay #24 (MDL Tutorial)**: Learning as data compression
- **Essay #26 (Kolmogorov)**: Structure vs noise as compressibility
- **Essay #6 (Hinton)**: Description length budgets for weights
- **Essay #20 (Coffee Automaton)**: Apparent complexity measurement

---

## Key Concepts

### Description Length (DL) Proxy

We use gzip compression as a practical proxy for Kolmogorov complexity:

```python
DL(x) = gzip_bytes(json.dumps(x, sort_keys=True))
```

- Higher DL = more complex/structured
- Lower DL = simpler/more compressible
- Very high DL with no structure = likely noise
- Very low DL = likely generic boilerplate

### MDL Scoring

MDL score combines model complexity and fit quality:

```
MDL_score = model_cost(strategy) + data_cost(outcomes)
```

**Model cost** captures strategy complexity:
- Rules: 8 bits per rule
- Parameters: 4 bits per parameter
- Token budget: 0.1 bits per token
- Modules: 16 bits per module

**Data cost** captures how well the strategy fits:
- Mistakes: 10 bits per mistake
- Backtracks: 8 bits per backtrack
- Overrides: 12 bits per override
- Ungrounded suggestions: 6 bits each

Lower MDL score = better. Prefer simpler strategies that fit well.

### Thread Model

A thread model represents the current context:
- Top handles/entities from recent items
- Open questions from session state
- Keywords from evidence shards

Used to compute overlap with artifacts being evaluated.

---

## Structure-vs-Noise Gate

The gate decides whether an artifact should be saved:

```python
result = structure_vs_noise_gate(artifact, thread_model)
# result["allowed"] = True/False
# result["bucket"] = "too_simple" | "too_random" | "structured"
# result["reason"] = explanation
```

### Decision Rules

1. **High overlap** (>20% with thread model) → Allow (structured)
2. **Low DL + Low overlap** → Reject (too_simple/boilerplate)
3. **High DL + Low overlap** → Reject (too_random/noise)
4. **Midband DL OR acceptable overlap** → Allow (structured)

### Thresholds

Default thresholds (calibrated from cohort stats):
- `dl_low_ratio`: 0.3 (reject if DL < median × 0.3)
- `dl_high_ratio`: 2.5 (reject if DL > median × 2.5)
- `min_overlap`: 0.1 (minimum thread overlap to allow)

---

## Complexity Budget

`ComplexityBudget` enforces soft limits on system growth:

```python
budget = ComplexityBudget(
    model_max=1000,    # Model complexity budget
    memory_max=10000,  # Field/memory budget
    total_max=12000,   # Combined budget
)

ok, reason = budget.check(model_cost=500, memory_cost=5000)
```

These are soft limits that generate warnings, not hard failures.

---

## Integration Points

### Bundling (`bundling.py`)

MDL gate blocks mega-bundles and thin-evidence bundles:

```python
from fieldkit.bundling import apply_mdl_gate_to_proposals

proposals = detect_bundle_candidates(data_dir)
proposals = apply_mdl_gate_to_proposals(proposals, thread_model)

# Blocked proposals have:
# - blocked_by_mdl: True
# - mdl_reason: explanation
```

### Pruning (`pruning.py`)

MDL gate protects structured novelty from pruning:

```python
from fieldkit.pruning import apply_structured_novelty_protection

candidates = detect_prune_candidates(data_dir)
candidates = apply_structured_novelty_protection(candidates, thread_model)

# Protected candidates have:
# - lowered priority
# - "[MDL PROTECTED: reason]" in details
```

### Governor Integration

The governance layer can include MDL rationale in observations.

---

## Example Gate Outputs

### Boilerplate (Rejected)

```python
artifact = {"title": "OK", "body": "OK"}
cohort_stats = {"median_dl": 200}

# Result:
{
    "allowed": False,
    "bucket": "too_simple",
    "reason": "Too simple (DL=43 < 60) with low overlap (0.00%)",
    "dl_artifact": 43,
    "overlap_score": 0.0
}
```

### Noise (Rejected)

```python
artifact = {"title": "Random", "body": "xyz1abc xyz2abc xyz3abc..."}
cohort_stats = {"median_dl": 50}

# Result:
{
    "allowed": False,
    "bucket": "too_random",
    "reason": "Too random (DL=892 > 125) with low overlap (0.00%)",
    "dl_artifact": 892,
    "overlap_score": 0.0
}
```

### Structured Novelty (Allowed)

```python
artifact = {"title": "ML Pipeline Design", "body": "...machine learning..."}
thread_model = {"handles": [{"quote": "machine learning"}]}

# Result:
{
    "allowed": True,
    "bucket": "structured",
    "reason": "Acceptable overlap (25.00%) with thread model",
    "dl_artifact": 156,
    "overlap_score": 0.25
}
```

---

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/mdl_scoring.py` | MDL scoring, budget, gate |
| `src/fieldkit/bundling.py` | Bundle proposal MDL integration |
| `src/fieldkit/pruning.py` | Prune candidate MDL protection |
| `tests/test_mdl_controls.py` | Unit tests (39 tests) |

---

## Design Decisions

### Why gzip proxy?

- No external dependencies
- Deterministic and reproducible
- Reasonable approximation of Kolmogorov complexity
- Fast enough for real-time use

### Why suggest-only?

- MDL controls mark/annotate, don't block
- Keeps system predictable
- User retains final control
- Gradual adoption path

### Why token overlap?

- Simple, interpretable metric
- Captures "relevance to current context"
- Complements compression-based DL
- Works without embeddings

---

## Limitations

- **Heuristic, not formal**: Uses gzip proxy, not true Kolmogorov complexity
- **Fixed weights**: Model/data cost weights are hand-tuned
- **No NML**: Doesn't implement refined MDL (normalized maximum likelihood)
- **Local context**: Thread model is current session only

---

## Future Work

1. **Learned weights**: Tune cost weights from user feedback
2. **Embedding-based overlap**: Use semantic similarity instead of token overlap
3. **Time-decay**: Weight recent artifacts more heavily in cohort stats
4. **Budget auto-tuning**: Adjust budgets based on Field growth rate

---

## See Also

- [MEMORY_GOVERNANCE.md](MEMORY_GOVERNANCE.md) — Governance layer (S06)
- [COMPLEXITY_METRICS.md](COMPLEXITY_METRICS.md) — Complexity measurement
- Research essays: MDL (#24), Kolmogorov (#26), Hinton (#6), Coffee Automaton (#20)
