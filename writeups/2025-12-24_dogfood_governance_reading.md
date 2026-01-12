# Dogfood Governance Reading — 2025-12-24

First thermodynamic reading of a real dataset using S06 governance.

## Command
```bash
python3 src/cli.py --data-dir prototype/data_dogfood govern:report
```

## Output
```
============================================================
GOVERNANCE REPORT
============================================================

Timestamp: 2025-12-24T06:53:27.664328Z
Data Dir: prototype/data_dogfood

--- Recommended Action ---
  Action: BRANCH
  Confidence: 60%
  Rationale: Consider branching: Low bond ratio (0.07); Sparse graph detected.

--- Supporting Observations ---
  - High hubness (75.0%)
  - Soup state detected
  - High orphan rate (86.7%)
  - Low bond ratio (0.07)
  - Sparse graph detected
  - Bundle suggested but only 2 bonds (need 3)

--- Key Metrics ---
  Items: 30
  Bonds: 2
  Complexity: 390 bytes
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

## Interpretation

The dogfood dataset shows a classic "content dump without structure" state:

| Metric | Value | Meaning |
|--------|-------|---------|
| Items | 30 | Substantial content |
| Bonds | 2 | Almost no structure |
| Orphan Rate | 86.7% | Most items disconnected |
| Bond Ratio | 0.07 | Far below healthy 0.2+ |
| Hubness | 75% | The few bonds hit same nodes |

**Diagnosis:** This is an early-stage Field where content was imported but connections haven't been made yet. The high hubness with high orphan rate is a signature pattern: "few connections, all to the same hub."

**Recommended Action:** BRANCH (explore, create connections)

This is the correct prescription. The Field needs more navigation paths, not consolidation or pruning.

## Notes

- First real-world governance reading validates S06 implementation
- "Soup detected" + "Sparse graph detected" can coexist (hub-dominated sparse graph)
- Duplicate rate 0% suggests good content hygiene
- Entropy ratio 100% means suggestion intents are well-distributed

---

*Logged as part of S06 completion.*
