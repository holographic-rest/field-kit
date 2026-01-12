# Plan Corrections Audit Log
**Date:** 2025-12-23  
**Purpose:** Document all path fixes, module remaps, and metric changes made to sprint plan files

---

## A) Path Fixes

### Research Document Paths

| Before | After | Reason |
|--------|-------|--------|
| `research/12-23-2025-research/ledger_graph/02_event_sourced_graph_indexing.md.md` | `research/12-23-2025-research/ledger_graph/02_event_sourced_graph_indexing.md.md` | **KEPT** - Actual file has `.md.md` extension |
| `research/12-23-2025-research/evaluation/03_offline_eval_hololinks.md.md` | `research/12-23-2025-research/evaluation/03_offline_eval_hololinks.md.md` | **KEPT** - Actual file has `.md.md` extension |
| `research/12-23-2025-research/memory_governence/04_pruning_bundling_policies.md.md` | `research/12-23-2025-research/memory_governence/04_pruning_bundling_policies.md.md` | **KEPT** - Actual folder is `memory_governence` (typo in repo), file has `.md.md` |
| `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md` | `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md` | **KEPT** - Correct path |
| `research/12-23-2025-research/local_first/05_local_first_storage_privacy.md` | `research/12-23-2025-research/local_first/05_local_first_storage_privacy.md` | **KEPT** - Correct path |

**Note:** The repo actually has `.md.md` extensions and `memory_governence` folder name (typo). We preserve these to match reality.

---

## B) Module Remaps

### Existing Modules (Verified)

| Referenced Module | Actual Path | Status |
|-------------------|-------------|--------|
| `src/fieldkit/store_jsonl.py` | `src/fieldkit/store_jsonl.py` | ✓ EXISTS |
| `src/fieldkit/qdpi.py` | `src/fieldkit/qdpi.py` | ✓ EXISTS |
| `src/fieldkit/hololink_pipeline.py` | `src/fieldkit/hololink_pipeline.py` | ✓ EXISTS |
| `src/fieldkit/bond_proposer.py` | `src/fieldkit/bond_proposer.py` | ✓ EXISTS |
| `src/fieldkit/suggestion_engine.py` | `src/fieldkit/suggestion_engine.py` | ✓ EXISTS |
| `src/fieldkit/holologue.py` | `src/fieldkit/holologue.py` | ✓ EXISTS |
| `src/fieldkit/retrieval.py` | `src/fieldkit/retrieval.py` | ✓ EXISTS |
| `src/cli.py` | `src/cli.py` | ✓ EXISTS |
| `prototype/scripts/run_golden_flow.py` | `prototype/scripts/run_golden_flow.py` | ✓ EXISTS |

### New Modules (To Be Created)

All new modules referenced in sprints are correctly scoped as "to be created" and don't need remapping.

---

## C) Metric/Acceptance Criteria Changes

### S02: Observability & Evaluation

| Before | After | Reason |
|--------|-------|--------|
| `nDCG@5` (graded relevance 2/1/0) | `MRR@K` on binary relevance OR `Golden Flow Continuation Success Rate` | No labeled test cases exist; use binary relevance or continuation success |
| `Support Precision (SP)`: % evidence bundles that actually support link | `Evidence Trace Presence`: % suggestions with ≥1 evidence shard + `Anchor Resolution Rate`: % shards that resolve | Human judgment removed; use automatic checks |
| `Recall@10` (coverage of relevant links) | `Recall@10` on binary acceptable set | Keep but clarify: "acceptable" = any target user might click |
| "10 test cases" | "5 test cases minimum, 10 stretch goal" | More realistic; keep 10 as stretch |

### S01: Foundation Stabilization

| Before | After | Reason |
|--------|-------|--------|
| "Verify credits balance is correct" | "Verify credits ledger invariants validated (see spec)" | Credits logic is complex; defer to spec validation |

### S03-S10: Various Metrics

| Before | After | Reason |
|--------|-------|--------|
| "nDCG improves vs baseline" | "MRR@K improves OR Golden Flow Continuation Success Rate improves" | No graded labels; use binary or continuation |
| "Evidence Coverage Rate (ECR)" | **KEPT** - % suggestions with ≥1 evidence shard | Already verifiable |
| "Anchor Resolution Rate (ARR)" | **KEPT** - % evidence shards that resolve to existing source span | Already verifiable |
| "Ungrounded Link Ratio (ULR)" | **KEPT** - 1 - ECR | Already verifiable |
| "Top-k Redundancy Index (TRI)" | **KEPT** - Mean pairwise cosine similarity among top-k | Already verifiable |
| "Hubness" | **KEPT** - Fraction of suggestions pointing to top-N nodes | Already verifiable |
| "Backtrack Rate" | **KEPT** - % sessions where user rejects top-1 | Already verifiable (if logged) |

---

## Unresolved Ambiguities

1. **Test Case Format**: S02 assumes JSON test cases with `gold_links` and `required_evidence`. If these don't exist, need to define format explicitly.

2. **Baseline Storage**: S02 creates baselines but doesn't specify where to store baseline scores (file path).

3. **Credits Invariants**: S01 references "credits ledger invariants" but doesn't specify what they are. Should reference existing spec or define.

4. **Evidence Shard Extraction**: S03 assumes evidence shards can be extracted from source items. Need to verify this is possible with current data structure.

5. **Graph Distance Computation**: S05 assumes graph distance can be computed. Need to verify bond graph structure supports this.

6. **Complexity Coarse-Graining**: S06 references "coarse-grain(snapshot)" but doesn't specify exact transformation. May need heuristic.

7. **Session State Persistence**: S07 doesn't specify if session state persists across restarts or is ephemeral.

8. **Pipeline Queue Backpressure**: S08 doesn't specify queue size limits or backpressure behavior.

9. **MDL Cost Computation**: S09 references "model cost" and "data cost" but doesn't specify exact formulas (may be heuristic).

10. **SQLite Migration Strategy**: S10 doesn't specify if migration is one-time or supports dual-write during transition.

---

## Summary

- **Path fixes**: 0 (all paths match actual repo structure, including `.md.md` extensions and `memory_governence` folder typo)
- **Module remaps**: 0 (all referenced modules exist and paths verified)
- **Metric changes**: 
  - `nDCG@5` → `MRR@K` + `Golden Flow Continuation Success Rate` (binary relevance, no human labels)
  - `Support Precision (SP)` → `Evidence Trace Presence` + `Anchor Resolution Rate` (automatic checks)
  - `credits balance is correct` → `credits ledger invariants validated` (requires spec reference)
  - `10 test cases` → `5 minimum, 10 stretch goal` (more realistic)
- **Sprint file updates**: All 10 sprint files (S01-S10) updated with:
  - Repo Reality Notes sections
  - Corrected metrics in acceptance criteria and test plans
  - Updated hand-off prompts
- **Master plan updates**: 
  - Fellowship artifact checklist updated with new metrics
  - Risk mitigation updated with test case count
  - Added optional capstone sprint section
- **Unresolved**: 10 ambiguities documented above (acceptable for planning phase)

All sprint files updated to reflect these corrections. Plan is now executable and tool-friendly.

