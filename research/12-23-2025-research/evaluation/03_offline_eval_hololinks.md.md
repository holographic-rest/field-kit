# Offline evaluation harness for hololink quality + continuity + anti-soup
**Path:** `/research/12-23-2025-research/evaluation/03_offline_eval_hololinks.md`  
**Status:** draft (research → v0.1 scorecard + goldset recipe)  
**Goal:** Define a minimal, offline, repeatable evaluation harness that (1) rewards evidence-grounded hololinks, (2) protects thread continuity, and (3) detects “drift into soup.”

---

## 0) What we are evaluating (units + the “why”)

Holographic/Gibsey is not “text generation eval” in the abstract. It’s a **Field navigation system** where:

- **Hololinks** must be *pointers with evidence* (see grounding doc).
- The system is used via the **QDPI loop**: Queue → Monologue → Dialogue → Holologue.
- The main failure is **soup**: lots of plausible links with weak/no evidence, repetitive hubs, and broken continuity.

### Evaluation units (keep it explicit)
We evaluate at three levels:

1) **Suggestion list** (ranked candidates)
- Input: a context snapshot (seed node(s), QDPI stage, working text excerpt, filters)
- Output: ranked hololink targets (Items/Episodes/Bonds) + “why” features + evidence candidates
- Metric type: ranking / abstention / confidence

2) **Evidence bundle**
- Input: a link + its attached evidence pointers
- Output: anchor resolution status + support judgment (“does this excerpt really support this link?”)
- Metric type: grounding / rot / coverage

3) **Bundle / thread**
- Input: a sequence or set (e.g., an Episode bundle, a dialogue thread, a holologue slice)
- Output: coherence/continuity + redundancy/entropy health
- Metric type: continuity / anti-soup

---

## 1) Gold set design (v0.1) — what humans label

This is the single biggest leverage point. Without a small, consistent gold set, metrics become vibes.

### 1.1 “HololinkGold v0.1” (recommended size)
- **50 contexts** total (enough to see regressions without turning into a dataset project)
- Balanced across QDPI stages:
  - Queue: 15 (candidate discovery)
  - Monologue: 20 (evidence-first linking while writing)
  - Dialogue: 10 (thread continuity + contradiction handling)
  - Holologue: 5 (bundle-level synthesis; optional in v0.1)

### 1.2 Context record (what to store per example)
Each context is a snapshot:
- `context_id`
- `qdpi_stage` (Queue/Monologue/Dialogue/Holologue)
- `seed_nodes` (IDs: Episode/Item + any active Bonds)
- `working_text` (the excerpt visible to the user)
- `candidate_pool_constraints` (optional: vault scope, time window, type filters)
- `gold_links[]` where each includes:
  - `target_node_id`
  - `relation_type` (e.g., supports / elaborates / contradicts / motif / timeline)
  - `relevance_grade`: **2 = strong**, **1 = weak/related**, **0 = irrelevant**
  - `required_evidence[]`: evidence bundle(s) or at minimum (doc ref + quoted excerpt)

This is deliberately close to “claim + evidence” task framing (FEVER is a useful reference pattern) even though you’re not verifying Wikipedia facts.  
Sources for the general “label claim + evidence sentences + NEI” framing: FEVER paper/site.  
- https://aclanthology.org/N18-1074/  
- https://arxiv.org/abs/1803.05355  
- https://fever.ai/dataset/fever.html

### 1.3 Annotation guidelines (minimal and strict)
Annotators label *targets* and *evidence*, not vibes.

For each candidate link target:
- **Strong (2):** Evidence excerpt directly supports the intended relation in-context.
- **Weak (1):** Related but not supporting the relation; might be “see also.”
- **Irrelevant (0):** Not helpful for this context.

Additionally, per context:
- **NIL (no-link) is allowed and important:** if nothing in the corpus is genuinely relevant, the correct behavior is abstention.

For each evidence bundle:
- **Support judgment:** does the cited excerpt support the link relation?
- **Anchor check:** does the evidence pointer resolve (ok / ambiguous / orphan)?

### 1.4 Agreement sanity check (don’t overbuild)
- Double-annotate **10 contexts** (20%) to surface ambiguity.
- Don’t aim for perfect agreement; aim to discover where guidelines need tightening.

---

## 2) Metric suite (offline-testable, v0.1)

We use a small set of **standard ranking metrics** and **Field-specific health metrics**.

