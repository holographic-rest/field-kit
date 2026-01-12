# Graph Propagation (S05)

How Field-Kit uses MPNN-style message passing for graph-aware reranking.

## Overview

Graph propagation improves candidate ranking by using topological structure in the bond graph. Instead of scoring candidates purely on text similarity, we incorporate:
- Graph distance (closer nodes rank higher)
- Message passing (propagate neighbor information)
- Residual updates (combine new and original representations)

This addresses "handles not context" by ensuring context from graph neighbors influences suggestions.

## Key Insight

From research (MPNN paper):
> "Don't generate hololinks from text. Propagate context over the bond graph, then select."

After T rounds of message passing, a node's representation includes information from nodes up to T hops away.

## Architecture

### BondGraph

The bond graph is constructed from items and bonds:

```python
class BondGraph:
    nodes: Dict[str, NodeState]      # Items as nodes
    edges: List[Edge]                 # Bonds as edges
    adjacency: Dict[str, List[str]]   # Forward neighbors
    reverse_adjacency: Dict[str, List[str]]  # Backward neighbors
```

**Node features:**
- Type one-hot (Q, M, D, H)
- Title length (normalized)
- Body length (normalized)
- Has handles flag
- Recency score

**Edge structure:**
```python
Edge:
    source_id: str      # Input item
    target_id: str      # Output item
    bond_type: str      # Inferred from prompt
    weight: float       # Type-based weight
```

### Message Passing

Each round:
1. **Compute messages**: For each node, aggregate neighbor embeddings
2. **Update nodes**: Apply residual update

```python
def message_passing_step(graph, node_ids, T=2):
    for t in range(T):
        messages = compute_messages(graph, node_ids)
        updated = update_nodes(graph, node_ids, messages, residual_weight=0.5)
    return updated
```

**Message computation:**
```python
message[i] = mean(neighbor_embedding * recency_weight for neighbor in neighbors)
```

**Residual update:**
```python
new_embedding = 0.5 * original + 0.5 * message
```

### Graph Distance

BFS-based shortest path computation:

```python
def compute_graph_distance(source_id, target_id) -> int:
    # Returns:
    #   0 if same node
    #   N if N hops apart
    #   -1 if unreachable
```

Distance is used in scoring:
```python
if dist == -1:
    dist_score = 0.1      # Unreachable: low score
elif dist == 0:
    dist_score = 1.0      # Same node
else:
    dist_score = 1.0 / (1.0 + dist)  # Decay with distance
```

### GraphReranker

The reranker integrates graph features into candidate scoring:

```python
class GraphReranker:
    def rerank(self, subject_id, candidates, use_propagation=True):
        # 1. Run message passing (T=2 rounds)
        # 2. Compute graph distances
        # 3. Compute embedding similarities
        # 4. Blend scores: 0.7 * original + 0.3 * graph_score
        return reranked_candidates
```

**Graph score components:**
- 40% distance score (closer = better)
- 40% embedding similarity (after propagation)
- 20% neighborhood overlap (Jaccard of neighbor sets)

## Integration

### Suggestion Engine

The reranker is called after initial scoring:

```python
# In generate_bond_suggestions_with_evidence():
candidates = score_candidates(candidates)

# S05: Graph propagation reranking
if data_dir:
    reranker = GraphReranker(data_dir, propagation_rounds=2, graph_weight=0.3)
    candidates = reranker.rerank(item_id, candidates, use_propagation=True)

candidates = select_top_k(candidates, k=4, diversify=True)
```

### CLI Display

Graph distance is shown in suggestion output:

```
Suggestions presented for item it_...:
  1. [clarify] (25%) [d=1] Pin down the meaning of "..."
     [local@0] "handle text"
```

The `[d=1]` indicates 1-hop distance from subject.

## Metrics

The eval harness tracks:

```python
@dataclass
class MetricsResult:
    has_graph_distance: bool      # Any candidate has distance set
    avg_graph_distance: float     # Average distance (if available)
```

## Disambiguation

Graph distance helps resolve Q/QQ/QQQ ambiguity:
- If multiple items have similar text, prefer the one closer in the graph
- Items in the same "cluster" (connected subgraph) are more relevant
- Disconnected items get lower scores

## Best-Effort Behavior

Graph propagation is **best-effort**:
1. If no bonds exist, only local features are used
2. If items are disconnected, distance is -1 (low score)
3. The system never crashes if graph is empty

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/graph_propagation.py` | BondGraph, message passing, GraphReranker |
| `src/fieldkit/suggestion_engine.py` | Reranker integration |
| `src/fieldkit/pointer_scorer.py` | Graph distance in heuristic scoring |
| `tests/eval_harness.py` | Graph distance metrics |

## Future Work

1. **Learned message functions**: Train gθ on click data
2. **Edge type embeddings**: Use bond type more explicitly
3. **Multi-hop attention**: Attention over message passing rounds
4. **Incremental updates**: Only propagate in local neighborhood

## References

- Research: `research/27-essays/13_neural_message_passing_quantum_chemistry.md`
- Research: `research/27-essays/17_simple_NN_module_relational_reasoning.md`
- Related: `docs/architecture/POINTER_NAVIGATION.md`
