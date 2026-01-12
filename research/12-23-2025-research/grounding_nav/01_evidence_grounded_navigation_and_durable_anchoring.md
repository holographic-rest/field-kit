# Evidence-grounded navigation + durable anchoring (hololinks that don’t rot)
**Path:** `/research/12-23-2025-research/grounding_nav/01_evidence_grounded_navigation.md`  
**Status:** draft (research → decisions for v0.1)  
**Why now:** Holographic/Gibsey “hololinks” must be *pointers with evidence*—auditable, local-first, and resilient to edits—so navigation doesn’t drift into ungrounded “soup.”

---

## 0) Definitions (project-local, but aligned to standards)

### Hololink (project term)
A **graph edge** (often a Bond) that connects two project nodes (Item, Episode, etc.) and is *backed by one or more evidence bundles*.

### Evidence bundle (this doc’s deliverable)
A **portable record** of “what was cited” + “how to find it again” + “what version it was taken from.”  
Closest standard analogue: a W3C Web Annotation where the *Target* is a SpecificResource + Selector(s) and the *Body* is whatever you attach (claim, tag, link, or here: the hololink/Bond).  
- W3C model: decoupled annotation stored separately from the document.  
- Key concept: multiple selectors (quote + position + fragment) for robustness.

### Anchor resolution
The algorithm that maps a stored selector set back onto the current representation of a document (or internal text resource), producing:
- resolved span/range
- confidence
- “orphan/stale” signals when it can’t be safely found

---

## 1) Design requirements for hololinks as evidence pointers

These requirements keep navigation grounded and debuggable:

1. **Evidence is first-class, not prose.**
   - A hololink is invalid unless it has at least one evidence bundle, or is explicitly marked as “speculative / ungrounded.”

2. **Decoupled storage.**
   - Evidence must be stored outside the source file and must survive source edits and reformatting (mirrors Web Annotation’s intent).

3. **Multi-selector anchoring.**
   - Store at least one robust selector (quote + context) and one fast selector (position/offset) for the same target.

4. **Version/state capture.**
   - Every bundle records what *version* of the resource it was anchored against (timestamp + content hash and/or explicit version ID).

5. **Auditability + reversibility.**
   - Any re-anchoring, edits to the bundle, or resolution failures are logged as events.

6. **UI always exposes provenance.**
   - Users should be able to answer “why does this link exist?” in one gesture (hover, popover, side panel) without leaving context.

---

## 2) Anchors that survive edits: selector types + tradeoffs

### A) TextPosition (offset/range)
**What it is:** a character range `[start, end]` into a canonicalized text representation.  
**Pros:** fast.  
**Cons:** brittle to edits, line ending changes, normalization changes.  
**Use in v0.1:** cache-only (“fast path”), never the sole truth.

**Standard baseline:** RFC 5147 explicitly supports fragment identifiers by character/line range and even discusses integrity information to detect changes.  
- https://datatracker.ietf.org/doc/html/rfc5147

### B) TextQuote + context (robust anchoring)
**What it is:** store `exact` (the quoted text) plus `prefix`/`suffix` context to re-find it.  
**Pros:** robust to many edits; representation-agnostic (works for plaintext/markdown/HTML-as-text).  
**Cons:** collisions if text is repeated; can “reattach wrong” after heavy edits unless you score candidates.

**W3C selector:** `TextQuoteSelector` + optional `TextPositionSelector` together are the key “store both” move.  
- https://www.w3.org/TR/selectors-states/  
- https://www.w3.org/TR/annotation-model/

### C) Fragment identifiers (viewer-native deep links)
Useful for *jumping* the UI to evidence, not as the only anchor.
- **Web pages:** URL Fragment Text Directives (`#:~:text=`) can deep-link to a text snippet in compatible browsers.
  - Spec: https://wicg.github.io/scroll-to-text-fragment/
  - Repo: https://github.com/WICG/scroll-to-text-fragment
- **PDFs:** RFC 8118 registers `application/pdf` and discusses PDF-specific concerns; in practice, `#page=` style fragments are common, but viewer support varies.
  - https://datatracker.ietf.org/doc/html/rfc8118

### D) Keyword/fingerprint anchoring (heavy-edit resilience)
**What it is:** store a “fingerprint” of distinctive words from the selection and re-anchor by searching and scoring nearby clusters.  
**Pros:** survives more drastic edits and movement.  
**Cons:** heuristic; requires careful scoring and false-positive control.

**Primary reference:** “Robustly Anchoring Annotations Using Keywords” (Microsoft Research TR MSR-TR-2001-107).  
- https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf

---

## 3) Recommended v0.1: the “Local-First Waterfall” anchoring cascade

Borrow the core idea used in production annotation systems: store multiple selectors, resolve via a cascade from cheap → expensive.

### What to store (minimum viable)
For each evidence bundle:
- **TextQuoteSelector**
  - `exact` (verbatim excerpt)
  - `prefix` and `suffix` (short context windows)
- **TextPositionSelector**
  - `[start, end]` offsets into a canonicalized “plain text view” of the source
