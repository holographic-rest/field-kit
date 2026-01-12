# Queue Lattice v0.1

## 1) Front Matter

* **Title:** Queue Lattice v0.1
* **Version:** v0.1
* **Date:** 2025-12-20
* **Status:** Draft
* **Suggested repo path:** `/docs/specs/09_queue_lattice_v0.1.md`

## 2) Purpose

Define the **Queue Lattice** as a v0.1 interaction contract for Field-Kit / Holographic:

1. **Queue Items are the spine.** Users mint Queue Items first (Q, QQ, QQQ…).
2. **Hololinks are one-way sentences.** A hololink is a navigational sentence that points from one Item to another.
3. **Bonds are hololoops.** A Bond is a *two-way* navigational loop made from **two hololinks** (A→B and B→A).
4. **Generation only happens via operator execution.** The system must never treat typed text as both “Item” and “prompt.” Items are artifacts; **Bonds are operators**.

This spec exists to drive a rewrite of the earlier spec suite so the system stops behaving like “chat with extra steps” and becomes **artifact → link → operator → artifact**.

## 3) Terms (v0.1)

### 3.1 Core objects (same names, clarified meanings)

* **Episode**
  A local container for one working session. All objects/events belong to an Episode via `episode_id`.

* **Item**
  A persistent artifact. Items are addressable by ID and have a `type`:

  * `Q` = **Queue** (not “question/query”)
  * `M` = Monologue output (operator-generated)
  * `D` = Dialogue output (operator-generated from a user-authored Bond prompt)
  * `H` = Holologue output (many→one artifact)

* **Bond**
  A persistent connector and/or operator instruction. Bonds link Items and may be executed to generate an output Item (operator bonds). Some Bonds may be **link-only** (navigation bonds) and are not executed.

* **QDPIEvent**
  Append-only, immutable events logging meaningful actions/results. Ordered by `(episode_id, seq)`.

* **Proposal**
  Event-only suggestion(s) until the user confirms creation.

### 3.2 Queue Lattice–specific terms

* **Queue Item sequence (“Q lattice”)**
  A growing set of Queue Items minted by the user, typically in creation order:
  `Q, QQ, QQQ, QQQQ, …`
  This notation is for *mental model* and optional UI display. Implementation may store order via timestamps or an explicit `queue_rank`.

* **Hololink**
  A *one-way* navigational sentence connecting two Items.
  A hololink is “a hyperlink expanded into a sentence.”
  Hololinks may be presented as proposals; only selected hololinks become persisted link structure (via a Bond).

* **Hololoop**
  A two-way navigational loop formed by selecting hololinks in both directions between two Items.

* **Queue Bond (Q↔Q Bond)**
  A persisted hololoop between two Queue Items (A↔B). It exists to make the Queue lattice navigable. It is **not** an operator execution.

* **Operator Bond**
  A Bond that, when executed, produces exactly one output Item. Examples:

  * `Q→M` (Monologue)
  * `Q→D` (Dialogue)
  * `(Q,Q…)→H` (Holologue operator run)

* **Explicit vs implicit bonds**

  * **Explicit**: the one option the user selects (persisted)
  * **Implicit**: the 3 unselected options (stored only in the suggestion event refs; not persisted)

## 4) Scope and Non-goals (v0.1)

### In scope

* A **Queue-first** build mode (“Queue Lattice Mode”) where the user:

  1. mints Queue Items, and
  2. selects one of **4 hololoop options** to connect each new Queue into the lattice.
* Hololinks and hololoops are **content-derived** (must reference real handles from each Item).
* M/D/H generation remains possible later, but **only after** lattice bootstrapping rules are satisfied (Section 7).

### Non-goals

* No accounts, cloud, collaboration, publishing, payments.
* No “fixed link types” shown to the user (e.g., clarify/connect/contrast/example as visible labels).

  * If you want link-type metadata, it may exist internally later, but it must not become the visible bond text.
* No requirement that M/D must connect back to *every* Queue.
  Only the “everything must anchor back to a Queue” rule applies (Section 6).

## 5) The central invariants

### 5.1 “Q means Queue” (hard UI and language rule)

* In the UI and docs, **`Q` must be called “Queue.”**
  Never “Question,” never “Query.”
* Queue Items are *not* interpreted as prompts.

