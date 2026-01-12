# Machine Learning Spine for Gibsey / QDPI (Modules A–E)

This is a minimal ML foundation tailored to the Field, Gibsey, and QDPI. It doesn’t try to cover “all of machine learning”; it defines a concise spine of ideas that map directly onto pages, glyphs, bonds, and events in the Vault. You can read it as a functional specification for how the Field can be represented as vectors, graphs, and learnable processes.

---

## Module A – Vectors & Similarity

### Vectors

* A **scalar** is a single number (e.g. `3`, `-12.5`).
* A **vector** is an ordered list of numbers, e.g. in 3D:

  ```text
  v = [2, -1, 0.5]
  ```

Think of a vector as:

* A **point** in space (x, y, z), or
* An **arrow** from the origin to that point.

In ML, vectors are how we represent almost everything: words, sentences, pages, events, users, glyphs.

### Dot product

For two vectors of the same length:

```text
a = [a₁, a₂, ..., aₙ]
b = [b₁, b₂, ..., bₙ]
```

the **dot product** is:

[
a \cdot b = \sum_{i=1}^{n} a_i b_i
]

Intuitively:

* Large positive → vectors point in similar directions.
* Near zero → roughly orthogonal.
* Negative → point in opposite directions.

### Vector length (norm)

The **length** (Euclidean norm) of a vector (a) is:

[
|a| = \sqrt{a \cdot a} = \sqrt{\sum_i a_i^2}
]

### Cosine similarity

The **cosine similarity** between two vectors (a) and (b) is:

[
\text{cos_sim}(a, b) = \frac{a \cdot b}{|a| , |b|}
]

* ≈ 1 → very similar direction
* ≈ 0 → unrelated / orthogonal
* ≈ -1 → opposite direction

In an embedding space, “closeness in meaning” is often modeled as **high cosine similarity**.

### Glyphs as 3D vectors: Q / M / D / H

For one glyph family (e.g. `"an_author"`), your four page types are rotations of the same base shape:

* Queue (Q) – 0°
* Monologue (M) – 90°
* Dialogue (D) – 180°
* Holologue (H) – 270°

We encode them as **3D vectors**:

> [family_id, \sin\theta, \cos\theta]

where:

* `family_id = 1` for this glyph family,
* (\theta) is the rotation angle.

Using:

* sin(0°) = 0, cos(0°) = 1
* sin(90°) = 1, cos(90°) = 0
* sin(180°) = 0, cos(180°) = -1
* sin(270°) = -1, cos(270°) = 0

we get:

* **Queue (Q, 0°)**
  [
  v_Q = [1, 0, 1]
  ]

* **Monologue (M, 90°)**
  [
  v_M = [1, 1, 0]
  ]

* **Dialogue (D, 180°)**
  [
  v_D = [1, 0, -1]
  ]

* **Holologue (H, 270°)**
  [
  v_H = [1, -1, 0]
  ]

Each has the same squared norm:

[
|v|^2 = 1^2 + (\sin\theta)^2 + (\cos\theta)^2 = 2 \quad \Rightarrow \quad |v| = \sqrt{2}
]

### Cosine similarity between Q / M / D / H

Because all norms are (\sqrt{2}), cosine similarity is:

[
\text{cos_sim}(a, b) = \frac{a \cdot b}{2}
]

Dot products and similarities:

* (v_Q \cdot v_M = 1\cdot1 + 0\cdot1 + 1\cdot0 = 1) → cos = **0.5**

* (v_Q \cdot v_D = 1\cdot1 + 0\cdot0 + 1\cdot(-1) = 0) → cos = **0.0**

* (v_Q \cdot v_H = 1\cdot1 + 0\cdot(-1) + 1\cdot0 = 1) → cos = **0.5**

* (v_M \cdot v_D = 1\cdot1 + 1\cdot0 + 0\cdot(-1) = 1) → cos = **0.5**

