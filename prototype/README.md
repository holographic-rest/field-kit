# Field-Kit Prototype v0.1

This folder contains the **minimal runnable prototype** for Field-Kit v0.1.

**Acceptance Test (non-negotiable):** `/docs/specs/05_demo_golden_flow_v0.1.md`  
If the prototype can run the **Demo Golden Flow** end-to-end **without improvising**, it passes.

---

## What this prototype must prove (in 3–5 minutes)

Field-Kit is **not a chat app**. It must demonstrate:

1) **Persistent objects with stable IDs**
- `Network`, `Episode`, `Item`, `Bond` persisted locally with IDs:
  - `nw_…`, `ep_…`, `it_…`, `bd_…`, `ev_…`

2) **Lineage / provenance**
- Two Bond executions that prove:
  - inputs → Bond → output Item  
  - `Bond.status:"executed"` and `Bond.output_item_id` set  
  - output Items include provenance pointing back to the Bond

3) **Holologue many→one**
- Select 2+ Items → run Holologue → produce **exactly one** `H` output Item

4) **Ledger inspection**
- Append-only `QDPIEvent` log, ordered by `(episode_id, seq)`
- Ledger can show:
  - Objects: Items, Bonds, Episodes (and optionally Network)
  - Events: canonical event names only
  - JSON preview

5) **Credits simulation (optional, but supported)**
- `credits.delta` events are inspectable
- The displayed credits balance is a **derived view** from events
- No real money, no transferability, no redemption

---

## v0.1 constraints (do not violate)

- **Private • Local** only (no accounts, no cloud sync, no publishing, no collaboration)
- **No payments / crypto / KYC / cash-out**
- **No new event names** beyond the canonical list
- **No UI-only events logged by default** (`ui.*` must be debug-only and OFF)
- **No persisted placeholder output Items**
  - Any “in progress” placeholder must be **UI-only** (ephemeral) until success

---

## Build order (do not reorder)

Implement in this strict sequence:

1) Storage
2) Append-only QDPIEvent logger
3) Create Item
4) Create Bond (draft)
5) Run Bond → output Item + `bond.executed`
6) Run Holologue → output Item + `holologue.completed` (+ optional proposals event)
7) Ledger viewer (Objects + Events + JSON)
8) Credits.delta + derived balance (simulation)

---

## Storage floor (recommended)

### JSONL-first (fastest)
Start with JSONL files (matches the Core Data Objects spec and is easiest to debug):

- `prototype/data/items.jsonl`
- `prototype/data/bonds.jsonl`
- `prototype/data/episodes.jsonl`
- `prototype/data/networks.jsonl`
- `prototype/data/qdpi_events.jsonl` (**append-only, immutable**)

Snapshot objects (Items/Bonds/Episodes/Networks) can be “latest write wins” by `id`.  
Events are append-only and **never overwritten**.

SQLite is allowed later, but JSONL is the best v0.1 bootstrap floor.

---

## Canonical event taxonomy (must match specs)

Do not invent new event names. Use only:

- `app.first_run.started`
- `episode.created`
- `tutorial.started`
- `item.created`
- `bond.suggestions.presented`
- `bond.draft_created`
- `bond.run_requested`
- `bond.executed`
- `bond.execution_failed`
- `holologue.run_requested`
- `holologue.validation_failed`
- `holologue.completed`
- `holologue.failed`
- `bond.proposals.presented`
- `ledger.opened`
- `store.commit`
- `store.commit_failed`
- `credits.delta`

All events use:
- `direction: "user→field"` or `"system→field"`
- ordering: `(episode_id, seq)` monotonic per episode

---

## Object invariants (must match specs)

### Bond lifecycle (hard rule)
- Draft: `status:"draft"` AND `output_item_id:null`
- Executed: `status:"executed"` AND `output_item_id` non-null
- Failure: remains `draft` + `last_error` (no third status in v0.1)

### Proposals are events-only
- Suggestions/proposals do not create Bonds until the user confirms **Create Bond**

### Holologue
- many→one: exactly one output Item per run (`type:"H"`)
- proposals after Holologue are events-only (`bond.proposals.presented`)

### Canon / Curated view (optional)
- Canon is derived from Episode fields (no “Canon object”):
  - `curated_item_ids?: string[]`
  - `curated_bond_ids?: string[]`

---

## Credits simulation (if enabled, must match Golden Flow)

Credits are included only to prove the “economic layer is evented and inspectable.”

- Event name: `credits.delta`
- `qdpi:"Q"`, `direction:"system→field"`
- `refs` includes: `delta`, `balance_after`, `reason`
- Optional direct refs: `item_id`, `bond_id`, `output_item_id`, `event_id` (no `related_*` keys)

Demo-default credit policy (from Golden Flow):
- seed: `+100` (`reason:"seed"`)
- item creation: `+1` (`reason:"item_created"`)
- bond run spend: `-10` (`reason:"bond_run_spend"`)
- bond success reward: `+3` (`reason:"bond_executed_reward"`)
- holologue run spend: `-20` (`reason:"holologue_run_spend"`)
- holologue success reward: `+5` (`reason:"holologue_completed_reward"`)
- refunds on failure: `+10` / `+20` with `bond_run_refund` / `holologue_run_refund`

