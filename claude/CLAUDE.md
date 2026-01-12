# CLAUDE.md — Field-Kit v0.1 Guardrails (Queue Lattice Rewrite)

You are Claude Code working inside the **field-kit** repo.

Your job is to implement the system described in `/docs/specs/` with **Queue Lattice as the primary ontology**, and to keep the project **buildable, testable, and non-drifting** while we iterate.

This is **not** a chat app. The UI may *look* chat-like, but the ontology is **artifact → links → operators → new artifacts**.

---

## 0) Read this first: the mental model (non-negotiable)

### Items are artifacts

* Creating an Item is **minting a persisted object** (a page / note / artifact).
* By default, a newly created Item is a **Queue** Item (Q).
* Users can create Items that **do nothing** unless acted upon.

### Hololinks and hololoops are navigation

* A **Hololink** is a **one-way** sentence link from Item A → Item B.
* A **Hololoop / Bonded loop** is **two** hololinks selected (A→B and B→A), forming a **two-way navigable bond**.
* The early system should feel like: **create Qs → choose hololinks to connect Qs → build the lattice**.

### Bonds cause generation (operators)

* **Only execution of an operator bond produces a new Item.**
* Do not collapse “typed text” into both Item creation and Bond authoring.
* The UI MUST clearly separate:

  * **Create Item** input (mints Q)
  * **Bond authoring / selection** input (targets an existing Item)

Queue Lattice spec is the reference for how this should feel.

---

## 1) Source of truth (priority order)

**Primary ontology:**

* `/docs/specs/09_queue_lattice_v0.1.md` (highest priority)

**Suite:**

* `/docs/specs/01_*.md` through `/docs/specs/08_*.md`

If any older doc contradicts `09`, **follow 09** and surface the contradiction in a short note.

**Acceptance tests:**

* `/docs/specs/05_demo_golden_flow_v0.1.md` (may be rewritten by Composer; treat the repo’s current version as authoritative)
* Existing test scripts under `prototype/scripts/` must continue to pass unless the updated specs intentionally change them.

---

## 2) v0.1 constraints (still true)

### Private • Local only

* No accounts / sign-in / identity
* No cloud sync / collaboration / sharing / publishing
* No network dependency required to browse existing data (Field + Ledger)

### No money rails

* No Stripe/subscriptions
* No crypto/blockchain
* No KYC/AML
* No redemption/cash-out

### Credits are simulation only

* Credits are local-only, not transferable, not redeemable
* Credits recorded only as events: `credits.delta`
* UI may show a derived credits chip, but ledger is the source of truth

---

## 3) Canonical vocabulary (do not rename)

Use these terms consistently (as defined in specs, especially `09`):

* Episode / Item / Hololink / Hololoop (Bonded loop) / Bond / QDPIEvent / Proposal / Canon / Bundle

**Important:** Canon is a **derived projection** (curated lists on Episode), not a “Canon object.”

**Also important:** Q means **Queue**, not Question/Query.

---

## 4) Canonical event taxonomy (do not invent new names)

The v0.1 event log uses ONLY these names:

* `app.first_run.started`
* `episode.created`
* `field.opened`
* `tutorial.started`
* `item.created`
* `bond.suggestions.presented`
* `bond.draft_created`
* `bond.run_requested`
* `bond.executed`
* `bond.execution_failed`
* `holologue.run_requested`
* `holologue.validation_failed`
* `holologue.completed`
* `holologue.failed`
* `bond.proposals.presented`
* `ledger.opened`
* `store.commit`
* `store.commit_failed`
* `credits.delta`

If you need intermediate UI phases (streaming, placeholder display, “run started”), those are **UI state only** and must NOT create new event names.

### Event schema invariants

* Field name is `direction` (not `flow`)
* `direction` values limited to: `user→field` and `system→field`
* Events are append-only and immutable
* Event ordering is `(episode_id, seq)` monotonic per Episode

---

## 5) Canonical QDPI tagging (must match suite)

