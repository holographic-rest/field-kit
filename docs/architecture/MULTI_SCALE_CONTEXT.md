# Multi-Scale Context Aggregation (S04)

How Field-Kit samples context at multiple temporal scales using dilated offsets.

## Overview

Evidence shards can now be sourced from different temporal scales in the event history. This provides richer context for navigation suggestions while maintaining local resolution.

## Key Insight

From research:
> "Dilated convolutions in CNNs sample pixels at exponentially increasing distances... The same principle applies to temporal sequences: sample events at offsets -1, -2, -4, -8, -16, -32 to cover more history without losing local detail."

## Dilation Schedule

```python
DILATION_OFFSETS = [-1, -2, -4, -8, -16, -32]
```

Each offset represents how many events back in history to sample from. The exponential spacing ensures:
- Dense coverage of recent events (local context)
- Sparse but wide coverage of older events (far context)

## Scale Definitions

| Scale | Offset Range | Description |
|-------|-------------|-------------|
| local | 0 | The subject item itself |
| mid | -1 to -8 | Recent context (1-8 events back) |
| far | -16+ | Distant context (16+ events back) |

## Architecture

### DilatedContextSampler

```python
class DilatedContextSampler:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.dilation_offsets = DILATION_OFFSETS

    def sample(self, subject_item_id: str) -> ContextPack:
        # 1. Find subject item's position in event history
        # 2. Sample items at each dilation offset
        # 3. Categorize by scale (local/mid/far)
        # 4. Return ContextPack with items at each scale
```

### ContextPack

```python
@dataclass
class ContextPack:
    local_items: List[ContextItem]  # offset 0
    mid_items: List[ContextItem]    # offsets -1 to -8
    far_items: List[ContextItem]    # offsets -16+
```

### ContextItem

```python
@dataclass
class ContextItem:
    item_id: str
    title: str
    body: Optional[str]
    scale: str           # "local" | "mid" | "far"
    dilation_offset: int # The event offset (e.g., -4)
```

## Integration

### Suggestion Engine

The suggestion engine now accepts a `data_dir` parameter:

```python
result = generate_bond_suggestions_with_evidence(
    item,
    data_dir=str(self.store.data_dir)  # S04
)
```

When provided, it samples multi-scale context and attempts to add evidence from mid/far items.

### Evidence Creation

```python
def _add_multiscale_evidence(candidate, context_pack, handle):
    keywords = handle.anchor_phrase.lower().split()

    # Search mid items for matching text
    for ctx_item in context_pack.mid_items:
        match = find_matching_text_in_item(ctx_item, keywords)
        if match:
            shard = EvidenceShard(
                source_id=ctx_item.item_id,
                text_span=match[0],
                scale="mid",
                dilation_offset=ctx_item.dilation_offset,
            )
            candidate.evidence_shards.append(shard)
```

## Metrics

### Scale Coverage

The eval harness tracks:

```python
@dataclass
class MetricsResult:
    scale_count: int           # Number of distinct scales present
    scales_present: List[str]  # Which scales (e.g., ["local", "mid"])
```

### Report Output

```
Test Case                          MRR@K  Recall@K  ECR    TRI    Scales
------------------------------------------------------------------------------
q_golden_flow_v1                  1.000  1.000     1.000  0.122  local
q_multiscale_evidence_v1          1.000  1.000     1.000  0.142  local,mid
```

## Best-Effort Behavior

Multi-scale evidence is **best-effort**:

1. If no event history exists, only local scale is present
2. If no matching text is found in mid/far items, those scales are skipped
3. At minimum, local scale should always be present

## CLI Display

```
Suggestions presented for item it_...:
  (scales: local, mid)
  1. [clarify] (25%) What would falsify "My First Field Item"?
     WHY:
     [local@0] "My First Field Item"
     [mid@-4] "related context from earlier"
```

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/dilated_context.py` | DilatedContextSampler, ContextPack |
| `src/fieldkit/suggestion_engine.py` | Multi-scale evidence integration |
| `src/fieldkit/candidate_set.py` | EvidenceShard with dilation_offset |
| `tests/eval_harness.py` | Scale coverage metrics |

## References

- Research: `research/27-essays/12_multi_scale_context_aggregation_dilated_convolutions.md`
- Related: `docs/architecture/EVIDENCE_CITATIONS.md`
