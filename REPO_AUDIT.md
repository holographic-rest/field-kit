# field-kit — Repository Overview (for application use)

## 1) One-paragraph summary (what this repo is, in plain English)

Field-Kit is a local-first knowledge work system that treats AI interactions as persistent, traceable objects rather than ephemeral chat. The system organizes content into Networks and Episodes, where Items (Queue, Monologue, Dialogue, Holologue) are connected by Bonds (executable transformations). All actions are logged as append-only QDPIEvents, creating an inspectable ledger. The system includes a credits simulation, evidence-based suggestions with multi-scale context, graph-aware navigation, and governance mechanisms. Field-Kit demonstrates that AI interaction can be structured, auditable, and portable—not just a chat interface. The prototype runs end-to-end via CLI and includes a web UI, with comprehensive tests and evaluation harnesses.

---

## 2) What is implemented today (proof of execution)

- **Core data schemas (Network, Episode, Item, Bond, QDPIEvent)** — `src/fieldkit/schemas.py` — run: `python3 src/cli.py init` / see: `prototype/data/*.jsonl`
- **JSONL storage layer** — `src/fieldkit/store_jsonl.py` — run: `python3 src/cli.py init` / see: `prototype/data/items.jsonl`, `bonds.jsonl`, `episodes.jsonl`, `networks.jsonl`, `qdpi_events.jsonl`
- **SQLite storage with FTS5** — `src/fieldkit/store_sqlite.py` — run: `python3 src/cli.py migrate:jsonl-to-sqlite` / see: `prototype/data/fieldkit.db`
- **CLI with 30+ commands** — `src/cli.py` — run: `python3 src/cli.py --help` / commands: `init`, `item:create`, `bond:create`, `bond:run`, `holologue:run`, `ledger:open`, `curated:view`, `govern:report`, `backup:create`
- **Golden Flow acceptance test** — `prototype/scripts/run_golden_flow.py` — run: `python3 prototype/scripts/run_golden_flow.py --fresh` / expected: credits=73, all assertions pass
- **Event logging system (QDPI events)** — `src/fieldkit/qdpi.py` — run: `python3 src/cli.py ledger:open` / see: canonical event names in `qdpi_events.jsonl`
- **Credits simulation** — `src/cli.py` (credits_delta methods) — run: `python3 src/cli.py init` then `item:create` / see: credits balance updates via events
- **Holologue (many→one synthesis)** — `src/fieldkit/holologue.py`, `src/fieldkit/generation.py` — run: `python3 src/cli.py holologue:run --items it_XXX it_YYY` / see: H-type output item created
- **Bond execution with provenance** — `src/cli.py cmd_bond_run()` — run: `python3 src/cli.py bond:run bd_XXX` / see: output item with `provenance.bond_id`
- **Spin Recipes (suggestion templates)** — `src/fieldkit/spin_recipes.py` — run: `python3 src/cli.py suggestions:show it_XXX` / see: 4 content-shaped suggestions
- **Queue Lattice (handles, hololoops)** — `src/fieldkit/handles.py`, `src/fieldkit/hololoop_engine.py` — run: `python3 src/cli.py hololoop:options it_A it_B` / see: 4 hololoop relation options
- **Evidence-based suggestions with multi-scale context** — `src/fieldkit/suggestion_engine.py`, `src/fieldkit/dilated_context.py` — run: `python3 src/cli.py suggestions:show it_XXX` / see: evidence shards with scale metadata
- **Graph propagation for reranking** — `src/fieldkit/graph_propagation.py` — run: `python3 src/cli.py suggestions:show it_XXX` / see: graph_distance in output
- **Governance layer (complexity metrics, bundle/prune suggestions)** — `src/fieldkit/governor.py`, `src/fieldkit/complexity.py`, `src/fieldkit/bundling.py`, `src/fieldkit/pruning.py` — run: `python3 src/cli.py govern:report` / see: action recommendations
- **Session state (6-slot memory)** — `src/fieldkit/session_state.py` — implemented but not yet fully integrated into CLI flow
- **MDL scoring (structure vs noise)** — `src/fieldkit/mdl_scoring.py` — implemented as suggest-only annotations
- **Backup/restore with verification** — `src/fieldkit/backup.py` — run: `python3 src/cli.py backup:create` / see: `backup_TIMESTAMP.tar` with SHA-256 manifest
- **Evaluation harness and regression suite** — `tests/eval_harness.py`, `tests/regression_suite.py` — run: `python3 src/cli.py eval:dashboard` / see: MRR@K, Recall@K, ECR metrics
- **Web UI (Flask-based)** — `prototype/ui/app.py` — run: `python3 prototype/ui/app.py` / open: `http://localhost:5001` / see: flow-first UI with composer, suggestions, ledger drawer

