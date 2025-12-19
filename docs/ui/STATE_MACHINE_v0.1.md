# Field-Kit UI State Machine v0.1

## States

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI STATES                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   IDLE                    No items, composer empty               │
│     │                                                            │
│     ▼                                                            │
│   COMPOSING               User typing in composer                │
│     │                                                            │
│     ▼ [Enter]                                                    │
│   ITEM_CREATED            Q Item saved, suggestions loading      │
│     │                                                            │
│     ▼                                                            │
│   SUGGESTIONS_SHOWN       4 suggestions displayed under item     │
│     │                                                            │
│     ├──[click suggestion]──▶ BOND_READY (draft Bond created)    │
│     │                                                            │
│     └──[type custom prompt]──▶ BOND_AUTHORING                   │
│                                    │                             │
│                                    ▼ [Enter]                     │
│                               BOND_READY (draft Bond, D type)    │
│                                    │                             │
│   BOND_READY ◀─────────────────────┘                            │
│     │                                                            │
│     ▼ [Run Bond]                                                 │
│   EXECUTING               Ephemeral run card, AI working         │
│     │                                                            │
│     ├──[success]──▶ OUTPUT_CREATED (M or D Item saved)          │
│     │                                                            │
│     └──[failure]──▶ EXECUTION_FAILED (error shown)              │
│                                                                  │
│   OUTPUT_CREATED          New Item in list, suggestions shown    │
│     │                                                            │
│     └──▶ SUGGESTIONS_SHOWN (cycle continues)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Multi-Select Path (Holologue)

```
┌─────────────────────────────────────────────────────────────────┐
│                     MULTI-SELECT STATES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SUGGESTIONS_SHOWN (or any state with items)                   │
│     │                                                            │
│     ▼ [Shift/Cmd + click 2+ items]                              │
│   MULTI_SELECTED          Holologue bar appears                  │
│     │                                                            │
│     ▼ [Run Holologue]                                           │
│   HOLO_MODAL              Kind selector shown                    │
│     │                                                            │
│     ▼ [Select kind + confirm]                                   │
│   EXECUTING               Ephemeral run card                     │
│     │                                                            │
│     └──▶ OUTPUT_CREATED (H Item saved)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## State Definitions

| State | UI Elements | User Actions Available |
|-------|-------------|------------------------|
| `IDLE` | Empty composer | Type to enter COMPOSING |
| `COMPOSING` | Composer with text | Enter → create Item |
| `ITEM_CREATED` | New Item card, loading spinner | Wait |
| `SUGGESTIONS_SHOWN` | Item + 4 suggestion chips | Click suggestion, type custom, multi-select |
| `BOND_AUTHORING` | Custom prompt input visible | Type prompt, Enter to confirm |
| `BOND_READY` | Draft Bond indicator, "Run Bond" button | Click Run Bond |
| `EXECUTING` | Ephemeral run card with shimmer | Wait |
| `OUTPUT_CREATED` | New output Item in list | Continue workflow |
| `EXECUTION_FAILED` | Error message | Retry or dismiss |
| `MULTI_SELECTED` | Selection indicators, Holologue bar | Run Holologue, deselect |
| `HOLO_MODAL` | Kind selector modal | Select kind, confirm |

## Transitions

| From | Event | To | Side Effect |
|------|-------|-----|-------------|
| IDLE | user types | COMPOSING | — |
| COMPOSING | Enter | ITEM_CREATED | `item.created` event, Q Item saved |
| ITEM_CREATED | suggestions loaded | SUGGESTIONS_SHOWN | `bond.suggestions.presented` event |
| SUGGESTIONS_SHOWN | click suggestion | BOND_READY | `bond.draft_created` event |
| SUGGESTIONS_SHOWN | type custom | BOND_AUTHORING | — |
| BOND_AUTHORING | Enter | BOND_READY | `bond.draft_created` event |
| BOND_READY | Run Bond | EXECUTING | `bond.run_requested` event |
| EXECUTING | success | OUTPUT_CREATED | `bond.executed` event, M/D/H Item saved |
| EXECUTING | failure | EXECUTION_FAILED | `bond.execution_failed` event |
| any | Shift+click 2+ | MULTI_SELECTED | — |
| MULTI_SELECTED | Run Holologue | HOLO_MODAL | — |
| HOLO_MODAL | confirm | EXECUTING | `holologue.run_requested` event |

## Invariants

1. **ITEM_CREATED never triggers AI.** It only stores the Q Item.
2. **BOND_READY requires explicit Run.** The Bond exists as draft (output_item_id=null).
3. **EXECUTING is the only state that calls AI.** Credits deducted here.
4. **Suggestions are events-only.** They become Bonds only when clicked.
5. **Output type is determined by Bond origin:**
   - Suggestion → M
   - Custom prompt → D
   - Holologue → H

## UI Components by State

```
┌────────────────────────────────────────────────────────────┐
│ Header                                      [Credits: 100] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Item List                                            │  │
│  │                                                      │  │
│  │  [Q] User's first item                               │  │
│  │      ├─ [suggestion 1] [suggestion 2]                │  │
│  │      └─ [suggestion 3] [suggestion 4]                │  │
│  │                                                      │  │
│  │  [M] AI-generated monologue                          │  │
│  │      └─ (suggestions for this item...)               │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Bond Panel (when BOND_READY)                         │  │
│  │   Draft Bond: "Expand into checklist"                │  │
│  │   Input: [Q] User's first item                       │  │
│  │   Output type: M                                     │  │
│  │                              [Run Bond]              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Composer                                             │  │
│  │   [Create anything...]                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Forbidden Transitions

These transitions violate the ontology:

| From | Event | Why Forbidden |
|------|-------|---------------|
| COMPOSING | Enter | → directly to EXECUTING | Skips Item creation and Bond draft |
| SUGGESTIONS_SHOWN | click | → directly to EXECUTING | Skips Bond draft state |
| ITEM_CREATED | auto | → EXECUTING | Items never auto-execute |
| any | dropdown select type | Type is derived from Bond, not chosen |