* (v_M \cdot v_H = 1\cdot1 + 1\cdot(-1) + 0\cdot0 = 0) → cos = **0.0**

* (v_D \cdot v_H = 1\cdot1 + 0\cdot(-1) + (-1)\cdot0 = 1) → cos = **0.5**

Table:

| Pair | Cosine similarity |
| ---- | ----------------- |
| Q–M  | 0.5               |
| Q–D  | 0.0               |
| Q–H  | 0.5               |
| M–D  | 0.5               |
| M–H  | 0.0               |
| D–H  | 0.5               |

Interpretation:

* Adjacent rotations (0° ↔ 90°, 90° ↔ 180°, 180° ↔ 270°, 270° ↔ 0°) have similarity **0.5**.
* Opposite rotations (0° ↔ 180°, 90° ↔ 270°) are **orthogonal** (0.0).

You’ve enforced a **ring topology** over the four narrative modes: neighbors are moderately similar; opposite modes are maximally distinct but not “anti” each other.

### On `family_id` and “lineage”

The first dimension (`family_id = 1`) encodes that these four vectors belong to the **same glyph family**:

* It injects a shared component so that all four states for `"an_author"` are closer to each other than to glyphs from a completely different family (once you give other families different values or embeddings in that dimension).
* If later you introduce multiple glyph families, you can:

  * encode `family_id` as different scalars, or
  * better, as a small **family embedding** that’s concatenated or added to the orientation vector.

Note on “opposites”:

* In standard cosine similarity, **-1** is a strict “opposite direction”.
* Here, Q and D have similarity **0.0** (orthogonal), not -1.
  That’s actually a good match: a Dialogue page is not the anti-matter of a Queue page; it’s a distinct orthogonal mode.

If you ever wanted sharper opposites, you could:

* Represent orientation purely as ([\sin\theta, \cos\theta]) (2D), with family handled separately, or
* Keep family and orientation in different subspaces and control how strongly each influences similarity.

For now, your choice of `[family_id, sinθ, cosθ]` is practical and expressive: it encodes **shared lineage** plus **cyclical narrative mode** in one small vector.

### Why this matters

This is a genuine ML move, not just cute math:

* You’ve defined a **semantic coordinate system** for one glyph family.
* Each Q/M/D/H state has a concrete vector.
* Similarity between page types is now measurable.

In general:

* Embeddings represent concepts as vectors.
* Distances/angles encode similarity and difference.

For the Field:

* Each **page type**, **glyph family**, and **page** can be embedded.
* **QDPI events** can embed the active glyph/page state via these vectors.
* You can build a baby “page-type similarity metric” and extend it to the whole Vault.

---

## Module B – Computation Graph & Gradient Descent

### Model as a function

Consider the simplest possible model:

[
\hat{y} = f_\theta(x) = w x + b
]

* Parameters: (\theta = (w, b))
* Input: (x)
* Output (prediction): (\hat{y})

Training example:

* (x = 2)
* (y = 5) (true value)

We want (w, b) such that:

[
w \cdot 2 + b \approx 5
]

### Forward pass with an initial guess

Start with:

* (w = 1)
* (b = 0)

Prediction:

[
\hat{y} = 1 \cdot 2 + 0 = 2
]

The model predicts **2** instead of **5**.

### Loss function

Squared error:

[
L = (\hat{y} - y)^2
]

Plug in:

[
L = (2 - 5)^2 = (-3)^2 = 9
]

* At ((w, b) = (1, 0)), loss is **9**.
* This is the scalar “how wrong are we?” measure.

### The computation graph

Even this tiny model has a computation graph:

* Node: (x = 2)
* Node: (w = 1)
* Node: (b = 0)
* Node: multiply → (w x)
* Node: add → (\hat{y} = w x + b)
* Node: subtract → (\hat{y} - y)
* Node: square → (L = (\hat{y} - y)^2)

