# S06: Memory Governance
**Days:** Dec 30-31 (2 days)  
**Theme:** Prevent soup; bundle/prune with MDL discipline

---

## Objective

Implement bundling policies, complexity metrics, and pruning rules to prevent the Field from becoming "soup" (everything linked to everything, ungrounded links, generic suggestions). Use MDL/complexodynamics thinking to govern memory growth.

---

## Why This Matters for Fellowship Narrative

- **Prevents system rot**: Complexity metrics detect drift toward soup
- **Demonstrates governance**: Explicit policies for when to bundle/prune
- **Shows MDL thinking**: Complexity budgets and structure-vs-noise gates
- **Enables long-term use**: System can run for months without collapse

---

## Inputs

### Research Documents
- `research/12-23-2025-research/memory_governence/04_pruning_bundling_policies.md.md` - Governance policies
- `research/27-essays/20_quantifying_rise_fall_complexity_closed_systems_coffee_automaton.md` - Complexity metrics
- `research/27-essays/02_first_law_of_complexodynamics.md` - Complexity budgets
- `research/27-essays/18_variational_lossy_autoencoder.md` - Holologue as compression
- `research/27-essays/24_tutorial_introduction_minimum_description_length_principle.md` - MDL scoring

### Repo Modules
- `src/fieldkit/holologue.py` - Holologue bundling
- `src/fieldkit/store_jsonl.py` - Storage

---

## Tasks

### Task 1: Implement Complexity Metrics
1. Create `src/fieldkit/complexity.py` with:
   - `apparent_complexity(snapshot)`: Coarse-grain → compress → measure
   - `gzip_bytes(macrostate_json)` as proxy
   - `branching_factor(graph)`: Average degree
   - `duplicate_rate(items)`: Near-duplicate detection
   - `suggestion_entropy(suggestions)`: Distribution sharpness
2. Add to instrumentation (from S01)

### Task 2: Implement Bundling Policies
1. Create `src/fieldkit/bundling.py` with:
   - `should_bundle(items)`: Check triggers (high linkage, stabilized, clear purpose)
   - `stop_rules(bundle)`: Check guardrails (too many topics, hubness, thin evidence)
   - `create_bundle(items)`: Create Holologue with reversibility (constituents list)
2. Integrate into holologue pipeline

### Task 3: Implement Pruning Policies
1. Create `src/fieldkit/pruning.py` with:
   - `decay_candidates(candidates, N)`: Hide after N exposures without selection
   - `archive_stale(items)`: Move to cold storage if orphan + stale
   - `protect_evidence(items)`: Never prune if referenced by hololink
2. Add to memory governance loop

### Task 4: Add Complexity Governor
1. Create `ComplexityGovernor` class:
   ```python
   def observe_and_act(self, snapshot):
       complexity = apparent_complexity(snapshot)
       if complexity > threshold:
           return "bundle"  # Force H-bundling
       elif complexity < low_threshold:
           return "branch"  # Encourage new bonds
       else:
           return "continue"  # Keep flow
   ```
2. Integrate into main loop (suggest actions, don't auto-execute)

### Task 5: Implement MDL Scoring
1. Create `src/fieldkit/mdl.py` with:
   - `mdl_score(strategy, outcomes)`: L(strategy) + L(outcomes|strategy)
   - Model cost: rules + parameters + prompt tokens
   - Data cost: mistakes + backtracks + overrides
2. Use to compare bundling strategies

### Task 6: Test Anti-Soup
1. Create test case that simulates soup (many links, low evidence)
2. Verify complexity metrics detect it
3. Verify bundling/pruning prevents it

---

## Acceptance Criteria

- [ ] Complexity metrics compute (apparent complexity, branching factor, etc.)
- [ ] Bundling policies exist (should_bundle, stop_rules)
- [ ] Pruning policies exist (decay, archive, protect)
- [ ] Complexity governor suggests actions
- [ ] MDL scoring compares strategies
- [ ] Anti-soup test case passes
- [ ] Documentation: `docs/architecture/MEMORY_GOVERNANCE.md`

---

## Test Plan

### Test 1: Complexity Metrics
```python
from fieldkit.complexity import apparent_complexity, branching_factor
snapshot = {...}  # Field state
comp = apparent_complexity(snapshot)
assert comp > 0
bf = branching_factor(snapshot["graph"])
assert bf >= 0
```
**Expected:** Metrics compute correctly

### Test 2: Bundling Triggers
```python
from fieldkit.bundling import should_bundle
items = [...]  # High linkage cluster
assert should_bundle(items) == True
```
**Expected:** Bundling triggers correctly

### Test 3: Stop Rules
```python
from fieldkit.bundling import stop_rules
bundle = {...}  # Mega-bundle (too many topics)
assert stop_rules(bundle) == True  # Should stop
```
**Expected:** Stop rules prevent mega-bundles

### Test 4: Anti-Soup
```bash
python3 tests/eval_harness.py --test-case tests/test_cases/soup_simulation.json
```
**Expected:** Complexity metrics detect soup; bundling prevents it

---

## Documentation Outputs

1. `docs/architecture/MEMORY_GOVERNANCE.md` - Governance policies
2. `docs/architecture/COMPLEXITY_METRICS.md` - Complexity measurement
3. Update `docs/architecture/MULTI_SCALE_CONTEXT.md` with bundling integration

---

## Fallback Plan

If governance is too complex:
- **Fallback:** Simple bundling trigger only (high linkage + stabilized)
- **Minimum deliverable:** Complexity metrics exist; bundling works
- **Document:** Plan to add pruning and governor in future

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/holologue.py`, `src/fieldkit/store_jsonl.py`)
- **Research docs:** Paths match actual files (including `memory_governence` folder typo and `.md.md` extension)

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S06: Memory Governance.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S06_memory_governance.md
Also read: research/12-23-2025-research/memory_governence/04_pruning_bundling_policies.md.md

Your goal:
1. Implement complexity metrics (apparent complexity, branching factor, etc.)
2. Implement bundling policies (should_bundle, stop_rules, create_bundle)
3. Implement pruning policies (decay, archive, protect_evidence)
4. Add complexity governor (observe complexity, suggest actions)
5. Implement MDL scoring (compare strategies)
6. Test anti-soup (prevent drift)

Constraints:
- Bundling must be reversible (keep constituents list)
- Never prune evidence referenced by hololinks
- Complexity governor suggests, doesn't auto-execute
- MDL scoring can be heuristic (approximate costs)

After completion:
- Verify complexity metrics detect soup
- Test bundling prevents mega-bundles
- Document governance architecture

Start by implementing complexity metrics.
```

