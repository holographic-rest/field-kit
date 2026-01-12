# Test Case Schema

**Sprint:** S02 (Observability & Evaluation Harness)
**Version:** v0.1

---

## Overview

Test cases define evaluation scenarios for the Field-Kit hololink suggestion system.
Each test case specifies:
- How to construct the evaluation state
- Which item to request suggestions for
- What counts as an acceptable suggestion

---

## JSON Schema

```json
{
  "name": "string (unique identifier)",
  "description": "string (human-readable description)",
  "qdpi_stage": "Q | M | D | H",
  "seed": {
    "type": "golden_flow | data_dir | synthetic",
    "data_dir": "optional: path to data directory",
    "setup_steps": "optional: list of setup commands"
  },
  "subject_item_id": "string (item ID to get suggestions for) OR 'dynamic:N' for Nth created item",
  "k": 4,
  "acceptable_targets": {
    "type": "suggestion_indices | intent_types | item_ids",
    "values": ["list of acceptable values"]
  },
  "expected_evidence": {
    "min_with_evidence": 0,
    "notes": "optional: notes about evidence expectations"
  },
  "notes": "optional: additional context"
}
```

---

## Field Definitions

### `name`
Unique identifier for the test case. Convention: `{stage}_{description}_{version}`.
Example: `q_golden_flow_v1`, `m_preface_items_v1`

### `description`
Human-readable description of what the test case evaluates.

### `qdpi_stage`
The QDPI stage being evaluated:
- `Q` - Queue stage (item discovery, initial suggestions)
- `M` - Monologue stage (single-item exploration)
- `D` - Dialogue stage (multi-item comparison)
- `H` - Holologue stage (synthesis artifacts)

### `seed`
How to construct the evaluation state:

| Type | Description |
|------|-------------|
| `golden_flow` | Run golden flow to create fresh data |
| `data_dir` | Use existing data from specified directory |
| `synthetic` | Create items programmatically (via setup_steps) |

### `subject_item_id`
The item ID to request suggestions for.
- Exact ID: `"it_ABC123..."`
- Dynamic: `"dynamic:N"` means the Nth item created during setup (0-indexed)

### `k`
Number of suggestions to evaluate (default: 4).

### `acceptable_targets`
What counts as an acceptable suggestion:

| Type | Description | Example |
|------|-------------|---------|
| `suggestion_indices` | Any of these suggestion positions (1-indexed) | `[1, 2, 3, 4]` |
| `intent_types` | Suggestions with these intent types | `["explore", "compare"]` |
| `item_ids` | Suggestions targeting these items | `["it_A", "it_B"]` |

For binary relevance evaluation:
- Acceptable = relevant (score 1)
- Not acceptable = irrelevant (score 0)

### `expected_evidence`
Evidence grounding expectations:
- `min_with_evidence`: Minimum suggestions that should have evidence (0 for current system)
- Currently the system does not produce evidence shards, so this is typically 0.

### `notes`
Additional context about the test case, known limitations, etc.

---

## Example Test Cases

### Golden Flow (Q stage)

```json
{
  "name": "q_golden_flow_v1",
  "description": "Queue-stage suggestions after golden flow creates 2 items",
  "qdpi_stage": "Q",
  "seed": {
    "type": "golden_flow"
  },
  "subject_item_id": "dynamic:0",
  "k": 4,
  "acceptable_targets": {
    "type": "suggestion_indices",
    "values": [1, 2, 3, 4]
  },
  "expected_evidence": {
    "min_with_evidence": 0,
    "notes": "Current system does not produce evidence shards"
  },
  "notes": "Baseline golden flow test - all 4 suggestions should be acceptable"
}
```

### Preface Items (M stage)

```json
{
  "name": "m_preface_pair_v1",
  "description": "Monologue suggestions for preface items from Queue Lattice tests",
  "qdpi_stage": "M",
  "seed": {
    "type": "synthetic",
    "setup_steps": [
      "init",
      "item:create --title 'Found Text and The Author' --body '...'",
      "item:create --title 'The Curator and Scheherazade' --body '...'"
    ]
  },
  "subject_item_id": "dynamic:0",
  "k": 4,
  "acceptable_targets": {
    "type": "intent_types",
    "values": ["clarify", "concretize", "connect", "test"]
  },
  "expected_evidence": {
    "min_with_evidence": 0
  }
}
```

---

## Running Test Cases

Test cases are loaded and executed by `tests/eval_harness.py`:

```bash
# Run single test case
python3 tests/eval_harness.py --test-case tests/test_cases/golden_flow.json

# Run all test cases
python3 tests/eval_harness.py --all

# Run via CLI
python3 src/cli.py eval:regression --data-dir prototype/data
```

---

## Known Limitations (v0.1)

1. **No evidence shards**: The current system does not produce evidence shards as first-class objects.
   ECR (Evidence Coverage Rate) will report 0% until this is implemented.

2. **Suggestion format**: Suggestions are prompt texts, not target IDs. Acceptable targets
   are evaluated by suggestion index or intent type, not by target item ID.

3. **Dynamic IDs**: Golden flow creates new item IDs each run. Use `dynamic:N` syntax
   to reference items by creation order rather than exact ID.

4. **Single-stage evaluation**: Each test case evaluates one QDPI stage. Cross-stage
   evaluation (e.g., thread continuity) is planned for v0.2.