---

## 3) Major subsystems (map the repo)

### Core Storage
- **Purpose:** Persist Network, Episode, Item, Bond objects and append-only QDPIEvents
- **Key files:** `src/fieldkit/store_jsonl.py`, `src/fieldkit/store_sqlite.py`, `src/fieldkit/schemas.py`
- **Data structures:** Network, Episode, Item, Bond, QDPIEvent (all in `schemas.py`)
- **Status:** working (JSONL default, SQLite opt-in with migration)

### Event Logging (QDPI)
- **Purpose:** Append-only event ledger with canonical event names
- **Key files:** `src/fieldkit/qdpi.py`, `src/cli.py` (EventLogger usage)
- **Data structures:** QDPIEvent with `(episode_id, seq)` ordering
- **Status:** working (33 events in Golden Flow, all canonical names)

### Bond System
- **Purpose:** Executable transformations from input Items to output Items
- **Key files:** `src/cli.py` (bond commands), `src/fieldkit/generation.py`, `src/fieldkit/spin_recipes.py`
- **Data structures:** Bond (draft → executed), Item with provenance
- **Status:** working (draft creation, execution, failure handling with refunds)

### Holologue (Many→One)
- **Purpose:** Synthesize multiple Items into a single H-type artifact
- **Key files:** `src/fieldkit/holologue.py`, `src/fieldkit/generation.py`
- **Data structures:** Item (type="H") with ItemProvenanceHolologue
- **Status:** working (validates ≥2 items, generates output, emits proposals)

### Suggestion Engine
- **Purpose:** Generate evidence-based bond suggestions with multi-scale context
- **Key files:** `src/fieldkit/suggestion_engine.py`, `src/fieldkit/dilated_context.py`, `src/fieldkit/pointer_scorer.py`, `src/fieldkit/graph_propagation.py`
- **Data structures:** Suggestions with evidence_shards, scale metadata, graph_distance
- **Status:** working (S03/S04/S05 features implemented, evidence shards present)

### Queue Lattice
- **Purpose:** Handle extraction and hololoop generation for Queue Items
- **Key files:** `src/fieldkit/handles.py`, `src/fieldkit/hololoop_engine.py`, `src/fieldkit/anchor_pairing.py`
- **Data structures:** ItemHandle (quote, kind, starred), hololoop Bonds
- **Status:** working (handle extraction, hololoop options, hololoop creation)

### Governance Layer
- **Purpose:** Measure complexity and suggest actions (bundle/prune/branch/continue)
- **Key files:** `src/fieldkit/governor.py`, `src/fieldkit/complexity.py`, `src/fieldkit/bundling.py`, `src/fieldkit/pruning.py`
- **Data structures:** ComplexityObservation, BundleProposal, PrunePlan
- **Status:** working (suggest-only, no auto-execution)

### Evaluation & Testing
- **Purpose:** Measure suggestion quality and prevent regressions
- **Key files:** `tests/eval_harness.py`, `tests/regression_suite.py`, `prototype/scripts/run_golden_flow.py`
- **Data structures:** TestCase JSON, BaselineScores JSON
- **Status:** working (MRR@K, Recall@K, ECR metrics, regression thresholds)

