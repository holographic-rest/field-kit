# Sanity Checks Architecture

**Sprint:** S01 (Foundation Stabilization)
**Status:** Implemented
**Module:** `src/fieldkit/sanity_checks.py`

---

## Overview

Pre-activation sanity checks validate inputs at pipeline boundaries before processing. Inspired by CS231n debugging discipline, these checks catch errors early and make failures traceable.

---

## Core Concepts

### Warn Mode vs Strict Mode

Checks operate in one of three modes:

| Mode | Behavior |
|------|----------|
| `warn` | Log warning, continue execution |
| `strict` | Raise ValueError immediately |
| `silent` | Return result, no logging |

Default is `warn` mode for non-blocking diagnostics.

### Check Boundaries

Sanity checks are placed at critical boundaries:

1. **Candidate set entry**: Before processing candidates
2. **Score normalization**: After computing probabilities
3. **ID assignment**: Before using IDs in references
4. **Event creation**: Before logging events

---

## API Reference

### SanityChecker Class

```python
from fieldkit.sanity_checks import SanityChecker

checker = SanityChecker(mode="warn")  # or "strict", "silent"

# Run checks
result = checker.check_candidates(candidates)
result = checker.check_probabilities(scores)
result = checker.check_id_format(item_id, id_type="item")
result = checker.check_event(event_dict)
result = checker.check_no_duplicates(items, key_fn=lambda x: x["id"])

# Get summary
summary = checker.summary()
# {"total": 5, "passed": 4, "failed": 1, "failures": [...]}

# Reset for new check sequence
checker.reset()
```

### CheckResult Dataclass

```python
@dataclass
class CheckResult:
    passed: bool           # True if check passed
    check_name: str        # Name of the check
    message: str           # Human-readable message
    context: Dict          # Additional context for debugging
```

### Convenience Functions

For quick one-off checks:

```python
from fieldkit.sanity_checks import (
    validate_candidate_set,
    validate_probabilities,
    validate_id,
    validate_event,
)

if not validate_candidate_set(candidates):
    # Handle empty/invalid candidates
    pass

if not validate_probabilities(scores, sum_to_one=True):
    # Handle invalid probability distribution
    pass
```

---

## Available Checks

### 1. Candidates Check

Validates that candidate sets are non-empty and meet minimum count:

```python
checker.check_candidates(
    candidates=[...],      # List of candidates
    min_count=1,           # Minimum required (default: 1)
    context={"step": "selection"}
)
```

**Fails if:**
- `candidates` is None
- Length < `min_count`

### 2. Probabilities Check

Validates probability scores are normalized:

```python
checker.check_probabilities(
    scores=[0.1, 0.2, 0.3, 0.4],
    sum_to_one=True,       # Check if sum ≈ 1.0
    context={}
)
```

**Fails if:**
- Any score < 0 or > 1
- `sum_to_one=True` and sum not ≈ 1.0 (±0.01)

### 3. ID Format Check

Validates IDs match canonical patterns:

```python
checker.check_id_format(
    id_value="it_ABCD1234",
    id_type="item",        # Optional: item, bond, episode, network
    context={}
)
```

**Canonical patterns:**
| Type | Pattern |
|------|---------|
| item | `it_[A-Za-z0-9_]{4,}` |
| bond | `bd_[A-Za-z0-9_]{4,}` |
| episode | `ep_[A-Za-z0-9_]{4,}` |
| network | `nt_[A-Za-z0-9_]{4,}` |
| holologue | `hl_[A-Za-z0-9_]{4,}` |

### 4. Event Check

Validates events have required fields and canonical names:

```python
checker.check_event(
    event={"name": "item.created", "ts": "2025-01-01T00:00:00Z"},
    context={}
)
```

**Required fields:** `name`, `ts`

**Canonical event names:**
- `app.first_run.started`
- `episode.created`
- `credits.delta`
- `item.created`, `item.updated`
- `bond.suggestions.presented`, `bond.draft_created`
- `bond.run_requested`, `bond.executed`
- `holologue.run_requested`, `holologue.completed`
- `bond.proposals.presented`
- `ledger.opened`
- `store.commit`
- `tutorial.started`

### 5. Duplicates Check

Validates no duplicates in a list:

```python
checker.check_no_duplicates(
    items=[{"id": "a"}, {"id": "b"}],
    key_fn=lambda x: x["id"],  # Extract key for comparison
    context={}
)
```

---

## Integration Examples

### With ResidualModule

```python
from fieldkit.residual import ResidualModule
from fieldkit.sanity_checks import SanityChecker

class ScoringModule(ResidualModule):
    def __init__(self):
        super().__init__("ScoringModule")
        self.checker = SanityChecker(mode="warn")

    def precheck(self, state):
        # Validate candidates exist
        self.checker.check_candidates(
            state.get("candidates", []),
            min_count=1,
            context={"module": self.name}
        )
        return state

    def propose_delta(self, state):
        scores = self._compute_scores(state["candidates"])

        # Validate scores before returning
        self.checker.check_probabilities(scores)

        return {"scores": scores}
```

### Collecting Failures

```python
checker = SanityChecker(mode="warn")

# Run multiple checks
checker.check_candidates(step1_candidates)
checker.check_probabilities(step1_scores)
checker.check_candidates(step2_candidates)
checker.check_probabilities(step2_scores)

# Get summary
summary = checker.summary()
if summary["failed"] > 0:
    for failure in summary["failures"]:
        print(f"WARN: {failure['check']} - {failure['message']}")
```

---

## Debugging Tips

### 1. Use Context

Pass context to help identify failures:

```python
checker.check_candidates(
    candidates,
    context={
        "step": "diversity_selection",
        "item_id": current_item.id,
        "batch": batch_number
    }
)
```

### 2. Switch Modes for Testing

Use strict mode in tests to catch issues early:

```python
# In tests
checker = SanityChecker(mode="strict")

def test_my_function():
    # Will raise ValueError if any check fails
    result = my_function(checker)
```

### 3. Log Summaries

At the end of a pipeline, log the checker summary:

```python
import logging

summary = checker.summary()
if summary["failed"] > 0:
    logging.warning(f"Sanity check failures: {summary}")
```

---

## Design Principles

### 1. Fail Soft by Default

Warn mode allows the system to continue even with suboptimal inputs. This is important for:
- Graceful degradation
- Production stability
- Debugging without blocking

### 2. Checks Are Cheap

Checks should be fast and side-effect free. Don't do I/O or heavy computation in checks.

### 3. Context Is Key

Always include context to make failures actionable:

```python
# Bad: No context
checker.check_candidates(candidates)

# Good: Rich context
checker.check_candidates(
    candidates,
    context={"function": "select_top_k", "k": 5, "input_size": len(all_items)}
)
```

---

## Future Extensions

- **Check chaining**: `checker.check_all([check1, check2, ...])`
- **Custom checks**: Register custom validation functions
- **Metrics export**: Track check pass/fail rates over time
- **Threshold checks**: `check_min/max(value, threshold)`
