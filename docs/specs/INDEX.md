# Field-Kit Specs

**Specs are enforceable decisions.** If code violates a spec, the code is wrong.

---

## Reading Order

| Doc | Title | Summary |
|-----|-------|---------|
| 00 | [Winter Sprint Plan](00_winter_sprint_plan.md) | Sprint timeline and goals |
| 01 | [First Run Experience](01_first_run_experience_v0.1.md) | App initialization flow |
| 02 | [Core Data Objects](02_core_data_objects_v0.1.md) | Network, Episode, Item, Bond, QDPIEvent schemas |
| 03 | [Bond Ontology](03_bond_ontology_v0.1.md) | Bond lifecycle, proposals, execution |
| 04 | [Holologue Spec](04_holologue_spec_v0.1.md) | Many→one synthesis |
| **05** | [**Demo Golden Flow**](05_demo_golden_flow_v0.1.md) | **Acceptance test** |
| 06 | [Canon Policy](06_canon_policy_v0.1.md) | Curated lists, derived projection |
| 07 | [Spin Recipes](07_spin_recipes_v0.1.md) | Suggestion templates |
| 08 | [UI/UX Foundation](08_UI_UX_foundation_v0.1.md) | UI surfaces and behavior |

---

## Acceptance Test

**The acceptance test is Document 05: Demo Golden Flow.**

> "If the prototype can run the Demo Golden Flow end-to-end **without improvising**, it passes."

Run it:
```bash
python3 prototype/scripts/run_golden_flow.py --fresh
```

Expected: Credits end at **73**, all events in correct order.

---

## Key Invariants

### Objects
- **Network** — root container (`nw_` prefix)
- **Episode** — session container (`ep_` prefix)
- **Item** — content node (`it_` prefix), types: Q, M, D, H
- **Bond** — transformation (`bd_` prefix), status: draft → executed
- **QDPIEvent** — immutable log entry (`ev_` prefix)

### Events (canonical names only)
```
app.first_run.started
episode.created
tutorial.started
item.created
bond.suggestions.presented
bond.draft_created
bond.run_requested
bond.executed
bond.execution_failed
holologue.run_requested
holologue.validation_failed
holologue.completed
holologue.failed
bond.proposals.presented
ledger.opened
store.commit
store.commit_failed
credits.delta
```

### Credits (Golden Flow policy)
- Seed: +100
- Item created: +1
- Bond run: -10 (spend), +3 (reward on success), +10 (refund on failure)
- Holologue run: -20 (spend), +5 (reward on success), +20 (refund on failure)
- Final balance on success: **73**
