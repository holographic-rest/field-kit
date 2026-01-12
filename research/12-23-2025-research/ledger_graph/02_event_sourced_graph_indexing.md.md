# Event-sourced object graph + incremental retrieval/indexing
**Path:** `/research/12-23-2025-research/ledger_graph/02_event_sourced_graph_indexing.md`
**Status:** draft (research → v0.1 decisions)  
**Goal:** Make the ledger/event-log the single source of truth; derive the object graph + search indexes as *disposable projections* that can be rebuilt, incrementally updated, and used to produce explainable hololink candidates.

---

## 0) Why this doc exists (prototype-critical)
Holographic/Gibsey needs *grounded navigation* over Items/Bonds/Episodes/Vault. That implies:
- A durable ledger (append-only events).
- Projections that build a usable object graph and indexes from that ledger.
- Retrieval that’s fast **and** explainable (“this hololink because…”), without full rebuilds on every edit.

---

## 1) Core invariants (non-negotiable)
These are the “don’t corrupt the Field” rules.

### 1.1 Ledger is the source of truth; projections are disposable
Event sourcing’s core move is storing state changes as an append-only sequence of events, and rebuilding state by replay when needed.
- **Invariant:** you can delete any projection (graph, search index) and rebuild it from the ledger.  
References: Fowler on Event Sourcing; Azure Event Sourcing pattern.  
- https://martinfowler.com/eaaDev/EventSourcing.html  
- https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing

### 1.2 Read model ≠ write model (CQRS as a pragmatic boundary)
CQRS separates write concerns (commands/events) from read concerns (optimized views/indexes).
- **Invariant:** “graph/index views” are read models; they can change independently from the event log schema.  
References: Fowler CQRS; Azure CQRS pattern.  
- https://martinfowler.com/bliki/CQRS.html  
- https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs

### 1.3 Event immutability + compensating events
To “undo” a fact, you append a new event that compensates rather than rewriting history.
- https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing

### 1.4 Deterministic replay (time travel must be real)
Replaying events to rebuild state must be deterministic:
- no randoms, no wall-clock dependencies, no external calls during replay.
If you need side effects, isolate them so replay can run “dry.”

---

## 2) Event-sourcing primitives you actually need in this project

### 2.1 Streams + identity (what gets a stream?)
You have options; choose the one that keeps rebuilds and indexing sane:

- **Option A: stream-per-aggregate**
  - e.g., `Item-{id}`, `Episode-{id}`, `Bond-{id}`.
  - Pros: targeted replays; easy to reason about one entity.
  - Cons: cross-entity projections need multi-stream consumption.

- **Option B: workspace/ledger stream + partition keys**
  - One main log (or a few), events include `entity_id` + `entity_type`.
  - Pros: simple append and global ordering.
  - Cons: requires careful partitioning/checkpointing for projections.

v0.1 recommendation: **a small number of streams** (e.g., `Ledger`, plus optional high-churn “draft” streams) to keep ops simple, and put entity identity in event metadata.

### 2.2 Idempotency + at-least-once reality (projection safety)
Even locally, your projector/indexer will crash/restart. Assume events can be reprocessed.
- **Rule:** each projection update must be idempotent (safe to apply twice).
- **Rule:** projections checkpoint their progress (last processed position/event id).
Good practice references (replay + projection hygiene):  
- https://docs.eventsourcingdb.io/best-practices/optimizing-event-replays/  
- https://event-driven.io/en/how_to_scale_projections_in_the_event_driven_systems/

### 2.3 Schema evolution without rewriting history (upcasting)
Event schemas change. Don’t rewrite old events unless you absolutely must.
- **Pattern:** attach version metadata to events; transform old versions *on read/replay* using an upcaster chain.
Axon’s event versioning/upcasting docs are a clear, concrete model:
- https://docs.axoniq.io/axon-framework-reference/4.12/events/event-versioning/
Greg Young’s “Versioning in an Event Sourced System” is the deeper pattern reference:
- https://leanpub.com/esversioning

### 2.4 Projection rebuild strategy (avoid downtime: blue/green)
When projection logic changes, rebuild *a new projection instance* side-by-side and swap over when caught up.
Marten describes this blue/green approach for projections explicitly:
- https://martendb.io/tutorials/advanced-considerations  
- https://martendb.io/events/projections/rebuilding

### 2.5 “Write amplification” warning (don’t double your ledger accidentally)
EventStoreDB/Kurrent’s projections can append/link additional events and warn about IO pressure (“write amplification”).
The local-first translation: **don’t create new ledger events as a normal byproduct of read projections** unless you truly want them as facts.
- https://docs.kurrent.io/server/v25.1/features/projections/custom

