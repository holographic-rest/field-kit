# Field-Kit — ONE PAGER (Draft)

* **What it is:** Field-Kit is a local-first “Field” system built around **QDPI** (Queue / Monologue / Dialogue / Holologue) for navigating and developing structured knowledge over time.
* **Core problem:** Most AI navigation is “vibes + prose.” Field-Kit targets **grounded navigation**: suggestions must cite *why* they were suggested.
* **Key capability:** Suggestions are **pointer-like** and probabilistic (ranked distribution) and include **evidence shards** that quote exact spans with offsets.
* **Multi-scale context:** Evidence can draw from **local + mid + far** context using a dilated sampling schedule, instead of collapsing everything into a single summary.
* **Graph awareness:** Suggestions incorporate **graph structure** (distance + message-passing reranking), enabling disambiguation and structural coherence.
* **Session continuity:** A 6-slot **session state** (RMC-inspired) preserves “the thread” across steps and tracks whether state influenced outcomes (`state_utilized`).
* **Measurement:** An **eval harness + regression suite** makes improvements measurable and prevents regressions (dashboard + automated checks).
* **Governance:** A “thermodynamic” governance layer measures drift (complexity, hubness, orphan rate, entropy) and **recommends** actions (branch/bundle/prune/continue) without auto-executing destructive changes.
* **Anti-noise controls:** MDL/structure-vs-noise gates help filter boilerplate and randomness while protecting structured novelty (suggest-only annotations today).
* **Local durability:** Storage supports JSONL and an opt-in **SQLiteStore (FTS5 + WAL)** with **migration** and **backup/restore with SHA-256 verification**, ensuring portability and recoverability for demos and research.

**Status:** End-to-end demo is stable (golden flow), grounded suggestions are operational (ECR > 0), multi-scale + graph signals are visible in CLI output, and eval/regression remains green across iterative sprints.