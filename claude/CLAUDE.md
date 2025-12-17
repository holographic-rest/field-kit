# CLAUDE.md — Field-Kit v0.1 Build Guardrails (Source of Truth)

You are Claude Code working inside the **field-kit** repo.

Your job is to **implement Field-Kit v0.1 exactly as specified** (no feature invention), with a runnable minimal prototype that can execute the **Demo Golden Flow v0.1** end-to-end.

---

## 1) Source of truth

**All product + data + event decisions are locked by these specs:**
`/docs/specs/*.md`

Do not “improve” the system by changing terminology, schemas, or event names unless the user explicitly asks you to revise specs.

**Acceptance test:** `/docs/specs/05_demo_golden_flow_v0.1.md`  
If implementation choices are unclear, default to what makes Golden Flow executable without improvising.

---

## 2) v0.1 non-negotiable constraints

### Private • Local only
- No accounts / sign-in / identity
- No cloud sync / collaboration / sharing / publishing
- No network dependency required to browse existing data (Field + Ledger)

### No money rails
- No Stripe/subscriptions
- No crypto/blockchain
- No KYC/AML
- No redemption/cash-out

### Credits are simulation only
- Credits are **local-only**
- Credits are **not transferable**
- Credits are **not redeemable**
- Credits are recorded only as events (`credits.delta`) and a derived balance UI chip (if UI exists)

---

## 3) Canonical vocabulary (do not rename)

Use these exact terms as defined in the specs:
- Episode / Item / Bond / QDPIEvent / Proposal / Canon / Bundle

Important: **Canon is a derived projection** (curated lists on Episode), not a new “Canon object.”

---

## 4) Canonical event taxonomy (do not invent new event names)

The v0.1 event log uses ONLY these names:

- `app.first_run.started`
- `episode.created`
- `field.opened`
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

If you need intermediate UI phases (streaming, placeholder display, run started), those are **UI state only** and must NOT create new event names.

### Event schema invariants
- Use the field name `direction` (not `flow`)
- `direction` values are limited to: `user→field` and `system→field` (anything else is debug-only and OFF by default)
- Events are append-only and immutable
- Event ordering is by `(episode_id, seq)` where `seq` is monotonic per Episode

---

## 5) Canonical QDPI tagging scheme (must match the suite)

Use:
- **Q (Queue):** requests + inspection + bookkeeping  
  Examples: `bond.run_requested`, `ledger.opened`, `store.commit`, `credits.delta`, suggestions/proposals presented
- **D (Dialogue):** user-confirmed structure decisions  
  Example: `bond.draft_created`
- **M (Monologue):** system outputs/completions  
  Examples: `bond.executed`, `bond.execution_failed`
- **H (Holologue):** holologue lifecycle  
  Examples: `holologue.run_requested`, `holologue.completed`, `holologue.failed`, `holologue.validation_failed`

---

## 6) Canonical object model rules (do not violate)

### Bond lifecycle (hard rule)
- Draft: `status:"draft"` AND `output_item_id:null`
- Executed: `status:"executed"` AND `output_item_id` is non-null
- Failure model: stays `draft` + `last_error` (no third status in v0.1)

### Proposals are events-only
- Suggestions/proposals are **never persisted as Bonds** until the user explicitly confirms **Create Bond**.

### Holologue semantics (hard rule)
- many→one: one run produces **exactly one** output Item (type `H`)
- not summary-by-default: output must be a usable artifact
- proposals from Holologue are events-only (`bond.proposals.presented`)

### Canon / curation (v0.1)
- Episode may include optional:
  - `curated_item_ids?: string[]`
  - `curated_bond_ids?: string[]`
- Curated view is derived from those lists and filters out archived/missing objects (per Canon Policy)

### JSON conventions
- Use `snake_case` for field names in persisted JSON and examples
- IDs use prefixes: `nw_`, `ep_`, `it_`, `bd_`, `ev_`

---

## 7) Credits event shape (do not drift)

Credits changes are recorded as:
- event name: `credits.delta`
- `qdpi:"Q"`, `direction:"system→field"`
- `refs` MUST include:
  - `delta` (int)
  - `balance_after` (int)
  - `reason` (string)
- Optional direct refs (no `related_*` keys):
  - `item_id`, `bond_id`, `output_item_id`, `event_id`

Never emit keys like `related_bond_id`.

---

## 8) UI constraints (if/when UI is implemented)

- Primary surface: Field (Item list, bottom-append)
- Operator drawer: suggestions → prompt editor → run state
- Ledger drawer: Objects / Events / Curated (Canon Projection) / JSON
- “Ephemeral run card” is **UI-only** until success; do not persist placeholder Items.

Keep “magic” visuals only at invocation moments (suggestions/proposals + running/streaming), and keep the rest calm/minimal.

---

## 9) Implementation order (do not reorder)

Implement the **Bootstrap Floor** in this strict order:
1) Storage (JSONL or SQLite)
2) Append-only QDPIEvent logger
3) Create Item
4) Create Bond (draft)
5) Run Bond → output Item + `bond.executed`
6) Run Holologue → output Item + `holologue.completed` (+ optional proposals event)
7) Ledger viewer (objects + events + JSON)
8) Credits.delta + derived balance

Only after the above passes, start polishing UI/UX.

---

## 10) Working style (how to avoid drift)

- Make changes in small increments.
- After each increment, run the smallest possible proof:
  - can we create an Item and see it persisted + evented?
  - can we execute one Bond and verify lineage in Ledger?
  - can we run Holologue and see one artifact output?
- If you encounter ambiguity or a spec contradiction:
  - STOP and report the exact doc + section causing conflict.
  - Propose the smallest resolution that preserves v0.1 constraints.
  - Do not invent a new model.

---

## 11) Definition of “done” for Claude

You are done when:
- The **Demo Golden Flow v0.1** can be executed end-to-end without improvising
- Objects/events match schemas and naming exactly
- No v0.1 non-goals are violated
- The repo contains a minimal runnable prototype and clear run instructions