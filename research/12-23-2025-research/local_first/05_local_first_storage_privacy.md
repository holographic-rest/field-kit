# Local-first storage, indexing, privacy/security constraints (v0.1 ethos)
**Path:** `/research/12-23-2025/local_first/05_local_first_storage_privacy.md`  
**Status:** draft (research → pick 2 stacks + v0.1 security posture + backup plan)

## Purpose
Choose defensible local-first storage + indexing patterns (including security/privacy posture) that support **ledger replay**, **evidence anchors**, and **fast navigation**—without accounts/payments/cloud dependence.

---

## 0) What we’re optimizing for (v0.1 constraints)
**Hard constraints**
- **Offline-first / local-first:** no required cloud services, accounts, or payments.
- **Auditability:** ledger replay must remain possible (or at least reconstructable) without trusting derived indexes.
- **Grounding integrity:** evidence anchors must remain resolvable and protected from “cleanup.”
- **Small moving parts:** prefer one process + one durable store until it hurts.

**Soft constraints**
- Optional future sync/collab is allowed, but **must not** distort v0.1 into a distributed-systems project.

---

## 1) Threat model (v0.1) + privacy goals

### Assets to protect
- The novel text (The Entrance Way), drafts, and derivatives.
- The ledger (event history) + object graph.
- Evidence bundles (selectors + excerpts) and Vault sources.
- User identity metadata (even if “local identity”).

### Adversaries (realistic for local-first)
- **Lost/stolen device** (offline attacker with disk access).
- **Curious local user** (shared computer account).
- **Backup leakage** (an unencrypted export copied elsewhere).
- **Bit rot / corruption** (accidental but destructive).

### Out of scope (v0.1, be honest)
- A fully compromised OS (malware with user privileges can exfiltrate plaintext at runtime).
- Nation-state forensic recovery against SSD wear-leveling beyond what app-level controls can guarantee.

### Privacy goals
- **Encryption at rest** for sensitive data.
- **Minimal telemetry:** ideally none.
- **No secret material in logs** (crash logs are a common footgun).
- **Tamper-evidence** for the ledger (detect silent edits to the DB file).

---

## 2) Local-first architecture options (CRDT vs event-log vs hybrid)

These are *architectural shapes*, not products.

### Option A — Event-sourced ledger (recommended for v0.1)
**Why it fits Gibsey/Holographic:** audit trails, time travel, projections, “system reads itself.”

- Store append-only events locally.
- Build projections (graph + FTS + vector) as disposable views.
- Sync/collab, if later: replicate logs; allow explicit merges/forks (Git-like).

Primary references:
- Ink & Switch local-first essay (principles and tradeoffs): https://www.inkandswitch.com/essay/local-first/
- Kleppmann et al. local-first paper (formal framing): https://martin.kleppmann.com/papers/local-first.pdf

### Option B — Pure CRDT state (not recommended for v0.1)
Best when real-time collaboration is the main requirement.
- Pros: automatic merge; great concurrent editing UX.
- Cons: audit intent is often weaker; metadata/tombstones can grow; harder to explain “why.”

Starting points:
- Yjs docs: https://docs.yjs.dev/
- Automerge docs: https://automerge.org/

### Option C — Hybrid (CRDT for text, ledger for graph)
Potential future direction if you later need collaborative text editing *without* sacrificing graph auditability.
- Higher complexity (two consistency models).
- Defer until collaboration is a real requirement.

**v0.1 decision:** default to **Option A** (event-sourced ledger). Everything else is scope risk.

---

## 3) Embedded storage + indexing stacks (choose 2 plausible ones)

We need: (a) event log, (b) graph queries, (c) full-text search, (d) optional vector search — all local.

### Stack 1 — “Modern SQLite” (recommended v0.1 baseline)
**Shape:** one SQLite database file as source-of-truth + built-in FTS; optional vector extension; Vault as files.

**Why it’s attractive**
- Single portable file + ACID transactions + crash safety.
- Easy backups, easy export, easy “open with any tool.”
- FTS5 is mature and local.
- Fits event sourcing well (events table + projections tables).

Primary references:
- SQLite (overview): https://sqlite.org/docs.html
- WAL mode (crash/recovery behavior): https://sqlite.org/wal.html
- FTS5: https://sqlite.org/fts5.html

**Vector**
- For “small-to-medium” corpora, brute-force SIMD can be acceptable; for larger, you’ll need ANN.
- sqlite-vec (project primary): https://github.com/asg017/sqlite-vec

**Tradeoffs / gotchas**
- Graph traversals via SQL recursive queries are fine up to modest hop counts; deep traversals are slower than graph-native engines.
- If you add separate sidecar indexes later, you must manage “index drift.”

### Stack 2 — SQLite (truth) + Tantivy (search sidecar)
**Shape:** SQLite remains the ledger + graph; Tantivy is a search projection for high-performance BM25 and richer query features.

