# S04: Multi-Scale Context Aggregation
**Days:** Dec 28 (1 day)  
**Theme:** Systematic context packing without losing resolution

---

## Objective

Implement dilated context sampling: aggregate evidence at multiple scales (local/mid/far) without collapsing detail. This prevents "summary replaces the thing" failure mode and enables better grounding.

---

## Why This Matters for Fellowship Narrative

- **Fixes context selection**: Systematically includes relevant history without overwhelming
- **Preserves resolution**: Keeps fine-grained shards while adding far context
- **Demonstrates dilated thinking**: Multi-scale receptive fields without downsampling
- **Improves evidence quality**: More context → better alignment traces

---

## Inputs

### Research Documents
- `research/27-essays/12_multi_scale_context_aggregation_dilated_convolutions.md` - Dilation schedule pattern
- `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md` - Evidence packing

### Repo Modules
- `src/fieldkit/candidate_set.py` - Candidate building (from S03)
- `src/fieldkit/retrieval.py` - Retrieval logic

---

## Tasks

### Task 1: Define Dilation Schedule
1. Create `src/fieldkit/dilated_context.py` with:
   ```python
   DILATION_OFFSETS = [-1, -2, -4, -8, -16, -32]  # Events/pages back
   ```
2. For each offset, define what to pull:
   - The item/page at that time
   - Its top neighbors (graph distance 1)
   - Associated Vault pins

### Task 2: Implement Context Sampler
1. Create `DilatedContextSampler` class:
   ```python
   def sample(self, current_state, dilation_offsets):
       context_pack = []
       for offset in dilation_offsets:
           items = self.get_items_at_offset(current_state, offset)
           neighbors = self.get_neighbors(items)
           vault_pins = self.get_vault_pins(items)
           context_pack.extend([items, neighbors, vault_pins])
       return context_pack
   ```
2. Combine with local window (last N events)

### Task 3: Integrate into Candidate Building
1. Update `build_candidate_set()` to use dilated context:
   - Local scale: immediate neighborhood
   - Mid scale: dilation steps (2, 4, 8, 16)
   - Far scale: Vault anchors / Holologue bundles
2. Ensure fine-grained shards remain available (don't replace with summaries)

### Task 4: Add Context Pack Metadata
1. Tag each evidence shard with scale:
   - `scale: "local" | "mid" | "far"`
   - `dilation_offset: int`
2. Use in alignment traces (show which scale contributed)

### Task 5: Test Multi-Scale Coverage
1. Create test case with long history
2. Verify context pack includes items from multiple scales
3. Verify no scale dominates (balanced representation)

---

## Acceptance Criteria

- [ ] Dilation schedule defined and used
- [ ] Context sampler pulls from multiple scales
- [ ] Fine-grained shards preserved (not replaced by summaries)
- [ ] Evidence shards tagged with scale metadata
- [ ] Test case verifies multi-scale coverage
- [ ] Documentation: `docs/architecture/MULTI_SCALE_CONTEXT.md`

---

## Test Plan

### Test 1: Dilation Schedule
```python
from fieldkit.dilated_context import DILATION_OFFSETS
assert DILATION_OFFSETS == [-1, -2, -4, -8, -16, -32]
```
**Expected:** Dilation offsets are defined

### Test 2: Context Sampling
```python
from fieldkit.dilated_context import DilatedContextSampler
sampler = DilatedContextSampler()
context = sampler.sample(current_state, DILATION_OFFSETS)
assert len(context) > 0
assert any(shard.scale == "local" for shard in context)
assert any(shard.scale == "mid" for shard in context)
assert any(shard.scale == "far" for shard in context)
```
**Expected:** Context includes multiple scales

### Test 3: Resolution Preserved
```python
# Verify fine-grained shards exist alongside summaries
local_shards = [s for s in context if s.scale == "local"]
assert all(len(s.text_span) < 500 for s in local_shards)  # Not summaries
```
**Expected:** Local shards are fine-grained

---

## Documentation Outputs

1. `docs/architecture/MULTI_SCALE_CONTEXT.md` - Dilated context design
2. Update `docs/architecture/EVIDENCE_CITATIONS.md` with scale metadata

---

## Fallback Plan

If dilation is too complex:
- **Fallback:** Simple 3-scale (local/mid/far) without strict dilation schedule
- **Minimum deliverable:** Context includes multiple time scales
- **Document:** Plan to refine dilation schedule later

---

## Repo Reality Notes

- **Module paths verified:** All referenced modules exist (`src/fieldkit/candidate_set.py` from S03, `src/fieldkit/retrieval.py`)
- **Research docs:** All paths match actual files

---

## Hand-off to Claude Code

**Prompt:**
```
I need you to execute Sprint S04: Multi-Scale Context Aggregation.

Read the sprint file: sprints/12-23-2025-to-01-04-2026/S04_multi_scale_context.md
Also read: research/27-essays/12_multi_scale_context_aggregation_dilated_convolutions.md

Your goal:
1. Define dilation schedule (offsets: -1, -2, -4, -8, -16, -32)
2. Implement context sampler (pulls items at each offset + neighbors + Vault pins)
3. Integrate into candidate building (multi-scale context pack)
4. Tag evidence shards with scale metadata
5. Test multi-scale coverage

Constraints:
- DO NOT replace fine-grained shards with summaries
- Keep local window dense (every item in near region)
- Progressively sample farther back (gaps increase)
- Must preserve resolution (actual text spans, not summaries)

After completion:
- Verify context pack includes multiple scales
- Document dilated context architecture
- Test with long history case

Start by defining the dilation schedule and context sampler.
```

