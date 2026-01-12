# UI Ontology Gap Report

**Sprint:** G.2 (UI/Ontology Alignment)
**Date:** 2025-12-20
**Status:** Analysis Complete

---

## Executive Summary

The current `ui_v2` implementation violates core ontology rules from the v0.1 specs. The UI treats the bottom composer as a "chat input" that always creates Q Items, when in fact:

1. **Creating an Item MINTS an artifact — it does NOT generate.**
2. **A Bond is the ONLY thing that causes generation.**
3. **D (Dialogue) = user-authored Bond prompt — the typed text IS a Bond, not an Item.**

The UI must support two distinct modes:
- **No active Q Item**: Composer creates new Q Items (minting)
- **Active Q Item selected**: Composer creates + runs D Bonds targeting that Q (generating)

---

## Spec References

| Spec Document | Key Rule |
|---------------|----------|
| `01_first_run_experience_v0.1.md` | "Q→D via user-written Bond prompt (write prompt → Run Bond → output Item)" |
| `08_ui_ux_foundations_v0.1.md` | "Creating Item does NOT generate. Bond is the only thing that causes generation." |
| `07_spin_recipes_v0.1.md` | "Anchor phrase MUST appear verbatim in rendered prompt" |
| `CLAUDE.md` (guardrails) | "Proposals are events-only until user explicitly confirms Create Bond" |

---

## Gap Analysis

### Gap 1: Composer Always Creates Q Items (CRITICAL)

**What spec demands:**
- When NO active Q Item exists: typing creates new Q (minting)
- When Q Item IS active: typing creates a D Bond targeting that Q, then executes it (generating)

**What UI does:**
- `createQueueItem()` in `app.js:262` ALWAYS creates Q Items regardless of context
- There is no concept of an "active" or "selected" Q Item that receives prompts
- Users cannot type custom prompts to create D Bonds

**Evidence:**
```javascript
// app.js:262-310 - Always creates Q Items
async function createQueueItem() {
  const body = inputEl.value.trim();
  // ...
  const res = await fetch('/api/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ body }),  // Always creates Q
  });
```

**Required fix:**
- Track "active Q Item" state in UI
- When active Q exists, composer submission creates D Bond + runs it
- Add visual indicator showing which Q Item is active
- Change placeholder text dynamically based on mode

---

### Gap 2: D Type Unused (CRITICAL)

**What spec demands:**
- D (Dialogue) outputs are created when user writes their own Bond prompt
- "Q→D via user-written Bond execution (prompt → Run Bond → output Item)" — spec section B5

**What UI does:**
- Only M (Monologue) outputs are ever created
- `runSuggestion()` hardcodes `output_type: 'M'` at line 355
- No code path exists to create D outputs

**Evidence:**
```javascript
// app.js:355 - Always uses output_type 'M'
body: JSON.stringify({
  input_item_ids: [itemId],
  prompt_text: promptText,
  intent_type: currentSuggestions[index]?.intent_type,
  recipe_id: currentSuggestions[index]?.recipe_id,
  output_type: 'M',  // Never 'D'
}),
```

**Required fix:**
- Clicking a suggestion → output_type: 'M' (correct)
- Typing custom prompt → output_type: 'D' (missing)

---

### Gap 3: Suggestions Placement (MODERATE)

**What spec demands:**
- "Show 4 content-shaped suggestions after item creation" — immediately under the Q Item
- Suggestions are contextual to the active Q

**What UI does:**
- Suggestions render at the bottom of the entire feed via `renderSuggestions()`
- Suggestions are visually disconnected from their parent Q Item

**Evidence:**
```javascript
// app.js:157-160 - Suggestions always at end
for (const item of items) {
  html += renderItem(item);
}
// Add suggestions if we have them
if (currentSuggestions && currentSuggestionItemId) {
  html += renderSuggestions(currentSuggestions, currentSuggestionItemId);
}
```

**Required fix:**
- Render suggestions inline immediately after their parent Q Item
- When user creates a new Q, previous suggestions should clear

---

### Gap 4: New Session Doesn't Reset Store (MODERATE)

**What spec demands:**
- "New Session" should create a fresh Episode with clean state
- Or reset the store entirely for a true fresh start

**What UI does:**
- `newSessionBtn.addEventListener('click', () => location.reload())` just reloads
- Same Episode and Items persist after "New Session"

**Evidence:**
```javascript
// app.js:91
newSessionBtn.addEventListener('click', () => location.reload());
```

**Required fix:**
- Either call store reset API (`reset_store()`) before reload
- Or create new Episode via API

---

### Gap 5: Content-Shaped Suggestions (VERIFIED OK)

**What spec demands:**
- Anchor phrase from Item body must appear verbatim in suggestions
- "Every recipe MUST incorporate at least one anchor phrase from the input Item(s)"

**What implementation does:**
- `spin_recipes.py` correctly extracts anchor phrases
- Templates include `{{anchor_phrase}}` placeholders
- `generate_suggestions_for_item()` renders templates with anchor

**Status:** PASS — Implementation matches spec. The test `test_ui_suggestions_content_shaped.py` validates this.

---

## Required State Machine

The UI needs a simple state machine:

