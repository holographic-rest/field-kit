# Memory Governance (S06)

How Field-Kit manages complexity and suggests curation actions.

## Overview

Memory Governance provides a suggest-only layer that observes Field state and recommends governance actions. It never auto-executes destructive operations - all actions are proposals that require user confirmation.

The system addresses the "soup problem": when Fields become over-connected, cluttered with duplicates, or lose navigability. Governance detects these states early and suggests corrective actions.

## Key Concepts

### Governance Actions

The governor can suggest one of four actions:

| Action | When Suggested | Effect |
|--------|----------------|--------|
| **bundle** | High complexity, many connections | Consolidate related items |
| **prune** | Duplicates, orphans, low-entropy | Archive stale items |
| **branch** | Sparse graph, low entropy | Encourage exploration |
| **continue** | Healthy state | No action needed |

### Suggest-Only Principle

From the sprint requirements:

> "Do NOT auto-execute destructive actions - only suggest and log proposed actions."

All governance operations produce proposals or plans that the user can review before execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Command                               │
│           govern:report / govern:bundle:propose              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 ComplexityGovernor                           │
│                  (governor.py)                               │
│                                                              │
│   observe(data_dir) → GovernanceObservation                 │
│   - Computes metrics via complexity.py                      │
│   - Applies thresholds                                      │
│   - Suggests action with rationale                          │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Complexity    │ │    Bundling     │ │    Pruning      │
│   Metrics       │ │   Proposals     │ │     Plans       │
│                 │ │                 │ │                 │
│ (complexity.py) │ │ (bundling.py)   │ │ (pruning.py)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## ComplexityGovernor

### Usage

```python
from fieldkit.governor import ComplexityGovernor

governor = ComplexityGovernor()
observation = governor.observe(data_dir)

print(observation.action)      # "bundle" | "prune" | "branch" | "continue"
print(observation.rationale)   # Human-readable explanation
print(observation.confidence)  # 0.0 to 1.0
```

### GovernanceObservation

```python
@dataclass
class GovernanceObservation:
    timestamp: str
    data_dir: str
    metrics: Dict[str, Any]      # All computed metrics
    thresholds: Dict[str, Any]   # Active thresholds
    action: str                  # Suggested action
    rationale: str               # Why this action
    confidence: float            # 0.0 to 1.0
    details: List[str]           # Supporting observations
```

### Thresholds

Default thresholds (conservative):

```python
@dataclass
class GovernanceThresholds:
    # Bundle thresholds
    complexity_high: int = 800      # bytes - bundle if above
    hubness_high: float = 0.7       # fraction - bundle if above
    avg_degree_high: float = 4.0    # bundle if above

    # Prune thresholds
    duplicate_rate_high: float = 0.15  # prune if above
    orphan_rate_high: float = 0.4      # prune if above

    # Branch thresholds
    entropy_ratio_low: float = 0.5     # branch if below
    bond_ratio_low: float = 0.2        # branch if below

    # Minimums
    min_items_for_action: int = 5      # don't act on tiny Fields
    min_bonds_for_bundle: int = 3      # need enough to bundle
```

## Bundling

### BundleProposal

```python
@dataclass
class BundleProposal:
    proposal_id: str          # "bp_..." unique ID
    bundle_title: str         # Proposed title for bundle
    constituent_ids: List[str] # Items to be bundled
    action: str               # "bundle"
    status: str               # "proposed" | "accepted" | "rejected"
    rationale: str
    similarity_score: float   # How related are constituents
```

### Detection

```python
from fieldkit.bundling import detect_bundle_candidates

proposals = detect_bundle_candidates(data_dir)
for p in proposals:
    print(f"{p.bundle_title}: {len(p.constituent_ids)} items")
```

Detection uses:
- Title prefix similarity (items with same prefix)
- Shared bond connections (items in same bonds)

### Reversibility

Bundles are "D" type items that keep a reference to their constituents:

```python
{
  "id": "it_BUNDLE123",
  "type": "D",
  "title": "Bundle: Related Items",
  "bundle_metadata": {
    "constituent_ids": ["it_001", "it_002", "it_003"],
    "bundled_at": "2025-12-24T00:00:00Z"
  }
}
```