Primary references:
- Tantivy architecture: https://github.com/quickwit-oss/tantivy/blob/main/ARCHITECTURE.md
- (Also see Lucene segment model as conceptual backing): https://lucene.apache.org/core/

**Why this stack exists**
- Tantivy uses immutable segments + merges, which maps well to incremental indexing and replayable projections.
- You can rebuild the Tantivy index from the ledger if it corrupts or drifts.

**Tradeoffs / gotchas**
- Two durable stores to back up and keep consistent.
- Needs a clear “projection lag” UX: search may be slightly behind the latest edits unless you tune update cadence.

### Stack 3 — Embedded graph DB (Kùzu) + separate event log
**Shape:** graph-native queries (fast hops) with an embedded graph database; keep a separate append-only event log for audit.

Primary references:
- Kùzu docs: https://docs.kuzudb.com/

**Tradeoffs**
- Great for graph traversal.
- You’ll still need FTS and robust event-sourcing patterns; ecosystems are younger than SQLite.
- More migration risk for v0.1 unless graph traversal is the dominant workload.

### Stack 4 — Columnar / vector-native (LanceDB) + separate graph handling
**Shape:** strongest when embeddings are the center; weaker for graph traversals and event semantics.

Primary references:
- LanceDB docs: https://lancedb.github.io/lancedb/

**v0.1 recommendation:** pick **Stack 1 now**, keep **Stack 2** as the first upgrade path.

---

## 4) Storage layout (v0.1) — minimal, debuggable, recoverable

**Principle:** separate *truth* from *derived views* from *source artifacts*.

### Suggested layout
- `/data/gibsey.sqlite`  
  - ledger events (truth)
  - object graph read model (nodes/edges, evidence registry)
  - FTS index (either inside SQLite via FTS5, or via sidecar)
- `/vault/`  
  - source documents (PDF/MD/TXT) referenced by evidence bundles
  - optionally encrypted blobs (see security posture)
- `/indexes/` (optional, only if you add sidecars)
  - tantivy index directory (rebuildable)
  - vector index files (rebuildable)
- `/exports/`  
  - timestamped backups/exports (encrypted)

**Invariant:** if `/indexes/` is deleted, the system still works after a rebuild from ledger + vault.

---

## 5) Indexing update strategy (local, incremental)

### Full-text (FTS)
- Prefer incremental updates that are **transactionally tied** to the ledger commit where possible.
- If you run async indexing, make the lag visible and always provide a “rebuild index” command.

SQLite FTS5 reference: https://sqlite.org/fts5.html

### Vector search
- v0.1 can tolerate:
  - brute-force SIMD for smaller N (simpler, fewer failure modes), or
  - a “hot/cold” split (recent vectors in a hot store, periodic merge/rebuild).

sqlite-vec reference: https://github.com/asg017/sqlite-vec

### Graph expansion
- Keep graph traversal logic independent of the search index so that indexing failures do not break basic navigation.

---

## 6) Encryption-at-rest + key handling (v0.1 posture)

### 6.1 Database encryption
**Do not roll your own.** Use a proven SQLite encryption layer.

Primary references:
- SQLCipher design: https://www.zetetic.net/sqlcipher/design/
- SQLCipher docs (general): https://www.zetetic.net/sqlcipher/

**Guidance**
- Encrypt the SQLite database containing: ledger, graph, evidence registry, and FTS content.
- Treat derived indexes as either:
  - encrypted as well, or
  - rebuildable from the encrypted DB (but beware: plaintext sidecar indexes can leak sensitive text).

### 6.2 Key derivation (password → key)
NIST SP 800-132 covers PBKDF2-based derivation guidance (baseline):  
- https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf

OWASP guidance generally recommends modern, memory-hard schemes like Argon2id for password hashing/KDF in many contexts:  
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

**v0.1 policy**
- If you do password-based encryption, pick a conservative KDF and document parameters.
- If possible, prefer OS keychains to avoid user-managed passwords entirely (below).

### 6.3 Key storage (don’t put secrets in config files)
- Use OS-managed secure storage for the master key.
  - Electron safeStorage: https://www.electronjs.org/docs/latest/api/safe-storage
  - (If not Electron, use the OS keychain equivalents; the principle is the same.)

### 6.4 Memory hygiene (nice-to-have, not theater)
- Zero sensitive key material after use when feasible.
- Avoid writing secrets to crash logs.

---

## 7) Secure deletion (what “delete” can actually mean)

**Reality check:** on SSDs, overwriting bytes is not a reliable guarantee because of wear leveling.

### v0.1 recommended strategy: crypto-shredding for sensitive blobs
- Encrypt each large blob (or vault file) with a per-item key, wrapped by a master key.
- To delete: delete the per-item key (renders ciphertext unrecoverable).

Concept reference (crypto-shredding overview): https://www.seald.io/blog/data-destruction-using-crypto-shredding