Edges carry values from op to op. During:

* **Forward pass**: inputs flow toward the loss.
* **Backprop**: gradients flow from the loss back to parameters.

The directed graph of operations and intermediate values is the **computation graph**.

### Make the loss explicit in terms of (w, b)

With (x = 2):

[
\hat{y} = w x + b = 2w + b
]

Define:

[
z = 2w + b - 5
]

Then:

[
L(w,b) = z^2
]

### Gradients: how loss changes when we nudge (w) and (b)

We want (\frac{\partial L}{\partial w}), (\frac{\partial L}{\partial b}).

From (L = z^2):

[
\frac{\partial L}{\partial z} = 2z
]

Also:

* (z = 2w + b - 5)
* (\frac{\partial z}{\partial w} = 2)
* (\frac{\partial z}{\partial b} = 1)

Chain rule:

[
\frac{\partial L}{\partial w} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial w} = 2z \cdot 2 = 4z
]

[
\frac{\partial L}{\partial b} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial b} = 2z \cdot 1 = 2z
]

At (w = 1, b = 0):

[
z = 2\cdot 1 + 0 - 5 = -3
]

So:

* (\frac{\partial L}{\partial w} = 4\cdot(-3) = -12)
* (\frac{\partial L}{\partial b} = 2\cdot(-3) = -6)

These gradients say:

* Increasing (w) will **reduce** the loss (gradient is negative).
* Increasing (b) will **reduce** the loss.

### One gradient descent step

Update rule:

[
\theta_{\text{new}} = \theta_{\text{old}} - \eta \cdot \nabla_\theta L
]

Pick (\eta = 0.1).

Current:

* (w_{\text{old}} = 1)
* (b_{\text{old}} = 0)

Update:

[
w_{\text{new}} = 1 - 0.1 \cdot (-12) = 1 + 1.2 = 2.2
]

[
b_{\text{new}} = 0 - 0.1 \cdot (-6) = 0 + 0.6 = 0.6
]

### New prediction and loss

[
\hat{y}_{\text{new}} = 2.2 \cdot 2 + 0.6 = 4.4 + 0.6 = 5.0
]

[
L_{\text{new}} = (5 - 5)^2 = 0
]

We’ve reached parameters that fit this example exactly.

### Narrative summary

* A model is a **function with parameters**.
* The **loss** is a scalar that measures mismatch between prediction and reality.
* The **gradient** tells you in which direction in parameter space to move to reduce loss.
* **Gradient descent** is repeatedly nudging parameters in that direction.

In Field terms: the internal weights are the Field’s habits. QDPI events say “this was good/bad”, the loss quantifies that, and gradient descent is the Field adjusting itself so that similar future events go better.

---

## Module C – Three Graphs

There are three different graphs that matter:

1. **Data graph** – the Vault and bonds (what exists and how it’s connected).
2. **Attention graph** – token-level focus for a particular model call (the current thought).
3. **Computation graph** – the fixed wiring of the model’s operations (the plumbing).

Together they describe **where knowledge lives**, **what is active right now**, and **how activity flows**.

### 1. Data graph (Vault / bonds graph)

**Nodes**:

* Q, M, D, H pages
* QDPI events
* Users, HPUs, other entities

**Edges**:

* Bonds: Q→M, Q→Q, M→D, etc., with types and directions.
* Edge types encode semantics (“expands”, “answers”, “zooms in”, “is caused by”).

This graph:

* Lives in your data layer (Cassandra, Obsidian, schemas).
* Changes when you add pages, bonds, or events.
* Is human-curated and long-lived.

It is the **topology of the Field**.

#### Mini-subgraph example

Q pages:

* Q1 – “FIELD – Purpose of the Field Overview”
* Q2 – “L0 – Math & Metal: Physics of the Field”
* Q3 – “L1 – Pages, Vault, and QDPI Events”

M pages:

