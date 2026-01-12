OK Step 1 looks good. 

(.venv) ghostradongus@Brennans-Mac-mini field-kit % python3 prototype/scripts/run_golden_flow.py --fresh --data-dir prototype/data_tomorrow_golden 


[--fresh] Archiving existing data...
No existing JSONL files to archive.

======================================================================
FIELD-KIT v0.1 — DEMO GOLDEN FLOW
======================================================================

──────────────────────────────────────────────────────────────────────
STEP 1: Launch → Episode 0 created → Blank Field visible
──────────────────────────────────────────────────────────────────────
Store initialized.
  Network: nw_2ECA34F62F62479FAE783C44
  Episode: ep_DC199DFEA3A34F88B068AE09 (Session 0)
  Credits: 100
✓ Episode created: ep_DC199DFEA3A34F88B068AE09
✓ Credits: 100

──────────────────────────────────────────────────────────────────────
STEP 2: Start Guided Tutorial
──────────────────────────────────────────────────────────────────────
Tutorial started.
✓ Tutorial started

──────────────────────────────────────────────────────────────────────
STEP 3: Create Item 1 (Q)
──────────────────────────────────────────────────────────────────────
Item created: it_049EB3D34F1F451CB8663EBE
  Type: Q
  Title: My First Field Item
  Credits: 101
✓ Item 1: it_049EB3D34F1F451CB8663EBE
✓ Credits: 101

──────────────────────────────────────────────────────────────────────
STEP 4: Create Item 2 (Q)
──────────────────────────────────────────────────────────────────────
Item created: it_70B65BA68F8A4AD0BE4A50CB
  Type: Q
  Title: Second Field Item
  Credits: 102
✓ Item 2: it_70B65BA68F8A4AD0BE4A50CB
✓ Credits: 102

──────────────────────────────────────────────────────────────────────
STEP 5: Suggested Bond prompts appear (events only)
──────────────────────────────────────────────────────────────────────
Suggestions presented for item it_049EB3D34F1F451CB8663EBE:
  (scales: local)
  1. [clarify] (25%) [d=1] Unpack "My First Field Item": what are its 3 core components?
     [local@0] "My First Field Item"
  2. [concretize] (24%) [d=1] Sketch a scenario that instantiates "Item" end-to-end.
     [local@0] "Item"
  3. [connect] (25%) [d=1] Link "My First Field Item" to its preconditions and postconditions.
     [local@0] "My First Field Item"
  4. [test] (25%) [d=1] Sketch a scenario that instantiates "My First Field Item" end-to-end.
     [local@0] "My First Field Item"
✓ 4 suggestions presented (events-only)
✓ No Bond created

──────────────────────────────────────────────────────────────────────
STEP 6: Q→M via suggested Bond execution
──────────────────────────────────────────────────────────────────────
Bond draft created: bd_FDD09373A7E74022A27828CA
  Inputs: ['it_049EB3D34F1F451CB8663EBE']
  Prompt: Unpack "My First Field Item": what are its 3 core components?
Bond executed: bd_FDD09373A7E74022A27828CA
  Output Item: it_E6A10C5519B448EEBA4E919E (type=M)
  Credits: 95
✓ Bond 1: bd_FDD09373A7E74022A27828CA
✓ Output M: it_E6A10C5519B448EEBA4E919E
✓ Credits: 95

──────────────────────────────────────────────────────────────────────
STEP 7: Q→D via user-written Bond execution
──────────────────────────────────────────────────────────────────────
Bond draft created: bd_DF2E8D77CA1C4FFB9CE3E7E5
  Inputs: ['it_70B65BA68F8A4AD0BE4A50CB']
  Prompt: Write a short decision note (5 bullets) that makes one clear choice based on Item 1.
Bond executed: bd_DF2E8D77CA1C4FFB9CE3E7E5
  Output Item: it_EBA7B907C8EB49E2A76EBC53 (type=D)
  Credits: 88
✓ Bond 2: bd_DF2E8D77CA1C4FFB9CE3E7E5
✓ Output D: it_EBA7B907C8EB49E2A76EBC53
✓ Credits: 88

──────────────────────────────────────────────────────────────────────
STEP 8: (Q,Q)→H Holologue artifact creation
──────────────────────────────────────────────────────────────────────
Holologue completed: it_67AE9EBEF9E74C1C95F2832E
  Artifact kind: plan
  Selected items: 2
  Credits: 73
  Proposals presented (events-only):
    1. [clarify_to_testable_claim] Define "Holologue: plan (2 items)" with 3 concrete...
    2. [architecture_map] Show where "Key Themes" fits in the architecture w...
    3. [interaction_trace] Trace how "Action Items" flows through the system ...
    4. [spec_fragment_rules] Give 3 test cases that validate "Synthesis Plan" w...
