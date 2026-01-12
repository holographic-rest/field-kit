# S05: Graph Propagation Reranker
**Days:** Dec 29 (1 day)  
**Theme:** Use graph structure for better ranking and disambiguation

---

## Objective

Implement 1-2 rounds of message passing over the bond graph to improve node representations, then use updated representations to rerank hololink candidates. This fixes "handles not context" by propagating neighborhood information.

---

## Why This Matters for Fellowship Narrative

- **Uses graph structure**: MPNN pattern shows graph-native thinking
- **Improves ranking**: Graph propagation should improve MRR@K or Golden Flow Continuation Success Rate vs baseline
- **Enables disambiguation**: Q/QQ/QQQ ambiguity resolved via graph distance
- **Demonstrates message passing**: Clean implementation of MPNN pattern

---

## Inputs

### Research Documents
- `research/27-essays/13_neural_message_passing_quantum_chemistry.md` - MPNN pattern
- `research/27-essays/17_simple_NN_module_relational_reasoning.md` - Relational scoring
- `research/27-essays/19_relational_RNNs.md` - Relational memory

### Repo Modules
- `src/fieldkit/candidate_set.py` - Candidates (from S03)
- `src/fieldkit/store_jsonl.py` - Graph data access

---

## Tasks

### Task 1: Implement Message Passing
1. Create `src/fieldkit/graph_propagation.py` with:
   ```python
   def message_passing_step(nodes, edges, T=2):
       # T rounds of message passing
       for t in range(T):
           messages = compute_messages(nodes, edges)
           nodes = update_nodes(nodes, messages)
       return nodes
   ```
2. Message = (neighbor embedding + bond-type embedding + recency)
3. Aggregate = sum/mean + normalization
4. Update = residual update (from S01)

### Task 2: Integrate into Reranker
1. Update pointer scorer to:
   - Step 1: Run message passing on candidate nodes
   - Step 2: Use updated node embeddings for scoring
   - Step 3: Return reranked candidates
2. Keep deterministic (no training yet)

### Task 3: Add Graph Distance Features
1. Compute graph distance from current node to each candidate
2. Use as feature in scoring (closer = higher score, with decay)
3. Handle disconnected nodes (infinite distance = low score)

### Task 4: Test Disambiguation
1. Create test case with Q/QQ/QQQ ambiguity
2. Verify graph propagation resolves ambiguity (closest in graph wins)
3. Measure improvement vs baseline

---

## Acceptance Criteria

- [ ] Message passing runs 1-2 rounds over graph
- [ ] Node embeddings updated via message aggregation
- [ ] Reranker uses updated embeddings
- [ ] Graph distance computed and used in scoring
- [ ] Disambiguation test case passes
- [ ] MRR@K improves vs baseline OR Golden Flow Continuation Success Rate improves (measured in eval harness)
- [ ] Documentation: `docs/architecture/GRAPH_PROPAGATION.md`

---

## Test Plan

### Test 1: Message Passing
```python
from fieldkit.graph_propagation import message_passing_step
nodes = {...}  # Node embeddings
edges = {...}  # Bond graph
updated_nodes = message_passing_step(nodes, edges, T=2)
assert len(updated_nodes) == len(nodes)
assert updated_nodes["it_1"] != nodes["it_1"]  # Changed
```
**Expected:** Node embeddings updated after message passing

### Test 2: Graph Distance
```python
from fieldkit.graph_propagation import compute_graph_distance
dist = compute_graph_distance("it_current", "it_target", graph)
assert dist >= 0
assert dist == 0 if same node
```
**Expected:** Graph distance computed correctly

### Test 3: Reranking Improves
```bash
python3 tests/eval_harness.py --compare-baseline
```
**Expected:** MRR@K with graph propagation > baseline OR Golden Flow Continuation Success Rate improves

---

## Documentation Outputs

1. `docs/architecture/GRAPH_PROPAGATION.md` - MPNN-style message passing
2. Update `docs/architecture/POINTER_NAVIGATION.md` with graph reranking

---

## Fallback Plan

If message passing is too complex:
- **Fallback:** Simple graph distance feature only (no message passing)
- **Minimum deliverable:** Graph distance used in scoring
- **Document:** Plan to add message passing in future

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/candidate_set.py` from S03, `src/fieldkit/store_jsonl.py`)
- **Research docs:** All paths match actual files
- **Metrics:** Changed `nDCG@5 improves` to `MRR@K improves OR Golden Flow Continuation Success Rate improves` (binary relevance)

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S05: Graph Propagation Reranker.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S05_graph_propagation.md
Also read: research/27-essays/13_neural_message_passing_quantum_chemistry.md

Your goal:
1. Implement message passing (1-2 rounds: compute messages, aggregate, update nodes)
2. Integrate into reranker (use updated embeddings for scoring)
3. Add graph distance features (closer = higher score)
4. Test disambiguation (Q/QQ/QQQ resolved via graph)

Constraints:
- Keep deterministic (no training yet)
- Use residual updates (from S01)
- Message = neighbor embedding + bond-type + recency
- Aggregate = sum/mean + normalization

After completion:
- Verify MRR@K improves vs baseline OR Golden Flow Continuation Success Rate improves
- Document graph propagation architecture
- Test disambiguation case

Start by implementing message passing step.
```

