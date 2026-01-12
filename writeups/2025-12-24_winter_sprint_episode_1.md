# Winter Sprint Episode 1 — Demo Readiness + Discriminative Evals

**Date:** 2025-12-24
**Data:** `prototype/data_demo_architecture` (architecture corpus demo dataset)

## What I did today (high level)

* Captured a clean baseline run (golden flow + regression + dashboard + governance).
* Built a real demo dataset from the 27 architecture pages + seeded bonds (30+ items).
* Added two discriminative eval test cases:

  * `q_strict_accept_only_v2` (only **clarify** counts as acceptable)
  * `q_requires_mid_scale_v1` (requires at least **mid** evidence scale)
* Ran a mini-session: created + executed a bond and observed system updates.

---

## Key outputs

### Money shot — evidence-grounded suggestions (after action)

**Subject item:** `it_3B424DED62C74E7BA93935E7`
**Bond executed:** `bd_8EA83A3E7BA9492F91851D51`
**Output item:** `it_6D8B027CB644466198FCF05E` (type=M)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture suggestions:show it_3B424DED62C74E7BA93935E7
```

**Output (excerpt)**

```
Suggestions presented for item it_3B424DED62C74E7BA93935E7:
  (scales: local, mid)
  1. [clarify] (26%) [d=1] Break "P11: L2 – Field Intelligence: How the Field Reads Itself" into 4 testable...
     [local@0] "P11: L2 – Field Intelligence: How the Field Reads ..."
     [mid@-2] "M: L2 – Field Intelligence: How the Field Reads It..."
  2. [concretize] (25%) [d=1] Ground "the Gibsey Index" in a specific use case with named components.
     [local@0] "the Gibsey Index"
     [mid@-2] "M: L2 – Field Intelligence: How the Field Reads It..."
  3. [connect] (25%) [d=1] Where does "The Field Engine" fit in the overall data flow?
     [local@0] "The Field Engine"
     [mid@-2] "M: L2 – Field Intelligence: How the Field Reads It..."
  4. [test] (25%) [d=1] Ground "the field knows" in a specific use case with named components.
     [local@0] "the field knows"
     [mid@-2] "M: L2 – Field Intelligence: How the Field Reads It..."
```

---

### Governance report (after action)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture govern:report
```

**Output**

```
GOVERNANCE REPORT

Recommended Action:
  Action: BRANCH
  Confidence: 60%
  Rationale: Consider branching: Low bond ratio (0.13); Sparse graph detected.

Supporting Observations:
  - Soup state detected
  - High orphan rate (77.4%)
  - Low bond ratio (0.13)
  - Sparse graph detected

Key Metrics:
  Items: 31
  Bonds: 4
  Complexity: 383 bytes
  Hubness: 50.0%
  Duplicate Rate: 3.2%
  Entropy Ratio: 100.0%
```

---

### Eval dashboard (demo_architecture)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture eval:dashboard
```

**Output**

```
FIELD-KIT EVALUATION REPORT

Test Case                          MRR@K  Recall@K  ECR    TRI    Scales
------------------------------------------------------------------------------
q_golden_flow_v1                  1.000  1.000     1.000  0.117  local
m_no_suggestions_expected         0.000  0.000     0.000  0.000  -
q_synthetic_field_overview        1.000  1.000     1.000  0.112  local
q_synthetic_strict_intent         1.000  1.000     1.000  0.120  local
q_governance_metrics_v1           1.000  1.000     1.000  0.151  local
q_graph_propagation_v1            1.000  1.000     1.000  0.126  local
q_multiscale_evidence_v1          1.000  1.000     1.000  0.111  local
q_synthetic_top1_only             1.000  1.000     1.000  0.200  local
q_requires_mid_scale_v1           1.000  1.000     1.000  0.181  local,mid
q_strict_accept_only_v2           1.000  1.000     1.000  0.117  local

Aggregate:
  Avg MRR@K: 1.0000
  Avg Recall@K: 1.0000
  Avg ECR: 1.0000
  Avg TRI: 0.1371
  Avg Scales: 1.11 (local,mid)
```

---

### Regression stayed green

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture eval:regression
```

**Output (summary)**

```
Total checks: 50
Passed: 50
Failed: 0
REGRESSION SUITE PASSED
```

---

## What changed / what it proves

* Field actions mutate the graph and produce new items (M outputs from bonds).
* Suggestions remain evidence-grounded with multi-scale citations (local + mid visible).
* Governance metrics update as the Field grows and recommend a safe action (suggest-only).
* Evaluation + regression stay green while the system evolves.

## What I’ll do next

* Fellowship packaging: `docs/fellowship/ONE_PAGER.md` + `docs/fellowship/RESULTS.md`.
* Tighten eval cases so MRR/Recall can actually move (more selective acceptable target sets).