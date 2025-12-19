# Field-Kit v0.1 Ontology-Correct UI

Local-only web UI for Field-Kit prototype. Built on Flask + vanilla HTML/CSS/JS.

**This UI enforces the Item/Bond/Execute ontology.** It is NOT chat software.

## Quick Start

```bash
# From repo root
python3 prototype/ui/app.py

# Open in browser
open http://localhost:5001
```

## Run Command

```bash
python3 prototype/ui/app.py
```

The server runs at `http://localhost:5001`.

## Custom Data Directory

Use the `FIELDKIT_DATA_DIR` environment variable to isolate data:

```bash
# Fresh test environment
FIELDKIT_DATA_DIR=/tmp/fieldkit-ui python3 prototype/ui/app.py

# Separate from headless tests
FIELDKIT_DATA_DIR=prototype/data_ui python3 prototype/ui/app.py
```

## Ontology-Correct UX Design

The UI enforces three distinct operations that must NOT be collapsed:

### 1. Create Item (No AI)

- **Bottom composer** → always creates a **Queue item** (Q)
- Typing and pressing Enter stores content, does NOT call AI
- Q items are artifacts, not prompts

### 2. Create Bond (No AI)

- **Click a suggestion** → creates a **draft Bond** (will produce M output)
- **Type custom prompt** → creates a **draft Bond** (will produce D output)
- Draft Bond appears in panel, does NOT call AI yet

### 3. Execute Bond (Calls AI)

- **Click "Run Bond"** → executes the draft Bond
- AI is called, credits are deducted
- Output Item is created (M, D, or H)

### Multi-Item Synthesis (Holologue)

- **Select 2+ items** → "Run Holologue" button appears
- Select artifact kind in modal → produces **Holologue** (H)

## Type Terminology

| Type | Name | Created By |
|------|------|------------|
| Q | Queue | User typing in composer (direct) |
| M | Monologue | Bond execution (suggestion origin) |
| D | Dialogue | Bond execution (custom prompt origin) |
| H | Holologue | Holologue execution (multi-item) |

**Critical:** Q = **Queue** (holding area), NOT "Question" or "Query".

**Output types are DERIVED, not selected:**
- Suggestion → M
- Custom prompt → D
- Holologue → H

## UI Surfaces

### Bottom Composer

The main input area. **ONLY creates Q Items.**

- **Placeholder**: "Create Item (Q)"
- **Button**: "Create" (not "Send")
- **Enter**: Creates Q item (NO AI call)
- **Shift+Enter**: New line

### Inline Suggestions

Appear under Queue items after creation.

- **4 content-shaped suggestions** from Spin Recipes
- **Click**: Creates draft Bond (NO AI call yet)
- **Shimmer effect**: Magic at draft creation
- **Recipe ID shown**: e.g., `[expand_to_checklist]`

### Custom Prompt Input

Appears under suggestions for each item.

- **Input field**: "Enter custom prompt..."
- **Button**: "Create Bond"
- **Creates draft Bond** with D output type

### Draft Bond Panel

Appears when a Bond is drafted but not yet executed.

- Shows input items, prompt text, output type (derived)
- **"Run Bond" button**: Executes the Bond (AI call)
- **"Cancel" button**: Discards the draft Bond

### Holologue Bar

Appears when 2+ items are selected (Shift+click or Cmd+click).

- Shows count: "3 items selected"
- "Run Holologue" button opens modal
- Artifact kind selector: Plan, Checklist, Spec Fragment, Experiment, Story Beat

### Ledger Drawer (Left)

Click "Ledger" button or press `L`. Four tabs:

- **Objects**: Items, Bonds, Episodes
- **Events**: QDPIEvent log with filters (by name, by QDPI type)
- **Curated**: Canon projection view
- **JSON**: Preview/export for selected object

### Credits Chip

Top-right header shows current credits balance.

- **Derived** from `credits.delta` events
- **Flashes green** on credit gain
- **Flashes red** on credit spend

### Tutorial Banner

Shows after first item creation: "Tutorial logging enabled. Steps not yet implemented."

Dismissible. No false promises.

### Ephemeral Run Card

Shown during Bond/Holologue execution.

- **UI-only** - never persisted
- **Shimmer animation** while running
- Replaced by real Item on success

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Submit composer |
| `Shift+Enter` | New line in composer |
| `L` | Toggle Ledger drawer |
| `Esc` | Close topmost modal/drawer |
| `Click` | Select item (single) |
| `Shift+Click` / `Cmd+Click` | Multi-select items |

## API Endpoints

All API routes return JSON.

### Status & Init

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get store status |
| `/api/init` | POST | Initialize store |

### Items

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/items` | GET | List all items |
| `/api/items` | POST | Create new item (type, title, body) |
| `/api/items/<id>/suggestions` | GET | Get 4 suggestions for item |

### Bonds

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bonds` | GET | List all bonds |
| `/api/bonds` | POST | Create draft bond |
| `/api/bonds/<id>/run` | POST | Run a bond |
| `/api/bonds/run-suggestion` | POST | Create + run in one step |

### Holologue

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/holologue/run` | POST | Run holologue on items |

### Ledger & Export

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ledger` | GET | Get full ledger data |
| `/api/credits` | GET | Get credits balance + events |
| `/api/export/episode` | GET | Export episode JSON |
| `/api/export/curated` | GET | Export curated projection |

## Design Principles

From `/docs/specs/08_UI_UX_foundation_v0.1.md`:

1. **Minimal by default** - Calm, typographic, whitespace-forward
2. **Magic at invocation** - Shimmer/effects only during suggestions and running
3. **Never dead air** - Ephemeral run card shows immediately during runs
4. **Never block reading** - Drawers don't prevent viewing Items
5. **Ephemeral = UI only** - Run cards are never persisted until success

## v0.1 Constraints

- **Private + Local** only
- No accounts, cloud sync, collaboration
- No persisted placeholder Items
- No UI-only events logged (canonical events only)
- Credits are simulated (not real money)

## File Structure

```
prototype/ui/
├── app.py              # Flask application
├── README.md           # This file
├── templates/
│   └── index.html      # Main HTML template
└── static/
    ├── css/
    │   └── style.css   # Styles
    └── js/
        └── app.js      # UI JavaScript
```

## Integration with Headless Core

The UI wraps the existing CLI logic (`src/cli.py`). It:

1. Uses the same `FieldKitCLI` class
2. Writes to the same JSONL store
3. Logs the same canonical events
4. Respects all spec constraints

The headless tests continue to work independently.

## Manual UI Checklist

Test the ontology-correct UX:

1. `python3 prototype/ui/app.py`
2. Type "I want to build something cool" → Enter
   - **Verify**: Q item created, NO AI call, credits +3
3. See 4 content-shaped suggestions appear
4. Click any suggestion
   - **Verify**: Draft Bond panel appears, NO AI call yet
5. Click "Run Bond"
   - **Verify**: AI called, M item created, credits deducted
6. Type in custom prompt input under an item → "Create Bond"
   - **Verify**: Draft Bond panel appears (D output type)
7. Click "Run Bond"
   - **Verify**: D item created
8. Shift+click to select 2 items
9. Click "Run Holologue" → select kind → confirm
   - **Verify**: H item created
10. Press `L` → verify events follow correct sequence:
    - item.created → bond.draft_created → bond.run_requested → bond.executed
