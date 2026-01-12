# Complexity Metrics (S06)

How Field-Kit measures complexity to detect soup and guide governance.

## Overview

Complexity metrics provide quantitative signals for governance decisions. All metrics are:
- **Deterministic**: Same input → same output
- **Stdlib-only**: No external dependencies
- **Offline**: Computed from stored data, not real-time

The core insight comes from the Coffee Automaton paper: coarse-grain first, then measure complexity.

## Key Metrics

### Apparent Complexity

The primary metric, measured in gzip bytes of a coarse-grained snapshot.

```python
from fieldkit.complexity import apparent_complexity

complexity = apparent_complexity(data_dir)  # Returns int (bytes)
```

**Interpretation:**
- Higher = more structured/complex state
- Lower = simpler/more compressible
- Sudden increases may indicate soup formation

**How it works:**
1. Create coarse-grained snapshot (counts, histograms, stats)
2. Serialize to JSON
3. Gzip compress
4. Return byte count

This is a practical proxy for Kolmogorov complexity.

### Branching Factor

Average number of suggestions presented per decision point.

```python
from fieldkit.complexity import branching_factor_from_events

bf = branching_factor_from_events(data_dir)  # Returns float
```

**Interpretation:**
- 4.0 = healthy (4 suggestions per decision)
- Very high = possibly too many choices (soup)
- Very low = limited exploration

Computed from `bond.suggestions.presented` events.

### Duplicate Rate

Fraction of items that are near-duplicates by title.

```python
from fieldkit.complexity import duplicate_rate

rate, count = duplicate_rate(data_dir)  # (float, int)
```

**Interpretation:**
- 0.0 = no duplicates
- >0.15 = concerning, suggests pruning
- Uses title prefix hashing (first 50 chars)

### Suggestion Entropy

Shannon entropy of suggestion intent distribution.

```python
from fieldkit.complexity import suggestion_entropy_from_events

entropy, max_entropy = suggestion_entropy_from_events(data_dir)
```

**Interpretation:**
- High entropy (close to max) = diverse suggestions
- Low entropy = concentrated on few intents
- Max entropy for 4 intents = 2.0 bits

**Entropy Ratio** = entropy / max_entropy (0.0-1.0)

### Hubness Score

Fraction of edges touching the top-N most connected nodes.

```python
from fieldkit.complexity import hubness_score

hubness, top_hubs = hubness_score(data_dir, top_n=3)
```

**Interpretation:**
- High hubness (>0.6) = few nodes dominate (soup indicator)
- Low hubness = distributed connectivity (healthy)
- Returns top hub IDs for investigation

## Coarse-Grained Snapshot

The snapshot collapses raw data into summary statistics:

```python
{
    "counts": {
        "items": 42,
        "bonds": 15,
        "draft_bonds": 3,
        "events": 156
    },
    "item_types": {
        "Q": 30,
        "M": 10,
        "D": 2
    },
    "event_types": {
        "item.created": 42,
        "bond.executed": 15,
        ...
    },
    "bond_stats": {
        "type_distribution": {
            "clarify": 5,
            "concretize": 4,
            ...
        }
    },
    "suggestion_stats": {
        "total_presented": 100,
        "intent_distribution": {...},
        "presentation_count": 25
    },
    "graph_stats": {
        "avg_degree": 2.5,
        "max_degree": 8,
        "min_degree": 1,
        "connected_nodes": 35,
        "orphan_count": 7,
        "orphan_rate": 0.166
    }
}
```

This macrostate is what gets gzip-compressed for apparent complexity.

## Derived Indicators

### is_soupy

Heuristic check for "soup" state:

```python
metrics = compute_all_metrics(data_dir)
if metrics["is_soupy"]:
    print("Soup detected!")
```

Triggers when ANY of:
- Hubness > 0.6
- Duplicate rate > 0.2
- Orphan rate > 0.5 (with >5 items)
- Avg degree > 5

### is_sparse

Check if graph lacks connections:

```python
if metrics["is_sparse"]:
    print("Consider more exploration")
```

Triggers when:
- Bond ratio < 0.3 (fewer than 0.3 bonds per item)

## Compute All Metrics

Get everything in one call:

```python
from fieldkit.complexity import compute_all_metrics, format_metrics_report

metrics = compute_all_metrics(data_dir)
print(format_metrics_report(metrics))
```

Returns:
```python
{
    "snapshot": {...},           # Coarse-grained snapshot
    "apparent_complexity": 385,  # gzip bytes
    "branching_factor": 4.0,
    "duplicate_rate": 0.05,
    "duplicate_count": 2,
    "suggestion_entropy": 1.92,
    "max_entropy": 2.0,
    "entropy_ratio": 0.96,
    "hubness": 0.45,
    "top_hubs": ["it_001", "it_002", "it_003"],
    "is_soupy": False,
    "is_sparse": False,
}
```

## Usage in Governance

The governor uses these metrics to decide actions:

```python
from fieldkit.governor import ComplexityGovernor

governor = ComplexityGovernor()
observation = governor.observe(data_dir)

# Metrics are available in observation
print(observation.metrics["apparent_complexity"])
print(observation.metrics["hubness"])
```

Threshold checks:
- `complexity > 800` → consider bundling
- `hubness > 0.7` → consider bundling
- `duplicate_rate > 0.15` → consider pruning
- `entropy_ratio < 0.5` → consider branching

## Research Background

### Coffee Automaton Paper

Key insight: Apparent complexity peaks then decays as a system evolves.

> "A cup of coffee doesn't appear complex at equilibrium (all mixed). Complexity peaks during the transition when structure is visible."

For Field-Kit:
- Early Fields are simple (low complexity)
- Active Fields develop structure (medium complexity)
- Soup has high but meaningless complexity (many connections, no structure)

### MDL Principle

Minimum Description Length: prefer models where L(H) + L(D|H) is minimal.

For governance:
- L(H) = complexity of the Field structure
- L(D|H) = effort to navigate given the structure
- Bundling reduces both by consolidating related items
- Pruning reduces L(H) by removing redundant items

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/complexity.py` | All complexity metrics |
| `src/fieldkit/governor.py` | Uses metrics for governance |
| `tests/test_governance.py` | Metric tests |

## References

- Research: `research/27-essays/20_quantifying_rise_fall_complexity_closed_systems_coffee_automaton.md`
- Research: `research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md`
- Related: `docs/architecture/MEMORY_GOVERNANCE.md`
