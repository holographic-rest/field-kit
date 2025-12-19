# Sprint: UI Ontology Fix Plan v0.1

## Problem Statement

The current UI collapses three distinct operations:
1. Creating an Item
2. Creating a Bond
3. Executing a Bond

This makes the UI feel like "chat software" where typing = immediate AI response.

## Current Violations

| Issue | Location | Current Behavior | Correct Behavior |
|-------|----------|------------------|------------------|
| 1 | `handleComposerSubmit()` | If items exist, typing runs a bond immediately | Typing always creates Items; Bonds are created separately |
| 2 | `runSuggestionOneClick()` | Clicking suggestion runs bond immediately | Clicking suggestion creates draft bond; explicit "Run Bond" required |
| 3 | Operator drawer | Has M/D radio buttons for user to choose | Output type derived from Bond origin (suggestion=M, custom=D) |
| 4 | Composer placeholder | "Create anything" is ambiguous | Should clearly say "Create Item" |

## Implementation Checklist

### Phase 1: Separate Item Creation from Bond Creation

- [ ] **1.1** Modify `handleComposerSubmit()` to ALWAYS create Q Items
  - Remove the `if (state.items.length > 0)` branch that calls `runCustomBondFromComposer()`
  - Composer always calls `createQueueItem()`
  - File: `prototype/ui/static/js/app.js:316-327`

- [ ] **1.2** Update composer placeholder
  - Change "Create anything" to "Create Item"
  - File: `prototype/ui/templates/index.html:131`

- [ ] **1.3** Add Bond authoring UI (new section under selected item)
  - When an item is selected, show a "Create Bond" section
  - Contains: prompt text input, "Create Bond" button
  - Does NOT show output type dropdown

### Phase 2: Separate Bond Creation from Execution

- [ ] **2.1** Modify suggestion click handler
  - `runSuggestionOneClick()` → `createBondFromSuggestion()`
  - Creates a draft Bond (output_item_id = null)
  - Shows Bond in a "pending" state with "Run Bond" button
  - File: `prototype/ui/static/js/app.js:428-462`

- [ ] **2.2** Add draft Bond display
  - New UI element: "Draft Bond Panel"
  - Shows: prompt text, input items, output type (derived, not selectable)
  - Has: "Run Bond" button, "Cancel" button
  - Appears below suggestions when a Bond is drafted

- [ ] **2.3** Modify Bond execution
  - "Run Bond" button calls `executeBond(bondId)`
  - Only execution triggers AI call
  - Only execution deducts credits

- [ ] **2.4** Remove output type selector from operator drawer
  - Delete the radio buttons for M/D selection
  - Output type is derived from Bond origin
  - File: `prototype/ui/templates/index.html:153-158`

### Phase 3: Custom Bond Path (D output)

- [ ] **3.1** Add custom prompt input under item
  - When item is selected, show both:
    - Suggestions (4 chips)
    - Custom prompt input with "Create Bond" button
  - Custom prompt creates Bond with output_type='D'

- [ ] **3.2** Custom Bond follows same draft → execute flow
  - User types custom prompt → clicks "Create Bond" → Bond drafted
  - User clicks "Run Bond" → AI executes → D Item created

### Phase 4: State Machine Enforcement

- [ ] **4.1** Add `currentDraftBond` to state
  - Tracks the Bond that is drafted but not yet executed
  - Contains: bond_id, prompt_text, input_item_ids, output_type

- [ ] **4.2** UI reflects state
  - If `currentDraftBond` is null → show suggestions/custom prompt
  - If `currentDraftBond` exists → show draft Bond panel with "Run Bond"

- [ ] **4.3** Disable conflicting actions when Bond is drafted
  - Cannot select different items while Bond is drafted
  - Must "Run" or "Cancel" the draft Bond first

### Phase 5: Holologue Path

- [ ] **5.1** Verify Holologue follows correct pattern
  - Multi-select → "Run Holologue" button → Modal (kind selector) → Execution
  - Current implementation is close but verify no shortcuts

## API Changes

No API changes required. The UI will use existing endpoints differently:
- `/api/bonds` POST to create draft bond
- `/api/bonds/<id>/run` POST to execute (instead of `/api/bonds/run-suggestion`)

## Files to Modify

1. `prototype/ui/static/js/app.js` - Main UI logic
2. `prototype/ui/templates/index.html` - HTML structure
3. `prototype/ui/static/css/style.css` - Styling for new draft Bond panel

## Testing

Create `prototype/scripts/test_ui_ontology_smoke.py` that verifies:
1. Creating an Item does NOT trigger AI
2. Clicking a suggestion creates a draft Bond (not output)
3. "Run Bond" on draft Bond produces output
4. Custom prompt creates D-type Bond
5. No dropdown for Q/M/D/H selection exists

## Success Criteria

1. User can type + Enter multiple times → multiple Q Items, no AI calls
2. User can click suggestion → draft Bond appears → no AI call yet
3. User must click "Run Bond" → AI executes → output Item appears
4. Output type (M/D) is never user-selected, always derived
5. All existing tests pass (Golden Flow credits=73)

## Commit Message

```
ui: enforce Item/Bond/Execute ontology (no dropdown Q/M/D/H)
```