### 2.1 Ranking quality (suggestion list)
Use graded relevance (2/1/0) when possible.

- **nDCG@k** (graded ranking quality; rewards strong links at the top)  
  Canonical reference: Järvelin & Kekäläinen “Cumulated gain-based evaluation…” (2002).  
  - https://dl.acm.org/doi/10.1145/582415.582418  
  - (PDF copy often circulated in courses): https://faculty.cc.gatech.edu/~zha/CS8803WST/dcg.pdf

- **MRR** (how soon the *first* acceptable link appears)  
  (Definition reference: Craswell’s IR encyclopedia entry.)  
  - https://link.springer.com/rwe/10.1007/978-0-387-39940-9_488

- **Precision@k / Recall@k** (top-k “shortlist” quality)  
  (Standard IR definitions; a primary textbook reference.)  
  - https://nlp.stanford.edu/IR-book/pdf/irbookonlinereading.pdf

### 2.2 Abstention / “don’t hallucinate links”
This is the anti-Clippy metric: sometimes the right answer is “no link.”

- **NIL Accuracy (Abstention correctness)**  
  % of NIL contexts where system returns no link (or flags low confidence) *and* would have otherwise produced false positives.  
  Entity-linking literature treats NIL behavior as first-class; use it as an analogy even if you’re not doing EL.  
  - Entity linking evaluation analysis: https://aclanthology.org/L16-1693.pdf  
  - TAC KBP entity linking examples: https://nlp.stanford.edu/pubs/kbp2010-entitylinking.pdf

### 2.3 Grounding & evidence quality (evidence bundles)
These are Field-specific and should be “hard gates” for what counts as grounded.

- **Evidence Coverage Rate (ECR):** % of hololinks in the evaluated set that have ≥1 evidence bundle attached.
- **Anchor Resolution Rate (ARR):** % of evidence bundles that resolve to a unique span (ok vs ambiguous/orphan).
- **Support Precision (SP):** % of attached evidence bundles judged to actually support the stated relation.
- **Link Rot Rate (LRR):** % of previously-ok bundles that become orphaned after edits.

Citation-quality benchmarks (ALCE) are relevant because they explicitly evaluate citation precision/recall and support behavior in systems that attach citations to outputs.  
- ALCE (arXiv): https://arxiv.org/abs/2305.14627  
- ALCE (ACL Anthology): https://aclanthology.org/2023.emnlp-main.398/  
- ALCE repo: https://github.com/princeton-nlp/ALCE

### 2.4 Continuity + coherence (bundle/thread health proxies)
These are proxies; they must be interpreted in-genre (experimental novel ≠ news article).

- **Lexical cohesion continuity** (topic shift detection proxy)  
  TextTiling is a canonical reference for cohesion-based segmentation.  
  - https://aclanthology.org/J97-1003.pdf  
  - https://people.ischool.berkeley.edu/~hearst/papers/cl-texttiling97.pdf

- **Entity-grid coherence score** (local coherence proxy; “do entities persist sensibly across sentences/episodes?”)  
  - https://aclanthology.org/J08-1001.pdf  
  - https://direct.mit.edu/coli/article/34/1/1/1969/Modeling-Local-Coherence-An-Entity-Based-Approach

Practical Field adaptation:
- Compute continuity on **Episode-to-Episode transitions** within a bundle (not across arbitrary distant nodes).
- Allow “intentional incoherence” labels for experimental effects (don’t auto-fail art).

### 2.5 Confidence calibration (trust badges must mean something)
If the UI displays confidence (or “strong evidence”), track whether it’s calibrated.

- **Expected Calibration Error (ECE)** for “confidence bins vs actual correctness”  
  Canonical reference: Guo et al. “On Calibration of Modern Neural Networks” (2017).  
  - https://arxiv.org/abs/1706.04599  
  - https://proceedings.mlr.press/v70/guo17a/guo17a.pdf

---

## 3) Anti-soup metrics (Field health alarms)

These are not about “accuracy”; they’re about preventing the system from devolving into repetitive, ungrounded linking.

Minimum v0.1 anti-soup set:

1) **Ungrounded Link Ratio (ULR)**  
   % of hololinks with no evidence bundle (or only orphan/ambiguous bundles).  
   *Alarm:* any upward trend after changes.

2) **Top-k Redundancy Index (TRI)**  
   Average similarity (or overlap) among the top-k suggested targets for a context.  
   *Alarm:* top-5 suggestions are near-duplicates (same hub, same motif node, same generic episode).

