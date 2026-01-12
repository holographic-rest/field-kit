# Session State (S07)

How Field-Kit maintains continuity across navigation steps using RMC-style multi-slot memory.

## Overview

Session State implements the Relational Memory Core (RMC) pattern: multiple memory slots that interact via attention weights. This fixes "loses the thread" by maintaining structured memory across user actions.

The key insight from research:

> "Don't store your session/world state as one vector. Store it as **K slots**, and let the slots **talk to each other** every step via attention."

## Why It Matters

Without session state, suggestions are generated purely from the current item. This leads to:
- "Handles not context" - suggestions based on surface text, not thread
- Loss of continuity - system "forgets" what user is working on
- No accumulation - each step is independent

With session state:
- Suggestions consider entities from previous steps
- Open questions persist and influence future suggestions
- Evidence accumulates and influences selection
- The "thread" is maintained across navigation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Action                               │
│        (navigate, select suggestion, execute bond)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SessionState                              │
│                  (session_state.py)                          │
│                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ active_page │  │ user_intent │  │   entities  │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │open_questions│  │recent_evidence│ │vault_anchors│        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   slot_attention()                           │
│                                                              │
│   Computes weights: pinned > recent > non-empty             │
│   Returns normalized weights summing to 1.0                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Suggestion Generation                           │
│            (suggestion_engine.py)                            │
│                                                              │
│   Keywords from state bias evidence selection               │
│   state_utilized: true if state influenced results          │
└─────────────────────────────────────────────────────────────┘
```

## The 6 Memory Slots

| Slot | Purpose | Updates From |
|------|---------|--------------|
| **active_page** | Current item being viewed | Navigate to item |
| **user_intent** | What user is trying to do | Chosen suggestion, bond execution |
| **entities** | Accumulated entity mentions | Handles from items |
| **open_questions** | Unresolved clarify/test intents | Suggestions presented |
| **recent_evidence** | Recent evidence shards | Suggestions with evidence |
| **vault_anchors** | Curated/pinned items | Load from curated list |

### MemorySlot Structure

```python
@dataclass
class MemorySlot:
    slot_id: str           # "active_page", "entities", etc.
    content: Dict[str, Any]  # JSON-ish content
    recency: float         # Step counter when updated
    is_pinned: bool        # Pinned slots get higher attention
    embedding: Optional[List[float]]  # Reserved for future
```

## Slot-to-Slot Attention

Attention weights determine how much each slot influences suggestions.

### Heuristic Weighting

```python
weight = 0.0
if not slot.is_empty():
    weight += 1.0           # Non-empty bonus
if slot.is_pinned:
    weight += 2.0           # Pinned bonus
weight += (recency / max_recency) * 1.0  # Recency bonus
```

Weights are normalized to sum to 1.0.

### Why Heuristic First

From the RMC paper insight:

> "You can start with heuristic attention, then swap for learned weights later."

This gives us the structural benefit (multi-slot interaction) without requiring training data.

## Update Functions

### update_from_action()

Primary update after user actions:

```python
state = update_from_action(
    state,
    subject_item={"id": "it_001", "title": "My Item"},
    suggestions=[...],
    evidence_shards=[...],
    chosen_intent="clarify",
)
```

Updates:
- `active_page` from subject_item
- `entities` from handles (accumulated)
- `open_questions` from clarify/test suggestions
- `recent_evidence` from evidence shards
- `user_intent` from chosen_intent

### update_from_event()

Update from QDPI events:

```python
state = update_from_event(state, event)
```

Handles:
- `item.created` → active_page
- `bond.suggestions.presented` → open_questions
- `bond.executed` → user_intent
- `holologue.completed` → user_intent

## State Influence on Suggestions

### Keyword Extraction

```python
from fieldkit.session_state import get_state_influence_keywords

keywords = get_state_influence_keywords(state)
# Returns set of keywords from entities, open_questions, recent_evidence
```

### Integration with Suggestion Engine

```python
result = generate_bond_suggestions_with_evidence(
    item,
    data_dir=data_dir,
    session_state=state,  # S07: pass state
)

print(result["state_utilized"])  # True if state influenced results
```

When `session_state` is provided:
1. Keywords are extracted from state
2. Keywords bias multi-scale evidence selection
3. `state_utilized` indicates if state had influence

**Identity behavior**: When `session_state=None`, behavior is identical to pre-S07.

## Research Lineage

### RMC (Essay #19)

> "Multiple memory slots interact via multi-head dot-product attention."

We implement this as K=6 slots with heuristic attention.

### LSTM (Essay #4)

> "Gating (forget/input/output) for memory governance."

Our slot updates implement implicit gating:
- **Input gate**: What gets written to slots
- **Forget gate**: Bounded accumulation (max 5 questions, max 10 entities)
- **Output gate**: Attention weights determine what influences output

### NTM (Essay #21)

> "External memory with explicit read/write heads."

Session state is external memory with:
- **Read head**: get_state_influence_keywords extracts from slots
- **Write head**: update_from_action writes to specific slots

## Future: Learned Attention

The current heuristic attention can be replaced with learned weights:

1. **Log slot states**: Track which slots were active when user selected suggestions
2. **Train attention**: Learn slot→slot attention weights from selection data
3. **Swap in**: Replace `slot_attention()` with trained module

This is the RMC upgrade path.

## Files

| File | Purpose |
|------|---------|
| `src/fieldkit/session_state.py` | MemorySlot, SessionState, slot_attention |
| `src/fieldkit/suggestion_engine.py` | Integration point (session_state param) |
| `tests/test_session_state.py` | Unit tests (26 tests) |

## Metrics

### state_utilized (S07)

New metric in suggestion output:

```python
{
    "suggestions": [...],
    "state_utilized": True,  # State had keywords that influenced selection
}
```

This allows tracking how often state influences suggestions without requiring A/B eval.

## References

- Sprint: `sprints/12-23-2025-to-01-04-2026/S07_session_state.md`
- Research: `research/27-essays/19_relational_RNNs.md` (RMC)
- Research: `research/27-essays/04_understanding_LSTM_networks.md` (Gating)
- Research: `research/27-essays/21_neural_turing_machines.md` (External memory)
- Related: `docs/architecture/POINTER_NAVIGATION.md`
