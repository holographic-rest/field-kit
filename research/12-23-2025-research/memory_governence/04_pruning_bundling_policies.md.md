# Memory governance: pruning/decay, bundling, reversibility, entropy control
**Path:** `/research/12-23-2025-research/memory_governance/04_pruning_bundling_policies.md`  
**Status:** draft (research → v0.1 policy matrix + controls)

## Purpose
Turn “memory” into governed mechanics: when to keep, bundle, summarize, or prune—while preserving audit trails (ledger truth), protecting evidence/hololinks, and preventing runaway entropy (“soup”).

---

## 1) Governance goals and invariants

### Non‑negotiable invariants
1) **Ledger is the truth (append-only):** corrections are new events, not rewrites. (Event-sourcing premise; aligns with replay/audit.)  
2) **Evidence must not be destroyed:** any source span or object referenced by a hololink is *protected* until explicitly unlinked and reviewed.  
3) **Reversibility by construction:** bundling/summarization produces *derived* nodes that keep backpointers to constituents (and the exact evidence anchors that justified them).  
4) **Local-first ergonomics:** governance should reduce UI clutter and compute cost without requiring cloud services or opaque background jobs.

### What “memory” means in Gibsey/Holographic terms
Memory is not “everything stored.” It’s **what stays navigable + retrievable + grounded** across:
- the QDPI loop (Queue → Monologue → Dialogue → Holologue),
- the ledger (event log),
- the object graph (Items/Bonds/Episodes/Vault),
- and derived indices (FTS/vector/graph caches).

---

## 2) Memory surfaces (what we govern)

1) **Canonical ledger (events):** immutable history; governs *growth and replay cost* (via rollups/snapshots), not truth deletion.
2) **Object graph (read model):** Items/Bonds/Episodes as *current* state; can be rebuilt from ledger.
3) **Queue (working set):** volatile staging area; high churn; must decay aggressively.
4) **Vault (sources + evidence bundles):** documents, excerpts, selectors; hololink integrity depends on this.
5) **Derived artifacts:** summaries, bundles, embeddings, full-text indexes, candidate caches; should be treated as **rebuildable** and versioned.

---

## 3) Allowed operations (and what they must record)

### 3.1 Retain / Pin
- **Pin** is an explicit user override that exempts objects from automated pruning/eviction.
- Pins must be visible and auditable (“why is this kept forever?”) to avoid silent hoarding.

### 3.2 Decay (rank down, don’t delete)
- Reduce prominence in suggestions and navigation instead of deleting:
  - lower retrieval priority,
  - collapse in UI,
  - hide behind “archived” filters.

### 3.3 Bundle (structural compaction)
Bundling is *graph-level compaction*: group many small nodes/edges/events into a stable, named unit.
- Must create a **Bundle object** with:
  - pointers to constituent Episodes/Items/Bonds,
  - the rationale (evidence bundles or “why these belong together”),
  - a reversible mapping (expandable view).

### 3.4 Summarize (semantic rollup)
Summarization is allowed only if:
- the summary is **derived** (never a replacement of evidence),
- it carries provenance to the underlying objects,
- and it can be invalidated/rolled back.

### 3.5 Prune (remove from working set; keep recoverable)
Pruning means: remove from hot navigation and/or delete derived caches while keeping:
- the ledger events (truth),
- and any protected evidence.

### 3.6 Hard delete (rare, gated)
Only for:
- ephemeral Queue artifacts not referenced anywhere,
- derived caches/embeddings that can be rebuilt,
- duplicate blobs with a surviving canonical object.
Hard delete requires a **preflight check**: “not referenced by any hololink evidence bundle.”

---

## 4) Policy signals (what triggers governance)

Use a small set of measurable signals:

- **Age:** time since last edit / last access.
- **Recency vs frequency:** prefer adaptive policies over brittle TTL-only (see ARC below).
- **Graph connectivity:** orphan status, hubness, degree growth.
- **Duplication:** similarity to existing nodes; cluster size of near-duplicates.
- **Evidence dependence:** referenced-by-hololink = protected.
- **Cost:** size on disk, index rebuild cost, replay cost (event count since last snapshot).

---

## 5) Compaction patterns to steal (and how they map)

### 5.1 Key-based compaction (Kafka)
Kafka’s log compaction keeps the “last known value” per key in a topic partition—useful as a mental model for “latest state per object” projections.  
- Kafka design doc: log compaction overview.  
  https://kafka.apache.org/design.html#compaction  
- Confluent doc: compaction mechanism + guarantees.  
  https://docs.confluent.io/kafka/design/log_compaction.html  
- Topic config (`cleanup.policy` supports `delete`, `compact`, or both):  
  https://kafka.apache.org/30/generated/topic_config.html

**Mapping to Gibsey:**
- **Projection compaction:** keep latest object state per `EpisodeId/ItemId` in the *read model* (graph), while ledger remains append-only.
- **Draft squashing:** keep fine-grained edit events briefly; later roll up into session summaries / checkpoints (below).

