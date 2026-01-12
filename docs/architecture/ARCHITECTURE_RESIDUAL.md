# Residual Module Architecture

**Sprint:** S01 (Foundation Stabilization)
**Status:** Implemented
**Module:** `src/fieldkit/residual.py`

---

## Overview

The Residual Module pattern provides a consistent interface for pipeline steps that:
- Validate inputs before transformation (precheck)
- Propose changes as deltas (propose_delta)
- Apply changes via residual addition (apply)

This architecture is inspired by ResNet's residual learning, where each module learns a delta from the identity function.

---

## Core Concepts

### Residual = Identity + Delta

Each module computes:
```
output = input + delta
```

Where `delta` can be:
- **Zero** (identity): Module makes no changes
- **Non-zero**: Module adds/modifies state

This enables:
- **Graceful degradation**: Remove a module = revert to identity
- **Safe composition**: Modules don't overwrite each other's outputs
- **Traceable debugging**: Delta shows exactly what changed

### Pre-Activation

Before computing delta, modules validate and normalize input via `precheck()`. This follows the pre-activation pattern from ResNet v2, where normalization happens before the transformation.

---

## API Reference

### ResidualModule (Abstract Base Class)

```python
from fieldkit.residual import ResidualModule

class MyModule(ResidualModule):
    def precheck(self, state: dict) -> dict:
        # Validate and normalize state
        # Raise ValueError if invalid
        return state

    def propose_delta(self, prechecked_state: dict) -> dict:
        # Compute changes to make
        # Return empty dict for no-op
        return {"new_key": "new_value"}

    # apply() is inherited: return {**state, **delta}
```

### IdentityModule

A no-op module that passes state through unchanged:

```python
from fieldkit.residual import IdentityModule

identity = IdentityModule()
output, trace = identity.run({"x": 1})
# output == {"x": 1}
# trace.delta == {}
```

### ResidualPipeline

Chain multiple modules in sequence:

```python
from fieldkit.residual import ResidualPipeline

pipeline = ResidualPipeline()
pipeline.add(module_a)
pipeline.add(module_b)

output, traces = pipeline.run(initial_state)
# traces is a list of ResidualTrace objects
```

### ResidualTrace

Trace record for debugging:

```python
@dataclass
class ResidualTrace:
    module_name: str           # Name of the module
    prechecked_state_hash: str # SHA256 hash of prechecked state
    delta: Dict[str, Any]      # The delta that was applied
    confidence: float          # Module's confidence score
    warnings: List[str]        # Any warnings generated
```

---

## Usage Examples

### Basic Module

```python
from fieldkit.residual import ResidualModule

class ScoreNormalizer(ResidualModule):
    """Normalizes scores to [0, 1] range."""

    def precheck(self, state: dict) -> dict:
        if "scores" not in state:
            raise ValueError("State must contain 'scores' key")
        return state

    def propose_delta(self, prechecked_state: dict) -> dict:
        scores = prechecked_state["scores"]
        if not scores:
            return {}  # Identity for empty scores

        min_s, max_s = min(scores), max(scores)
        if min_s == max_s:
            return {"normalized_scores": [0.5] * len(scores)}

        normalized = [(s - min_s) / (max_s - min_s) for s in scores]
        return {"normalized_scores": normalized}
```

### Pipeline with Tracing

```python
from fieldkit.residual import ResidualPipeline

pipeline = ResidualPipeline([
    ScoreNormalizer(),
    TopKSelector(k=5),
    DiversityFilter(lambda_=0.7),
])

state = {"scores": [10, 20, 30, 40, 50]}
output, traces = pipeline.run(state)

# Debug: See what each module did
for trace in traces:
    print(f"{trace.module_name}: delta={trace.delta}")
```

---

## Design Principles

### 1. Deltas Are Additive

Deltas should add new keys or modify existing ones, not remove keys:

```python
# Good: Add a new key
return {"filtered_items": items[:5]}

# Bad: Overwrite with fewer keys
return {"items": items[:5]}  # Loses other state
```

### 2. Precheck Is Validation, Not Transformation

Keep precheck focused on validation:

```python
# Good: Validate and return
def precheck(self, state):
    if not state.get("items"):
        raise ValueError("Items required")
    return state

# Bad: Transform in precheck
def precheck(self, state):
    state["items"] = [x.lower() for x in state["items"]]  # Don't do this
    return state
```

### 3. Identity Is Always Safe

A module can return `{}` (empty delta) at any time. This is the identity case and should always be safe:

```python
def propose_delta(self, state):
    if self._should_skip(state):
        return {}  # Safe identity
    return self._compute_changes(state)
```

---

## Integration Points

### With Sanity Checks

Combine with `sanity_checks.py` for validation:

```python
from fieldkit.sanity_checks import SanityChecker

class ValidatedModule(ResidualModule):
    def __init__(self):
        super().__init__()
        self.checker = SanityChecker(mode="warn")

    def precheck(self, state):
        self.checker.check_candidates(state.get("candidates", []))
        return state
```

### With Instrumentation

Log module behavior for debugging:

```python
from fieldkit.instrumentation import compute_stats_from_events

# After pipeline run
summary = pipeline.summary()
print(f"Modules: {summary['modules_count']}")
print(f"Non-identity: {summary['modules_with_delta']}")
```

---

## Future Extensions

- **Rollback support**: Save state snapshots for undo
- **Async modules**: Support `async` precheck/propose_delta
- **Confidence-weighted deltas**: Scale delta by confidence
- **Module composition**: Combine modules into meta-modules
