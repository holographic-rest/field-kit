# 14-Day Execution Plan: Dec 23, 2025 - Jan 4, 2026
**Goal:** Repair and complete a working prototype by applying ideas from 32 research documents. Fellowship-ready outcome: working demo + measurable progress + strong documentation.

---

## Executive Summary

This plan synthesizes 32 research documents (27 essays + 5 research docs) into 10 focused sprints over 14 days. The first 2 sprints stabilize the baseline and add observability. The remaining 8 sprints systematically upgrade navigation, grounding, memory governance, and evaluation—all while maintaining a working golden path demo.

**Core Strategy:**
- **Residual/identity architecture**: Every upgrade is a delta that can safely be zero
- **Golden path first**: Demo must work reliably for outsiders
- **Local-first**: No cloud dependencies
- **Evidence-grounded**: Every hololink must cite actual spans
- **Ledger as truth**: Event-sourced projections are disposable

---

## Initiative Buckets (10)

### Bucket 1: Foundation Stabilization
**Docs:** CS231n (#27), ResNet (#11), Identity Mappings (#16), Evidence Grounding (#01), Event Sourcing (#02)
**Theme:** Restore working baseline with debuggable architecture
**Sprint:** S01

### Bucket 2: Observability & Evaluation
**Docs:** Evaluation Harness (#03), CS231n (#27), Scaling Laws (#23), MDL (#24)
**Theme:** Measure everything; establish regression tests
**Sprint:** S02

### Bucket 3: Pointer-Based Navigation
**Docs:** Pointer Networks (#07), Order Matters (#09), Attention (#14), Bahdanau Alignment (#15)
**Theme:** Replace prose generation with pointer selection + evidence citations
**Sprint:** S03

### Bucket 4: Multi-Scale Context
**Docs:** Dilated Convolutions (#12), Multi-Scale Context, Evidence Grounding (#01)
**Theme:** Systematic context packing without losing resolution
**Sprint:** S04

### Bucket 5: Graph Propagation
**Docs:** MPNN (#13), Relational Reasoning (#17), Relational RNNs (#19)
**Theme:** Use graph structure for better ranking and disambiguation
**Sprint:** S05

### Bucket 6: Memory Governance
**Docs:** Memory Governance (#04), Coffee Automaton (#20), Complexodynamics (#02), VLAE (#18)
**Theme:** Prevent soup; bundle/prune with MDL discipline
**Sprint:** S06

### Bucket 7: Session State & Continuity
**Docs:** RNNs (#03), LSTM (#04), Relational RNNs (#19), NTM (#21)
**Theme:** Multi-slot memory that preserves thread continuity
**Sprint:** S07

### Bucket 8: Pipeline & Batching
**Docs:** GPipe (#10), Deep Speech 2 (#22), AlexNet (#08)
**Theme:** Microbatching and pipeline stages for latency/throughput
**Sprint:** S08

### Bucket 9: Complexity & MDL Controls
**Docs:** MDL (#24), Kolmogorov Complexity (#26), Coffee Automaton (#20), Keeping Simple (#06)
**Theme:** Complexity budgets and structure-vs-noise gates
**Sprint:** S09

### Bucket 10: Storage & Privacy
**Docs:** Local First (#05), Event Sourcing (#02)
**Theme:** SQLite + FTS5 + encryption; rebuildable projections
**Sprint:** S10

---

## Dependency Graph

```
S01 (Foundation) → S02 (Observability)
  ↓
S03 (Pointers) ← S02
  ↓
S04 (Multi-Scale) ← S03
  ↓
S05 (Graph) ← S04
  ↓
S06 (Memory) ← S05
  ↓
S07 (Session State) ← S06
  ↓
S08 (Pipeline) ← S07
  ↓
S09 (Complexity) ← S08
  ↓
S10 (Storage) ← S09 (can run in parallel with S09)
```

**Critical Path:** S01 → S02 → S03 → S04 → S05 (must complete in order)
**Parallelizable:** S06-S10 can overlap if dependencies met

---

## 14-Day Schedule Overview

| Days | Sprint | Theme | Key Deliverable |
|------|--------|-------|-----------------|
| Dec 23-24 | S01 | Foundation Stabilization | Working golden path + residual module interface |
| Dec 25-26 | S02 | Observability & Eval | Eval harness + 10 test cases + metrics dashboard |
| Dec 27 | S03 | Pointer-Based Navigation | Pointer-style hololinks with evidence citations |
| Dec 28 | S04 | Multi-Scale Context | Dilated context sampler + evidence pack builder |
| Dec 29 | S05 | Graph Propagation | 1-2 hop message passing reranker |
| Dec 30-31 | S06 | Memory Governance | Bundling policies + complexity metrics |
| Jan 1 | S07 | Session State | Multi-slot memory + slot-to-slot attention |
| Jan 2 | S08 | Pipeline & Batching | Microbatching + stage queues |
| Jan 3 | S09 | Complexity Controls | MDL scoring + structure-vs-noise gates |
| Jan 4 | S10 | Storage & Privacy | SQLite migration + encryption + backup |

**Buffer Days:** Dec 25, Dec 30, Jan 1 (holidays) are lighter; can catch up or extend previous sprint

---

## Fellowship Artifact Checklist

### Must-Have (Core Demo)
- [ ] **Working Golden Flow** runs end-to-end without errors
- [ ] **Pointer-style hololinks** with evidence citations visible in UI
- [ ] **Eval harness** with 5+ test cases (stretch goal 10) and regression protocol
- [ ] **Metrics dashboard** showing: MRR@K, Golden Flow Continuation Success Rate, evidence coverage, complexity trends
- [ ] **Documentation**: Architecture overview + sprint reports

### Strong-to-Have (Differentiation)
- [ ] **Graph propagation** improves ranking vs baseline (measured)
- [ ] **Multi-scale context** reduces "handles not context" failures (measured)
- [ ] **Memory governance** prevents soup (complexity metrics stay in band)
- [ ] **Session continuity** improves thread coherence (measured)

### Nice-to-Have (Future Work)
- [ ] **Learned controller** (tiny LSTM/GRU) trained on QDPI logs
- [ ] **Voice ingestion** path (speech → QDPI objects)
- [ ] **Encrypted storage** with keychain integration

---

## Risk Mitigation

**Risk 1: Prototype too broken to stabilize in 2 days**
- **Mitigation:** S01 focuses on minimal working path only; defer all upgrades
- **Fallback:** Extend S01 to 3 days, compress later sprints

**Risk 2: Too many dependencies block progress**
- **Mitigation:** Each sprint has explicit "fallback deliverable" if blocked
- **Fallback:** Skip non-critical sprints (S08-S10) if time runs out

**Risk 3: Eval harness takes too long**
- **Mitigation:** S02 uses existing golden flow as first test case; add 4-9 more incrementally (5 minimum, 10 stretch)
- **Fallback:** Ship with 5 test cases, expand to 10 post-fellowship

**Risk 4: Research docs too abstract**
- **Mitigation:** Each sprint includes concrete "steal this" mechanics from papers
- **Fallback:** Implement heuristic versions first, document learned path later

---

## Success Criteria

**Minimum Viable (Fellowship-Ready):**
- Golden flow works
- Eval harness runs
- Pointer-style hololinks with evidence
- Documentation explains architecture

**Stretch Goal:**
- All 10 sprints complete
- Measured improvements vs baseline
- Demo video showing evidence citations
- Architecture diagram showing residual modules

---

## Next Steps

1. Read `S01_foundation_stabilization.md` and execute
2. After S01, read `S02_observability_eval.md` and execute
3. Continue through S10 in order
4. Document blockers and adjust plan as needed

Each sprint file includes:
- Objective and fellowship narrative value
- Inputs (doc references + repo modules)
- Tasks (numbered, specific)
- Acceptance criteria (checkboxes)
- Test plan (commands/procedures)
- Documentation outputs (exact filenames)
- Hand-off prompt for Claude Code

---

## Optional Capstone: Fellowship Packet

After S10 (or whenever the system is demo-stable), consider creating a fellowship packet with:

### Outputs

1. **`/docs/fellowship/FELLOWSHIP_PACKET.md`**
   - Executive summary of the project
   - Key innovations (pointer-based navigation, evidence grounding, memory governance)
   - Measured improvements vs baseline
   - Architecture overview with residual module pattern
   - Links to demo video and documentation

2. **`/docs/fellowship/DEMO_SCRIPT.md`**
   - Step-by-step demo script for golden flow
   - How to show evidence citations
   - How to demonstrate eval harness
   - Key talking points per feature

3. **`/docs/fellowship/RUNBOOK.md`**
   - How to set up the system from scratch
   - How to run golden flow
   - How to run eval harness
   - How to interpret metrics dashboard
   - Troubleshooting common issues

4. **`/docs/fellowship/RESULTS.md`**
   - Baseline metrics (from S02)
   - Final metrics (after all sprints)
   - Improvement deltas (MRR@K, ECR, complexity trends)
   - Test case pass rates
   - Regression suite results

5. **`/docs/fellowship/ARCH_DIAGRAM.md`**
   - Architecture diagram showing:
     - Residual module pattern
     - Pointer-based navigation flow
     - Multi-scale context aggregation
     - Graph propagation reranker
     - Memory governance loop
     - Event-sourced storage

**Note:** This capstone is optional and can be executed after S10 or whenever the system is demo-stable. It's not a required sprint but recommended for fellowship presentation.

