# S08: Pipeline & Batching
**Days:** Jan 2 (1 day)  
**Theme:** Microbatching and stage queues for latency/throughput

---

## Objective

Implement GPipe-style pipeline stages with microbatching to improve throughput and reduce perceived latency. This makes the system feel "smooth" instead of "laggy" when handling multiple requests.

---

## Why This Matters for Fellowship Narrative

- **Demonstrates systems thinking**: Pipeline parallelism for efficiency
- **Improves UX**: Faster response times via batching
- **Shows GPipe insight**: Overlap stages, microbatch work
- **Enables scaling**: Foundation for future distributed work

---

## Inputs

### Research Documents
- `research/27-essays/10_gpipe_efficient_training_giant_neural_networks.md` - Pipeline stages
- `research/27-essays/22_deep_speech_2_end_to_end_speech_recognition.md` - Batch dispatch

### Repo Modules
- `src/fieldkit/hololink_pipeline.py` - Current pipeline
- `src/fieldkit/retrieval.py` - Retrieval logic

---

## Tasks

### Task 1: Define Pipeline Stages
1. Create `src/fieldkit/pipeline.py` with:
   ```python
   STAGES = [
       "candidate_generation",  # Graph + embeddings
       "candidate_scoring",     # Pointer ranking
       "response_assembly",     # Templated + citations
       "writeback",             # Events + Vault + bonds
   ]
   ```
2. Each stage has input queue and output queue

### Task 2: Implement Microbatching
1. Create `Microbatcher` class:
   - Collects requests for N ms or until batch_size reached
   - Flushes batch to next stage
   - Keeps latency low (small batches)
2. Use for embedding queries, reranker calls, summarizations

### Task 3: Add Stage Queues
1. Create in-memory queues per stage:
   - `stage_a_queue`, `stage_b_queue`, etc.
   - Backpressure handling (queue full = wait)
2. Integrate into pipeline

### Task 4: Add Flush Boundaries
1. Define "sync step" per user-visible response:
   - Flush all microbatches before returning
   - Ensure consistency (no partial results)
2. Add to pipeline execution

### Task 5: Test Throughput
1. Create benchmark: 10 concurrent requests
2. Measure latency with/without batching
3. Verify throughput improves

---

## Acceptance Criteria

- [ ] Pipeline stages defined and used
- [ ] Microbatching works (collects requests, flushes batches)
- [ ] Stage queues exist (in-memory, with backpressure)
- [ ] Flush boundaries ensure consistency
- [ ] Throughput benchmark shows improvement
- [ ] Documentation: `docs/architecture/PIPELINE_BATCHING.md`

---

## Test Plan

### Test 1: Microbatching
```python
from fieldkit.pipeline import Microbatcher
batcher = Microbatcher(batch_size=5, timeout_ms=100)
batcher.add(request1)
batcher.add(request2)
batch = batcher.flush()  # If timeout or batch_size reached
assert len(batch) >= 1
```
**Expected:** Microbatching collects requests

### Test 2: Pipeline Stages
```python
from fieldkit.pipeline import execute_pipeline
result = execute_pipeline(request, stages=STAGES)
assert "candidates" in result
assert "scores" in result
assert "response" in result
```
**Expected:** Pipeline executes all stages

### Test 3: Throughput
```bash
python3 tests/benchmark_throughput.py --concurrent 10
```
**Expected:** Batching improves throughput vs serial

---

## Documentation Outputs

1. `docs/architecture/PIPELINE_BATCHING.md` - Pipeline design
2. Update `docs/architecture/POINTER_NAVIGATION.md` with pipeline integration

---

## Fallback Plan

If pipeline is too complex:
- **Fallback:** Simple request queue only (no stages)
- **Minimum deliverable:** Microbatching exists for embedding calls
- **Document:** Plan to add full pipeline later

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/hololink_pipeline.py`, `src/fieldkit/retrieval.py`)
- **Research docs:** All paths match actual files

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S08: Pipeline & Batching.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S08_pipeline_batching.md
Also read: research/27-essays/10_gpipe_efficient_training_giant_neural_networks.md

Your goal:
1. Define pipeline stages (candidate_gen, scoring, assembly, writeback)
2. Implement microbatching (collect requests, flush batches)
3. Add stage queues (in-memory, backpressure)
4. Add flush boundaries (sync per user response)
5. Test throughput (benchmark improvement)

Constraints:
- Keep queues in-memory (no external dependencies)
- Microbatches should be small (low latency)
- Flush boundaries ensure consistency
- Must maintain correctness (no race conditions)

After completion:
- Verify throughput improves
- Document pipeline architecture
- Test with concurrent requests

Start by defining the pipeline stages.
```