```
                    ┌────────────────────────────────────────┐
                    │                                        │
                    ▼                                        │
┌──────────────────────────────────┐                        │
│  STATE: NO_ACTIVE_ITEM           │                        │
│  - Composer placeholder: "Queue  │                        │
│    something..."                 │                        │
│  - Submit → Create Q Item        │                        │
│  - No suggestions visible        │                        │
└────────────┬─────────────────────┘                        │
             │                                              │
             │ [Q Item created]                             │
             ▼                                              │
┌──────────────────────────────────┐                        │
│  STATE: Q_ITEM_ACTIVE            │                        │
│  - Active Q highlighted          │                        │
│  - 4 suggestions visible below Q │                        │
│  - Composer placeholder:         │                        │
│    "Write a prompt for this..."  │                        │
│  - Submit → Create D Bond + run  │──────┐                 │
│  - Click suggestion → Run M Bond │──────┤                 │
└────────────┬─────────────────────┘      │                 │
             │                            │                 │
             │ [M or D output created]    │                 │
             ▼                            ▼                 │
┌──────────────────────────────────────────────────────┐    │
│  STATE: OUTPUT_SHOWN                                 │    │
│  - Output item visible (M or D)                      │    │
│  - Suggestions cleared                               │    │
│  - Composer returns to "Queue something..."          │────┘
│  - Submit → Create new Q Item                        │
└──────────────────────────────────────────────────────┘
```

---

## Minimal Code Changes Required

### 1. Add Active Item State (app.js)

```javascript
let activeItemId = null;  // Track which Q Item is receiving prompts
```

### 2. Update Composer Behavior

```javascript
async function handleComposerSubmit() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  if (activeItemId) {
    // Mode: Create + run D Bond targeting active Q
    await createAndRunDBond(activeItemId, body);
  } else {
    // Mode: Create new Q Item
    await createQueueItem(body);
  }
}
```

### 3. Add createAndRunDBond Function

```javascript
async function createAndRunDBond(targetItemId, promptText) {
  isProcessing = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  try {
    const res = await fetch('/api/bonds/run-suggestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_item_ids: [targetItemId],
        prompt_text: promptText,
        output_type: 'D',  // User-authored = Dialogue
      }),
    });

    const data = await res.json();
    if (data.status === 'executed' && data.output_item) {
      items.push(data.output_item);
      clearActiveItem();  // Reset to NO_ACTIVE_ITEM state
      updateCredits();
      updateUI();
    }
  } catch (e) {
    console.error('Create D Bond error:', e);
  }

  isProcessing = false;
  inputEl.focus();
}
```

### 4. Track Active Item After Q Creation

```javascript
async function createQueueItem(body) {
  // ... existing Q creation code ...

  if (data.item) {
    items.push(data.item);
    setActiveItem(data.item.id);  // Q becomes active
    await fetchSuggestions(data.item.id);
  }
}

function setActiveItem(itemId) {
  activeItemId = itemId;
  currentSuggestionItemId = itemId;
  inputEl.placeholder = "Write a prompt for this item...";
  // Add visual highlight to active item
}

function clearActiveItem() {
  activeItemId = null;
  currentSuggestions = null;
  currentSuggestionItemId = null;
  inputEl.placeholder = "Queue something...";
}
```

### 5. Render Suggestions Inline

```javascript
function renderItem(item) {
  let html = `<div class="item-container item-${item.type.toLowerCase()}" ...>`;
  html += `...item content...`;
  html += `</div>`;

  // Render suggestions immediately after their parent Q Item
  if (currentSuggestionItemId === item.id && currentSuggestions) {
    html += renderSuggestions(currentSuggestions, item.id);
  }

  return html;
}
```

### 6. Fix New Session

```javascript
newSessionBtn.addEventListener('click', async () => {
  if (confirm('Start fresh? This will clear all items.')) {
    await fetch('/api/reset', { method: 'POST' });
    location.reload();
  }
});
```

And add reset endpoint in `app.py`:

```python
@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset the store for a fresh session."""
    reset_store(DATA_DIR)
    return jsonify({"status": "reset"})
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Creating Q Item when no active item → works
- [ ] After Q created, suggestions appear under it
- [ ] Clicking suggestion → M output created
- [ ] Typing custom prompt + submit → D output created
- [ ] After output, state returns to NO_ACTIVE_ITEM
- [ ] New Session truly resets store
- [ ] All suggestions contain anchor phrase verbatim
- [ ] Regression tests still pass (`run_golden_flow.py`, etc.)

---

## Files to Modify

| File | Changes |
|------|---------|
| `prototype/ui_v2/static/js/app.js` | State machine, composer behavior, inline suggestions |
| `prototype/ui_v2/app.py` | Add `/api/reset` endpoint |
| `prototype/ui_v2/static/css/style.css` | Active item highlight styling |

---

## Conclusion

The current UI treats Field-Kit like a chat app ("type → get response"). The ontology requires a two-phase model:

1. **Mint**: Create Q Items (queue thoughts)
2. **Generate**: Create + run Bonds (transform thoughts into artifacts)

The fixes above are minimal and preserve the wrapper's ChatGPT aesthetic while enforcing the correct ontology.