### 5.2 LSM/leveled & universal compaction (RocksDB)
LSM compaction explains real failure modes: tombstones, write amplification, compaction storms (write stalls).  
- RocksDB compaction overview: https://github.com/facebook/rocksdb/wiki/Compaction  
- Universal (tiered) compaction tradeoffs: https://github.com/facebook/rocksdb/wiki/universal-compaction  
- Write stalls (when compaction can’t keep up): https://github.com/facebook/rocksdb/wiki/Write-Stalls

**Mapping to Gibsey:**
- Treat **derived indexes/caches** as LSM-like: many small updates → background merges.
- Monitor compaction backlog as a governance health metric (“index drift / rebuild debt”).

### 5.3 Multi-resolution retention (Prometheus TSDB)
Prometheus documents strict retention constraints and recommends keeping retention size below disk headroom.  
- Storage & retention guidance: https://prometheus.io/docs/prometheus/latest/storage/  
- Flags/config fields (retention size/time): https://prometheus.io/docs/prometheus/latest/command-line/prometheus/

**Mapping to Gibsey:**
- Keep **high-resolution history** for a short window (e.g., per-keystroke edits for a few days).
- Keep **medium-resolution** longer (session summaries).
- Keep **low-resolution** indefinitely (milestone snapshots + bundle summaries), *with pointers back to evidence*.

### 5.4 Snapshotting (event sourcing)
Snapshots reduce replay cost but must be treated as optimization (risk: snapshot drift if logic changes).  
- ARC-style “use when needed” framing:  
  https://www.kurrent.io/blog/snapshots-in-event-sourcing  
- EventSourcingDB snapshots & performance guidance:  
  https://docs.eventsourcingdb.io/best-practices/snapshots-and-performance/

**Mapping to Gibsey:**
- Snapshot **Episode text state** and/or **Bundle state** at safe points (e.g., after Holologue commit).
- Snapshot must record the last event included so replay can resume correctly.

---

## 6) v0.1 governance policy matrix (recommended)

### 6.1 Retention tiers
- **Hot:** active QDPI work (today/this week); full indices; aggressive suggestions.
- **Warm:** recently used; indexed; visible in navigation.
- **Cold:** archived; searchable but not noisy; minimal candidate expansion.
- **Deep archive:** compressed / de-indexed; recoverable by explicit action.
- **Trash/Quarantine:** pending delete; reversible for a short window.

### 6.2 Object-by-object policies (minimal but complete)

**Queue entries (volatile)**
- Default: **TTL prune** to reduce clutter.
- Upgrade path: if referenced/linked into an Episode, convert to an Episode/Item and protect.
- Hard delete allowed only if unreferenced.

**Draft edit events (high-churn ledger stream)**
- Keep raw micro-events briefly.
- **Session rollup:** after inactivity gap, emit a `SessionSummary` derived event + optional snapshot.
- Older micro-events can move to deep archive (compressed), but only if replayability is preserved via snapshots.

**Episodes (primary narrative nodes)**
- Never auto-delete if:
  - pinned, or
  - referenced by a Bond, or
  - contains hololinks/evidence bundles.
- If orphan + stale: archive (cold) and collapse in UI, but keep searchable.

**Items (evidence objects)**
- **Protected if referenced by hololinks.**
- Non-protected evidence blobs may be evicted from “hot cache” but keep metadata (source id, selectors) so the system can re-fetch from Vault/local source.

**Bonds (edges)**
- User-created bonds are durable.
- System-suggested bonds can decay and expire unless “promoted” by user acceptance.

**Bundles (Holologue units)**
- Bundles are *stable artifacts*: require a stop rule (see below).
- Never auto-merge bundles without manual review (prevents mega-bundles).

**Derived indices/embeddings**
- Treat as rebuildable.
- Version them and allow full drop/rebuild (no partial mystery state).

### 6.3 Cache/eviction policy for large local blobs (ARC)
For local storage pressure, ARC is a strong default because it adapts between recency and frequency without workload-specific tuning.  
- ARC paper (FAST 2003): https://www.cs.cmu.edu/~natassa/courses/15-721/papers/arcfast.pdf  
- USENIX page: https://www.usenix.org/conference/fast-03/arc-self-tuning-low-overhead-replacement-cache

**Use ARC for:** non-protected evidence blobs, thumbnails, derived caches.  
**Do not use ARC for:** canonical ledger, protected evidence, pinned objects.

---

## 7) Bundling heuristics and “when to stop bundling”

### 7.1 When to bundle (triggers)
Bundle when all are true:
- A cluster of Episodes/Items has **high internal linkage** (dense Bonds),
- It has **stabilized** (low edit rate for N days),
- It has **clear purpose** in QDPI (e.g., supports a Holologue synthesis),
- Evidence coverage is adequate (bundled claims have pointers).

### 7.2 Stop rules (anti mega-bundle guardrails)
Stop bundling if any is true:
- Bundle spans too many distinct motifs/topics (continuity score drops; see eval doc),
- Hubness dominates (bundle just collects popular nodes),
- Evidence becomes thin (increasing ungrounded ratio),
- The bundle becomes non-navigable (user can’t explain why a node is inside).

