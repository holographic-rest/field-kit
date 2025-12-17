---
title: Field Starter Kit v0.1 — Winter Sprint Plan
repo: field-kit
status: active
owner: Brennan
tags: [field-kit, holographic, gibsey, qdpi, holologue, roadmap, sprint]
---

# Field Starter Kit v0.1 — Winter Sprint Plan

## Context: what’s already “hard and done”
You already have the three hardest foundations:

- a **world + ethics thesis** (BKC essay)
- a **system-level architecture** (27-page Field overview)
- a **technical learning spine** that maps ML directly onto the Field primitives (Modules A–E)

What remains is to ship:

1) a **tight, minimal, enforceable “decision layer”** (specs the system can obey), and  
2) a **runnable proof loop** (a tiny organism that demonstrates Field behavior end-to-end)

---

## North Star (deadline + proof)
**By Jan 2**, ship a small **Field Starter Kit v0.1** that proves:

1. the Field has **objects** (Item / Bond / Episode / Event)
2. the Field has **conduct** (QDPI event trail)
3. the Field can **reflect and grow itself** (Holologue bundle + bond proposals)

This is **dogfooding as proof-of-world** — and a high-signal artifact for OpenAI Residency / Anthropic Fellowship.

---

## Goals

### Goal 1 — Make the Field enforceable (not just describable)
Turn concept into **constraints the system can obey** via a short spec pack.

**Spec pack contents:**
- First-run experience
- Core data objects
- Bond ontology
- Holologue output bundle
- Demo golden flow
- Canon / sample-world policy
- Prompt “spin recipes” (optional but powerful)

---

### Goal 2 — Make it real with a bootstrap floor
You don’t need the full monorepo dream. You need the minimum floor that unlocks everything else.

**Bootstrap floor:**
- an **empty Vault**
- an **Item type**
- a **Create Item action**
- a **QDPI event logger**
- a way to run a **Holologue** that outputs **text + bond proposals**
- a way to **accept one bond** and see it persist

This is the first “organism” of the Field.

---

### Goal 3 — Make it measurable (one empirical artifact)
To align with Anthropic Fellows / OpenAI Residency, produce at least one artifact that reads like:

> question → experiment harness → result → write-up → reproducible repo

**Mini-study output:**
- event embeddings (text + glyph vector + simple features)
- “find similar events”
- “propose typed bonds”
- a small evaluation (30–50 examples) with error analysis

This is evaluation + measurement: safe, legible, and high-signal.

---

### Goal 4 — Package it (so it converts into opportunities)
By Jan 2:
- a clean repo structure
- README that tells the story fast
- a 1-page demo script
- a 1–2 page winter sprint report
- a mini research proposal draft

---

## Deliverables

### Deliverable A — Field Spec Pack v0.1 (docs)
Minimum set (high leverage, low ambiguity):

1. **First-Run Experience v0.1**
2. **Core Data Objects v0.1** (Item/Bond/Episode/QDPIEvent)
3. **Bond Ontology v0.1** (12 bond types + anti-patterns)
4. **Holologue Spec v0.1** (bundle output + bond proposals)
5. **Demo Golden Flow v0.1** (step-by-step walkthrough)

Stretch (if time/energy):
6) **Canon Policy v0.1** (blank field vs sample world)  
7) **Spin Recipes v0.1** (prompt pack templates)

These are decision artifacts. Once they exist, building becomes obvious.

---

### Deliverable B — Field Starter Kit v0.1 (runnable proof loop)
Implementation can be minimal: Obsidian+Python, tiny web app, or a minimal slice of an existing system.  
**Behavior matters more than stack.**

**Required capabilities:**
- Create Item (Q/M/D/H as types or tags)
- Create Bond (typed, directional)
- Log QDPIEvent (append-only)
- Run Holologue → outputs:
  - narrative synthesis
  - bond proposals (typed, with rationale + confidence)
  - open questions
  - suggested next Queues
- Accept a proposed bond → persists in store

**Definition of Done:**  
You can run the Demo Golden Flow end-to-end without improvising.

---

### Deliverable C — Field Intelligence mini-study v0.1
**Minimal experiment:**
- Use a set of QDPI events (your usage over 1–2 weeks)
- Build event embeddings:
  - text embedding (request/response)
  - glyph vector (family + sin/cos orientation)
  - action type embedding/one-hot
- Implement:
  - nearest-neighbor retrieval (“similar past events”)
  - bond-type suggestion baseline (rules + similarity thresholds)
- Evaluate on 30–50 cases:
  - are neighbors sensible?
  - are bond types sensible?
  - what fails? (taxonomy)

