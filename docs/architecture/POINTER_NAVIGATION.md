# Pointer-Based Navigation (S03)

Technical architecture for pointer-style navigation in Field-Kit.

## Overview

Sprint S03 replaced "generate link text" with "select pointer to object + cite evidence spans". Instead of generating navigation text, the system:

1. Produces a candidate set of navigation targets
2. Scores each candidate using attention-like mechanisms
3. Attaches evidence shards that justify each suggestion
4. Returns a probability distribution over candidates

## Key Concepts

### Pointer Networks Insight

From the research (see `research/27-essays/07_pointer_networks.md`):

> The output is a pointer to one of the input elements, rather than generated text.

This means:
- Suggestions point to existing content/structures
- No hallucination of navigation targets
- Each suggestion is grounded in source material

### Evidence Bundles

From the research (see `research/12-23-2025-research/grounding_nav/`):

Every navigation decision is backed by an evidence bundle containing:
- **EvidenceShard**: A text span from the source item
- **TextQuoteSelector**: The exact quote with context
- **Position Info**: Character offsets in the source

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Suggestion Request                        │
│                   (item_id, context)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              generate_bond_suggestions_with_evidence         │
│                   (suggestion_engine.py)                     │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Generate Base   │ │ Build Candidate │ │ Attach Evidence │
│ Suggestions     │ │ Objects         │ │ Shards          │
│                 │ │                 │ │                 │
│ (LLM/template)  │ │ (candidate_set) │ │ (from handles)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    score_candidates                          │
│                   (pointer_scorer.py)                        │
│                                                              │
│   - Heuristic scoring (evidence, handle quality)            │
│   - Softmax to probabilities                                │
│   - Diversified top-k selection                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Structured Output                         │
│                                                              │
│   suggestions: [{                                           │
│     intent, handle_quote, prompt_text,                      │
│     evidence_shards: [{shard_id, text_span, offsets}],      │
│     candidate_id, probability, score, rank                  │
│   }]                                                        │
└─────────────────────────────────────────────────────────────┘
```

## Data Structures

### Candidate

```python
@dataclass
class Candidate:
    candidate_id: str           # Stable ID
    target_type: str            # "item" | "suggestion"
    target_id: Optional[str]    # ID of target object
    title: str                  # Display title
    summary: str                # Full prompt text
    evidence_shards: List[EvidenceShard]
    score: float               # Quality score (0-1)
    probability: float         # Selection probability
    rank: int                  # Position in list
    intent_type: str           # clarify | concretize | connect | test
    handle_quote: str          # Handle driving this suggestion
```

### EvidenceShard

```python
@dataclass
class EvidenceShard:
    shard_id: str        # Stable ID
    source_type: str     # "item" | "bond" | "prompt_template"
    source_id: str       # ID of source
    text_span: str       # Quoted text (max ~300 chars)
    span_start: int      # Character offset (-1 if unknown)
    span_end: int        # Character offset end
    scale: str           # "local" | "mid" | "far"
```

## Scoring

### Heuristic Scoring (v0.1)

Current scoring uses these factors:
- **Evidence presence**: +0.15 for having evidence shards
- **Handle quality**: +0.05 to +0.10 for multi-word handles
- **Source quality**: +0.10 for LLM-generated, +0.05 for heuristic

### Probability Distribution

Scores are converted to probabilities using softmax:

```python
probability = exp(score) / sum(exp(scores))
```

This produces a proper distribution over candidates.

### S05: Graph Propagation Reranking

After initial scoring, candidates are reranked using graph features:

```python
# In suggestion_engine.py
reranker = GraphReranker(data_dir, propagation_rounds=2, graph_weight=0.3)
candidates = reranker.rerank(item_id, candidates, use_propagation=True)
```

Graph-based scoring components:
- **Graph distance**: Closer nodes rank higher (BFS shortest path)
- **Embedding similarity**: After message passing propagation
- **Neighborhood overlap**: Jaccard similarity of neighbor sets

Final score blends original (70%) and graph (30%) scores.

See `docs/architecture/GRAPH_PROPAGATION.md` for details.

### S07: State Conditioning

Session state influences evidence selection:

```python
# In suggestion_engine.py
result = generate_bond_suggestions_with_evidence(
    item,
    data_dir=data_dir,
    session_state=state,  # S07: pass session state
)
```

State-based influence:
- **Keywords from entities**: Prior entities bias evidence selection
- **Open questions**: Unresolved intents influence which evidence is prioritized
- **state_utilized**: Output field indicates if state had influence

When `session_state=None`, behavior is identical to pre-S07.

See `docs/architecture/SESSION_STATE.md` for details.

### S08: Batched Processing

Multiple suggestion requests can now be processed in batches for improved throughput:

```python
from fieldkit.hololink_pipeline import batch_suggest, batch_suggest_with_metrics

requests = [
    {"item_a": item1, "item_b": item2},
    {"item_a": item3, "item_b": item4},
]

# Process in batches
results = batch_suggest(requests, batch_size=5)

# With metrics
results, metrics = batch_suggest_with_metrics(requests, batch_size=5)
```

Batching benefits:
- **Identity-safe**: When batch_size=1, behavior identical to serial processing
- **Throughput**: 5-12% improvement in local scenarios, more with I/O
- **Metrics**: Track throughput, latency, and batch efficiency

See `docs/architecture/PIPELINE_BATCHING.md` for details.

### Future: Learned Scoring

When embeddings/click data available:
- Cosine similarity between subject and candidate embeddings
- Attention-like scoring as in Transformer decoder
- Trained message functions for graph propagation

## QDPI Events

### hololink.candidates_generated

Logged when candidates are produced:

```json
{
  "name": "hololink.candidates_generated",
  "refs": {
    "subject_item_id": "it_...",
    "candidate_ids": ["cd_...", "cd_...", ...],
    "has_evidence_count": 4,
    "total_candidates": 4
  }
}
```

### hololink.pointer_selected

Logged when user selects a candidate:

```json
{
  "name": "hololink.pointer_selected",
  "refs": {
    "subject_item_id": "it_...",
    "chosen_candidate_id": "cd_...",
    "probability": 0.25,
    "top_evidence_shard_ids": ["sh_...", "sh_..."]
  }
}
```

## CLI Output

Suggestions now show probabilities and evidence:

```
Suggestions presented for item it_...:
  1. [clarify] (25%) What would falsify "My First Field Item"?
     WHY: "My First Field Item"
  2. [concretize] (24%) Make "Item" tangible...
     WHY: "Item"
```

## Metrics

### Evidence Coverage Rate (ECR)

The key metric from S03:
- ECR = % of suggestions with at least one evidence shard
- Before S03: ECR = 0%
- After S03: ECR = 100%

### Measurement

ECR is computed in the eval harness:

```python
with_evidence = sum(1 for s in suggestions if s.has_evidence)
ecr = with_evidence / len(suggestions)
```

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/candidate_set.py` | Candidate and EvidenceShard dataclasses |
| `src/fieldkit/pointer_scorer.py` | Scoring and probability computation |
| `src/fieldkit/suggestion_engine.py` | Integration with evidence generation |
| `src/fieldkit/qdpi.py` | New event logging methods |
| `src/fieldkit/schemas.py` | Event name registration |

## References

- Sprint: `sprints/12-23-2025-to-01-04-2026/S03_pointer_based_navigation.md`
- Research: `research/27-essays/07_pointer_networks.md`
- Research: `research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation_and_durable_anchoring.md`
