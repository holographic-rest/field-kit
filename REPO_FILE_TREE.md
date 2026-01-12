# Repository File Tree
**Generated:** 2025-12-23  
**Note:** Excludes `.venv`, `.git`, `__pycache__`, `node_modules`

---

```
field-kit/
├── .claude/ (has content)
│   └── settings.local.json (1167 bytes)
├── .env (414 bytes)
├── .env.example (303 bytes)
├── .gitignore (489 bytes)
├── LICENSE (1073 bytes)
├── README.md (4431 bytes)
│
├── claude/ (has content)
│   ├── CLAUDE.md (8251 bytes)
│   └── thursday_sprint_plan.md (8548 bytes)
│
├── docs/ (has content)
│   ├── INDEX.md (1835 bytes)
│   │
│   ├── architecture/ (has content)
│   │   ├── INDEX.md (3342 bytes)
│   │   └── field_overview/ (has content)
│   │       ├── 01_field_purpose.md (656 bytes)
│   │       ├── 02_field_one_sentence.md (395 bytes)
│   │       ├── 03_field_five_layers.md (737 bytes)
│   │       ├── 04_l0_core_concepts.md (298 bytes)
│   │       ├── 05_l0_physics.md (432 bytes)
│   │       ├── 06_l0_why_it_matters.md (681 bytes)
│   │       ├── 07_l1_core_concepts.md (152 bytes)
│   │       ├── 08_l1_python_cpp.md (431 bytes)
│   │       ├── 09_l1_pytorch_transformers.md (648 bytes)
│   │       ├── 10_l2_core_concepts.md (624 bytes)
│   │       ├── 11_l2_how_field_reads_itself.md (1268 bytes)
│   │       ├── 12_l3_core_concepts.md (419 bytes)
│   │       ├── 13_l3_microservices.md (537 bytes)
│   │       ├── 14_l3_traffic_connectivity.md (438 bytes)
│   │       ├── 15_l3_data_events_reliability.md (1106 bytes)
│   │       ├── 16_l4_core_concepts.md (216 bytes)
│   │       ├── 17_l4_agents_qdpi.md (754 bytes)
│   │       ├── 18_l4_evals_guardrails_ui.md (794 bytes)
│   │       ├── 19_example_trapped_overview.md (455 bytes)
│   │       ├── 20_example_entering_field.md (542 bytes)
│   │       ├── 21_example_agent_decides.md (626 bytes)
│   │       ├── 22_example_retrieval.md (782 bytes)
│   │       ├── 23_example_packing_generation_guarding.md (622 bytes)
│   │       ├── 24_example_logging_updating_returning.md (821 bytes)
│   │       ├── 25_feedback_evals_ablation.md (681 bytes)
│   │       ├── 26_feedback_performance_cost_research.md (768 bytes)
│   │       └── 27_field_summary.md (693 bytes)
│   │
│   ├── baselines/ (has content)
│   │   ├── BASELINE_2025-12-23.md (7449 bytes)
│   │   └── artifacts/ (has content)
│   │       └── 2025-12-23/ (has content)
│   │           ├── analyze_events.py (483 bytes)
│   │           ├── event_log_dump.jsonl (16503 bytes)
│   │           ├── run_01.log (11973 bytes)
│   │           ├── run_02.log (12150 bytes)
│   │           ├── run_03.log (12164 bytes)
│   │           ├── run_04.log (12139 bytes)
│   │           └── run_05.log (12139 bytes)
│   │
│   ├── demo/ (has content)
│   │   └── DEMO_SCRIPT_v0.1.md (3780 bytes)
│   │
│   ├── essays/ (has content)
│   │   └── holographic_&_gibsey_paper.md (46672 bytes)
│   │
│   ├── specs/ (has content)
│   │   ├── 00_winter_sprint_plan.md (8859 bytes)
│   │   ├── 01_first_run_experience_v0.1.md (75699 bytes)
│   │   ├── 02_core_data_objects_v0.1.md (47443 bytes)
│   │   ├── 03_bond_ontology_v0.1.md (63741 bytes)
│   │   ├── 04_holologue_spec_v0.1.md (52052 bytes)
│   │   ├── 05_demo_golden_flow_v0.1.md (55183 bytes)
│   │   ├── 06_canon_policy_v0.1.md (25297 bytes)
│   │   ├── 07_spin_recipes_v0.1.md (57308 bytes)
│   │   ├── 08_UI_UX_foundation_v0.1.md (36834 bytes)
│   │   ├── 09_queue_lattice_v0.1.md (13124 bytes)
│   │   └── INDEX.md (2238 bytes)
│   │
│   └── ui/ (has content)
│       ├── MENTAL_MODEL_v0.1.md (4184 bytes)
│       ├── SPRINT_UI_FIX_PLAN.md (4955 bytes)
│       └── STATE_MACHINE_v0.1.md (10777 bytes)
│
├── prompts/ (has content)
│   ├── INDEX.md (empty)
│   └── spin_recipes/ (has content)
│       ├── dialogue_templates.md (empty)
│       ├── holologue_templates.md (empty)
│       └── monologue_templates.md (empty)
│
├── prototype/ (has content)
│   ├── INDEX.md (empty)
│   ├── README.md (11721 bytes)
│   │
│   ├── data/ (has content)
│   │   ├── episodes.jsonl (456 bytes)
│   │   ├── items.jsonl (1129 bytes)
│   │   ├── networks.jsonl (436 bytes)
│   │   └── qdpi_events.jsonl (4229 bytes)
│   │
│   ├── data_archive/ (has content)
│   │   └── [30+ timestamped archive directories]
│   │
│   ├── data_baseline_test/ (has content)
│   │   ├── bonds.jsonl (2380 bytes)
│   │   ├── episodes.jsonl (456 bytes)
│   │   ├── items.jsonl (4370 bytes)
│   │   ├── networks.jsonl (436 bytes)
│   │   └── qdpi_events.jsonl (16503 bytes)
│   │
│   ├── data_dogfood/ (has content)
│   │   ├── bonds.jsonl (2424 bytes)
│   │   ├── episodes.jsonl (456 bytes)
│   │   ├── items.jsonl (33027 bytes)
│   │   ├── networks.jsonl (436 bytes)
│   │   └── qdpi_events.jsonl (45268 bytes)
│   │
│   ├── data_queue_lattice_u/ (empty)
│   │
│   ├── data_queue_lattice_ui/ (has content)
│   │   ├── episodes.jsonl (456 bytes)
│   │   ├── items.jsonl (3437 bytes)
│   │   ├── networks.jsonl (436 bytes)
│   │   └── qdpi_events.jsonl (5461 bytes)
│   │
│   ├── outputs/ (has content)
│   │   ├── README.md (empty)
│   │   └── dogfood_architecture_index.json (5220 bytes)
│   │
│   ├── scripts/ (has content)
│   │   ├── ingest_architecture_pages.py (8472 bytes)
│   │   ├── run_golden_flow.py (12557 bytes)
│   │   ├── run_golden_flow_3x.py (2102 bytes)
│   │   ├── run_sprint_b_dogfood.py (9387 bytes)
│   │   ├── test_context_transformer_bonds.py (13186 bytes)
│   │   ├── test_embeddings_sprint1.py (14568 bytes)
│   │   ├── test_handle_extraction.py (7738 bytes)
│   │   ├── test_handle_suggestions.py (13853 bytes)
│   │   ├── test_pass1.py (5096 bytes)
│   │   ├── test_pass2.py (4925 bytes)
│   │   ├── test_pass3.py (7094 bytes)
│   │   ├── test_pass4.py (6439 bytes)
│   │   ├── test_pass5.py (6207 bytes)
│   │   ├── test_queue_lattice_evidence_sprint3.py (11882 bytes)
│   │   ├── test_queue_lattice_gold_preface.py (12597 bytes)
│   │   ├── test_queue_lattice_handle_quality_sprint3b.py (10254 bytes)
│   │   ├── test_queue_lattice_pairing_sprint2.py (12164 bytes)
│   │   ├── test_queue_lattice_pass1.py (13217 bytes)
│   │   ├── test_queue_lattice_pass2.py (12623 bytes)
│   │   ├── test_queue_lattice_pass2_quality.py (13923 bytes)
│   │   ├── test_queue_lattice_pass2_ui.py (11798 bytes)
│   │   ├── test_queue_lattice_quality.py (15983 bytes)
│   │   ├── test_sprint_c_canon.py (11758 bytes)
│   │   ├── test_sprint_d_spin_recipes.py (12668 bytes)
│   │   ├── test_sprint_e_stability.py (13553 bytes)
│   │   ├── test_sprint_g_bond_suggestions.py (13296 bytes)
│   │   ├── test_sprint_g_content_shaped.py (14664 bytes)
│   │   ├── test_sprint_g_generation_quality.py (13038 bytes)
│   │   ├── test_sprint_g_suggestions_quality.py (13989 bytes)
│   │   ├── test_sprint_g_ui_state_machine.py (11002 bytes)
│   │   ├── test_ui_ontology_smoke.py (9387 bytes)
│   │   ├── test_ui_suggestions_content_shaped.py (7598 bytes)
│   │   ├── test_varied_suggestions.py (12128 bytes)
│   │   └── validate_architecture_pages.py (3016 bytes)
│   │
│   ├── ui/ (has content)
│   │   ├── README.md (7542 bytes)
│   │   ├── app.py (14739 bytes)
│   │   ├── static/ (has content)
│   │   │   ├── css/ (has content)
│   │   │   │   └── style.css (24022 bytes)
│   │   │   └── js/ (has content)
│   │   │       └── app.js (36817 bytes)
│   │   └── templates/ (has content)
│   │       └── index.html (10419 bytes)
│   │
│   └── ui_v2/ (has content)
│       ├── app.py (25099 bytes)
│       ├── static/ (has content)
│       │   ├── css/ (has content)
│       │   │   └── style.css (22866 bytes)
│       │   └── js/ (has content)
│       │       └── app.js (20512 bytes)
│       └── templates/ (has content)
│           └── index.html (2651 bytes)
│
├── research/ (has content)
│   ├── 01_event_embedding_notes.md (empty)
│   ├── 02_event_similarity_smoke_test.md (empty)
│   │
│   ├── 12-23-2025-research/ (has content)
│   │   ├── evaluation/ (has content)
│   │   │   └── 03_offline_eval_hololinks.md.md (12523 bytes)
│   │   ├── grounding_nav/ (has content)
│   │   │   └── 01_evidence_grounded_navigation_and_durable_anchoring.md (15170 bytes)
│   │   ├── ledger_graph/ (has content)
│   │   │   └── 02_event_sourced_graph_indexing.md.md (empty)
│   │   ├── local_first/ (has content)
│   │   │   └── 05_local_first_storage_privacy.md (14961 bytes)
│   │   └── memory_governence/ (has content)
│   │       └── 04_pruning_bundling_policies.md.md (15040 bytes)
│   │
│   ├── 27-essays/ (has content)
│   │   ├── 01_annotated_transformer.md (6430 bytes)
│   │   ├── 02_first_law_of_complexodynamics.md (6396 bytes)
│   │   ├── 03_unreasonable_effectiveness_of_RNNs.md (6361 bytes)
│   │   ├── 04_understanding_LSTM_networks.md (4846 bytes)
│   │   ├── 05_recurrent_neural_network_regularization.md (4511 bytes)
│   │   ├── 06_keeping_neural_networks_simple.md (6251 bytes)
│   │   ├── 07_pointer_networks.md (5802 bytes)
│   │   ├── 08_imagenet_classification_deep_CNNs_alexnet.md (5963 bytes)
│   │   ├── 09_order_matters_sequence_to_sequence_sets.md (4124 bytes)
│   │   ├── 10_gpipe_efficient_training_giant_neural_networks.md (5119 bytes)
│   │   ├── 11_deep_residual_learning_image_recognition_resnet.md (4237 bytes)
│   │   ├── 12_multi_scale_context_aggregation_dilated_convolutions.md (4118 bytes)
│   │   ├── 13_neural_message_passing_quantum_chemistry.md (4881 bytes)
│   │   ├── 14_attention_is_all_you_need.md (5508 bytes)
│   │   ├── 15_neural_machine_translation_jointly_learning_align_translate.md (4064 bytes)
│   │   ├── 16_identity_mappings_deep_residual_networks.md (4362 bytes)
│   │   ├── 17_simple_NN_module_relational_reasoning.md (4315 bytes)
│   │   ├── 18_variational_lossy_autoencoder.md (4512 bytes)
│   │   ├── 19_relational_RNNs.md (4718 bytes)
│   │   ├── 20_quantifying_rise_fall_complexity_closed_systems_coffee_automaton.md (5260 bytes)
│   │   ├── 21_neural_turing_machines.md (5470 bytes)
│   │   ├── 22_deep_speech_2_end_to_end_speech_recognition.md (4492 bytes)
│   │   ├── 23_scaling_laws_neural_LMs.md (4196 bytes)
│   │   ├── 24_tutorial_introduction_minimum_description_length_principle.md (4487 bytes)
│   │   ├── 25_machine_super_intelligence_shane_legg_dissertation.md (5000 bytes)
│   │   ├── 26_kolmogorov_complexity_algorithmic_randomness.md (4633 bytes)
│   │   └── 27_CS231n_convolutional_neural_networks_visual_recognition.md (4318 bytes)
│   │
│   ├── INDEX.md (empty)
│   ├── ML_spine_for_gibsey_QDPI.md (22307 bytes)
│   └── results/ (has content)
│       └── README.md (empty)
│
├── sprints/ (has content)
│   └── 12-23-2025-to-01-04-2026/ (has content)
│       ├── 00_MASTER_PLAN.md (8755 bytes)
│       ├── PLAN_CORRECTIONS_AUDIT.md (6907 bytes)
│       ├── S01_foundation_stabilization.md (7579 bytes)
│       ├── S02_observability_eval.md (8564 bytes)
│       ├── S03_pointer_based_navigation.md (7351 bytes)
│       ├── S04_multi_scale_context.md (5634 bytes)
│       ├── S05_graph_propagation.md (5333 bytes)
│       ├── S06_memory_governance.md (6569 bytes)
│       ├── S07_session_state.md (5115 bytes)
│       ├── S08_pipeline_batching.md (4753 bytes)
│       ├── S09_complexity_controls.md (5550 bytes)
│       └── S10_storage_privacy.md (5415 bytes)
│
├── src/ (has content)
│   ├── cli.py (48879 bytes)
│   └── fieldkit/ (has content)
│       ├── __init__.py (4175 bytes)
│       ├── anchor_pairing.py (15552 bytes)
│       ├── bond_proposer.py (empty)
│       ├── bond_suggester.py (23833 bytes)
│       ├── context_transformer.py (22506 bytes)
│       ├── embeddings.py (15367 bytes)
│       ├── generation.py (39951 bytes)
│       ├── handles.py (18577 bytes)
│       ├── hololink_pipeline.py (16339 bytes)
│       ├── holologue.py (empty)
│       ├── hololoop_engine.py (51820 bytes)
│       ├── qdpi.py (13398 bytes)
│       ├── retrieval.py (6867 bytes)
│       ├── schemas.py (11686 bytes)
│       ├── spin_recipes.py (36715 bytes)
│       ├── store_jsonl.py (13757 bytes)
│       └── suggestion_engine.py (16552 bytes)
│
├── tests/ (has content)
│   ├── test_schemas.py (empty)
│   └── test_store_jsonl.py (empty)
│
├── wrapper/ (has content)
│   ├── .env.example (26 bytes)
│   ├── .gitignore (19 bytes)
│   ├── README.md (1449 bytes)
│   ├── client/ (has content)
│   │   ├── app.js (10646 bytes)
│   │   ├── index.html (2430 bytes)
│   │   └── style.css (8195 bytes)
│   ├── package-lock.json (39282 bytes)
│   ├── package.json (261 bytes)
│   └── server/ (has content)
│       └── index.js (4352 bytes)
│
└── writeups/ (has content)
    ├── 2025-12_winter_sprint_episode_0.md (empty)
    ├── 2026-01_winter_sprint_report.md (empty)
    └── ui_ontology_gap_report.md (12048 bytes)
```