### 5.2 Item creation never triggers generation

* Creating an Item is minting an artifact.
* The system must allow Items to do nothing until acted upon.

### 5.3 Bond creation is the only gateway to generation

* A Bond does nothing until executed (for operator bonds).
* A Queue Bond is a **link-only hololoop** and is not executed.

### 5.4 The bond sentence must feel like navigation, not a template

A hololink (and thus the bond option the user sees) MUST:

* reference at least one **handle** from Item A and at least one from Item B
* read like a sentence a human would click to “go there”
* be short (typically 8–22 words) but specific
* avoid cookie-cutter scaffolds like:

  * “Expand X into a 5-item checklist…”
  * “Derive a minimal JSON schema for X…”
    unless the *source content itself* is already explicitly about checklists/schemas/tests.

## 6) Anchoring rule for M and D (Queue is always the ground)

### 6.1 Required anchoring

* Any generated `M` or `D` Item MUST have an explicit navigable path back to a Queue Item.
* v0.1 default: the Queue that the operator executed on is the anchor.

In existing Field-Kit semantics this is already satisfied by lineage:

* `Bond.input_item_ids` includes the source Queue
* `Bond.output_item_id` points to the generated Item
* The generated Item’s `provenance.input_item_ids` points back to the Queue

### 6.2 Optional additional hololinks for M/D

* M and D items MAY have additional hololinks to other Items.
* M↔M, D↔D, and M↔D bonds are optional and never required in v0.1.
* Any additional links must be explicitly chosen by the user (no silent linking).

## 7) Queue Lattice Mode (the required bootstrapping behavior)

Queue Lattice Mode is a **tutorial + structure lock-in** that forces the system to behave “artifact-first.”

### 7.1 Minimum lattice size: 4 Queue Items (recommended)

* **Default:** `QUEUE_LATTICE_MIN_Q = 4`
  Rationale: symmetry, enough “negative space,” and enough topology for meaningful proposals.

(You may later experiment with 3, but v0.1 defaults to 4.)

### 7.2 Allowed actions while bootstrapping (Q lattice only)

While `queue_count < QUEUE_LATTICE_MIN_Q`:

* User can:

  * create new Queue Items
  * select Queue Bonds (hololoop options) when presented
  * open ledger
* User cannot:

  * run Monologue (Q→M) generation
  * run Dialogue (Q→D) generation
  * run Holologue
    (These unlock after bootstrap.)

### 7.3 The lattice step rule (how each new Q is connected)

When a new Queue Item `Q_k` is created and there exists at least one prior Queue Item:

1. The system MUST choose (or let the user choose) a **target Queue** among existing Queue Items.

   * Default target = the most recently created Queue (linear path).
   * UI may optionally allow selecting another target (nonlinear path).
2. The system MUST present **exactly 4 hololoop options** between `Q_k` and the chosen target `Q_t`.
3. The user MUST select **exactly 1** option to persist.
4. The 3 unselected options are recorded as **implicit proposals** (event refs only).

This ensures the lattice gains both:

* **explicit structure** (what the user chose), and
* **negative space** (what the user declined).

## 8) Hololink proposal generation (how to derive 4 real options)

### 8.1 Handle extraction (content engineering)

Given Item A and Item B, extract handles from each:

* If markdown:

  * headings
  * bold phrases
  * bullet headers
  * noun phrases in the first 2–4 sentences
* If plain text:

  * candidate noun phrases
  * repeated key terms
  * “named entities” (names, titles, system components)
* Handles should be short (1–12 words) and quoteable.

### 8.2 Hololink construction (prompt engineering)

Each hololoop option must consist of:

* **Forward hololink:** sentence that makes A → B feel clickable
* **Return hololink:** sentence that makes B → A feel clickable

Constraints:

* Each hololink should quote or reuse at least one handle from the source and one from the target.
* Options should be *meaningfully distinct*:

  * different selected handles, different angle of connection
  * not “same sentence with synonyms”

### 8.3 What the user sees

In Queue Lattice Mode, the UI shows **4 bond options** that are conceptually “A↔B”:

* Each option is displayed as a single line label (clickable).
* On hover/expand, it may reveal the forward and return hololink sentences.

The UI must never truncate options into unreadable ellipses.

## 9) Persistence and eventing (v0.1 compatible)