**Output:**
- `/research/field_event_similarity.md` (short write-up)
- `/research/notebooks_or_scripts/` (reproducible code)
- small results table + qualitative error analysis

---

### Deliverable D — Packaging kit (application-ready)
By Jan 2:
- README: what it is + how to run + what it proves
- Demo script (from the spec pack)
- Winter sprint report (2–4 pages): decisions + what shipped + what’s next
- Mini research proposal (1 page): question, method, week-1 MVP, stretch goal

---

## Execution system: run the project as QDPI
Each day, run the project *as itself*:

- **Queue (10–20 min):** review yesterday + pick today’s smallest win
- **Monologue (30–60 min):** write one spec section / implement one function
- **Dialogue (30–90 min):** co-work on hard piece (schema, test, algorithm)
- **Holologue (10–20 min):** end-of-day synthesis + create 1–3 bonds between artifacts

Also: treat each week as an **Episode**:
- Episode 1 = Spec Lock
- Episode 2 = Bootstrap Floor
- Episode 3 = Measurement + Packaging

---

## Calendar (Dec 12 → Jan 2)

### Week 1 — Spec Lock + Repo Skeleton (Dec 12–18)
**Outputs by end of week:**
- Spec pack docs 1–5 in rough form
- Repo skeleton exists
- QDPIEvent schema “frozen enough” to implement

Suggested breakdown:
- Fri: Episode 0 sprint kickoff doc + repo structure
- Sat: First-run experience
- Sun: Core data objects
- Mon: Bond ontology
- Tue: Holologue spec
- Wed: Demo golden flow
- Thu: spec freeze pass (tighten, remove ambiguity, add non-goals)

**Week 1 Definition of Done:**  
A future engineer (or future you) can build without guessing.

---

### Week 2 — Bootstrap Floor (Dec 19–25)
**Outputs by end of week:**
- Create Item works
- QDPI events append-only logging works
- Create Bond works
- Holologue bundle output works (even crude)
- Demo Golden Flow runs end-to-end once

**Build order (do not reorder):**
1) Storage first  
2) Create Item  
3) Log QDPIEvent  
4) Create Bond  
5) Holologue bundle output  
6) Accept bond proposal → persist  

Suggested schedule:
- Dec 19–20: storage + schemas
- Dec 21: create item + auto-log Queue event
- Dec 22: create bond + bond list view
- Dec 23: holologue generator (bundle output, even mocked)
- Dec 24–25: light days (papercuts + run demo + note bugs)

---

### Week 3 — Measurement + Packaging (Dec 26–Jan 2)
**Outputs by end of week:**
- Event similarity script works (feels right)
- Bond proposer baseline exists
- Evaluation write-up exists
- README + sprint report exist
- Mini research proposal exists

Suggested schedule:
- Dec 26–27: research harness (glyph vectors + embeddings + event embedding)
- Dec 28: similarity retrieval
- Dec 29: bond proposal baseline
- Dec 30: evaluate 30–50 cases + failure taxonomy
- Dec 31: write-up
- Jan 1–2: package everything

---

## Low-energy menu (so progress is always possible)

### 20 minutes
- tighten one spec paragraph
- add 2 examples to Bond Ontology
- write one Holologue sample output bundle

### 45 minutes
- implement one schema + a validation test
- implement one CLI command: `create_item` / `log_event` / `create_bond`

### 90 minutes
- run demo flow and write a bug list
- run one notebook chain: embed → similarity → output

### 2–3 hours
- integrate Holologue bundle into prototype UI
- write evaluation + results section

---

## OpenAI / Anthropic alignment (without hijacking the project)

**What OpenAI Residency sees:**
- ambiguity → spec → working prototype
- clean code + tests
- learning velocity (ML spine → working embedding/similarity harness)

**What Anthropic Fellows sees:**
- empirical eval harness + measurement
- public-output-shaped write-up
- safety-adjacent work: evaluation, provenance, oversight-like analysis

---

## Single unifying story (use everywhere)
> **Holographic is a protocol + event-sourced substrate for long-horizon human–AI co-authorship; Gibsey is a sample world that stress-tests it; QDPI makes interaction measurable; Holologues turn logs into structured reflection and bond proposals.**

---

## If time collapses: the 3 must-haves
If everything goes sideways, do these three and the Field still exists:

1) **Core Data Objects v0.1 + QDPIEvent schema implemented**
2) **Holologue bundle output spec + one working Holologue generator**
3) **Demo Golden Flow executed end-to-end once (even ugly)**