- **State**
  - `captured_at`
  - `content_hash` (hash of canonicalized full source, or at least the containing chunk)
  - optional `version_id` (ledger revision / file revision)
- Optional “jump aid”
  - `view_fragment` (e.g., `#:~:text=` or `#page=`)

### Resolution cascade (conceptual)
1. **Fast path: position check**
   - If current text `[start:end]` matches `exact`, accept (high confidence).
2. **Robust path: quote+context search**
   - Search for `exact` with `prefix/suffix` constraints; score candidates.
3. **Fuzzy path (guarded)**
   - If exact match fails but edit distance is small, do limited-window fuzzy match and require strong candidate score.
   - Practical library reference for Bitap + diff-based utilities: https://github.com/google/diff-match-patch

### Orphans + wrong-reattachment
Two distinct failure states:
- **Orphan:** cannot find a safe match.
- **Ambiguous:** multiple plausible matches; requires user confirmation.
A mature system *surfaces* these states rather than silently “reattaching wrong.”

**Operational reference point:** Hypothesis documentation and tooling on robust/fuzzy anchoring and testing.  
- Robust anchoring overview: https://web.hypothes.is/robust-anchoring/  
- Fuzzy anchoring strategy: https://web.hypothes.is/blog/fuzzy-anchoring/  
- Anchoring evaluation tools: https://github.com/hypothesis/anchoring-test-tools

---

## 4) Evidence bundle spec (fields you actually need)

Think of an evidence bundle as: **Target + Selector(s) + State + Provenance + Resolution status**.

### Required fields (v0.1)
- **IDs**
  - `evidence_id` (stable)
  - `hololink_id` (the Bond/edge this bundle supports)
- **Target resource**
  - `resource_ref` (Vault path / internal URI)
  - `media_type` (text/plain, text/markdown, application/pdf, etc.)
- **Selectors**
  - `text_quote`: exact + prefix + suffix
  - `text_position`: start + end (cache)
  - optional `fragment`: `#:~:text=` or `#page=…`
- **State**
  - `captured_at`
  - `content_hash` (and hash algorithm)
- **Provenance**
  - `created_by` (optional local identity)
  - `created_from_event` (ledger event ID that created/attached it)
- **Resolution status (mutable, logged)**
  - `last_resolved_at`
  - `status`: ok | stale | orphan | ambiguous
  - `confidence` (bounded scale, e.g., 0–1)

### Nice-to-have (still small)
- `normalized_excerpt` (UI-friendly snippet)
- `notes` (why this evidence supports the hololink)
- `tags` (e.g., “definition”, “contradiction”, “motif”, “timeline”)

---

## 5) Provenance model: don’t reinvent, map

Two complementary layers:

### A) Web Annotation concepts (selection mechanics)
Use the W3C Web Annotation mental model for describing *what was selected* (selectors, specific resource, state):
- Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
- Selectors and States: https://www.w3.org/TR/selectors-states/
- Vocabulary/terms: https://www.w3.org/TR/annotation-vocab/

### B) PROV-O concepts (chain-of-custody)
Use PROV(-O) style relationships when you need to show “how this evidence was produced” (especially if OCR/extraction/summarization appears later):
- PROV-O: https://www.w3.org/TR/prov-o/
- PROV overview: https://www.w3.org/TR/prov-overview/

**Practical mapping suggestion**
- Evidence bundle = `prov:Entity`
- Capture action = `prov:Activity`
- Creator/operator = `prov:Agent`
- “Derived from” relationships track transformations (extraction → highlight → link)

Keep this optional in v0.1 unless you already have multi-step pipelines.

---

## 6) UI patterns that keep evidence visible (and prevent “soup”)

Below are patterns worth implementing early because they reduce ungrounded drift.

### 1) Citation popover / evidence hovercard
- **What it does:** hovering a hololink shows the exact excerpt + provenance + jump action.
- **Prevents:** “trust me” links; context loss.
- **Pitfall:** snippet tunnel-vision → always provide “open in context”.

### 2) Parallel (synoptic) view: claim ↔ evidence
- **What it does:** side-by-side pane with synchronized highlight.
- **Prevents:** misquotes, laundering.
- **Pitfall:** screen real estate; make it a toggle, not the default.

### 3) Semantic zoom on hololinks
- **What it does:** link chip → snippet preview → full context as you zoom/expand.
- **Why it works:** progressive disclosure keeps the field navigable.
- **Primary anchor:** Pad++ multiscale UI research (semantic zoom lineage).
  - https://www.cs.columbia.edu/graphics/courses/csw4170/resources/bedersonHollanUIST94.pdf

### 4) Information scent cues at link-time
- **What it does:** show small cues next to a hololink (e.g., evidence count, freshness, confidence).
- **Prevents:** random clicking, wasted traversal.
- **Pitfall:** false scent → cues must reflect real evidence, not guesses.

