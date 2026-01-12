# thursday_sprint_plan.md — Queue Lattice Sprint v0.1 (Claude Code)

**Repo:** field-kit  
**Status:** active sprint plan  
**Goal:** make the system *coherent* under the new ontology: **Queue Items + Hololinks + Hololoops (bonds)**, with suggestions that are **content-derived** (not cookie-cutter templates).

This sprint is the “reset of reality.”  
We are no longer trying to make the previous Golden Flow feel good. We are implementing the **Queue Lattice** (Spec 09) as the new foundation.

---

## 0) Source of truth (read first)

**Primary:** `/docs/specs/09_queue_lattice_v0.1.md`  
**Then:** `/docs/specs/01_*.md` … `/docs/specs/08_*.md` (as rewritten by Composer)  
**Guardrails:** `/CLAUDE.md`

If any older spec contradicts `09`, follow `09` and leave a short note (doc + section) in the PR/commit message.

---

## 1) Definition of “done” for this sprint (minimum win)

By end of sprint, the prototype supports this flow end-to-end in **UI and CLI**:

1) User creates **Queue Item Q1** (“Create anything” composer)  
2) User creates **Queue Item Q2**  
3) System immediately presents **4 hololink candidates Q1→Q2** and **4 hololink candidates Q2→Q1**  
4) User selects **one** hololink each direction → forms a **hololoop** (a bonded loop)  
5) Ledger shows:
   - the two Items persisted
   - the hololinks selected + the hololoop recorded (per spec)
   - canonical event names only (unless Spec 09 explicitly changed them)
6) Suggestions are **actually based on content**:
   - they quote/point to *real handles* from the source item
   - they “aim” into the target item (not generic “expand X…” templates)
   - they are readable in full (no ellipsis-only chips)

**Important:** This sprint does not need Monologue/Dialogue/Holologue generation to be perfect or even present—unless Spec 09 explicitly requires it. We’re building the lattice first.

---

## 2) Non-negotiable UI rules (this sprint)

### A) Item creation ≠ bond authoring
- “Create Item” composer mints an Item (Queue by default).
- Bond/hololink authoring is separate and always targets existing Items.

### B) No Q/M/D/H dropdown for Item creation
- Creating an Item defaults to **Queue**.
- If types exist at all, they are derived from how an Item was produced (e.g., generated output), not chosen by user at creation time.

### C) Gating (Queue-first)
After creating Q1:
- user can only create Q2 (nothing else).
After creating Q2:
- user must pick hololinks (Q1→Q2 and Q2→Q1) to form the first hololoop before proceeding.
(Unless Spec 09 allows skipping; default is strict gating.)

---

## 3) Sprint work plan (Pass order)

### PASS 1 — Data model + storage for Hololinks / Hololoops

**Goal:** represent hololinks and hololoops in data in a way that is:
- faithful to Spec 09
- testable in JSONL
- visible in Ledger

**Rules:**
- Do **not** invent new structures unless Spec 09 requires them.
- Prefer minimal schema extension:
  - either add optional fields to existing objects, or
  - introduce a small new object type only if spec demands it.

**Deliverables:**
- Updated schema(s) in `src/fieldkit/schemas.py`
- Store support in `src/fieldkit/store_jsonl.py`
- Ledger rendering support in `src/cli.py ledger:open` and UI ledger tab

**Run check:**
- create Q1/Q2 via CLI
- create hololinks/hololoop via CLI
- ledger prints them clearly

---

### PASS 2 — Hololink suggestion generator (“context transformer”)

**Goal:** generate hololink candidates that are **content-derived**, not templates.

**Core behavior:**
Given two Items A (source) and B (target), generate:
- 4 candidate hololinks **A→B**
- 4 candidate hololinks **B→A**

**Hard requirements for each hololink sentence:**
- references (quotes or near-quotes) a *handle* from the source Item  
- points into the target Item by referencing at least one target handle or concept  
- reads like a “hyperlink expanded into a sentence” (question or statement)
- not “expand X into a checklist…” style boilerplate

**Implementation approach (required pipeline):**
1) **Parse item content into handles** (source + target)
   - Prefer: headings, bold spans, bullet headers, named entities, key noun phrases
   - Fallback: first sentence fragments, top-scoring ngrams
