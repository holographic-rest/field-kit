# Field-Kit Demo Script v0.1

**Duration:** 3–5 minutes
**Audience:** Engineers, reviewers, stakeholders
**Goal:** Prove Field-Kit is "not a chat app" — persistent objects, lineage, Holologue, inspectable credits

---

## Before You Start

Ensure you're in the repo root:
```bash
cd field-kit
```

If you've run the demo before, use `--fresh` to start clean.

---

## The Demo (Step by Step)

### Step 1: Run the Golden Flow

**Say:** "I'm going to run the Golden Flow — our acceptance test. This creates objects with stable IDs, logs every action as an event, and ends with a known credits balance."

**Run:**
```bash
python3 prototype/scripts/run_golden_flow.py --fresh
```

**What they'll see:**
- Store initialization (Network, Episode created)
- Items created with `it_` IDs
- Bond draft created → Bond executed → output Item produced
- Holologue run → single H output Item
- Ledger view with Objects, Events, and Credits

**Point out:**
- "Notice the IDs — `nw_`, `ep_`, `it_`, `bd_`. These are stable, persisted identifiers."
- "Credits end at 73 — exactly as specified."

---

### Step 2: Highlight "Not Chat"

**Say:** "This is NOT a chat app. Here's the proof:"

**Point to the output:**
1. **Bond execution:** "See `Bond executed: bd_...` and `Output Item: it_...`. The Bond knows its inputs and output. This is lineage."
2. **Ledger events:** "Every action is an event: `bond.run_requested`, `bond.executed`, `holologue.completed`. Append-only, immutable."
3. **Credits:** "Credits are events too — `credits.delta`. The balance (73) is derived, not stored. Fully inspectable."

---

### Step 3: Show Holologue (Many→One)

**Say:** "Holologue takes 2+ Items and synthesizes them into exactly one output."

**Point to the output:**
```
Holologue completed: it_...
  Artifact kind: plan
  Selected items: 2
```

**Say:** "Two inputs, one output. The H-type Item has provenance pointing back to its sources."

---

### Step 4: Explain Credits (Not Money)

**Say:** "Credits are simulated. They prove the economic layer is evented and inspectable."

**Point to:**
```
Credits events: 9
  seq=3: delta=+100, balance=100, reason=seed
  ...
  seq=28: delta=+5, balance=73, reason=holologue_completed_reward
```

**Say:** "Every delta is logged. The balance is derived. No real money, no payments, no crypto. Just an inspectable simulation."

---

### Step 5: (Optional) Run Sprint B Dogfood

**Say:** "We also have a dogfood test that ingests 27 architecture pages as Items."

**Run:**
```bash
python3 prototype/scripts/run_sprint_b_dogfood.py --fresh
```

**Point out:**
- 27 Items created from markdown pages
- Credits accumulate (+1 per item)

---

## If Something Fails

If the demo fails mid-run:

1. Run with `--fresh` to reset:
   ```bash
   python3 prototype/scripts/run_golden_flow.py --fresh
   ```

2. Check for leftover data:
   ```bash
   ls prototype/data/
   ```
   Files should be gitignored, but you can delete `prototype/data/` manually if needed.

3. Re-run.

---

## Key Takeaways

After the demo, summarize:

1. **Persistent objects** — IDs are stable, not ephemeral
2. **Lineage** — Bonds track input→output, provenance is explicit
3. **Holologue** — Many→one synthesis, exactly one output
4. **Events** — Append-only log, canonical names only
5. **Credits** — Evented, derived, inspectable (not real money)

**Final line:** "This is what 'not a chat app' looks like. Questions?"

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `python3 prototype/scripts/run_golden_flow.py --fresh` | Run acceptance test |
| `python3 prototype/scripts/run_sprint_b_dogfood.py --fresh` | Ingest architecture pages |
| `python3 prototype/scripts/test_sprint_e_stability.py` | Test failure + refund paths |