3) **Hubness / Concentration**  
   Fraction of suggestions pointing to the top-N most linked nodes.  
   *Alarm:* “everything links to the same 10 nodes.”

4) **Staleness of evidence**  
   Median age since last successful anchor resolution for bundles used in suggestions.  
   *Alarm:* lots of old evidence in active writing contexts.

---

## 4) v0.1 scorecard (8–12 metrics you can run “on paper”)

Keep this stable. Don’t churn metrics weekly.

**Ranking / utility**
- nDCG@5 (graded relevance)
- MRR (first acceptable)
- Recall@10 (coverage of relevant links)

**Abstention**
- NIL Accuracy (no-link correctness)

**Grounding**
- Evidence Coverage Rate (ECR)
- Anchor Resolution Rate (ARR)
- Support Precision (SP)
- Link Rot Rate (LRR)

**Continuity / drift**
- Episode-to-episode lexical cohesion continuity (bundle transitions)
- Ungrounded Link Ratio (ULR) + Top-k Redundancy Index (TRI)

Optional if you show confidence:
- ECE (calibration)

---

## 5) Harness shape (offline, local-first)

### 5.1 What the harness does
Given HololinkGold contexts:
1) Generate candidates (your retrieval pipeline)
2) Optionally rerank (your controller)
3) Produce:
   - ranked list per context (+ confidence)
   - proposed evidence bundles per candidate (if you do that)
4) Compute metrics and store a timestamped report

### 5.2 Baselines (must have, to avoid placebo progress)
At minimum, keep three baselines:
- **Lexical-only** (FTS/BM25)
- **Vector-only** (ANN)
- **Graph-only** (neighborhood expansion / PPR-lite)
Then compare your “hybrid” against them.

### 5.3 Regression protocol (“system reads itself”)
- Freeze HololinkGold v0.1 as **regression set**.
- On every change to anchoring/retrieval/reranking:
  - rerun the suite
  - fail the change if key metrics drop beyond tolerance
  - require manual spot-check of the worst regressions (top 5 contexts)

---

## 6) Known pitfalls + guardrails (anti-Goodhart)

**Pitfall:** optimizing nDCG by always returning hub nodes  
→ Guardrail: Hubness/Concentration alarm + NIL accuracy.

**Pitfall:** maximizing “evidence coverage” with weak/irrelevant citations (“citation laundering”)  
→ Guardrail: Support Precision (SP) + periodic manual audits.

**Pitfall:** continuity metrics penalize intentional discontinuity (experimental narrative)  
→ Guardrail: allow “intentional break” labels; treat continuity as a warning signal, not a hard gate.

**Pitfall:** evaluator inconsistency  
→ Guardrail: tight labeling rules + double-annotation on 20% until stable.

**Pitfall:** test leakage (tuning on the regression set)  
→ Guardrail: maintain a small holdout (10 contexts) you never tune against.

---

## 7) Stop condition (what “enough research” looks like)
You are done for v0.1 when:

- You can define and run (without debate) a **stable scorecard** of 8–12 metrics.
- You have a **HololinkGold v0.1** recipe (50 contexts) and clear annotation guidelines.
- You have baseline comparisons (lexical/vector/graph) and a regression protocol.
- New sources stop adding new metric categories (only variants).

---

## 8) Primary sources (canonical starting set)
- nDCG: Järvelin & Kekäläinen (2002)  
  https://dl.acm.org/doi/10.1145/582415.582418
- MRR definition (IR encyclopedia entry)  
  https://link.springer.com/rwe/10.1007/978-0-387-39940-9_488
- IR metrics (precision/recall) textbook reference  
  https://nlp.stanford.edu/IR-book/pdf/irbookonlinereading.pdf
- FEVER (claim + evidence labeling template)  
  https://aclanthology.org/N18-1074/
- ALCE (citation precision/recall framing)  
  https://arxiv.org/abs/2305.14627
- FActScore (atomic support concept)  
  https://arxiv.org/abs/2305.14251
- RAGAS (multi-dimension RAG evaluation; optional automation)  
  https://arxiv.org/abs/2309.15217
- TextTiling (lexical cohesion proxy)  
  https://aclanthology.org/J97-1003.pdf
- Entity Grid coherence model  
  https://aclanthology.org/J08-1001.pdf
- Calibration (ECE)  
  https://arxiv.org/abs/1706.04599