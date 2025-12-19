# Field-Kit Mental Model v0.1

## The Core Triad: Item → Bond → Execution

Field-Kit has exactly three distinct concepts. Conflating any two breaks the system.

### 1. Item (The Artifact)

An **Item** is a piece of content that exists in the Field. Items are *nouns*.

| Type | Name | Created By |
|------|------|------------|
| Q | Queue | User types content in composer |
| M | Monologue | AI generates via Bond execution |
| D | Dialogue | AI generates via Bond execution |
| H | Holologue | AI synthesizes multiple items via execution |

**Critical:** Q means "Queue" (a holding area for user-authored content), NOT "Question" or "Query".

**Rule:** Creating an Item is a pure write operation. It never triggers AI generation.

### 2. Bond (The Operator)

A **Bond** is an operation that transforms input Items into output Items. Bonds are *verbs*.

A Bond has:
- `input_item_ids`: What Items it reads
- `prompt_text`: What transformation to apply
- `intent_type`: One of 12 semantic labels (e.g., `expand`, `synthesize`, `critique`)
- `output_item_id`: null until executed, then points to the result

**Two paths to create a Bond:**

| Path | Bond Type | User Action |
|------|-----------|-------------|
| Suggestion | Creates M output | User clicks AI-proposed suggestion |
| Custom | Creates D output | User writes their own prompt |

**Rule:** A Bond is always a separate object from Items. It is never "implied" by typing.

### 3. Execution (The Action)

**Execution** is the explicit act of running a Bond to produce output.

- Requires a "Run Bond" button click
- Produces exactly one output Item (M, D, or H)
- Logs `bond.run_requested` then `bond.executed` events
- Deducts credits

**Rule:** Execution is always explicit. Typing never auto-executes.

---

## Why Typed Text Cannot Mean Both Item AND Bond

Consider what happens when a user types "expand this into a checklist" and presses Enter.

### The Wrong Model (Chat Software)

```
User types → [Magic box] → AI output appears
```

This model collapses three operations into one keystroke:
1. Create an Item (the user's text)
2. Create a Bond (the transformation)
3. Execute the Bond (call AI)

Problems:
- User cannot create an Item without triggering AI
- User cannot author a Bond without immediately running it
- No draft state, no review, no "undo before execute"
- The system has no ontological clarity

### The Correct Model (Field-Kit)

```
User types → Item created (stored)
                    ↓
            Suggestions appear (4 AI-proposed Bonds)
                    ↓
            User clicks suggestion OR writes custom prompt
                    ↓
            Bond created (draft, not yet run)
                    ↓
            User clicks "Run Bond"
                    ↓
            AI executes → Output Item created
```

Each step is discrete:
- **Item creation:** Pure storage, no AI
- **Bond creation:** Sets up the operation, no AI
- **Execution:** Explicit AI call with clear cost

---

## The Selection Model

Users can select Items to operate on:

| Selection State | Available Actions |
|-----------------|-------------------|
| No items selected | Create new Q Item |
| 1 item selected | View suggestions, create Bond |
| 2+ items selected | Run Holologue (multi-item synthesis) |

Suggestions are **event-only** until the user confirms. Clicking a suggestion creates a Bond, then the user explicitly runs it.

---

## Output Type Determination

The output type is determined by the Bond, not by user choice:

| Bond Origin | Output Type |
|-------------|-------------|
| AI-suggested prompt | M (Monologue) |
| User-authored prompt | D (Dialogue) |
| Holologue operation | H (Holologue) |

**Q is never an output type.** Q is only created by direct user input.

---

## Summary Table

| Concept | What It Is | User Action | AI Involved? |
|---------|-----------|-------------|--------------|
| Item | Content artifact | Type + Enter | No |
| Bond | Transformation operator | Click suggestion OR write prompt | No |
| Execution | Run the Bond | Click "Run Bond" | Yes |

The UI must enforce these separations. A composer that "feels like chat" violates the ontology.
