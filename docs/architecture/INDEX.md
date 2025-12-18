# Field-Kit Architecture

> **Architecture explains; Specs constrain.**

Architecture documents explain the "why" and "how" behind Field-Kit. They provide context and rationale. For enforceable decisions, see [`../specs/INDEX.md`](../specs/INDEX.md).

---

## Field Overview (27 pages)

The Field Overview is a comprehensive architecture walkthrough organized by layer.

**Location:** [`field_overview/`](field_overview/)

### Pages in Order

| Page | Title |
|------|-------|
| 01 | [Purpose of the Field Overview](field_overview/01_field_purpose.md) |
| 02 | [One-Sentence Definition](field_overview/02_field_one_sentence.md) |
| 03 | [The Five Layers](field_overview/03_field_five_layers.md) |

**Layer 0 — Math & Metal**
| Page | Title |
|------|-------|
| 04 | [L0 Core Concepts](field_overview/04_l0_core_concepts.md) |
| 05 | [L0 Physics of the Field](field_overview/05_l0_physics.md) |
| 06 | [L0 Why It Matters](field_overview/06_l0_why_it_matters.md) |

**Layer 1 — Models & Code**
| Page | Title |
|------|-------|
| 07 | [L1 Core Concepts](field_overview/07_l1_core_concepts.md) |
| 08 | [L1 Python & C++](field_overview/08_l1_python_cpp.md) |
| 09 | [L1 PyTorch & Transformers](field_overview/09_l1_pytorch_transformers.md) |

**Layer 2 — Field Intelligence**
| Page | Title |
|------|-------|
| 10 | [L2 Core Concepts](field_overview/10_l2_core_concepts.md) |
| 11 | [L2 How the Field Reads Itself](field_overview/11_l2_how_field_reads_itself.md) |

**Layer 3 — Field Architecture & Data**
| Page | Title |
|------|-------|
| 12 | [L3 Core Concepts](field_overview/12_l3_core_concepts.md) |
| 13 | [L3 Microservices](field_overview/13_l3_microservices.md) |
| 14 | [L3 Traffic & Connectivity](field_overview/14_l3_traffic_connectivity.md) |
| 15 | [L3 Data, Events & Reliability](field_overview/15_l3_data_events_reliability.md) |

**Layer 4 — Interaction & Agents**
| Page | Title |
|------|-------|
| 16 | [L4 Core Concepts](field_overview/16_l4_core_concepts.md) |
| 17 | [L4 Agents & QDPI](field_overview/17_l4_agents_qdpi.md) |
| 18 | [L4 Evals, Guardrails & UI](field_overview/18_l4_evals_guardrails_ui.md) |

**Example: Trapped in the Field**
| Page | Title |
|------|-------|
| 19 | [Example Overview](field_overview/19_example_trapped_overview.md) |
| 20 | [Entering the Field](field_overview/20_example_entering_field.md) |
| 21 | [Agent Decides](field_overview/21_example_agent_decides.md) |
| 22 | [Retrieval](field_overview/22_example_retrieval.md) |
| 23 | [Packing, Generation & Guarding](field_overview/23_example_packing_generation_guarding.md) |
| 24 | [Logging, Updating & Returning](field_overview/24_example_logging_updating_returning.md) |

**Feedback & Summary**
| Page | Title |
|------|-------|
| 25 | [Evals & Ablation](field_overview/25_feedback_evals_ablation.md) |
| 26 | [Performance, Cost & Research](field_overview/26_feedback_performance_cost_research.md) |
| 27 | [Field Summary](field_overview/27_field_summary.md) |

---

## Layers at a Glance

```
Layer 4 — Interaction & Agents     (users, QDPI, UI, evals)
Layer 3 — Field Architecture       (microservices, DBs, events)
Layer 2 — Field Intelligence       (RAG, vector search, retrieval)
Layer 1 — Models & Code            (Python, PyTorch, transformers)
Layer 0 — Math & Metal             (vectors, matrices, GPUs)
```