---

## Empty Files Summary

**Empty files found:**
- `prompts/INDEX.md`
- `prompts/spin_recipes/dialogue_templates.md`
- `prompts/spin_recipes/holologue_templates.md`
- `prompts/spin_recipes/monologue_templates.md`
- `prototype/INDEX.md`
- `prototype/outputs/README.md`
- `research/01_event_embedding_notes.md`
- `research/02_event_similarity_smoke_test.md`
- `research/INDEX.md`
- `research/ledger_graph/02_event_sourced_graph_indexing.md.md`
- `research/results/README.md`
- `src/fieldkit/bond_proposer.py`
- `src/fieldkit/holologue.py`
- `tests/test_schemas.py`
- `tests/test_store_jsonl.py`
- `writeups/2025-12_winter_sprint_episode_0.md`
- `writeups/2026-01_winter_sprint_report.md`

**Empty directories:**
- `prototype/data_queue_lattice_u/`

---

## Notes

- **Total empty files:** 17
- **Total empty directories:** 1
- **Largest files:** 
  - `src/cli.py` (48879 bytes)
  - `src/fieldkit/hololoop_engine.py` (51820 bytes)
  - `docs/specs/03_bond_ontology_v0.1.md` (63741 bytes)
- **Most content-rich directories:**
  - `prototype/scripts/` (34 test/utility scripts)
  - `research/27-essays/` (27 research papers)
  - `prototype/data_archive/` (30+ timestamped archives)