* M1 – expands Q1
* M2 – expands Q2
* M3 – “What Counts as a QDPI Event?” (expands Q3)
* M4 – “How Are We Going to Turn QDPI Events into Vectors?” (linked from Q2/Q3)

D pages:

* D1 – answer to “How are we going to turn QDPI events into vectors?”
* D2 – “Why the Field Needs to Learn About Itself” (synthesizes Q1 + Q3)

Example bonds:

* Q1 → Q2, Q2 → Q3
* Q1 → M1, Q2 → M2, Q3 → M3, Q3 → M4
* M4 → D1, Q1 → D2, Q3 → D2
* D1 → M2, D2 → M1 (cross-links)

Static picture:

```text
Q1 → Q2 → Q3
 |     |     \
 v     v      v
M1    M2     M3, M4
 |           |
 v           v
D2         D1
```

This is the **Data Graph**: what’s in the Vault and how it’s wired.

### 2. Attention graph (inside a forward pass)

Now imagine:

* The reader is on **Q3**.
* The system feeds the model:

  * Q3 text,
  * snippets from M3 and M4,
  * D1 if already generated.

In a transformer layer:

* **Nodes**: tokens from Q3, M3, M4, D1 (e.g. `pages`, `Vault`, `events`, `vectors`, …).
* **Edges**: attention weights from each token to each other token.

Examples:

* “events” (in Q3) → attends strongly to “event schema” (in M3).
* “vectors” (in Q3) → attends strongly to mentions of “embedding”, “cosine similarity” (in M4 / D1).
* “Vault” (in Q3) → attends to phrases describing storage and structure in related pages.

The **attention graph** is:

* Rebuilt at each layer and attention head.
* Fully dynamic and ephemeral.
* The pattern of “which words/light nodes are informing which others right now.”

You can think of it as the **Field’s current thought** over a subset of the Vault.

### 3. Computation graph (the model’s wiring)

Regardless of which Q/M/D/H are in play, the transformer’s computation graph is fixed:

1. **Token IDs** → embeddings.
2. Add **positional encodings**.
3. For each layer:

   * Project to Q/K/V.
   * Compute attention scores and apply softmax.
   * Combine values via attention weights.
   * Add residuals, layer norms.
   * Apply feed-forward MLP.
4. Finally, map to logits, softmax, and sample/argmax to get tokens.

Each operation and intermediate tensor is a **node**; data flowing between them are **edges**. This defines the **Computation Graph**: the “wiring diagram” the Field uses to route information when answering a question.

### Putting them together

* The **Data Graph** (Vault) is the curated structure of pages, bonds, and events.
* The **Attention Graph** is the transient pattern of which tokens and phrases are talking to each other in this specific context.
* The **Computation Graph** is the underlying neural wiring that makes embeddings and attention possible.

Architecturally:

* You don’t need the model to memorize the Data Graph.
* The model supplies a rich Computation Graph that, via the Attention Graph, can **navigate** the Data Graph.
* The Field’s power comes from pairing a well-designed Vault graph with a good attentional/computational engine.

---

## Module D – Transformers in Story Form

### Story-level view

When you send a message, three big things happen inside the model:

1. **Tokens → embeddings**
   Your text is split into tokens:

   > “How / are / we / going / to / turn / QDPI / events / into / vectors / ?”

   Each token becomes a vector in meaning space. Instead of raw text, the model now has a little constellation of points.

2. **Self-attention builds a temporary graph (per layer)**
   At each layer, every token looks at every other token and asks:

   > “How relevant are you to me right now?”

   This yields a weighted graph:

   * “QDPI” attends strongly to “events” and prior mentions of QDPI in the context.
   * “events” attends to definitions of events in M3.
   * “vectors” attends to “embeddings”, “cosine similarity”, “space” in prior context and in the model’s internal representational habits.

   The pattern of attention edges changes slightly at each layer, refining what the model considers important.

