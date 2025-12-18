# Field-Kit

A minimal, runnable proof loop for Holographic/QDPI.

Field-Kit proves that an AI interaction system can be **not a chat app**: persistent objects with stable IDs, append-only event logs with lineage, many-to-one synthesis (Holologue), and an inspectable credits simulation.

## v0.1 Scope

- **Persistent objects**: Network, Episode, Item, Bond (IDs: `nw_`, `ep_`, `it_`, `bd_`, `ev_`)
- **Append-only events**: QDPIEvents ordered by `(episode_id, seq)`, canonical names only
- **Lineage / provenance**: Bond executions produce output Items with traceable provenance
- **Holologue**: many→one synthesis (2+ Items → exactly 1 H output)
- **Credits simulation**: evented deltas, derived balance, inspectable in Ledger

### v0.1 Constraints

- **Private / Local only** — no accounts, no cloud, no payments
- **Credits are simulated events** — not real money, not redeemable
- **Stdlib-only Python** — no external dependencies required

---

## Acceptance Test

The acceptance test is the **Demo Golden Flow**:

**Spec:** [`/docs/specs/05_demo_golden_flow_v0.1.md`](docs/specs/05_demo_golden_flow_v0.1.md)

> "If the prototype can run the Demo Golden Flow end-to-end **without improvising**, it passes."

---

## Quickstart

### Requirements

- Python 3.9+ (stdlib only, no pip install required)

### Run Golden Flow (3–5 minutes)

```bash
# Clone the repo
git clone https://github.com/holographic-rest/field-kit.git
cd field-kit

# Run the Golden Flow (fresh data directory each time)
python3 prototype/scripts/run_golden_flow.py --fresh
```

Expected output ends with:
```
GOLDEN FLOW COMPLETE — ALL ASSERTIONS PASSED!
```

### Run Sprint B Dogfood (architecture pages ingestion)

```bash
python3 prototype/scripts/run_sprint_b_dogfood.py --fresh
```

### Separate data directories

Use `FIELDKIT_DATA_DIR` to isolate runs:

```bash
FIELDKIT_DATA_DIR=prototype/data_dogfood python3 prototype/scripts/ingest_architecture_pages.py
```

---

## What to Look For

After running Golden Flow, verify:

- [ ] IDs appear with prefixes: `nw_`, `ep_`, `it_`, `bd_`, `ev_`
- [ ] Ledger shows canonical event names only (no invented names)
- [ ] Credits end at **73** on clean Golden Flow run
- [ ] `bond.run_requested` precedes `bond.executed`
- [ ] `holologue.run_requested` precedes `holologue.completed`
- [ ] `bond.proposals.presented` occurs after `holologue.completed`
- [ ] Output Items have provenance pointing back to their source Bond/Holologue

---

## Repo Map

```
/docs/
├── specs/              # Decision layer (enforceable specs)
│   ├── 01–08           # Core specs (Golden Flow = 05)
│   └── INDEX.md
├── architecture/       # Architecture explains
│   └── field_overview/ # 27-page architecture overview
├── essays/             # BKC essay (theory)
└── INDEX.md

/prototype/
├── scripts/            # Runnable scripts
│   ├── run_golden_flow.py
│   ├── run_sprint_b_dogfood.py
│   └── test_sprint_*.py
├── data/               # JSONL store (gitignored)
└── README.md           # Prototype details

/src/
├── fieldkit/           # Core library
│   ├── schemas.py      # Data objects
│   ├── store_jsonl.py  # JSONL storage
│   ├── qdpi.py         # Event logging
│   └── spin_recipes.py # Suggestion templates
└── cli.py              # CLI commands

/research/              # ML spine (embeddings, similarity)

/claude/                # Agent guardrails + sprint plans
└── CLAUDE.md
```

---

## Test Commands

```bash
# Golden Flow (acceptance test)
python3 prototype/scripts/run_golden_flow.py --fresh

# Sprint B: Dogfood (architecture ingestion)
python3 prototype/scripts/run_sprint_b_dogfood.py --fresh

# Sprint C: Canon Policy
python3 prototype/scripts/test_sprint_c_canon.py

# Sprint D: Spin Recipes
python3 prototype/scripts/test_sprint_d_spin_recipes.py

# Sprint E: Stability (forced failures + refunds)
python3 prototype/scripts/test_sprint_e_stability.py

# Golden Flow 3x (repeatability)
python3 prototype/scripts/run_golden_flow_3x.py
```

---

## Further Reading

- **Start here:** [`docs/INDEX.md`](docs/INDEX.md)
- **Specs (decision layer):** [`docs/specs/INDEX.md`](docs/specs/INDEX.md)
- **Architecture:** [`docs/architecture/INDEX.md`](docs/architecture/INDEX.md)
- **Prototype details:** [`prototype/README.md`](prototype/README.md)