---

## 3) Projection/read-model plan (graph + evidence + indexes)

### 3.1 Three projections you want early
1) **Object Graph Projection**
- Materialized adjacency: Items, Episodes, Bonds (typed edges), plus basic attributes needed for ranking/explanation.

2) **Evidence Registry Projection**
- Evidence bundles (from `/research/grounding_nav/…`) as first-class entities.
- Stores resolution status and “what text spans support this edge.”

3) **Search Projection(s)**
- Full-text index for lexical lookup and “exact string grounding.”
- Vector index for semantic recall (optional but useful).
- Lightweight graph traversal for “structural relevance.”

### 3.2 Projection hygiene checklist (v0.1)
- [ ] projector is idempotent
- [ ] projector checkpoints
- [ ] projector can rebuild from zero into a *new* projection store (blue/green)
- [ ] projection updates are replay-safe (no external side effects)

---

## 4) Incremental indexing architectures (text + vector) for local-first

### Shared idea: “segments + merges” (LSM mental model)
Many IR systems use a “write new immutable segments, then merge/compact” design.
- LSM-tree is the canonical compaction model: O’Neil et al.  
  https://www.cs.umb.edu/~poneil/lsmtree.pdf

### Option 1 (leanest): SQLite FTS5 for text + “hot” vector + periodic merge
- **Text:** SQLite FTS5 (BM25) gives you a real full-text engine in-process.  
  https://sqlite.org/fts5.html  
- **Vector:** a small “hot” vector store for recently changed objects; periodically fold into a larger “cold” index (or rebuild the cold index on milestones).
- **Why it’s good:** simplest operationally, good enough for v0.1, easy to rebuild from ledger.

### Option 2 (IR-grade): Lucene-like segments (Tantivy/Lucene) for text + tombstones + merges
- Lucene index is made of **segments**; inserts create new segments; segments have an immutable core.  
  https://lucene.apache.org/core/10_3_1/core/org/apache/lucene/index/package-summary.html
- Tantivy (Rust) is a Lucene-inspired embedded engine; its architecture doc explains why merges exist: reduce tombstones + reduce segment count.  
  https://github.com/quickwit-oss/tantivy/blob/main/ARCHITECTURE.md
- **Vector:** either separate vector index, or vector-as-field with external ANN; keep the “segments + merge” discipline conceptually.

### Option 3 (near-real-time semantics reference): refresh intervals (Elastic model)
Even if you don’t run Elasticsearch, its docs are a useful reference for “writes become searchable on refresh,” and refresh is resource-intensive.
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-refresh

**v0.1 recommendation:** Option 1 unless you already know you want Lucene/Tantivy.  
Reason: the project’s novelty is the Field + grounding + navigation, not search engine plumbing.

---

## 5) Hybrid retrieval for hololink candidate generation (explainable)

### 5.1 Candidate sources (3 channels)
Given a context node (current Episode/Item + active evidence):
1) **Lexical channel:** BM25/FTS over text fields + evidence excerpts.
2) **Vector channel:** nearest neighbors over embeddings of the same units.
3) **Graph channel:** neighborhood expansion / PPR around current node(s).

### 5.2 Merging candidate lists without “magic math”
Don’t sum unrelated scores (BM25 vs cosine) naïvely.
- Use Reciprocal Rank Fusion (RRF) as a simple, robust rank combiner.  
  https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf  
  (also indexed by Google Research: https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/ )

### 5.3 Explanation payload (minimum)
Every suggested hololink should be explainable via:
- “matched text” (lexical evidence)
- “semantic neighbor” (vector)
- “graph-close” (walk/neighbor)
and must reference at least one evidence bundle before it becomes “grounded.”

---

## 6) Incremental vector indexing notes (keep it honest)
If you use HNSW, the core paper explicitly describes incremental construction and high performance ANN:
- https://arxiv.org/pdf/1603.09320.pdf
Practical implication for v0.1:
- inserts are cheap-ish
- deletions/edits often behave like tombstones + rebuild/merge strategy
So you still want a **hot/cold** or **segment/merge** story.

---

## 7) Lightweight graph-aware retrieval (CPU-friendly)

### 7.1 Personalized PageRank / Random Walk with Restart (PPR/RWR)
Use when you want “structural closeness” beyond text similarity.
- Topic-sensitive PageRank (Haveliwala) is a strong canonical reference for biased PageRank vectors.  
  https://www-cs-students.stanford.edu/~taherh/papers/topic-sensitive-pagerank.pdf