### Web UI
- **Purpose:** Flow-first local web interface
- **Key files:** `prototype/ui/app.py`, `prototype/ui/templates/index.html`, `prototype/ui/static/`
- **Data structures:** Flask routes, JSON API
- **Status:** working (basic UI, composer, suggestions, ledger drawer)

### Backup & Export
- **Purpose:** Portable data export/import with verification
- **Key files:** `src/fieldkit/backup.py`
- **Data structures:** Backup manifest with SHA-256 hashes
- **Status:** working (create, restore, verify, list commands)

---

## 4) Architecture snapshot

- **Storage:** Dual-layer (JSONL default, SQLite opt-in) with migration path; append-only events, snapshot objects
- **Data model:** Network → Episode → Items/Bonds; all objects have stable prefixed IDs (`nw_`, `ep_`, `it_`, `bd_`, `ev_`)
- **Event ledger:** QDPIEvents ordered by `(episode_id, seq)`, canonical event names only, immutable append-only
- **Credits simulation:** Event-driven deltas (`credits.delta` events), derived balance, no real money
- **Bond lifecycle:** Draft → Executed (or Failed with refund); output Items have provenance back to Bond
- **Holologue:** Many→one synthesis (2+ Items → 1 H output), emits proposals after completion
- **Suggestion pipeline:** Item → embeddings → retrieval → dilated context → pointer scoring → graph propagation → 4 suggestions
- **Evidence shards:** Multi-scale context (local/mid/far) with dilation offsets, quoted text spans
- **Graph awareness:** MPNN-style message passing for graph distance and reranking
- **Queue Lattice:** Handle extraction (3-7 per Item), hololoop generation (4 relation types)
- **Governance:** Complexity metrics (hubness, orphan rate, entropy) → action suggestions (bundle/prune/branch)
- **Session state:** 6-slot memory (RMC-inspired) for continuity tracking
- **MDL controls:** Structure-vs-noise scoring (suggest-only annotations)
- **Evaluation:** Test cases with acceptability criteria, MRR@K/Recall@K/ECR metrics, regression baselines
- **CLI:** 30+ commands covering all operations (init, items, bonds, holologue, ledger, curation, export, governance, backup)
- **Web UI:** Flask server, flow-first UX (composer → suggestions → bonds → holologue), ledger drawer
- **Backup:** Tar archive with SHA-256 manifest, restore with verification

---

## 5) Specs and essays (what's documented)

### Specs (Decision Layer) — `docs/specs/`

- **00_winter_sprint_plan.md** — Sprint timeline and goals (S01-S10)
- **01_first_run_experience_v0.1.md** — App initialization flow — defines bootstrap sequence
- **02_core_data_objects_v0.1.md** — Network, Episode, Item, Bond, QDPIEvent schemas — canonical data model
- **03_bond_ontology_v0.1.md** — Bond lifecycle, proposals, execution — defines transformation semantics
- **04_holologue_spec_v0.1.md** — Many→one synthesis — defines artifact generation
- **05_demo_golden_flow_v0.1.md** — Acceptance test — the non-negotiable demo that must pass
- **06_canon_policy_v0.1.md** — Curated lists, derived projection — defines canon computation
- **07_spin_recipes_v0.1.md** — Suggestion templates — defines content-shaped suggestions
- **08_UI_UX_foundation_v0.1.md** — UI surfaces and behavior — defines flow-first UX

### Architecture (Explanation Layer) — `docs/architecture/`

