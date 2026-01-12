## 25) *Machine Super Intelligence* (Shane Legg dissertation) — how it helps Holographic/Gibsey

### The idea to steal

Legg builds a *clean spine* that connects:

1. **Intelligence = goal achievement across many environments** (his informal definition). ([Semantic Scholar][1])
2. **Uncertainty + adaptation are central** (agent doesn’t fully know the environment; must be adaptable). ([Semantic Scholar][1])
3. A theoretical “universal” route: Solomonoff-style priors / Kolmogorov complexity ideas for prediction, then RL for action. ([Semantic Scholar][1])
4. The **AIXI** family as an (incomputable) ideal, and approximate variants (e.g., MC-AIXI) as “try to make it practical.” ([Semantic Scholar][1])
5. A formal “universal intelligence” measure (the weighted sum over environments) that operationalizes the informal definition. ([Semantic Scholar][1])

Think of it as: **define the game, define the score, define the agent, then approximate intelligently.**

---

## Current applications for Holographic/Gibsey

### 1) Stop debating “is it working?”—define *environment + goals + reward* for Field behavior

Legg’s definition is brutally usable as a product rubric: “ability to achieve goals in a wide range of environments.” ([Semantic Scholar][1])

For you right now, “environment” can be:

* the **Field graph + Vault + ledger** as the world state
* the **user’s current task** as the goal condition
* the **UI constraints** (limited top-k links, evidence requirements) as physics

This forces each module (hololinks, bundling, routing) to have an explicit success criterion, not vibes.

### 2) Treat QDPI as an RL loop, even before you train anything

Legg explicitly frames RL as the general “agent interacts with environment → actions/observations/reward.” ([Semantic Scholar][1])

Gibsey translation:

* **observation** = current page + evidence pack + session memory slots
* **action** = pointer selection / bond proposal / bundle / ask / save
* **reward** = user accepts link, saves output, reduced backtracking, improved “thread continuity,” etc.

Even if you implement the policy heuristically today, logging it *as if it were RL* is how you create future training data.

### 3) Your “handles not context” issue becomes a *credit assignment* issue

If the system suggests junk links, Legg’s spine says: you don’t fix it by better prose; you fix it by clarifying:

* what action space exists
* what reward signals exist
* what the agent can observe
* what memory it can use

That’s the universal-agent viewpoint (not “chatbot viewpoint”).

---

## Future applications

### 1) A serious evaluation harness: “wide range of environments”

Legg’s core definition bakes in **generalization**: not “does it work on one page,” but “does it work across many environments.” ([Semantic Scholar][1])

For Field/Gibsey, your “environments” can be:

* different books/sections (Glyph vs Princhetta vs Natalie)
* different user intents (navigate, interpret, summarize, connect, debug)
* different memory regimes (fresh session vs months of Vault)

That’s how you make the project feel like a *system*, not a demo.

### 2) Build toward “universal intelligence” as a *north-star metric* (even if you can’t compute it)

He writes down the universal intelligence measure as a weighted sum over environments with weights based on environment complexity. ([Semantic Scholar][1])
You won’t compute that literally, but it gives you the pattern:

* maintain a **suite of environments/tasks**
* weight them so the agent can’t overfit the easy stuff
* score policies by **robust goal achievement**

This pairs cleanly with your MDL/complexity track: “good behavior should compress and generalize.”

### 3) Approximation mindset: AIXI is a beacon, not a build target

Legg is explicit that the pure theory runs into computability issues (e.g., Solomonoff predictor isn’t computable) and then discusses approximations and practical methods. ([Semantic Scholar][1])
That maps perfectly to your ethos:

* keep the clean theoretical interface (read/write memory, pointer actions, evidence)
* ship approximations (heuristics, small controllers, constrained policies)
* improve them iteratively with logged data

---

## One concrete next step for Gibsey

Write a **“Field Task Suite v0.1”** with 10–20 micro-environments (each one is a reproducible state + goal + scoring):

* **State**: a specific page + a specific candidate set + Vault context
* **Goal**: “choose the next link that preserves thread continuity” / “bundle to H without losing key evidence”
* **Reward**: click-through + low backtracking + strong alignment traces

That’s Legg’s framework in practice: define the environments, define success, then you can meaningfully improve policies over time. ([Semantic Scholar][1])

[1]: https://pdfs.semanticscholar.org/e758/b579456545f8691bbadaf26bcd3b536c7172.pdf "Machine Super Intelligence"