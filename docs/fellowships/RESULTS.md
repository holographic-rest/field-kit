
# Field-Kit — RESULTS (Draft)

**Date:** 2025-12-24
**Purpose:** Fellowship-ready evidence of stability, grounding, multi-scale context, governance, and local durability.

---

## Dataset A — Golden Flow Baseline

**Data dir:** `prototype/data_tomorrow_golden`
**What it represents:** Fresh, minimal end-to-end run proving stability and invariants.

### 1) Golden flow (stability)

* Golden flow completed successfully.
* Credits invariant held (final balance = 73).
* Canonical event ordering held (bond run → executed; holologue run → completed; etc.).

### 2) Regression suite

```text
Total checks: 40
Passed: 40
Failed: 0
REGRESSION SUITE PASSED
```

### 3) Eval dashboard snapshot

Key facts:

* Core eval metrics stayed green (MRR/Recall at ceiling for current cases).
* Evidence coverage is present (ECR = 1.0 for active suggestion cases).

### 4) Governance snapshot

Key facts:

* Action recommended: CONTINUE (small dataset / early stage)
* Observations are informational (no contradictory alarm phrasing)

---

## Dataset B — Architecture Demo Corpus

**Data dir:** `prototype/data_demo_architecture`
**What it represents:** A realistic demo dataset built from 27 architecture pages plus seeded bonds to produce multi-scale and graph-aware behavior.

### Dataset stats

* Items: 30+ (architecture pages + bond outputs)
* Bonds: 3+ (seeded and executed)
* Events: ~99+
* Size: ~112 KB

### 1) Evidence-grounded suggestions (money shot)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture suggestions:show it_3B424DED62C74E7BA93935E7
```

**What it shows**

* Suggestions have probabilities (ranked distribution).
* Evidence shards cite exact spans and show multi-scale provenance:

  * `[local@0]` (current item)
  * `[mid@-N]` (prior context)
  * `[far@-N]` (distant context)
* Graph distance shown as `[d=N]` (graph-aware reranking).

### 2) Evaluation dashboard (with discriminative test cases)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture eval:dashboard
```

**Highlights**

* `q_strict_accept_only_v2` added (only “clarify” acceptable).
* `q_requires_mid_scale_v1` added (must include mid evidence).
* Dashboard shows multi-scale evidence present for `q_requires_mid_scale_v1` (e.g., `far,local,mid`).

### 3) Regression suite (stability under iteration)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture eval:regression
```

**Result (summary)**

```text
Total checks: 50
Passed: 50
Failed: 0
REGRESSION SUITE PASSED
```

### 4) Governance report (system health / anti-rot)

**Command**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture govern:report
```

**What it shows**

* Governance recommends an action (often BRANCH on sparse graphs) with rationale.
* The system reports key drift indicators (orphan rate, hubness, complexity) without auto-executing destructive actions.

### 5) Backup + verification (local-first durability)

**Commands**

```bash
python3 src/cli.py --data-dir prototype/data_demo_architecture backup:create --output prototype/outputs/demo_backup.tar
python3 src/cli.py backup:verify prototype/outputs/demo_backup.tar
```

**What it proves**

* Portable dataset export exists.
* Backup includes manifest + SHA-256 hashes for integrity verification.

---

## Summary of measurable outcomes

* **Stability:** golden flow remains green across iterative development.
* **Grounding:** evidence coverage moved from 0% → 100% for suggestions once evidence shards were implemented.
* **Multi-scale:** demo dataset shows local + mid + far evidence provenance in CLI output and test cases.
* **Graph awareness:** graph distance and reranking are visible (`[d=N]`) and tested.
* **Governance:** complexity/hubness/orphan signals drive a suggest-only recommendation policy.
* **Durability:** opt-in SQLite store + migration exists; backup/restore with verification exists.

---

## Notes / Next tightening step

MRR/Recall are still near ceiling in several cases because the acceptable target sets are permissive. Next evaluation work: add stricter “acceptable targets” definitions so ranking improvements can move metrics meaningfully.