### 7.3 Reversibility requirement
Every bundle must keep:
- list of constituents,
- bundle rationale (evidence or explicit user note),
- and the ability to “explode” back into constituents.

---

## 8) Entropy prevention controls (v0.1 checklist)

Borrow “data quality control” ideas from knowledge base practice, but keep it lightweight.

### Controls (each should be measurable)
1) **Staleness:** track “time since last verification/anchor resolution” for evidence bundles.
2) **Duplication:** detect near-duplicate nodes and propose merges (block or warn on create).  
   A primary survey on blocking techniques for entity resolution:  
   https://arxiv.org/pdf/1905.06167
3) **Schema/shape checks:** validate required fields for objects before commit (SHACL is a useful conceptual model for constraint graphs).  
   SHACL spec: https://www.w3.org/TR/shacl/
4) **Provenance required:** assertions without evidence pointers are marked “unverified” and decay in rank.
5) **Orphan control:** keep orphan ratio low; orphans get archived or queued for linking.
6) **Hubness alarm:** if top-N nodes dominate suggestions, reduce their candidate weight (prevents soup).
7) **Rollback safety:** corrections happen by compensating events, not rewrites; keep audit trail patterns in mind.  
   (Log-based rollback recovery patterns overview landing page):  
   https://www.semanticscholar.org/paper/Design-Patterns-for-Log-Based-Rollback-Recovery-Saridakis/30a4b43c36d3b4f487126aa12234b8c79c3d351d
8) **Compaction pressure:** watch for compaction/write-stall style symptoms in any embedded store or index layer (even if homegrown).  
   RocksDB write stalls doc: https://github.com/facebook/rocksdb/wiki/Write-Stalls

### “Trust score” (optional, but useful)
KBT-style thinking can inform a simple source reputation signal (not web-scale; just local provenance reliability).  
- KBT paper (Dong et al., PVLDB 2015): https://www.vldb.org/pvldb/vol8/p938-dong.pdf  
- arXiv version: https://arxiv.org/pdf/1502.03519

---

## 9) Governance workflow (human-in-the-loop, v0.1)

### Daily (light)
- Review “expiring Queue” list (TTL candidates).
- Review “stale evidence” list (anchors failing or old).
- Review “duplicate suggestions” list (merge or keep separate).

### Weekly (maintenance)
- Run bundle candidate scan (suggest bundles; do not auto-create).
- Rebuild derived indices if drift/bugs suspected (since they’re rebuildable).
- Review pinned objects for pin-hoarding.

### Override rules
- **Pin beats automation.**
- **Hololink evidence beats automation.**
- Any hard delete requires an explicit confirmation and a reversible quarantine window.

---

## 10) Known failure modes + mitigations

- **Over-bundling → mega-nodes (soup in disguise):** enforce stop rules; require evidence coverage before bundle promotion.
- **Tombstone explosion / slow reads:** treat deletes as markers and compact later; monitor backlog (LSM lesson).  
  RocksDB compaction/write stall docs above.
- **Compaction storms / UI stalls:** keep compaction in background; rate-limit heavy maintenance.
- **Snapshot drift:** invalidate snapshots when logic changes; store snapshot version + last event included.  
  Snapshot guidance: https://www.kurrent.io/blog/snapshots-in-event-sourcing
- **Zombie data (resurrection):** never “partially delete” without consistent propagation; use quarantine and explicit checks.

---

## 11) Stop condition (what “done” means for this doc)
This doc is complete when you can:
- Fill in a **v0.1 policy matrix** (retain/bundle/summarize/prune) for Queue/Episodes/Items/Bonds/Bundles/indices,
- Define **6–10 entropy controls** with measurable triggers,
- Specify **reversibility/audit requirements** for bundle + summary artifacts,
- And identify failure modes for each policy (no “policy without pitfalls”).

---

## References (primary starting set)
- Kafka log compaction (Apache): https://kafka.apache.org/design.html#compaction  
- Kafka topic cleanup policy: https://kafka.apache.org/30/generated/topic_config.html  
- Confluent log compaction doc: https://docs.confluent.io/kafka/design/log_compaction.html  
- RocksDB compaction: https://github.com/facebook/rocksdb/wiki/Compaction  
- RocksDB universal compaction: https://github.com/facebook/rocksdb/wiki/universal-compaction  
- RocksDB write stalls: https://github.com/facebook/rocksdb/wiki/Write-Stalls  
- Prometheus storage/retention: https://prometheus.io/docs/prometheus/latest/storage/  
- ARC (FAST 2003): https://www.cs.cmu.edu/~natassa/courses/15-721/papers/arcfast.pdf  
- SHACL spec: https://www.w3.org/TR/shacl/  
- KBT (Dong et al., 2015): https://www.vldb.org/pvldb/vol8/p938-dong.pdf  
- Entity resolution blocking survey: https://arxiv.org/pdf/1905.06167