# S09: Complexity & MDL Controls
**Days:** Jan 3 (1 day)  
**Theme:** Complexity budgets and structure-vs-noise gates

---

## Objective

Implement MDL scoring and structure-vs-noise gates to prevent the Field from saving noise or becoming too generic. This completes the complexity governance from S06 with principled selection criteria.

---

## Why This Matters for Fellowship Narrative

- **Demonstrates MDL thinking**: Principled model selection via description length
- **Prevents noise**: Structure-vs-noise gates filter out random/unhelpful artifacts
- **Shows algorithmic statistics**: Kolmogorov-style compressibility checks
- **Enables curation**: System can auto-curate what gets saved

---

## Inputs

### Research Documents
- `research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md` - MDL principle
- `research/27-essays/26_kolmogorov_complexity_algorithmic_randomness.md` - Structure vs noise
- `research/27-essays/06_keeping_neural_networks_simple.md` - Description length budgets
- `research/27-essays/20_quantifying_rise_fall_complexity_closed_systems_coffee_automaton.md` - Complexity measurement

### Repo Modules
- `src/fieldkit/complexity.py` - Complexity metrics (from S06)
- `src/fieldkit/bundling.py` - Bundling (from S06)

---

## Tasks

### Task 1: Implement MDL Scoring
1. Create `src/fieldkit/mdl_scoring.py` with:
   ```python
   def mdl_score(strategy, outcomes):
       model_cost = compute_model_cost(strategy)  # Rules + params + tokens
       data_cost = compute_data_cost(outcomes)    # Mistakes + backtracks
       return model_cost + data_cost
   ```
2. Use to compare hololink/routing strategies

### Task 2: Implement Structure-vs-Noise Gate
1. Create `structure_vs_noise_gate(artifact, thread_model)`:
   - Compute compressibility conditioned on thread model
   - Score: how well artifact can be predicted from model + shards
   - Gate: only allow Vault save if (a) supported by shards AND (b) reduces future description length
2. Integrate before Vault saves

### Task 3: Add Complexity Budget Enforcement
1. Create `ComplexityBudget` class:
   - Model complexity budget (params, tokens)
   - Memory complexity budget (Vault size, graph branching)
   - Total budget (system stays compressible)
2. Enforce in bundling/pruning decisions

### Task 4: Test MDL Selection
1. Create test case comparing strategies:
   - Strategy A: Many rules, low errors
   - Strategy B: Few rules, high errors
   - Strategy C: Balanced
2. Verify MDL selects best (lowest total cost)

### Task 5: Test Noise Filtering
1. Create test case with noise artifacts:
   - Generic boilerplate (too compressible)
   - Random word salad (too incompressible)
   - Structured novelty (sweet spot)
2. Verify gate filters extremes, keeps middle

---

## Acceptance Criteria

- [ ] MDL scoring computes (model cost + data cost)
- [ ] Structure-vs-noise gate exists (compressibility check)
- [ ] Complexity budgets enforced (model + memory + total)
- [ ] MDL selection test passes (chooses best strategy)
- [ ] Noise filtering test passes (filters extremes)
- [ ] Documentation: `docs/architecture/MDL_CONTROLS.md`

---

## Test Plan

### Test 1: MDL Scoring
```python
from fieldkit.mdl_scoring import mdl_score
strategy = {...}
outcomes = {"mistakes": 5, "backtracks": 2}
score = mdl_score(strategy, outcomes)
assert score > 0
```
**Expected:** MDL score computes

### Test 2: Structure Gate
```python
from fieldkit.mdl_scoring import structure_vs_noise_gate
artifact = {...}
thread_model = {...}
allowed = structure_vs_noise_gate(artifact, thread_model)
assert isinstance(allowed, bool)
```
**Expected:** Gate returns boolean

### Test 3: Budget Enforcement
```python
from fieldkit.mdl_scoring import ComplexityBudget
budget = ComplexityBudget(model_max=1000, memory_max=10000)
assert budget.check(model_cost=500, memory_cost=5000) == True
assert budget.check(model_cost=2000, memory_cost=5000) == False
```
**Expected:** Budget enforces limits

---

## Documentation Outputs

1. `docs/architecture/MDL_CONTROLS.md` - MDL scoring and gates
2. Update `docs/architecture/MEMORY_GOVERNANCE.md` with MDL integration

---

## Fallback Plan

If MDL is too complex:
- **Fallback:** Simple compressibility check only (gzip size)
- **Minimum deliverable:** Structure-vs-noise gate exists
- **Document:** Plan to add full MDL scoring later

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/complexity.py` from S06, `src/fieldkit/bundling.py` from S06)
- **Research docs:** All paths match actual files

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S09: Complexity & MDL Controls.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S09_complexity_controls.md
Also read: research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md

Your goal:
1. Implement MDL scoring (model cost + data cost)
2. Implement structure-vs-noise gate (compressibility check)
3. Add complexity budget enforcement (model + memory + total)
4. Test MDL selection (chooses best strategy)
5. Test noise filtering (filters extremes)

Constraints:
- MDL scoring can be heuristic (approximate costs)
- Structure gate checks: (a) supported by shards AND (b) reduces description length
- Budgets are soft limits (warn, don't hard-fail)
- Must integrate with bundling/pruning from S06

After completion:
- Verify MDL selects best strategy
- Test noise filtering works
- Document MDL controls architecture

Start by implementing MDL scoring.
```