✓ Output H: it_67AE9EBEF9E74C1C95F2832E
✓ Credits: 73

──────────────────────────────────────────────────────────────────────
STEP 9: Holologue proposals presented (events only)
──────────────────────────────────────────────────────────────────────
✓ 4 proposals presented (events-only)

──────────────────────────────────────────────────────────────────────
STEP 10: Ledger inspection (Queue/Inspect)
──────────────────────────────────────────────────────────────────────
============================================================
LEDGER VIEW
============================================================

--- Objects ---
Networks: 1
Episodes: 1
Items: 5
  - it_049EB3D34F1F451CB8663EBE: type=Q, title=My First Field Item...
  - it_70B65BA68F8A4AD0BE4A50CB: type=Q, title=Second Field Item...
  - it_E6A10C5519B448EEBA4E919E: type=M, title=M: My First Field Item...
  - it_EBA7B907C8EB49E2A76EBC53: type=D, title=D: Second Field Item...
  - it_67AE9EBEF9E74C1C95F2832E: type=H, title=Holologue: plan (2 items)...
Bonds: 2
  - bd_FDD09373A7E74022A27828CA: status=executed, output_item_id=it_E6A10C5519B448EEBA4E919E
  - bd_DF2E8D77CA1C4FFB9CE3E7E5: status=executed, output_item_id=it_EBA7B907C8EB49E2A76EBC53

--- Events ---
Total events: 34
    1. app.first_run.started          (qdpi=Q, dir=system→field)
    2. episode.created                (qdpi=Q, dir=system→field)
    3. credits.delta                  (qdpi=Q, dir=system→field)
    4. store.commit                   (qdpi=Q, dir=system→field)
    5. tutorial.started               (qdpi=Q, dir=user→field)
    6. item.created                   (qdpi=M, dir=user→field)
    7. credits.delta                  (qdpi=Q, dir=system→field)
    8. store.commit                   (qdpi=Q, dir=system→field)
    9. item.created                   (qdpi=M, dir=user→field)
   10. credits.delta                  (qdpi=Q, dir=system→field)
   11. store.commit                   (qdpi=Q, dir=system→field)
   12. bond.suggestions.presented     (qdpi=Q, dir=system→field)
   13. hololink.candidates_generated  (qdpi=Q, dir=system→field)
   14. bond.draft_created             (qdpi=D, dir=user→field)
   15. store.commit                   (qdpi=Q, dir=system→field)
   16. bond.run_requested             (qdpi=Q, dir=user→field)
   17. credits.delta                  (qdpi=Q, dir=system→field)
   18. bond.executed                  (qdpi=M, dir=system→field)
   19. credits.delta                  (qdpi=Q, dir=system→field)
   20. store.commit                   (qdpi=Q, dir=system→field)
   21. bond.draft_created             (qdpi=D, dir=user→field)
   22. store.commit                   (qdpi=Q, dir=system→field)
   23. bond.run_requested             (qdpi=Q, dir=user→field)
   24. credits.delta                  (qdpi=Q, dir=system→field)
   25. bond.executed                  (qdpi=M, dir=system→field)
   26. credits.delta                  (qdpi=Q, dir=system→field)
   27. store.commit                   (qdpi=Q, dir=system→field)
   28. holologue.run_requested        (qdpi=H, dir=user→field)
   29. credits.delta                  (qdpi=Q, dir=system→field)
   30. holologue.completed            (qdpi=H, dir=system→field)
   31. credits.delta                  (qdpi=Q, dir=system→field)
   32. bond.proposals.presented       (qdpi=Q, dir=system→field)
   33. store.commit                   (qdpi=Q, dir=system→field)
   34. ledger.opened                  (qdpi=Q, dir=user→field)

--- Credits ---
Credits events: 9
  seq=3: delta=+100, balance=100, reason=seed
  seq=7: delta=+1, balance=101, reason=item_created
  seq=10: delta=+1, balance=102, reason=item_created
  seq=17: delta=-10, balance=92, reason=bond_run_spend
  seq=19: delta=+3, balance=95, reason=bond_executed_reward
  seq=24: delta=-10, balance=85, reason=bond_run_spend
  seq=26: delta=+3, balance=88, reason=bond_executed_reward
  seq=29: delta=-20, balance=68, reason=holologue_run_spend
  seq=31: delta=+5, balance=73, reason=holologue_completed_reward

Final Credits Balance: 73
============================================================