Expected final credits on success path: **73**.

---

## Recommended implementation approach (Phase 1 → Phase 2)

### Phase 1: Headless core + CLI (fastest proof)
Build a minimal CLI that can execute the Golden Flow deterministically.

Suggested commands (names flexible; behavior is not):

- `init`
  - create store, Network, Episode 0
  - append: `app.first_run.started`, `episode.created`, `credits.delta(seed)`, `store.commit`

- `tutorial:start`
  - append: `tutorial.started`

- `item:create`
  - create Item (Q default)
  - append: `item.created`, `credits.delta(item_created)`, `store.commit`

- `suggestions:show`
  - append: `bond.suggestions.presented` (events-only; no Bond created)

- `bond:create`
  - create Bond draft (`status:"draft"`, `output_item_id:null`)
  - append: `bond.draft_created`, `store.commit`

- `bond:run`
  - append: `bond.run_requested`, `credits.delta(bond_run_spend)`
  - on success:
    - create output Item (M or D)
    - update Bond to executed + set `output_item_id`
    - append: `bond.executed`, `credits.delta(bond_executed_reward)`, `store.commit`
  - on failure:
    - append: `bond.execution_failed`, `credits.delta(bond_run_refund)`

- `holologue:run`
  - validate selection; on invalid:
    - append: `holologue.validation_failed`
  - on valid:
    - append: `holologue.run_requested`, `credits.delta(holologue_run_spend)`
    - on success:
      - create one output Item (H)
      - append: `holologue.completed`, `credits.delta(holologue_completed_reward)`, `store.commit`
      - optionally append: `bond.proposals.presented` (events-only)
    - on failure:
      - append: `holologue.failed`, `credits.delta(holologue_run_refund)`

- `ledger:open`
  - append: `ledger.opened`
  - show Objects + Events + JSON

### Phase 2: Minimal UI (only after Phase 1 passes)
Implement UI surfaces per `/docs/specs/08_ui_ux_foundations_v0.1.md`:
- Field list (append to bottom)
- Operator drawer (suggestions → prompt editor → run state)
- Ledger drawer (Objects / Events / Curated / JSON)
- Ephemeral run card is UI-only until success

---

## Automated Golden Flow (recommended)

Create a script:
- `prototype/scripts/run_golden_flow.(ts|js|py)`

It should:
- run the Golden Flow steps in order
- assert minimum counts (Items=5, Bonds=2, etc.)
- assert event ordering (run_requested before executed; proposals after holologue.completed)
- assert credits final balance is 73 (if credits enabled)
- exit nonzero on failure

This prevents “it kinda works” drift.

---

## Definition of Done (prototype)

You are done when:
- Golden Flow runs end-to-end without improvising
- Objects + events match specs (names, fields, ordering)
- Ledger can verify lineage + credits deltas
- v0.1 non-goals are not violated

---

## Running the Prototype

### Golden Flow (Acceptance Test)

```bash
# Fresh run (recommended)
python3 prototype/scripts/run_golden_flow.py --fresh

# Re-run with existing data
python3 prototype/scripts/run_golden_flow.py
```

### Sprint B: Dogfood (Architecture Ingestion)

```bash
# Fresh run
python3 prototype/scripts/run_sprint_b_dogfood.py --fresh

# With custom data directory
FIELDKIT_DATA_DIR=prototype/data_dogfood python3 prototype/scripts/ingest_architecture_pages.py
```

### Separate Data Directories

Use `FIELDKIT_DATA_DIR` to isolate test runs:

```bash
FIELDKIT_DATA_DIR=/tmp/field-kit-test python3 prototype/scripts/run_golden_flow.py
```

Or use `--data-dir`:

```bash
python3 prototype/scripts/run_golden_flow.py --data-dir /tmp/test
```

---

## Test Scripts

| Script | Description |
|--------|-------------|
| `run_golden_flow.py` | Acceptance test (credits=73) |
| `run_golden_flow_3x.py` | Repeatability test (3 runs) |
| `run_sprint_b_dogfood.py` | Architecture pages ingestion |
| `test_sprint_c_canon.py` | Canon Policy tests |
| `test_sprint_d_spin_recipes.py` | Spin Recipes tests |
| `test_sprint_e_stability.py` | Forced failure + refund tests |
| `validate_architecture_pages.py` | Page format validator |

### Run All Tests

```bash
python3 prototype/scripts/run_golden_flow.py --fresh
python3 prototype/scripts/run_sprint_b_dogfood.py --fresh
python3 prototype/scripts/test_sprint_c_canon.py
python3 prototype/scripts/test_sprint_d_spin_recipes.py
python3 prototype/scripts/test_sprint_e_stability.py
```

---

## Data Directory Structure

```
prototype/data/          # Default JSONL store (gitignored)
├── networks.jsonl
├── episodes.jsonl
├── items.jsonl
├── bonds.jsonl
└── qdpi_events.jsonl    # Append-only event log

prototype/data_dogfood/  # Dogfood data (gitignored)
prototype/outputs/       # Export files (gitignored)
```

All runtime data is gitignored. Never commit JSONL files.