### 9.1 Canonical event names only

Queue lattice behavior must use the existing canonical events:

* `item.created`
* `bond.suggestions.presented`
* `bond.draft_created`
* `store.commit`
* `ledger.opened`
* `credits.delta` (optional)

No new event names.

### 9.2 Recording the 4 hololoop options

When presenting 4 options:

* Log `bond.suggestions.presented` with refs that include:

  * `mode: "queue_lattice"`
  * `source_item_id` (new Queue)
  * `target_item_id` (chosen existing Queue)
  * `suggestions[4]` where each element includes:

    * `forward_text`
    * `return_text`
    * `handles_used` (optional)
    * `option_id` (optional)
  * `note`: “Unselected options remain proposals only”

### 9.3 Persisting the selected hololoop

When user selects one option:

* Persist a link-only Bond representing the hololoop.

v0.1-compatible storage options (choose one):

**Option A (recommended, minimal schema change):**

* Persist one Bond draft:

  * `status:"draft"`, `output_item_id:null`
  * `input_item_ids:[source_item_id, target_item_id]`
  * `prompt_text` stores both hololinks as two lines:

    * `A→B: <forward_text>`
    * `B→A: <return_text>`
* Log `bond.draft_created` with refs including both item ids.

**Option B (cleaner schema, requires Core Objects update):**

* Add optional `bond_kind:"link"|"operator"` and optional `link_text_forward/link_text_return`.
* Link bonds are never executed.

### 9.4 Credits (optional gating)

Queue Lattice Mode may optionally change the credit policy later, but v0.1 does not require it. If you do add gating:

* credits are still evented via `credits.delta`
* no real money rails
* derived balance remains the only display

## 10) UI requirements (minimal)

### 10.1 Separate inputs (hard rule)

There must be two distinct inputs:

1. **Create Item** (mints a Queue Item)
2. **Create Bond** (writes/chooses a Bond for a specific Item)

They must never be merged.

### 10.2 Queue-first composer

* The primary composer must say something like: **“Create anything”**.
* Submitting it creates a new Queue Item.
* No dropdown for Q/M/D/H at creation. User-created Items are Queue (`Q`) by default.

### 10.3 After creating `Q_k` (k≥2)

* UI forces the lattice step:

  * choose target (default previous)
  * display 4 hololoop options
  * user selects one
  * bond persists (link-only) and the UI returns to “Create Item” state

## 11) Worked example (Q and QQ pages)

Given Q (page 1) and QQ (page 2), valid hololoop options look like:

* Q→QQ hololink example:

  * “If the Author is unknown, is the ‘collector’ detective or suspect?”
* QQ→Q hololink example:

  * “Does ‘Scheherazade in reverse’ reframe the found text as evidence?”

The chosen option persists as the bond between those Queue Items, forming the first hololoop.

## 12) Definition of Done (Queue Lattice v0.1)

The system satisfies Queue Lattice v0.1 when:

* [ ] Creating an Item mints a Queue Item (`type:"Q"`) with no generation.
* [ ] On creation of a second (and later) Queue Item, the system:

  * [ ] chooses/accepts a target Queue
  * [ ] presents exactly 4 hololoop options
  * [ ] records them as proposals (event-only)
  * [ ] persists exactly one selected hololoop as a link-only Bond
* [ ] The 3 unselected options remain inspectable in the ledger event refs.
* [ ] No non-canonical event names are introduced.
* [ ] After reaching `QUEUE_LATTICE_MIN_Q` (default 4):

  * [ ] Operator generation unlocks (Q→M, Q→D, and Holologue).
* [ ] Generated M/D items remain anchored back to a Queue via lineage.

## 13) Open Questions

1. Should the UI require selecting the Queue Bond immediately after creating each new Queue, or allow “later bonding” with a warning?
2. Should link-only bonds be persisted as a single Bond with two hololinks in `prompt_text`, or should we add explicit link fields (`bond_kind`, `link_text_forward/return`)?
3. How should target selection be presented: default previous Queue only, or a quick “target picker” chip list?
4. Should `QUEUE_LATTICE_MIN_Q` be 3 or 4 in future experiments, and how does that affect perceived flow and “negative space”?
5. Should Queue lattice mode seed credits at 0 (true gating tutorial) or keep seed 100 and treat lattice as structural onboarding only?