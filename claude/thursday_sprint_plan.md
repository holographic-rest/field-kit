# thursday_sprint_plan.md — Field-Kit v0.1 Build Night (Claude Code)

**Date:** Thursday (Build Night)  
**Goal:** Ship the **Bootstrap Floor** so the system can execute the **Demo Golden Flow v0.1** once (even ugly).

**Source of truth:**  
- `/docs/specs/*.md`  
- `CLAUDE.md` (guardrails)  
- `prototype/README.md` (acceptance + order)

**Hard rule:** Do NOT rename schemas/event names or invent new objects/features. Follow the specs.

---

## 0) What “done tonight” means (minimum win)

By end of night, we can run a **headless Golden Flow** (CLI or script) that proves:

- local store exists
- Episode 0 exists
- can create 2 Q Items
- can create + execute 2 Bonds (Q→M and Q→D) with lineage
- can run Holologue (2+ Items) and produce 1 H Item
- can open a Ledger view and see ordered events
- credits.delta can be appended + derived balance computed (if enabled)

UI can be deferred. Tonight is about correctness + persistence.

---

## 1) Work plan (strict pass order)

### Pass 1 — Storage + Event Log (append-only)
**Deliverables:**
- Local store directory created (e.g., `prototype/data/`)
- JSONL files exist (or SQLite if chosen)
- Event append function enforces `(episode_id, seq)` monotonic ordering

**Implement:**
- `prototype/src/store/` (or similar)
  - `append_event(qdpi_event)`
  - `load_events(episode_id?)`
  - `upsert_snapshot(object_type, object)` (Items/Bonds/Episodes/Networks)
  - `load_snapshots(object_type, filters?)`

**Run check:**
- Create an event via code and confirm it appends to `qdpi_events.jsonl`
- Reload and confirm order is preserved

---

### Pass 2 — Init + Create Item + Ledger (readback)
**Deliverables:**
- `init` command (or script) that creates:
  - Network
  - Episode 0
  - events: `app.first_run.started`, `episode.created`, optional `credits.delta(seed)`, `store.commit`
- `item:create` command that persists an Item (Q default) and logs:
  - `item.created`
  - optional `credits.delta(item_created)`
  - `store.commit`
- `ledger:open` command that prints:
  - Objects counts (Items/Bonds/Episodes/Network)
  - Events (name, qdpi, direction, seq)

**Run check:**
1. `init`
2. `item:create` twice
3. `ledger:open` shows 2 items + events appended in order

---

### Pass 3 — Create Bond (draft) + Run Bond (success path)
**Deliverables:**
- `bond:create` creates draft Bond with:
  - `status:"draft"`, `output_item_id:null`, `input_item_ids`, `prompt_text`
  - event: `bond.draft_created` + `store.commit`
- `bond:run` success path:
  - event: `bond.run_requested`
  - optional `credits.delta(bond_run_spend)`
  - create output Item (M or D)
  - update Bond to executed + set `output_item_id`
  - event: `bond.executed`
  - optional `credits.delta(bond_executed_reward)`
  - `store.commit`

**Run check:**
- Create Bond from Item 1, run it, see:
  - Bond status executed
  - output item exists with provenance
  - ledger shows run_requested before executed

---

### Pass 4 — Holologue (success path) + Proposals (events-only)
**Deliverables:**
- `holologue:run` requires 2+ items:
  - event: `holologue.run_requested`
  - optional `credits.delta(holologue_run_spend)`
  - create ONE output Item type H with provenance (holologue)
  - event: `holologue.completed`
  - optional `credits.delta(holologue_completed_reward)`
  - optional `bond.proposals.presented` (events-only; no bonds created)
  - `store.commit`

**Validation failure behavior:**
- If <2 items: log `holologue.validation_failed` and do nothing else

**Run check:**
- run holologue on two Q items → see one H item, and proposals event optionally

---

### Pass 5 — Credits (simulation) as derived view
**Deliverables:**
- `credits.delta` event writer (already used above)
- Derived balance function:
  - compute balance from seed + deltas in event stream
- Ledger shows credits events and current balance

**Run check:**
- After Golden Flow run, derived balance equals expected (73) on clean success path if policy matches specs

---

### Pass 6 — Golden Flow script (automated acceptance)
**Deliverable:**
- `prototype/scripts/run_golden_flow.(ts|js|py)` that:
  - runs: init → tutorial.started → create 2 items → suggestions event → bond 1 run → bond 2 run → holologue run → proposals event → ledger.opened
  - asserts:
    - Items >= 5
    - Bonds >= 2 (executed)
    - Event ordering constraints hold
    - Optional: credits final == 73 (if enabled)

**Run check:**
- One command runs the full flow and exits 0

---

## 2) Implementation notes (do NOT drift)

### Canonical event names only
Do NOT create `run.started`, `proposal.suggested`, etc.  
UI phases are UI-only; this is headless tonight.

### Proposals are events-only
Suggestions/proposals are logged but do not create bonds until explicitly created.

### No persisted placeholder output Items
If you want “never dead air” later, use UI-only ephemeral cards. For headless prototype, skip.

---

## 3) Minimal scaffolding choices (pick one and stick)

**Preferred:** Node/TS (or Bun/TS) CLI + JSONL store  
**Alternative:** Python CLI + JSONL store  
**Avoid tonight:** full UI, complex frameworks, plugins, auth, hosting

---

## 4) Deliverables to commit tonight

1. `CLAUDE.md` (already created)
2. `prototype/README.md` (already created)
3. `prototype/src/...` implementation for storage + core actions
4. `prototype/scripts/run_golden_flow.*`
5. A single `prototype/CHANGELOG.md` entry (today) with what works

**Commit message suggestion:**  
`prototype: bootstrap floor (jsonl + events + golden flow script)`

---

## 5) If blocked (how to proceed)

If a spec ambiguity appears:
1) cite the exact doc + section
2) propose the smallest resolution
3) do NOT invent a new object/event name
4) prefer whatever makes Golden Flow executable

---

## 6) Claude kickoff instruction (paste into Claude Code)

“Implement the Bootstrap Floor in Pass order 1→6 described in `thursday_sprint_plan.md`.  
Use JSONL storage unless you have a strong reason not to.  
Do not invent new event names.  
After each pass, provide the exact commands to run and the expected output.  
Stop if a spec contradiction is found and report it with doc+section.”