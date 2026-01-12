# S07: Session State & Continuity
**Days:** Jan 1 (1 day, lighter load)  
**Theme:** Multi-slot memory that preserves thread continuity

---

## Objective

Implement Relational Memory Core (RMC) pattern: multi-slot session state where slots interact via attention. This fixes "loses the thread" by maintaining structured memory across steps.

---

## Why This Matters for Fellowship Narrative

- **Fixes continuity**: System remembers "what we're doing" across clicks
- **Demonstrates RMC pattern**: Multi-slot memory with slot-to-slot attention
- **Enables better suggestions**: Links conditioned on full session state, not just last item
- **Shows relational thinking**: Slots interact to influence decisions

---

## Inputs

### Research Documents
- `research/27-essays/19_relational_RNNs.md` - RMC pattern
- `research/27-essays/04_understanding_LSTM_networks.md` - Gating (forget/input/output)
- `research/27-essays/21_neural_turing_machines.md` - External memory

### Repo Modules
- `src/fieldkit/qdpi.py` - Event logging
- `src/fieldkit/candidate_set.py` - Candidate building

---

## Tasks

### Task 1: Define Memory Slots
1. Create `src/fieldkit/session_state.py` with:
   ```python
   class MemorySlot:
       slot_id: str  # "active_page", "user_intent", "entities", etc.
       content: dict  # JSON-ish object
       embedding: ndarray  # Summary embedding
       recency: float
       is_pinned: bool
   ```
2. Define 6 slots:
   - Active page / scene frame
   - User intent / current ask
   - Entities & bindings
   - Open questions / unresolved bonds
   - Recent evidence shards
   - Vault anchors / arc constraints

### Task 2: Implement Slot Updates
1. Create `update_slots(slots, new_inputs)`:
   - Update each slot from new inputs (page, ask, shards)
   - Keep embeddings in sync with content
2. Integrate into main loop (update after each action)

### Task 3: Implement Slot-to-Slot Attention
1. Create `slot_attention(slots)`:
   - Compute attention weights between slots
   - Weighted mixing by type + recency + pinned
   - Heuristic for now (can be learned later)
2. Use attention to combine slot states

### Task 4: Use State in Candidate Building
1. Update `build_candidate_set()` to:
   - Accept session state (all slots)
   - Condition candidates on slot combinations
   - Use slot attention weights to weight features
2. Log slot states for future training

### Task 5: Test Continuity
1. Create test case with multi-step session
2. Verify slots update correctly
3. Verify suggestions improve with state (vs no state)

---

## Acceptance Criteria

- [ ] Memory slots defined (6 slots)
- [ ] Slot updates work (content + embeddings)
- [ ] Slot-to-slot attention computes
- [ ] Candidate building uses session state
- [ ] Continuity test case passes
- [ ] Documentation: `docs/architecture/SESSION_STATE.md`

---

## Test Plan

### Test 1: Slot Updates
```python
from fieldkit.session_state import MemorySlot, update_slots
slots = {...}
new_inputs = {"page": "...", "ask": "..."}
updated = update_slots(slots, new_inputs)
assert updated["active_page"].content["page"] == "..."
```
**Expected:** Slots update from inputs

### Test 2: Slot Attention
```python
from fieldkit.session_state import slot_attention
attention_weights = slot_attention(slots)
assert len(attention_weights) == len(slots)
assert all(0 <= w <= 1 for w in attention_weights.values())
```
**Expected:** Attention weights computed

### Test 3: State Improves Suggestions
```bash
python3 tests/eval_harness.py --with-state vs --without-state
```
**Expected:** Suggestions with state > without state

---

## Documentation Outputs

1. `docs/architecture/SESSION_STATE.md` - RMC-style memory slots
2. Update `docs/architecture/POINTER_NAVIGATION.md` with state conditioning

---

## Fallback Plan

If RMC is too complex:
- **Fallback:** Simple session state object (no slot attention)
- **Minimum deliverable:** Session state exists and is used in candidate building
- **Document:** Plan to add slot attention later

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/qdpi.py`, `src/fieldkit/candidate_set.py` from S03)
- **Research docs:** All paths match actual files

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S07: Session State & Continuity.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S07_session_state.md
Also read: research/27-essays/19_relational_RNNs.md

Your goal:
1. Define memory slots (6 slots: active_page, user_intent, entities, etc.)
2. Implement slot updates (content + embeddings from inputs)
3. Implement slot-to-slot attention (heuristic weighted mixing)
4. Use state in candidate building (condition on slots)
5. Test continuity (multi-step session)

Constraints:
- Keep slots simple (JSON + embedding)
- Attention can be heuristic (type + recency + pinned)
- Must update slots after each action
- Log slot states for future training

After completion:
- Verify slots update correctly
- Test suggestions improve with state
- Document session state architecture

Start by defining the 6 memory slots.
```