3. **Output next token / answer**
   After several layers of this graph-building and mixing, each output position has a vector that encodes a context-aware meaning. The model then maps that vector back into a word/token:

   > “We / can / serialize / each / QDPI / event / … / into / a / text / description / …”

   It chooses tokens one by one (or in parallel internally), forming the answer.

So a transformer, in compact story form, is:

> **tokens → vectors → repeated attention graphs → new vectors → words**

### Applied to the QDPI question

For the question:

> “How are we going to turn QDPI events into vectors?”

Inside the transformer:

* “QDPI” connects to tokens and memories about your QDPI schema.
* “events” locks onto definitions and examples of events in Q3 and M3.
* “vectors” pulls in concepts of embeddings, similarity, and geometry from both local context and the model’s training.

The evolving attention graphs over several layers guide the model toward an answer about serializing events and embedding them.

### Self-attention in Holographic terms

You can summarize this behavior as:

> **Self-attention, for me, is the Field briefly turning every word in a question into a node and letting them all look at each other at once, so the most important bonds for this moment light up. It’s the way a transformer decides which parts of the Vault and the current page should talk to each other to generate the next line of thought.**

---

## Module E – QDPI → ML Data Design

This is the bridge from your lived system (QDPI logs) to an ML-ready representation. Every Field interaction is a structured event that can be turned into an embedding.

### QDPIEvent schema

A reasonable schema for a single event:

```ts
type QDPIEvent = {
  event_id: string;              // unique id
  timestamp_iso: string;         // e.g. "2025-12-11T14:23:00Z"

  user_id: string | null;        // reader or you
  session_id: string | null;     // browsing or HPU thread

  page_id: string | null;        // foreground page
  page_type: "Q" | "M" | "D" | "H" | null;
  glyph_family_id: string | null;           // e.g. "an_author"
  glyph_orientation_deg: 0 | 90 | 180 | 270 | null;

  action_type:
    | "READ"
    | "INDEX"
    | "ASK"
    | "RECEIVE"
    | "BOND_CREATE"
    | "BOND_FOLLOW";

  channel: "UI" | "API" | "IMPORT";

  request_text: string | null;   // user prompt / question
  response_text: string | null;  // model or system reply
  note_text: string | null;      // annotations / commentary

  bond_ids: string[];            // bonds touched/created
  related_page_ids: string[];    // pages pulled into context

  dwell_time_ms: number | null;  // time on page before event
  scroll_percent: number | null; // how far user scrolled
  rating: number | null;         // thumbs or 1–5

  tags: string[];                // manual or auto tags
};
```

Now we categorize fields and their roles in embedding.

### Identity & time

* `event_id`

  * **Type**: categorical ID
  * **Usage**: lookup key only, not as a feature.

* `timestamp_iso` → derived features like hour-of-day, day-of-week, days-since-start

  * **Type**: scalars
  * **Usage**: normalized numeric features (e.g. `hour/24`, `day_of_week/7`), capturing temporal patterns.

### Actor / session

* `user_id`, `session_id`

  * **Type**: categorical
  * **Usage**: initial phase: for filtering and grouping.
    Later: optionally map to **user/session embeddings** if you want the Field to learn user-specific patterns.

### Page & glyph context

* `page_id`

  * **Type**: categorical
  * **Usage**: pointer to a **page embedding** (precomputed from full page text + metadata).

* `page_type`, `glyph_family_id`, `glyph_orientation_deg`

  * **Type**: categorical + scalar

  * **Usage**: combined into a **glyph/page-type vector**, e.g.:

    [
    e_{\text{glyph}} = [\text{family_id or family_embed}, \sin\theta, \cos\theta]
    ]

  * Optionally project this into the main embedding dimension with a small linear layer.

This grounds each event in a specific part of the glyph-space and narrative mode.

### Action context