### 5) Backlinks with filters (not an infinite list)
- **What it does:** show “what points here” but constrained by type/time/confidence.
- **Prevents:** isolated nodes; reveals reuse of evidence.
- **Pitfall:** explosion/noise → require filters and caps.

### 6) Orphan/stale affordances
- **What it does:** visibly mark evidence that no longer resolves; provide “re-anchor” flow.
- **Prevents:** silent corruption.

### 7) Graphical history for evidence edits
- **What it does:** show changes to evidence bundles over time (branching where needed).
- **Why:** evidence integrity becomes inspectable.
- **Primary reference:** Graphical histories design space.
  - https://idl.cs.washington.edu/files/2008-GraphicalHistories-InfoVis.pdf

### 8) “Lens” overlay for provenance/debug
- **What it does:** a mode/lens that overlays selector matches, confidence, and state-hash info.
- **Primary reference:** Toolglass/Magic Lenses.
  - https://www.billbuxton.com/tgml93.pdf

### 9) Stretchtext-like inline expansion (small!)
- **What it does:** expand evidence inline without navigation.
- **Prevents:** constant context switching.
- **Pitfall:** disorientation if expansions are large → cap size, collapse by default.

### 10) Transclusion (optional, later)
- **What it does:** embed the cited fragment inline while retaining a durable pointer.
- **Pitfall:** context neutrality violations; needs careful surrounding context display.

---

## 7) Known failure modes + mitigations (the “don’t rot” checklist)

### Anchor drift (position-only links rot)
- **Mitigation:** always store quote+context selector; treat offsets as cache.

### Quote collisions (repeated phrases)
- **Mitigation:** prefix/suffix windows + candidate scoring; mark ambiguous instead of guessing.

### Wrong reattachment after big edits
- **Mitigation:** guarded fuzzy match only in a limited window; require high score; otherwise orphan.

### Evidence laundering (links without inspectable proof)
- **Mitigation:** UI must show excerpt + source + state; require evidence on creation unless explicitly “speculative”.

### Link explosion (“soup”)
- **Mitigation:** enforce evidence-required links, filter backlinks, add scent cues, and provide “bundle views” rather than raw graphs.

### Viewer mismatch / fragment support variance (esp. PDF)
- **Mitigation:** keep fragment IDs as “jump aids” only; the true anchor is quote+context + state.

---

## 8) Concrete v0.1 recommendations (smallest safe set)

1. **Hololink validity rule**
   - A hololink is “grounded” only if it has ≥1 resolvable evidence bundle.

2. **Selector bundle**
   - Store: TextQuote (exact+prefix+suffix) + TextPosition (start/end) + State (captured_at + content_hash).
   - Optional: view fragment for convenience (web text fragments, PDF page).

3. **Resolution status is part of navigation**
   - Display stale/orphan/ambiguous states prominently; don’t hide.

4. **Evidence UI is a default affordance**
   - Every hololink shows a one-step “why” preview (popover) and one-step “open in context”.

5. **Ledger integration**
   - Creation/reattachment/orphaning are events; evidence bundles are entities with history.

---

## 9) Primary sources (canonical starting set)

### Web Annotation / selectors
- W3C Web Annotation Data Model (Rec): https://www.w3.org/TR/annotation-model/
- W3C Selectors and States (Note): https://www.w3.org/TR/selectors-states/
- W3C Web Annotation Vocabulary: https://www.w3.org/TR/annotation-vocab/

### Fragment identifiers / deep links
- RFC 5147 (text/plain fragments): https://datatracker.ietf.org/doc/html/rfc5147
- RFC 8118 (application/pdf media type): https://datatracker.ietf.org/doc/html/rfc8118
- URL Fragment Text Directives / Scroll-to-Text: https://wicg.github.io/scroll-to-text-fragment/

### Real-world anchoring strategies
- Hypothesis robust anchoring: https://web.hypothes.is/robust-anchoring/
- Hypothesis fuzzy anchoring: https://web.hypothes.is/blog/fuzzy-anchoring/
- Hypothesis anchoring evaluation tools: https://github.com/hypothesis/anchoring-test-tools
- Keyword anchoring TR: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2001-107.pdf

### Provenance
- PROV-O: https://www.w3.org/TR/prov-o/
- PROV overview: https://www.w3.org/TR/prov-overview/

### UI lineage (for evidence-first patterns)
- Pad++ (semantic zoom / multiscale UI): https://www.cs.columbia.edu/graphics/courses/csw4170/resources/bedersonHollanUIST94.pdf
- Toolglass and Magic Lenses: https://www.billbuxton.com/tgml93.pdf
- Graphical Histories for Visualization: https://idl.cs.washington.edu/files/2008-GraphicalHistories-InfoVis.pdf

---

## 10) Open questions to resolve later (don’t block v0.1)
- How to canonicalize text for offset stability (whitespace, hyphenation, unicode normalization)?
- How to represent anchors into the 710-page novel: “chapter/paragraph IDs” vs quote+context only?
- Do we need cross-format anchoring (same text in PDF and plaintext)?
- When do we permit fuzzy anchoring automatically vs requiring user confirmation?