======================================================================
FINAL ASSERTIONS
======================================================================
✓ Items: 5 (types: ['D', 'H', 'M', 'Q', 'Q'])
✓ Bonds: 2 (both executed)
✓ Event ordering: bond.run_requested < bond.executed
✓ Event ordering: holologue.run_requested < holologue.completed
✓ Event ordering: holologue.completed < bond.proposals.presented
✓ Credits: 73 (matches expected 73)

--- Success-path events found ---
  ✓ app.first_run.started (1x)
  ✓ episode.created (1x)
  ✓ credits.delta (9x)
  ✓ tutorial.started (1x)
  ✓ item.created (2x)
  ✓ bond.suggestions.presented (1x)
  ✓ bond.draft_created (2x)
  ✓ bond.run_requested (2x)
  ✓ bond.executed (2x)
  ✓ holologue.run_requested (1x)
  ✓ holologue.completed (1x)
  ✓ bond.proposals.presented (1x)
  ✓ ledger.opened (1x)
  ✓ store.commit (8x)

======================================================================
GOLDEN FLOW COMPLETE — ALL ASSERTIONS PASSED!
======================================================================
(.venv) ghostradongus@Brennans-Mac-mini field-kit % 

Step 2 also seemed to pass, as well 

(.venv) ghostradongus@Brennans-Mac-mini field-kit % python3 src/cli.py --data-dir prototype/data_tomorrow_golden eval:regression

======================================================================
FIELD-KIT REGRESSION SUITE
======================================================================

[PASS] m_no_suggestions_expected
[PASS] q_golden_flow_v1
[PASS] q_governance_metrics_v1
[PASS] q_graph_propagation_v1
[PASS] q_multiscale_evidence_v1
[PASS] q_synthetic_field_overview
[PASS] q_synthetic_strict_intent
[PASS] q_synthetic_top1_only

----------------------------------------------------------------------
Total checks: 40
Passed: 40
Failed: 0

REGRESSION SUITE PASSED
======================================================================
(.venv) ghostradongus@Brennans-Mac-mini field-kit % 

Step 3 also looks good

(.venv) ghostradongus@Brennans-Mac-mini field-kit % python3 src/cli.py --data-dir prototype/data_tomorrow_golden eval:dashboard

======================================================================
FIELD-KIT EVALUATION REPORT
======================================================================

Test Case                          MRR@K  Recall@K  ECR    TRI    Scales
------------------------------------------------------------------------------
q_golden_flow_v1                  1.000  1.000     1.000  0.121  local
m_no_suggestions_expected         0.000  0.000     0.000  0.000  -
q_synthetic_field_overview        1.000  1.000     1.000  0.109  local
q_synthetic_strict_intent         1.000  1.000     1.000  0.152  local
q_governance_metrics_v1           1.000  1.000     1.000  0.122  local
q_graph_propagation_v1            1.000  1.000     1.000  0.118  local
q_multiscale_evidence_v1          1.000  1.000     1.000  0.108  local
q_synthetic_top1_only             1.000  1.000     1.000  0.134  local

--- Aggregate Metrics ---
Avg MRR@K:    1.0000
Avg Recall@K: 1.0000
Avg ECR:      1.0000
Avg TRI:      0.1233
Avg Scales:   1.00 (local)

======================================================================
(.venv) ghostradongus@Brennans-Mac-mini field-kit % 

Step 4 seems good

(.venv) ghostradongus@Brennans-Mac-mini field-kit % python3 src/cli.py --data-dir prototype/data_tomorrow_golden govern:report

============================================================
GOVERNANCE REPORT
============================================================

Timestamp: 2025-12-24T18:54:45.481055Z
Data Dir: prototype/data_tomorrow_golden

--- Recommended Action ---
  Action: CONTINUE
  Confidence: 80%
  Rationale: Field appears healthy. Continue normal operation.

--- Supporting Observations ---
  - High hubness (75.0%)
  - Soup state detected
  - Bundle suggested but only 2 bonds (need 3)

--- Key Metrics ---
  Items: 5
  Bonds: 2
  Complexity: 385 bytes
  Hubness: 75.0%
  Duplicate Rate: 0.0%
  Entropy Ratio: 100.0%

--- Thresholds ---
  complexity_high: 800
  hubness_high: 0.7
  duplicate_rate_high: 0.15
  orphan_rate_high: 0.4
  entropy_ratio_low: 0.5
  bond_ratio_low: 0.2
  min_items_for_action: 5

============================================================
(.venv) ghostradongus@Brennans-Mac-mini field-kit %

## Governance report polish

Fixed the contradiction where action=CONTINUE but observations included "Soup state detected".

