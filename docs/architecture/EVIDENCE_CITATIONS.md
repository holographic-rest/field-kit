# Evidence Citations (S03/S04)

How Field-Kit produces and displays evidence for navigation suggestions.

**S04 Update**: Evidence shards now include multi-scale context via `dilation_offset`.

## Overview

Every suggestion now includes evidence shards that justify why the suggestion was made. This addresses the "handles not context" failure mode by showing the user what content drove the suggestion.

## Evidence Shard Structure

```python
@dataclass
class EvidenceShard:
    shard_id: str        # Stable, content-based ID (e.g., "sh_32FF33AE1166")
    source_type: str     # "item" | "bond" | "prompt_template"
    source_id: str       # ID of the source object
    text_span: str       # The quoted text (max ~300 chars)
    span_start: int      # Character offset in source (-1 if unknown)
    span_end: int        # Character offset end (-1 if unknown)
    scale: str           # "local" | "mid" | "far" (distance from subject)
    dilation_offset: int # S04: Event offset (0=local, negative=past events)
```

### Scale Definitions (S04)

| Scale | Dilation Offset | Meaning |
|-------|----------------|---------|
| local | 0 | Subject item itself |
| mid | -1 to -8 | Recent context (1-8 events back) |
| far | -16 and beyond | Distant context (16+ events back) |

## ID Generation

Shard IDs are stable and content-based:

```python
def generate_shard_id(source_id: str, text_span: str) -> str:
    content = f"{source_id}:{text_span[:100]}"
    hash_hex = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"sh_{hash_hex.upper()}"
```

This ensures the same evidence always gets the same ID.

## Evidence Sources

### v0.1: Handle-Based Evidence

Current implementation creates evidence from the handle quote:

```python
if handle:
    evidence = create_evidence_from_handle(item, handle)
    candidate.evidence_shards.append(evidence)
```

The handle is the anchor phrase extracted from the item that drives the suggestion.

### Future: Multi-Source Evidence

Planned evidence sources:
- **Item body spans**: Specific sentences that support the suggestion
- **Bond context**: Previous bond prompts that inform the suggestion
- **Graph neighbors**: Related items that justify the connection

## Span Location

Evidence shards include character offsets when available:

```python
full_text = title + "\n" + body
span_lower = text_span.lower()

if span_lower in full_text.lower():
    span_start = full_text.lower().index(span_lower)
    span_end = span_start + len(text_span)
else:
    span_start = -1
    span_end = -1
```

Offsets of -1 indicate the span wasn't found (acceptable in v0.1).

## Display Format

### CLI Output

```
Suggestions presented for item it_...:
  (scales: local, mid)
  1. [clarify] (25%) What would falsify "My First Field Item"?
     WHY:
     [local@0] "My First Field Item"
     [mid@-4] "related context from event history"
```

### Event Log Format

```json
{
  "evidence_shards": [
    {
      "shard_id": "sh_32FF33AE1166",
      "source_type": "item",
      "source_id": "it_513DD49C...",
      "text_span": "My First Field Item",
      "span_start": 0,
      "span_end": 19,
      "scale": "local",
      "dilation_offset": 0
    },
    {
      "shard_id": "sh_A8B2C4D6E8F0",
      "source_type": "item",
      "source_id": "it_789ABC...",
      "text_span": "context from earlier event",
      "span_start": 42,
      "span_end": 68,
      "scale": "mid",
      "dilation_offset": -4
    }
  ]
}
```

## Measurement

### Evidence Coverage Rate (ECR)

```python
# In eval harness
evidence_shards = sug.get("evidence_shards", [])
has_evidence = len(evidence_shards) > 0
```

ECR = (suggestions with evidence) / (total suggestions)

### Anchor Resolution Rate (ARR)

```python
# Future metric
resolved = sum(1 for s in shards if s.span_start >= 0)
arr = resolved / total if total > 0 else None
```

ARR = (shards with valid offsets) / (total shards)

## Best Practices

### Creating Evidence

1. Always include at least one evidence shard per suggestion
2. Use the handle quote as the primary evidence source
3. Set span offsets to -1 if you can't locate the text
4. Keep text_span under 300 characters

### Consuming Evidence

1. Check `evidence_shards` is non-empty before displaying
2. Display at most 2 shards to avoid clutter
3. Truncate text_span for display (50 chars is usually enough)
4. Show source_type if multiple source types exist

## W3C Web Annotation Alignment

The evidence shard structure aligns with W3C Web Annotation patterns:

| EvidenceShard field | W3C Equivalent |
|---------------------|----------------|
| text_span | TextQuoteSelector.exact |
| span_start/end | TextPositionSelector.start/end |
| source_id | Target.source |
| shard_id | Annotation.id |

This enables future interoperability with annotation tools.

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/candidate_set.py` | EvidenceShard dataclass |
| `src/fieldkit/suggestion_engine.py` | Evidence creation |
| `src/fieldkit/dilated_context.py` | S04: Multi-scale context sampling |
| `tests/eval_harness.py` | ECR and scale coverage measurement |

## References

- W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
- Research: `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md`