2) **Select 4 high-salience handles** from the source (diverse)
3) For each handle, craft a hololink sentence that:
   - includes the source handle (verbatim or close)
   - includes one target handle (verbatim or close)
   - uses one of several rhetorical frames (question, inversion, implication, contrast, identity, scope)
4) Ensure **dedupe**: no two hololinks are near-identical

**Important:** Frames may exist internally, but must not appear as “Clarify/Contrast/etc.” in the text shown to the user.

**Deliverables:**
- `src/fieldkit/hololinks.py` (or similar) implementing:
  - `extract_handles(text) -> list[str]`
  - `suggest_hololinks(a_text, b_text) -> list[str]` (length 4)
- tests:
  - deterministic handle extraction
  - suggestions differ when content differs
  - suggestions quote real handles

---

### PASS 3 — UI integration (wrapper feel, lattice behavior)

**Goal:** UI behaves like lattice, with wrapper-level visual simplicity.

**UI requirements:**
- Landing: “Create anything” composer
- After Item created:
  - Item appears in feed
  - immediately show hololink suggestions **below the item** (not hidden in a side panel)
  - show 4 options (full text visible; wrap lines; no truncation)
- After 2 Items exist:
  - show two suggestion stacks:
    - “From Q1 → Q2 (choose 1)”
    - “From Q2 → Q1 (choose 1)”
  - once both chosen, display “Hololoop created” and unlock creation of next Item

**Deliverables:**
- Update `prototype/ui/` to support this flow
- Ensure chips/buttons wrap text and remain readable

**Run check:**
- Start UI
- Create 2 items
- Select hololinks both directions
- See hololoop confirmed
- Ledger reflects it

---

### PASS 4 — CLI parity + acceptance tests

**Goal:** everything done in UI should also be doable headlessly.

**Deliverables:**
- CLI commands:
  - `item:create` (Queue default, no type dropdown)
  - `hololink:suggest --from <id> --to <id>` (returns 4)
  - `hololink:select --from <id> --to <id> --index <0-3>` (stores selected)
  - `hololoop:create --a <id> --b <id>` (or implicit when both directions selected)
- New test:
  - `prototype/scripts/test_sprint_queue_lattice.py` covering:
    - Q1, Q2 created
    - suggestions produced and contain real handles
    - selecting each direction creates hololoop
    - ledger shows correct structures/events
    - rerun is repeatable with `--fresh`

---

### PASS 5 — Git hygiene + commit

- Confirm no runtime JSONL committed
- Ensure new scripts (tests) are committed
- Commit message:
  - `sprint: queue lattice v0.1 (hololinks + hololoops + content-derived suggestions)`

---

## 4) What can be stubbed (allowed)

- Any “AI generation” beyond hololink suggestions can be stubbed.
- Hololink suggestion quality should be achieved via the pipeline above; an LLM is optional.
- If LLM is used:
  - key must remain in `.env` and gitignored
  - implement an adapter interface: `stub` vs `openai` vs `local`
  - default to stub if key missing

---

## 5) Stop conditions (do not improvise)

Stop and ask Brennan if:
- Spec 09 requires new event names beyond the canonical list
- Spec 09 requires a new object type that conflicts with existing storage assumptions
- UI cannot satisfy gating without breaking core usability

When blocked:
1) cite doc + section
2) propose smallest fix
3) wait

---

## 6) Commands Brennan should run after each pass

After each pass, provide:
- exact commands to run
- expected output snippets

Minimum final checks:
- `python3 prototype/ui/app.py`
- `python3 prototype/scripts/test_sprint_queue_lattice.py`
- `python3 prototype/scripts/run_golden_flow.py --fresh` (only if the rewritten spec suite still expects it)

---

## 7) Sprint kickoff instruction to Claude Code (paste into Claude)

“Implement Queue Lattice v0.1 as defined in `/docs/specs/09_queue_lattice_v0.1.md` and the rewritten spec suite. Follow the Pass order in this file. Do not collapse Item creation and Bond/Hololink authoring. Suggestions must be content-derived hololink sentences (not templates), readable in full, and must differ for different inputs. After each pass, give me the exact command(s) to run and the expected output. Stop if Spec 09 requires new event names or object types and cite the exact section.”