- **INDEX.md** — Architecture document index
- **field_overview/** (27 pages) — Comprehensive architecture walkthrough by layer (L0-L4) — mostly conceptual/research
- **POINTER_NAVIGATION.md** — Pointer-based navigation with candidate scoring (S03/S05) — implemented
- **EVIDENCE_CITATIONS.md** — Evidence shards and multi-scale context (S03/S04) — implemented
- **MULTI_SCALE_CONTEXT.md** — Dilated context sampling (S04) — implemented
- **GRAPH_PROPAGATION.md** — MPNN-style message passing (S05) — implemented
- **COMPLEXITY_METRICS.md** — Coffee Automaton-inspired complexity measurement (S06) — implemented
- **MEMORY_GOVERNANCE.md** — Suggest-only governance layer (S06) — implemented
- **SESSION_STATE.md** — RMC-style multi-slot session memory (S07) — implemented
- **PIPELINE_BATCHING.md** — GPipe-style microbatching (S08) — partial (pipeline exists, batching not fully integrated)
- **MDL_CONTROLS.md** — MDL scoring and structure-vs-noise gates (S09) — implemented (suggest-only)
- **STORAGE_SQLITE.md** — SQLite storage layer with FTS5 (S10) — implemented
- **BACKUP_EXPORT.md** — Backup, export, and restore functionality (S10) — implemented

### Essays (Theory/Research) — `docs/essays/`

- **field-markets.md** — Field Markets protocol proposal — conceptual/research (portable state, proof chains, anti-monolith trade)
- **holographic_&_gibsey_paper.md** — BKC theory essay — conceptual/research (Holographic, Gibsey, QDPI theory)

### Research — `research/`

- **ML_spine_for_gibsey_QDPI.md** — ML architecture for Gibsey QDPI — research notes
- **01_event_embedding_notes.md** — Event embedding research
- **02_event_similarity_smoke_test.md** — Event similarity testing
- Various research essays in `27-essays/` and `12-23-2025-research/`

---

## 6) Demo pathways (how to show this to a reviewer)

### Demo A: Golden Flow (CLI) — 3-5 minutes

**What to run:**
```bash
cd field-kit
python3 prototype/scripts/run_golden_flow.py --fresh
```

**What it shows:**
- Network and Episode 0 creation
- 5 Items created (Q, Q, M, D, H)
- 2 Bonds executed with provenance
- Holologue synthesis
- Event ordering validation
- Credits simulation (ends at 73)
- All assertions pass

**Expected output:**
```
GOLDEN FLOW COMPLETE — ALL ASSERTIONS PASSED!
```

**Evidence:** `prototype/data/*.jsonl` files, `prototype/scripts/run_golden_flow.py` (376 lines)

### Demo B: Evidence-Based Suggestions (CLI) — 2 minutes

**What to run:**
```bash
python3 src/cli.py init
python3 src/cli.py item:create --title "How does graph propagation work?" --body "I want to understand MPNN-style message passing..."
python3 src/cli.py suggestions:show it_XXX  # use item ID from previous command
```

**What it shows:**
- 4 content-shaped suggestions with evidence shards
- Multi-scale context (local/mid/far) with dilation offsets
- Graph distance metadata
- Pointer probabilities

**Expected output:**
```
Suggestions presented for item it_XXX:
  (scales: local, mid)
  1. [explain] (85%) [d=2] Explain graph propagation using...
     [local@0] "MPNN-style message passing"
     [mid@1] "graph structure"
  2. [compare] (12%) [d=3] Compare graph propagation to...
```

**Evidence:** `src/fieldkit/suggestion_engine.py`, `src/fieldkit/dilated_context.py`, `src/fieldkit/graph_propagation.py`

### Demo C: Governance Report (CLI) — 1 minute

**What to run:**
```bash
python3 src/cli.py govern:report
```

**What it shows:**
- Complexity metrics (hubness, orphan rate, entropy)
- Action recommendation (bundle/prune/branch/continue)
- Bundle candidates (if any)
- Prune plan (if any)

**Expected output:**
```
GOVERNANCE REPORT
Complexity: 0.42 (moderate)
Hubness: 0.15 (low)
Orphan rate: 0.08 (low)
Recommendation: continue
```

**Evidence:** `src/fieldkit/governor.py`, `src/fieldkit/complexity.py`

### Demo D: Web UI (Browser) — 5 minutes

**What to run:**
```bash
python3 prototype/ui/app.py
# Open http://localhost:5001
```

**What it shows:**
- Flow-first UI (composer at bottom)
- Create Queue item → see 4 inline suggestions
- Click suggestion → Bond executes → Monologue output
- Select 2+ items → Holologue bar appears
- Run Holologue → Holologue output + proposals
- Press L → Ledger drawer (Objects, Events, Curated, JSON tabs)
- Credits chip updates on actions

**Expected output:** Visual UI with working flow

**Evidence:** `prototype/ui/app.py` (518 lines), `prototype/ui/templates/index.html`, `prototype/ui/static/`

---

## 7) Tests and reliability

### Test Frameworks

- **Golden Flow:** Custom acceptance test script (`prototype/scripts/run_golden_flow.py`)
- **Regression Suite:** Custom regression test runner (`tests/regression_suite.py`)
- **Evaluation Harness:** Custom eval engine (`tests/eval_harness.py`)
- **Unit Tests:** Python unittest-style (`tests/test_*.py`)

### Test Locations

- **Acceptance tests:** `prototype/scripts/run_golden_flow.py`, `run_golden_flow_3x.py`
- **Sprint tests:** `prototype/scripts/test_sprint_*.py` (C, D, E, G)
- **Unit tests:** `tests/test_store_jsonl.py`, `test_store_sqlite.py`, `test_schemas.py`, `test_backup_restore.py`, `test_governance.py`, `test_mdl_controls.py`, `test_pipeline.py`, `test_session_state.py`
- **Evaluation:** `tests/eval_harness.py`, `tests/regression_suite.py`, `tests/test_cases/*.json`

### How to Run

```bash
# Golden Flow (acceptance test)
python3 prototype/scripts/run_golden_flow.py --fresh

# Regression suite
python3 src/cli.py eval:regression

# Evaluation dashboard
python3 src/cli.py eval:dashboard

# Unit tests (if pytest available)
python3 -m pytest tests/

# Sprint-specific tests
python3 prototype/scripts/test_sprint_c_canon.py
python3 prototype/scripts/test_sprint_d_spin_recipes.py
python3 prototype/scripts/test_sprint_e_stability.py
```

### CI/Linters/Type Checks

- **No CI config found** (no `.github/workflows/` or `.gitlab-ci.yml`)
- **No linter config found** (no `.flake8`, `.pylintrc`, `pyproject.toml` with linting)
- **No type checking config found** (no `mypy.ini`, `pyrightconfig.json`)
- **No requirements.txt** (stdlib-only Python, no external dependencies)

### Test Coverage

- **Golden Flow:** 5/5 runs pass (S01 diagnosis report)
- **Regression suite:** Baseline scores stored in `tests/baselines/baseline_scores.json`
- **Evaluation:** 4 test cases defined (`golden_flow.json`, `m_golden_flow_second_item.json`, `q_synthetic_field_overview.json`, `q_synthetic_strict_intent.json`)

---

## 8) Repo inventory (high-signal file tree)

```
field-kit/
├── src/
│   ├── cli.py                    # CLI entrypoint (1834 lines, 30+ commands)
│   └── fieldkit/
│       ├── schemas.py            # Core data objects (Network, Episode, Item, Bond, QDPIEvent)
│       ├── store_jsonl.py         # JSONL storage (default)
│       ├── store_sqlite.py        # SQLite storage (opt-in, FTS5)
│       ├── qdpi.py               # Event logging
│       ├── generation.py          # Bond/Holologue output generation
│       ├── spin_recipes.py       # Suggestion templates
│       ├── suggestion_engine.py  # Evidence-based suggestions
│       ├── dilated_context.py    # Multi-scale context
│       ├── graph_propagation.py  # Graph-aware reranking
│       ├── handles.py            # Queue Lattice handle extraction
│       ├── hololoop_engine.py    # Hololoop generation
│       ├── holologue.py           # Many→one synthesis
│       ├── governor.py           # Governance layer
│       ├── complexity.py          # Complexity metrics
│       ├── bundling.py            # Bundle detection
│       ├── pruning.py            # Prune planning
│       ├── session_state.py      # 6-slot session memory
│       ├── mdl_scoring.py         # MDL scoring
│       ├── backup.py              # Backup/restore
│       └── [20+ other modules]
├── prototype/
│   ├── scripts/
│   │   ├── run_golden_flow.py    # Acceptance test (376 lines)
│   │   ├── run_golden_flow_3x.py  # Repeatability test
│   │   ├── run_sprint_b_dogfood.py
│   │   └── test_sprint_*.py       # Sprint-specific tests
│   ├── ui/
│   │   ├── app.py                # Flask web UI (518 lines)
│   │   ├── templates/index.html
│   │   └── static/
│   └── data/                      # Runtime data (gitignored)
│       ├── *.jsonl                # JSONL store files
│       └── fieldkit.db            # SQLite (if migrated)
├── tests/
│   ├── eval_harness.py            # Evaluation engine
│   ├── regression_suite.py        # Regression test runner
│   ├── test_cases/                # Test case definitions (JSON)
│   ├── baselines/                 # Baseline scores (JSON)
│   └── test_*.py                  # Unit tests
├── docs/
│   ├── specs/                     # Decision layer (9 specs)
│   │   ├── 05_demo_golden_flow_v0.1.md  # Acceptance test spec
│   │   └── [other specs]
│   ├── architecture/              # Explanation layer
│   │   ├── field_overview/        # 27-page architecture overview
│   │   └── [sprint architecture docs]
│   └── essays/                    # Theory/research
│       ├── field-markets.md       # Field Markets protocol proposal
│       └── holographic_&_gibsey_paper.md
├── research/                      # Research notes and essays
├── sprints/                       # Sprint plans and reports
└── README.md                      # Main README
```

---

## 9) "What to claim in an application" (bullet bank)

- Built a local-first knowledge work system with persistent objects (Network, Episode, Item, Bond) and append-only event ledger (evidence: `src/fieldkit/schemas.py`, `src/fieldkit/store_jsonl.py`, `prototype/scripts/run_golden_flow.py`)
- Implemented evidence-based suggestions with multi-scale context (local/mid/far) and graph-aware reranking (evidence: `src/fieldkit/suggestion_engine.py`, `src/fieldkit/dilated_context.py`, `src/fieldkit/graph_propagation.py`, CLI output shows evidence shards)
- Built Holologue: many→one synthesis that takes 2+ Items and produces a single synthesized artifact (evidence: `src/fieldkit/holologue.py`, `src/cli.py cmd_holologue_run()`, Golden Flow Step 8)
- Implemented Queue Lattice: handle extraction and hololoop generation for connecting Queue Items (evidence: `src/fieldkit/handles.py`, `src/fieldkit/hololoop_engine.py`, CLI `hololoop:options` command)
- Built governance layer that measures complexity (hubness, orphan rate, entropy) and suggests actions without auto-executing (evidence: `src/fieldkit/governor.py`, `src/fieldkit/complexity.py`, CLI `govern:report` command)
- Implemented dual storage layer (JSONL default, SQLite opt-in) with migration and backup/restore with SHA-256 verification (evidence: `src/fieldkit/store_jsonl.py`, `src/fieldkit/store_sqlite.py`, `src/fieldkit/backup.py`, CLI `migrate:jsonl-to-sqlite`, `backup:create`)
- Built evaluation harness with MRR@K, Recall@K, ECR metrics and regression suite to prevent quality regressions (evidence: `tests/eval_harness.py`, `tests/regression_suite.py`, CLI `eval:dashboard`, `eval:regression`)
- Implemented credits simulation as event-driven deltas (not real money) to demonstrate inspectable economic layer (evidence: `src/cli.py` credits methods, Golden Flow ends at credits=73)
- Built comprehensive CLI with 30+ commands covering all operations (init, items, bonds, holologue, ledger, curation, export, governance, backup) (evidence: `src/cli.py` 1834 lines)
- Built flow-first web UI (Flask-based) with composer, inline suggestions, holologue bar, and ledger drawer (evidence: `prototype/ui/app.py` 518 lines, `prototype/ui/templates/index.html`)
- Implemented Bond system with draft→executed lifecycle, failure handling with refunds, and provenance tracking (evidence: `src/cli.py cmd_bond_run()`, Golden Flow Steps 6-7)
- Built session state system (6-slot memory, RMC-inspired) for continuity tracking (evidence: `src/fieldkit/session_state.py`)
- Implemented MDL scoring for structure-vs-noise detection (suggest-only annotations) (evidence: `src/fieldkit/mdl_scoring.py`)
- Created comprehensive specs (9 documents) and architecture docs (27-page field overview + sprint docs) that constrain and explain the system (evidence: `docs/specs/`, `docs/architecture/`)
- Demonstrated end-to-end Golden Flow acceptance test that validates all core capabilities (evidence: `prototype/scripts/run_golden_flow.py`, 5/5 runs pass per S01 diagnosis)

---

## 10) Open questions / TODOs (honest gaps)

### Engineering Work

1. **CI/CD pipeline missing** — No GitHub Actions, GitLab CI, or other CI config. Tests must be run manually.
2. **Type checking not enforced** — No mypy/pyright config. Code uses type hints but no validation.
3. **Linting not configured** — No flake8/pylint/black config. Code style not enforced.
4. **Session state not fully integrated** — `session_state.py` exists but not yet wired into CLI flow (S07 partial).
5. **Pipeline batching not fully integrated** — `pipeline.py` exists but GPipe-style microbatching not fully integrated (S08 partial).
6. **Web UI incomplete** — Basic UI works but missing some features from spec (e.g., ephemeral run cards, full state machine).
7. **No performance benchmarks** — No throughput/latency measurements documented.
8. **SQLite FTS5 optional** — FTS5 full-text search only works if SQLite compiled with FTS5 (graceful fallback exists).

### Research/Design Work

9. **Field Markets not implemented** — `field-markets.md` essay describes protocol but no implementation exists (conceptual only).
10. **Holographic/Gibsey theory not fully realized** — Essays describe theory but implementation focuses on QDPI primitives, not full Holographic vision.
11. **Architecture overview mostly conceptual** — 27-page field overview describes L0-L4 layers but many are research/aspirational, not implemented.
12. **Evidence Coverage Rate (ECR) currently 0** — ECR metric exists in eval harness but evidence shards not yet fully integrated into scoring (S03/S04 implemented but ECR=0 noted in tests/README.md).

---

## Quick index of links

1. `src/cli.py` — CLI entrypoint (1834 lines)
2. `src/fieldkit/schemas.py` — Core data objects
3. `src/fieldkit/store_jsonl.py` — JSONL storage
4. `src/fieldkit/store_sqlite.py` — SQLite storage
5. `prototype/scripts/run_golden_flow.py` — Acceptance test
6. `src/fieldkit/suggestion_engine.py` — Evidence-based suggestions
7. `src/fieldkit/holologue.py` — Many→one synthesis
8. `src/fieldkit/governor.py` — Governance layer
9. `tests/eval_harness.py` — Evaluation engine
10. `docs/specs/05_demo_golden_flow_v0.1.md` — Acceptance test spec
11. `docs/specs/02_core_data_objects_v0.1.md` — Data model spec
12. `docs/essays/field-markets.md` — Field Markets protocol proposal
13. `prototype/ui/app.py` — Web UI server
14. `src/fieldkit/backup.py` — Backup/restore
15. `README.md` — Main README
