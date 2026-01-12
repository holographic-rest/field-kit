# S01: Foundation Stabilization
**Days:** Dec 23-24 (2 days)  
**Theme:** Restore working baseline with debuggable architecture

---

## Objective

Restore the golden path to a working state and establish a residual/identity module architecture that allows safe incremental upgrades. This sprint fixes broken functionality and adds architectural discipline (pre-activation checks, identity paths, debuggable boundaries).

---

## Why This Matters for Fellowship Narrative

- **Demonstrates systems thinking**: Residual architecture prevents degradation as complexity grows
- **Shows debugging discipline**: CS231n-style sanity checks make failures traceable
- **Establishes baseline**: All future improvements can be measured against this foundation
- **Proves local-first**: No cloud dependencies; everything runs locally

---

## Inputs

### Research Documents
- `research/27-essays/11_deep_residual_learning_image_recognition_resnet.md` - Residual thinking
- `research/27-essays/16_identity_mappings_deep_residual_networks.md` - Pre-activation + identity paths
- `research/27-essays/27_CS231n_convolutional_neural_networks_visual_recognition.md` - Debugging discipline
- `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md` - Evidence requirements
- `research/12-23-2025-research/ledger_graph/02_event_sourced_graph_indexing.md.md` - Event sourcing basics

### Repo Modules
- `src/cli.py` - CLI entry point
- `src/fieldkit/store_jsonl.py` - Storage layer
- `src/fieldkit/qdpi.py` - Event logging
- `prototype/scripts/run_golden_flow.py` - Golden flow test
- `prototype/ui/app.py` - UI (if using)

---

## Tasks

### Task 1: Diagnose Current State
1. Run golden flow: `python3 prototype/scripts/run_golden_flow.py --fresh`
2. Document all failures (errors, missing features, broken paths)
3. Create `sprints/12-23-2025-to-01-04-2026/S01_diagnosis.md` with:
   - List of broken features
   - Error messages and stack traces
   - Missing dependencies
   - Data corruption issues (if any)

### Task 2: Fix Critical Paths
1. Fix storage initialization (if broken)
2. Fix event logging (if broken)
3. Fix item/bond creation (if broken)
4. Fix golden flow script (if broken)
5. Ensure all canonical events log correctly

### Task 3: Add Residual Module Interface
1. Create `src/fieldkit/residual.py` with:
   ```python
   class ResidualModule:
       def precheck(self, state: dict) -> dict:
           """Validate/normalize before transforming"""
           pass
       
       def propose_delta(self, prechecked_state: dict) -> dict:
           """Return delta update (can be zero)"""
           pass
       
       def apply(self, state: dict, delta: dict) -> dict:
           """Apply delta: state_out = state_in + delta"""
           return {**state, **delta}
   ```
2. Refactor one existing module (e.g., `bond_proposer.py`) to use ResidualModule
3. Add logging: `{prechecked_state_hash, delta, confidence, trace}`

### Task 4: Add Pre-Activation Sanity Checks
1. Add checks at module boundaries:
   - Candidate set isn't empty
   - Scores are normalized
   - IDs are canonical
   - Masks are enforced (read-only vs writable)
2. Create `src/fieldkit/sanity_checks.py` with reusable validators
3. Integrate into at least 3 critical paths (item creation, bond creation, bond execution)

### Task 5: Add Debug Instrumentation
1. Create `src/fieldkit/instrumentation.py` with:
   - Branching factor tracker
   - Suggestion entropy calculator
   - Vault write rate counter
   - Backtrack detector
2. Log these stats as QDPI events (debug-only, can be filtered)
3. Add CLI command: `python3 src/cli.py debug:stats`

### Task 6: Verify Golden Path
1. Run golden flow 5 times (fresh data each time)
2. Verify all assertions pass
3. Verify event log is correct (canonical names only)
4. Verify credits ledger invariants validated (see spec: credits must sum correctly, no negative balances, all events accounted for)
5. Document any remaining issues in `S01_diagnosis.md`

---

## Acceptance Criteria

- [ ] Golden flow runs end-to-end without errors
- [ ] All canonical events log correctly (no missing events, no invalid names)
- [ ] Residual module interface exists and one module uses it
- [ ] Pre-activation checks exist in at least 3 critical paths
- [ ] Debug instrumentation logs stats (even if just to console)
- [ ] CLI command `debug:stats` works
- [ ] Documentation: `S01_diagnosis.md` + `ARCHITECTURE_RESIDUAL.md`

---

## Test Plan

### Test 1: Golden Flow (5 runs)
```bash
for i in {1..5}; do
  python3 prototype/scripts/run_golden_flow.py --fresh
done
```
**Expected:** All runs pass; no flakiness

### Test 2: Event Log Validation
```bash
python3 src/cli.py init
python3 src/cli.py item:create --title "Test" --body "Body"
python3 src/cli.py ledger:open | grep "item.created"
```
**Expected:** `item.created` event exists with correct structure

### Test 3: Residual Module
```python
# In Python REPL
from fieldkit.residual import ResidualModule
module = ResidualModule()
state = {"items": []}
delta = module.propose_delta(module.precheck(state))
assert delta is not None  # Can be empty dict, but not None
```
**Expected:** Module returns delta (can be zero)

### Test 4: Sanity Checks
```python
# Test empty candidate set
from fieldkit.sanity_checks import validate_candidate_set
try:
    validate_candidate_set([])
    assert False, "Should raise"
except ValueError:
    pass  # Expected
```
**Expected:** Sanity checks raise on invalid inputs

---

## Documentation Outputs

1. `sprints/12-23-2025-to-01-04-2026/S01_diagnosis.md` - Current state analysis
2. `docs/architecture/ARCHITECTURE_RESIDUAL.md` - Residual module pattern
3. `docs/architecture/ARCHITECTURE_SANITY_CHECKS.md` - Pre-activation checks
4. Update `README.md` with new `debug:stats` command

---

## Fallback Plan

If golden flow is too broken to fix in 2 days:
- **Fallback:** Fix only storage + event logging; defer residual module to S02
- **Minimum deliverable:** Golden flow runs (even if with known limitations)
- **Document:** Known issues in `S01_diagnosis.md` for S02 to address

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules (`src/cli.py`, `src/fieldkit/store_jsonl.py`, `src/fieldkit/qdpi.py`, `prototype/scripts/run_golden_flow.py`) exist in repo
- **Research docs:** All paths match actual files (including `.md.md` extensions where they exist)
- **Credits validation:** Changed from "credits balance is correct" to "credits ledger invariants validated" - requires explicit invariant definition or reference to spec

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S01: Foundation Stabilization.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S01_foundation_stabilization.md

Your goal:
1. Diagnose current state by running golden flow and documenting failures
2. Fix critical paths (storage, events, item/bond creation)
3. Add residual module interface (see task 3 for spec)
4. Add pre-activation sanity checks (see task 4)
5. Add debug instrumentation (see task 5)
6. Verify golden path works

Constraints:
- DO NOT change event schema or storage format (only fix bugs)
- DO NOT add new features beyond residual interface
- DO NOT break existing working functionality
- Keep all changes local-first (no cloud dependencies)

After completion:
- Update S01_diagnosis.md with findings
- Create ARCHITECTURE_RESIDUAL.md
- Create ARCHITECTURE_SANITY_CHECKS.md
- Run all tests and document results

Start by running the golden flow and documenting what breaks.
```