### SQLite-specific mitigation: secure_delete (partial help)
SQLite provides `PRAGMA secure_delete` but it does not guarantee SSD-level erasure; it mainly reduces casual forensic recovery from freed pages inside the DB file.  
- SQLite pragma reference: https://sqlite.org/pragma.html#pragma_secure_delete

---

## 8) Integrity, corruption detection, and recovery

### 8.1 Tamper-evident ledger (detect silent edits)
Maintain a hash chain across event records (event_n includes hash of event_{n-1}). This is not “blockchain,” it’s a cheap integrity check.
- If verification fails, flag corruption/tampering and offer recovery (restore from backup).

### 8.2 SQLite integrity checks
- Use `PRAGMA integrity_check;` as a diagnostic tool (especially after crash recovery).
Reference: https://sqlite.org/pragma.html#pragma_integrity_check

### 8.3 Backups (must be boring and testable)
**Rules**
- Back up both:
  - the encrypted database
  - the Vault sources
  - any sidecar indexes only if you can’t rebuild quickly

SQLite backup primitives:
- Online Backup API: https://sqlite.org/backup.html
- “VACUUM INTO” (creates a consistent copy): https://sqlite.org/lang_vacuum.html

**Export format suggestion**
- `export.tar` containing:
  - db file
  - vault directory
  - a manifest (versions, hashes, last event id)
- Encrypt export with a modern AEAD-friendly tool format (example: age).  
  - age tool: https://github.com/FiloSottile/age

### 8.4 Migration/versioning
- Store schema versions for DB + event versions for the ledger.
- Prefer “upcasters” for event evolution (see event-sourcing doc).

---

## 9) Performance envelope + common failure modes

### Performance boundaries (qualitative)
- SQLite+FTS5 is strong for local workloads; performance issues usually come from:
  - huge documents indexed naively,
  - too many triggers/updates per keystroke,
  - rebuilding vectors too frequently,
  - complex graph traversals without constraints.

### Failure modes + mitigations
1) **Corruption / partial writes**
   - Mitigate: WAL mode, consistent backup strategy, integrity checks, power-loss testing.
2) **Index drift**
   - Mitigate: treat indexes as projections; store “last indexed event id”; rebuild on mismatch.
3) **Slow migrations**
   - Mitigate: version everything; do blue/green rebuild for projections; keep a reversible migration path.
4) **Index rebuild pain**
   - Mitigate: keep rebuild time bounded; document “rebuild index” procedure; keep minimal indexes in v0.1.
5) **Accidental plaintext leakage**
   - Mitigate: encrypt sidecar indexes or ensure they are rebuildable and not stored in backups unless encrypted.

---

## 10) v0.1 recommendations (decisions you can actually make now)

### Pick two stacks (decision set)
**Primary (ship first): Stack 1 — SQLite (WAL) + FTS5 + optional sqlite-vec**  
- One durable file; simplest to back up; best for local-first v0.1.

**Upgrade path: Stack 2 — SQLite + Tantivy sidecar**  
- Only if FTS5/hybrid queries become the bottleneck.

### Security posture (v0.1)
- Encrypt DB with SQLCipher (or equivalent).
- Store master key in OS keychain (Electron safeStorage or native).
- Use crypto-shredding for sensitive vault blobs when deletion matters.
- Ensure backups are encrypted and tested.

### Backup/export plan (v0.1)
- Nightly (or manual) encrypted export:
  - DB + Vault + manifest + hashes
- Monthly restore drill:
  - verify integrity
  - rebuild indexes from ledger
  - spot-check evidence anchor resolution

---

## 11) Stop condition (what “done” means for this doc)
This doc is complete when you can:
- Choose **2 plausible stacks** (baseline + upgrade path),
- Specify a **v0.1 threat model** and concrete security checklist,
- Define a **backup/export format** and a restore drill,
- List the top failure modes and how the design detects/recovers from them.

---

## Primary sources (starting set)
- Local-first principles: https://www.inkandswitch.com/essay/local-first/  
- Local-first paper (Kleppmann et al.): https://martin.kleppmann.com/papers/local-first.pdf  
- SQLite docs: https://sqlite.org/docs.html  
- SQLite WAL: https://sqlite.org/wal.html  
- SQLite FTS5: https://sqlite.org/fts5.html  
- sqlite-vec: https://github.com/asg017/sqlite-vec  
- Tantivy architecture: https://github.com/quickwit-oss/tantivy/blob/main/ARCHITECTURE.md  
- SQLCipher design: https://www.zetetic.net/sqlcipher/design/  
- NIST SP 800-132 (PBKDF guidance): https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf  
- OWASP password storage guidance: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html  
- Electron safeStorage: https://www.electronjs.org/docs/latest/api/safe-storage  
- SQLite backup: https://sqlite.org/backup.html  
- Crypto-shredding overview: https://www.seald.io/blog/data-destruction-using-crypto-shredding  
- age encrypted archives: https://github.com/FiloSottile/age