# S03: Pointer-Based Navigation
**Days:** Dec 27 (1 day)  
**Theme:** Replace prose generation with pointer selection + evidence citations

---

## Objective

Replace "generate link text" with "select pointer to object + cite evidence spans". This directly addresses the "handles not context" failure mode by making hololinks grounded by construction.

---

## Why This Matters for Fellowship Narrative

- **Fixes core UX problem**: "Handles not context" is the #1 user complaint
- **Demonstrates grounding**: Evidence citations prove links are justified
- **Shows pointer networks insight**: Using attention/selection instead of generation
- **Enables measurement**: Can measure evidence coverage (ECR metric from S02)

---

## Inputs

### Research Documents
- `research/27-essays/07_pointer_networks.md` - Pointer selection pattern
- `research/27-essays/09_order_matters_sequence_to_sequence_sets.md` - Set-first approach
- `research/27-essays/14_attention_is_all_you_need.md` - Attention as ranking
- `research/27-essays/15_neural_machine_translation_jointly_learning_align_translate.md` - Alignment traces
- `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md` - Evidence bundles

### Repo Modules
- `src/fieldkit/bond_proposer.py` - Current suggestion logic
- `src/fieldkit/suggestion_engine.py` - Suggestion generation
- `src/fieldkit/hololink_pipeline.py` - Hololink pipeline

---

## Tasks

### Task 1: Define Candidate Set Schema
1. Create `src/fieldkit/candidate_set.py` with:
   ```python
   class Candidate:
       id: str  # Item/Episode/Bond ID
       title: str
       summary: str
       embedding: Optional[ndarray]
       evidence_shards: List[EvidenceShard]  # Text spans that support this candidate
       graph_distance: int
       recency: float
   ```
2. Create `EvidenceShard` class:
   ```python
   class EvidenceShard:
       shard_id: str
       source_type: str  # "page", "item", "vault"
       source_id: str
       text_span: str
       span_start: int
       span_end: int
   ```

### Task 2: Implement Pointer-Style Scorer
1. Create `src/fieldkit/pointer_scorer.py` with:
   - `score_candidates(context, candidates) -> List[float]` (probabilities)
   - Uses attention-style scoring: `softmax(Q @ K^T / sqrt(d))`
   - Q = current state embedding
   - K = candidate embeddings
   - Returns top-k with probabilities
2. Start with heuristic scoring (similarity + recency + graph distance)
3. Log scores for future training data

### Task 3: Implement Alignment Traces
1. When scoring candidates, also compute:
   - `alignment_weights` per evidence shard (which shards support this candidate)
   - `top_supporting_shards` (top 3-5 shards per candidate)
2. Store alignment in candidate result:
   ```python
   {
       "candidate_id": "...",
       "score": 0.85,
       "top_shards": [
           {"shard_id": "...", "weight": 0.6, "text": "..."},
           ...
       ]
   }
   ```

### Task 4: Update Hololink Pipeline
1. Refactor `hololink_pipeline.py`:
   - Step 1: Build candidate set (graph neighbors + semantic top-k + Vault pins)
   - Step 2: Score with pointer scorer
   - Step 3: Attach alignment traces (top supporting shards)
   - Step 4: Return top-k pointers (IDs) + evidence citations
2. Remove prose generation step (or make it optional/derived)

### Task 5: Update UI to Show Evidence
1. Modify UI to display:
   - Candidate cards with ID + title
   - "Why" section showing top 3 supporting shards
   - Click to expand full evidence
2. Or if CLI-only: Print evidence citations in `suggestions:show` output

### Task 6: Log Pointer Events
1. Log QDPI events:
   - `hololink.candidates_generated` (candidate set)
   - `hololink.pointer_selected` (chosen ID + alignment weights)
2. Store for future training (pointer network learning)

---

## Acceptance Criteria

- [ ] Candidate set schema exists and is used
- [ ] Pointer scorer returns probabilities over candidates
- [ ] Alignment traces include top supporting shards
- [ ] Hololink pipeline uses pointer selection (not prose generation)
- [ ] UI/CLI shows evidence citations for suggestions
- [ ] Events log candidate sets and pointer selections
- [ ] Eval harness (S02) can measure ECR on new system

---

## Test Plan

### Test 1: Candidate Set Building
```python
from fieldkit.candidate_set import Candidate, build_candidate_set
context = {"current_item_id": "it_123"}
candidates = build_candidate_set(context)
assert len(candidates) > 0
assert all(hasattr(c, "evidence_shards") for c in candidates)
```
**Expected:** Candidate set includes evidence shards

### Test 2: Pointer Scoring
```python
from fieldkit.pointer_scorer import score_candidates
scores = score_candidates(context, candidates)
assert len(scores) == len(candidates)
assert all(0 <= s <= 1 for s in scores)
assert abs(sum(scores) - 1.0) < 0.01  # Probabilities sum to 1
```
**Expected:** Scores are valid probabilities

### Test 3: Alignment Traces
```python
result = pointer_scorer.score_with_alignment(context, candidates)
assert "top_shards" in result[0]
assert len(result[0]["top_shards"]) <= 5
```
**Expected:** Each candidate has alignment traces

### Test 4: ECR Metric Improves
```bash
python3 tests/eval_harness.py --compare-baseline
```
**Expected:** ECR (evidence coverage rate) > baseline OR Evidence Trace Presence > baseline (even if heuristic)

---

## Documentation Outputs

1. `docs/architecture/POINTER_NAVIGATION.md` - Pointer-based hololink design
2. `docs/architecture/EVIDENCE_CITATIONS.md` - Evidence shard and alignment spec
3. Update `docs/specs/` with pointer-style hololink behavior

---

## Fallback Plan

If evidence shards are too complex:
- **Fallback:** Use simple text matching (find quoted spans in source)
- **Minimum deliverable:** Pointer selection works; evidence citations are basic
- **Document:** Plan to improve evidence extraction in future sprint

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/bond_proposer.py`, `src/fieldkit/suggestion_engine.py`, `src/fieldkit/hololink_pipeline.py`)
- **Research docs:** All paths match actual files
- **Metrics:** Updated ECR test to also accept Evidence Trace Presence as proxy metric

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S03: Pointer-Based Navigation.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S03_pointer_based_navigation.md
Also read: research/27-essays/07_pointer_networks.md

Your goal:
1. Define candidate set schema (Candidate + EvidenceShard classes)
2. Implement pointer-style scorer (attention-based probability distribution)
3. Implement alignment traces (which shards support each candidate)
4. Update hololink pipeline to use pointer selection
5. Update UI/CLI to show evidence citations
6. Log pointer events for future training

Constraints:
- DO NOT generate prose for links (use pointer selection only)
- Evidence shards can be simple (text spans from source items)
- Scoring can be heuristic (similarity + recency + graph distance)
- Must maintain backward compatibility (existing tests still pass)

After completion:
- Run eval harness and verify ECR metric improves
- Document pointer navigation architecture
- Verify UI/CLI shows evidence citations

Start by creating the candidate set schema and pointer scorer.
```