- For local approximations that avoid full-matrix operations: Gleich & Polito on approximating PPR with limited graph access.  
  https://www.cs.purdue.edu/homes/dgleich/publications/gleich%202007%20-%20approximate%20personalized%20pagerank.pdf

**Signals needed from Bonds/Episodes graph**
- adjacency (typed edges)
- optional edge weights (Bond strength, recency, “evidence count”)
- seed set (current Episode + cited Items)

**Failure modes**
- hub bias (high-degree nodes dominate)
- expensive if you insist on global convergence (don’t)

### 7.2 Spreading activation (bounded)
Good for “expand a lexical hit into nearby conceptual nodes” with strict cutoffs.
- Crestani (survey) is the anchor reference.  
  https://link.springer.com/content/pdf/10.1023/A:1006569829653.pdf

**Failure modes**
- semantic drift / explosion if thresholds are loose

### 7.3 Absorbing / biased random walks
Useful for “steerable discovery” (e.g., prefer Bonds of type Refutes; stop when you hit a class of nodes).
- Microsoft Research publication page:  
  https://www.microsoft.com/en-us/research/publication/recommendations-using-absorbing-random-walks/?lang=zh-cn  
- PDF copy: https://www.cs.cmu.edu/~ajit/pubs/Singh2007.pdf

**Failure modes**
- trap subgraphs if bias is too strong

### v0.1 practical guidance
Don’t build matrices. Do:
- 2–3 hop neighborhood expansion + caps, OR
- Monte Carlo random walks with a small number of particles and steps

---

## 8) Known failure modes (and how to design them out)

### Inconsistent projections (duplicate processing, partial writes)
- Mitigate with idempotent projection writes + checkpoints + rebuild capability.

### Replay storms (rebuild too slow / blocks the system)
- Mitigate with: separate “rebuild mode,” progress reporting, and blue/green rebuild.

### Index drift (search points to stale versions)
- Mitigate with: tombstones or “latest version pointer” table derived from ledger; rebuild indexes from ledger on demand.

### Time-travel bugs (state differs across replays)
- Mitigate with deterministic replay rule + isolation of side effects.

### Write amplification (projection generates new facts)
- Mitigate by separating “facts” (ledger events) from “views” (projection outputs), and being extremely conservative about generating new events from read models.

---

## 9) v0.1 recommended architecture (smallest reliable)

**Ledger**
- Append-only events; compensating events for corrections.
- Event version metadata + upcaster registry.

**Projections**
1) Object graph projection (Items/Bonds/Episodes adjacency)
2) Evidence registry projection (evidence bundles + resolution status)
3) Search projection:
   - SQLite FTS5 for lexical recall
   - Optional vector index (hot/cold)
   - Graph neighborhood expansion for structural recall

**Hololink suggestion pipeline**
- generate candidates from (FTS + vector + graph)
- merge with RRF
- rerank with simple features (type, recency, evidence count, graph distance)
- attach evidence bundles before finalizing as “grounded”

---

## 10) Primary sources (starter set)
Event sourcing + CQRS:
- https://martinfowler.com/eaaDev/EventSourcing.html
- https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing
- https://martinfowler.com/bliki/CQRS.html
- https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs

Versioning/upcasting:
- https://leanpub.com/esversioning
- https://docs.axoniq.io/axon-framework-reference/4.12/events/event-versioning/

Projections (warnings + rebuild patterns):
- https://docs.kurrent.io/server/latest/features/projections/
- https://docs.kurrent.io/server/v25.1/features/projections/custom
- https://martendb.io/tutorials/advanced-considerations
- https://martendb.io/events/projections/rebuilding

Incremental text indexing primitives:
- https://lucene.apache.org/core/10_3_1/core/org/apache/lucene/index/package-summary.html
- https://github.com/quickwit-oss/tantivy/blob/main/ARCHITECTURE.md
- https://sqlite.org/fts5.html
- https://www.cs.umb.edu/~poneil/lsmtree.pdf

Hybrid rank fusion:
- https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf

Vector indexing (HNSW):
- https://arxiv.org/pdf/1603.09320.pdf

Graph-aware retrieval:
- https://www-cs-students.stanford.edu/~taherh/papers/topic-sensitive-pagerank.pdf
- https://www.cs.purdue.edu/homes/dgleich/publications/gleich%202007%20-%20approximate%20personalized%20pagerank.pdf
- https://link.springer.com/content/pdf/10.1023/A:1006569829653.pdf
- https://www.microsoft.com/en-us/research/publication/recommendations-using-absorbing-random-walks/?lang=zh-cn