* **Q (Queue):** requests + inspection + bookkeeping + suggestions/proposals presented
* **D (Dialogue):** user-confirmed structural decisions (e.g., bond draft created)
* **M (Monologue):** system completions / outputs (`bond.executed`, `bond.execution_failed`)
* **H (Holologue):** holologue lifecycle (`holologue.*`)

---

## 6) Object model rules (follow specs; don’t invent statuses)

### IDs and JSON conventions

* `snake_case` keys for persisted JSON
* IDs use prefixes: `nw_`, `ep_`, `it_`, `bd_`, `ev_`

### Bond lifecycle (operator bonds)

* Draft: `status:"draft"` AND `output_item_id:null`
* Executed: `status:"executed"` AND `output_item_id` non-null
* Failure: remains draft + `last_error` (no third status)

### Link-only bonds / hololoops

Queue lattice introduces **link-only** connections between Queue items.

**Do NOT invent a new event name or a new status ad hoc.**
Represent link-only hololinks/hololoops exactly as the updated specs specify.

If the updated specs require a schema extension (e.g., `bond_kind` or `link_text_forward/link_text_return`), implement it as:

* **optional fields**
* backwards compatible
* explicitly documented in `02_core_data_objects_v0.1.md`

If the specs are ambiguous, stop and propose the smallest extension.

### Proposals are events-only

* Suggestions/proposals must remain events-only until user confirms creation of a persisted Bond or Link-only structure (per updated specs).

### Holologue semantics

* many→one: one run produces exactly one output Item type `H`
* not-summary-by-default: output must be a usable artifact
* holologue proposals are events-only: `bond.proposals.presented`

---

## 7) UI guardrails (Queue Lattice behavior)

The UI should resemble the wrapper’s cleanliness, but **must behave like the lattice**.

### Absolute UI requirements

* **No Q/M/D/H dropdown at Item creation.**
* “Create Item” mints a Queue Item immediately.
* After creating (or selecting) an Item, the system shows **4 suggestions** that are:

  * readable in full (no ellipsis truncation)
  * specific to the content (not generic templates)
  * navigational hololink sentences (not “expand X into checklist” boilerplate)

### Two separate inputs (never collapse them)

1. **Create Item** (global composer) → creates a new Queue Item
2. **Create Bond / Hololink** (per-item) → creates a bond/hololink that targets an existing Item

Typing into the “bond” input must never mint a Queue Item.

### Execution

* Selecting a suggested operator bond or typing a bond creates a draft bond.
* Only executing the bond produces a new Item output.
* Output items must show lineage back to their source Queue.

### Tutorial

* Optional. If broken, do not block core lattice behavior.

---

## 8) Implementation posture (how to work without drift)

### Keep the core stable

* Don’t break headless acceptance tests unless the updated specs require it.
* Add new behavior behind clear flags/config where helpful (e.g., “queue lattice mode”).

### Prefer small increments + runnable checks

After each change, run:

* relevant sprint test(s)
* Golden Flow script(s)
* any Queue Lattice specific test(s) added in this rewrite

### If confused, don’t improvise new concepts

* Cite exact doc + section
* Propose smallest resolution
* Wait for user approval if it’s a spec-level change

---

## 9) Repo hygiene (still required)

* Never commit runtime JSONL stores
* `.env` must remain gitignored
* Keep `FIELDKIT_DATA_DIR` / `--data-dir` workflow functional

---

## 10) Definition of “done” (current phase)

You are done for a sprint when:

* The updated specs (including `09_queue_lattice_v0.1.md`) are implementable in code
* Queue Item creation is artifact-first (no dropdown)
* Queue-to-Queue lattice linking works (hololinks/hololoops per spec)
* Suggestions are content-derived and readable
* Operator execution produces new Items with lineage
* Ledger remains inspectable and canonical event names remain intact
* Tests pass and changes are committed cleanly (no runtime data)

---

If you want, I can also generate a **fresh “Sprint Plan v2”** doc that matches Queue Lattice (and replaces the old tutorial/golden-flow-first mindset) once Composer finishes rewriting the 8 specs.