**Issue**: The report said "CONTINUE" but also claimed "Soup state detected" - confusing for users.

**Fix**: Updated `src/fieldkit/governor.py` to:
1. Gate "soup state" / "sparse graph" assertions on minimum scale (3+ bonds or 10+ items)
2. Use softer language for small datasets ("Early soup-like indicators", "Hubness elevated - typical for early-stage")
3. Filter observations for CONTINUE action to avoid alarm phrases

**Updated output** (prototype/data_gov_polish):

```
============================================================
GOVERNANCE REPORT
============================================================

Timestamp: 2025-12-24T19:01:38.988793Z
Data Dir: prototype/data_gov_polish

--- Recommended Action ---
  Action: CONTINUE
  Confidence: 80%
  Rationale: Field appears healthy. Continue normal operation.

--- Supporting Observations ---
  - Bundle indicators present but below minimum scale (2 bonds, need 3)
  - Hubness elevated (75.0%) - typical for early-stage Fields

--- Key Metrics ---
  Items: 5
  Bonds: 2
  Complexity: 385 bytes
  Hubness: 75.0%
  Duplicate Rate: 0.0%
  Entropy Ratio: 100.0%

--- Thresholds ---
  complexity_high: 800
  hubness_high: 0.7
  duplicate_rate_high: 0.15
  orphan_rate_high: 0.4
  entropy_ratio_low: 0.5
  bond_ratio_low: 0.2
  min_items_for_action: 5

============================================================
```

**Verification**:
- Governance tests: 21/21 (added new test for no-alarm-phrases-on-continue)
- Regression: 40/40 PASSED
- Golden flow: PASSED

---

## Demo Architecture Dataset

Created `prototype/data_demo_architecture/` with 30 items from architecture documentation.

**Source**: 27 pages from `docs/architecture/field_overview/*.md`

**Dataset stats**:
- Items: 30 (27 Q from pages + 3 M from bonds)
- Bonds: 3 (executed)
- Events: 99
- Size: 112K

**Money shot demo** (P11: L2 – Field Intelligence: How the Field Reads Itself):
```
$ python3 src/cli.py --data-dir prototype/data_demo_architecture suggestions:show it_3B424DED62C74E7BA93935E7

Suggestions presented for item it_3B424DED62C74E7BA93935E7:
  (scales: local, mid)
  1. [clarify] (26%) [d=1] State "P11: L2 – Field Intelligence: How the Field Reads Itself" as a MUST/MUST ...
     [local@0] "P11: L2 – Field Intelligence: How the Field Reads ..."
     [mid@-4] "P10: L2 – Field Intelligence: Core Concepts..."
  2. [concretize] (25%) [d=1] Illustrate "the Gibsey Index" with a before/after comparison.
     [local@0] "the Gibsey Index"
     [mid@-4] "Sentence Window Retrieval & Auto-Merging..."
  3. [connect] (25%) [d=1] Link "The Field Engine" to its preconditions and postconditions.
     [local@0] "The Field Engine"
     [mid@-4] "Sentence Window Retrieval & Auto-Merging..."
  4. [test] (25%) [d=1] Operationalize "the field knows" as a sequence of observable events.
     [local@0] "the field knows"
     [mid@-4] "Sentence Window Retrieval & Auto-Merging..."
```

**Multi-scale context**: local + mid scales active (evidence grounding working).

**Governance report**:
```
============================================================
GOVERNANCE REPORT
============================================================

Timestamp: 2025-12-24T21:41:39.976299Z
Data Dir: prototype/data_demo_architecture

--- Recommended Action ---
  Action: BRANCH
  Confidence: 60%
  Rationale: Consider branching: Low bond ratio (0.10); Sparse graph detected.

--- Supporting Observations ---
  - Soup state detected
  - High orphan rate (80.0%)
  - Low bond ratio (0.10)
  - Sparse graph detected

--- Key Metrics ---
  Items: 30
  Bonds: 3
  Complexity: 357 bytes
  Hubness: 50.0%
  Duplicate Rate: 0.0%
  Entropy Ratio: 100.0%

--- Thresholds ---
  complexity_high: 800
  hubness_high: 0.7
  duplicate_rate_high: 0.15
  orphan_rate_high: 0.4
  entropy_ratio_low: 0.5
  bond_ratio_low: 0.2
  min_items_for_action: 5

============================================================
```

**Note**: With 30 items and 3 bonds, the governance report now correctly shows full state assertions ("Soup state detected", "Sparse graph detected") since we've exceeded the minimum scale thresholds.

**Eval dashboard**: 8/8 regression tests passing, 100% MRR@K and Recall@K.