This allows unbundling if needed.

## Pruning

### PruneCandidate

```python
@dataclass
class PruneCandidate:
    item_id: str
    item_title: str
    reason: str       # "duplicate" | "orphan" | "low_entropy"
    details: str
    priority: float   # 0.0 to 1.0
    related_ids: List[str]
```

### PrunePlan

```python
@dataclass
class PrunePlan:
    plan_id: str               # "pp_..." unique ID
    candidates: List[PruneCandidate]
    status: str                # "proposed" | "executed"
    summary: str
```

### Detection

```python
from fieldkit.pruning import detect_and_plan

plan = detect_and_plan(data_dir)
print(plan.summary)
```

Prune candidates:
- **Duplicates**: Same title prefix
- **Orphans**: No bonds, no recent activity
- **Low-entropy**: Never used as evidence source

### Archive-Only

Pruning does NOT delete items. It proposes setting `status="archived"`:

```python
# If user accepts prune plan
item.status = "archived"
item.archived_at = now_iso()
```

Archived items remain in storage but are filtered from active views.

## CLI Commands

### govern:report

Display governance report with suggested action:

```bash
python3 src/cli.py govern:report
```

Output:
```
============================================================
GOVERNANCE REPORT
============================================================

--- Recommended Action ---
  Action: CONTINUE
  Confidence: 80%
  Rationale: Field appears healthy. Continue normal operation.

--- Supporting Observations ---
  - High hubness (75.0%)
  - Bundle suggested but only 2 bonds (need 3)

--- Key Metrics ---
  Items: 5
  Bonds: 2
  Complexity: 385 bytes
  ...
============================================================
```

### govern:bundle:propose

Detect and display bundle proposals:

```bash
python3 src/cli.py govern:bundle:propose
```

### govern:prune:plan

Detect candidates and display prune plan:

```bash
python3 src/cli.py govern:prune:plan
```

## MDL Controls (S09)

Sprint S09 added MDL-based structure-vs-noise gates to governance.

### Where MDL is Applied

**Bundle Proposals:**
```python
from fieldkit.bundling import apply_mdl_gate_to_proposals

proposals = detect_bundle_candidates(data_dir)
proposals = apply_mdl_gate_to_proposals(proposals, thread_model)

# Blocked proposals have:
# - blocked_by_mdl: True
# - mdl_reason: "Too simple (DL=X < Y) with low overlap (Z%)"
```

**Prune Plans:**
```python
from fieldkit.pruning import apply_structured_novelty_protection

candidates = detect_prune_candidates(data_dir)
candidates = apply_structured_novelty_protection(candidates, thread_model)

# Protected candidates have lowered priority and MDL PROTECTED tag
```

### What is Still Suggest-Only

- MDL gate marks proposals/candidates, does not block execution
- User must approve any bundle or prune action
- Blocked proposals are shown with reason, user can override

See [MDL_CONTROLS.md](MDL_CONTROLS.md) for full details.

---

## Decision Logic

The governor uses a scoring system:

1. **Compute signals** for each action type
2. **Score signals** (0.0-1.0 per action)
3. **Select highest** score above threshold
4. **Default to 'continue'** if no clear signal

Priority order: bundle > prune > branch > continue

This is conservative - when uncertain, default to "continue".

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/complexity.py` | Complexity metrics computation |
| `src/fieldkit/governor.py` | ComplexityGovernor, thresholds, observation |
| `src/fieldkit/bundling.py` | BundleProposal, detection |
| `src/fieldkit/pruning.py` | PruneCandidate, PrunePlan |
| `src/cli.py` | CLI commands |
| `tests/test_governance.py` | Unit tests |

## References

- Sprint: `sprints/12-23-2025-to-01-04-2026/S06_memory_governance.md`
- Research: `research/27-essays/20_quantifying_rise_fall_complexity_closed_systems_coffee_automaton.md`
- Research: `research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md`
- Related: `docs/architecture/COMPLEXITY_METRICS.md`
