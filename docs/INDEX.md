# Field-Kit Documentation

This folder contains all specification and architecture documents for Field-Kit v0.1.

## Document Map

### Specs (Decision Layer)

**[`specs/INDEX.md`](specs/INDEX.md)** — Enforceable decisions that constrain implementation.

Key specs:
- **Demo Golden Flow** ([`05_demo_golden_flow_v0.1.md`](specs/05_demo_golden_flow_v0.1.md)) — The acceptance test
- **Core Data Objects** ([`02_core_data_objects_v0.1.md`](specs/02_core_data_objects_v0.1.md)) — Network, Episode, Item, Bond, QDPIEvent
- **Bond Ontology** ([`03_bond_ontology_v0.1.md`](specs/03_bond_ontology_v0.1.md)) — Bond lifecycle and proposals

### Architecture (Explanation Layer)

**[`architecture/INDEX.md`](architecture/INDEX.md)** — Architecture explains the "why" and "how."

- **Field Overview** ([`architecture/field_overview/`](architecture/field_overview/)) — 27-page architecture overview

### Essays

- **Holographic & Gibsey Paper** ([`essays/holographic_&_gibsey_paper.md`](essays/holographic_&_gibsey_paper.md)) — BKC theory essay

---

## Quick Reference

| What | Where |
|------|-------|
| Acceptance test | [`specs/05_demo_golden_flow_v0.1.md`](specs/05_demo_golden_flow_v0.1.md) |
| Object schemas | [`specs/02_core_data_objects_v0.1.md`](specs/02_core_data_objects_v0.1.md) |
| Event names | [`specs/02_core_data_objects_v0.1.md`](specs/02_core_data_objects_v0.1.md) (canonical list) |
| Credits policy | [`specs/05_demo_golden_flow_v0.1.md`](specs/05_demo_golden_flow_v0.1.md) (Golden Flow credits) |
| Prototype | [`../prototype/README.md`](../prototype/README.md) |

---

## Principle

> **Architecture explains; Specs constrain.**

Specs are enforceable decisions. If code violates a spec, the code is wrong.

Architecture documents explain rationale and context. They help you understand *why* a spec exists.