* `action_type` (READ / INDEX / ASK / RECEIVE / BOND_CREATE / BOND_FOLLOW)

  * **Type**: categorical
  * **Usage**: one-hot or a small **action embedding**; encodes what kind of QDPI verb this event is.

* `channel` (UI / API / IMPORT)

  * **Type**: categorical
  * **Usage**: small one-hot or embedding; distinguishes human UI usage from API or batch imports.

### Text fields

* `request_text`

  * **Type**: text
  * **Usage**: main **request embedding** `e_request`.

* `response_text`

  * **Type**: text
  * **Usage**: main **response embedding** `e_response`.

* `note_text`

  * **Type**: text
  * **Usage**: optional **note embedding** `e_note` (meta-commentary, summaries).

These capture the core “what was asked” and “what the Field said”.

### Graph / bond structure

* `bond_ids`

  * **Type**: list of categorical IDs
  * **Usage**: derive **graph features**, such as:

    * number of bonds touched,
    * distribution over bond types,
    * degree properties of the nodes involved.
      Optionally, bond-type embeddings can be aggregated.

* `related_page_ids`

  * **Type**: list of categorical IDs
  * **Usage**: for each related page, get its embedding and average/sum them into `e_context_pages`.

These connect each event to its local neighborhood in the Data Graph.

### Behavioral scalars

* `dwell_time_ms`, `scroll_percent`, `rating`

  * **Type**: scalars
  * **Usage**: normalized into a small **behavior vector**:

    [
    \text{behavior_vector} = [\tilde{\text{dwell}}, \tilde{\text{scroll}}, \tilde{\text{rating}}]
    ]

These track how long and how deeply the reader engaged and how they judged the outcome.

In the future, these can support **implicit RLHF** (Reinforcement Learning from Human Feedback):

* High dwell + good rating → the Field learns that this response was a “good move” for that request in that glyph state.
* Short dwell + bad rating → the opposite.

### Tags

* `tags`

  * **Type**: list of categorical / short text values
  * **Usage**:

    * encode as text (“tags: embedding, QDPI, glyphs”) and embed, or
    * maintain per-tag embeddings and average them.

Tags serve as human- and system-defined coarse topics.

### Event-level sub-embeddings and composition

For each event, you can compute:

* (e_{\text{request}} = \text{embedding}(\text{request_text}))
* (e_{\text{response}} = \text{embedding}(\text{response_text}))
* (e_{\text{note}} = \text{embedding}(\text{note_text})) (optional)
* (e_{\text{page}} = \text{page_embedding}(\text{page_id}))
* (e_{\text{glyph}}) = vector from glyph family + orientation
* (e_{\text{action}}) = action-type embedding
* (e_{\text{context_pages}}) = average of embeddings of `related_page_ids`
* (\text{behavior_vector}) = normalized ([\text{dwell}, \text{scroll}, \text{rating}])

Then combine:

[
e_{\text{event}} = \text{combine}\Big(
e_{\text{request}},
e_{\text{response}},
e_{\text{note}},
e_{\text{page}},
e_{\text{glyph}},
e_{\text{action}},
e_{\text{context_pages}},
\text{behavior_vector}
\Big)
]

where `combine` could be:

* simple concatenation followed by a small MLP, or
* a weighted sum in a shared space.

Once you have (e_{\text{event}}) for every interaction:

* The Field can measure **similarity between events**.
* Discover patterns/clusters of usage and meaning.
* Use event embeddings as input to recommender-style systems (which page to show next, which M/D to surface).
* Train models that predict good responses or next actions conditioned on past behavior.

### Summary

Every QDPI event is a structured, typed object: IDs, enums, numbers, and text. By:

* embedding request/response text,
* encoding glyph/page type and rotation,
* capturing action and graph neighborhood,
* and folding in behavior as feedback,

you turn each event into a single vector that lives in the Field’s geometry. This event embedding is the core bridge between the Vault’s lived history and any learning system you build on top of it.