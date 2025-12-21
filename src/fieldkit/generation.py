"""
Field-Kit v0.1 Generation Backend

Provides real content generation for Bond and Holologue outputs.

Sprint G2: Stub generation is now content-derived, not generic boilerplate.

Backends:
1. Stub backend (default, no network): Content-derived structured text
2. OpenAI backend (optional): Uses OPENAI_API_KEY if set

Environment variables:
- OPENAI_API_KEY: If set, enables OpenAI backend
- OPENAI_MODEL: Model to use (default: gpt-4o-mini)

Generation Mode:
- get_generation_mode() returns "stub" or "openai:<model>"
- UI can display this to show what's generating content
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple

from .spin_recipes import extract_anchor_phrase, extract_content_fingerprint


# === Generation Mode ===

def get_generation_mode() -> str:
    """
    Get the current generation mode for UI display.

    Returns:
        "stub" if no OpenAI key
        "openai:<model>" if OpenAI is configured
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        return f"openai:{model}"
    return "stub"


# Track last generation result for error reporting
_last_generation_warning: Optional[str] = None


def get_last_generation_warning() -> Optional[str]:
    """Get the last generation warning (e.g., OpenAI fallback to stub)."""
    return _last_generation_warning


def _set_generation_warning(warning: Optional[str]):
    """Set generation warning for UI to display."""
    global _last_generation_warning
    _last_generation_warning = warning


# === Stub Templates by Recipe ===

STUB_TEMPLATES = {
    "expand_to_checklist": """# Checklist: {anchor}

- [ ] Verify the core assumption holds
- [ ] Identify edge cases and boundary conditions
- [ ] Document the expected inputs and outputs
- [ ] Test with representative data samples
- [ ] Review for security and performance implications

## Definition of done

- All items above are checked and documented
- Edge cases have been enumerated and addressed
- Implementation matches the specification

---
*Based on: {snippet}*
""",

    "ground_in_experiment": """# Experiment: {anchor}

## Hypothesis
If we implement {anchor}, then we will observe measurable improvement in the target metric.

## Method
1. Establish baseline measurements
2. Implement minimal viable change
3. Measure post-implementation metrics
4. Compare against baseline

## Metric
Primary: Success rate / completion time / error rate
Secondary: User satisfaction / resource utilization

## Stop rule
Halt if error rate exceeds 10% or if no improvement after 48 hours.

## Controls
- Keep all other variables constant
- Use same test data set
- Document any environmental changes

---
*Based on: {snippet}*
""",

    "derive_min_schema": """# Minimal Schema: {anchor}

## Entities
- **PrimaryEntity**: The core object being modeled
- **RelatedEntity**: Supporting data that references the primary

## Fields

### PrimaryEntity
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | MUST | Unique identifier |
| name | string | MUST | Human-readable label |
| status | enum | MUST | Current state |
| created_at | datetime | MUST | Creation timestamp |
| metadata | object | MAY | Additional properties |

## Invariants
- id MUST be unique across all entities
- status MUST be one of: draft, active, archived
- created_at MUST be immutable after creation

## Queries
- Get by id: O(1) lookup
- List by status: indexed query
- Search by name: full-text search

---
*Based on: {snippet}*
""",

    "decision_with_reasons": """# Decision: {anchor}

## Recommendation
**YES** - Proceed with implementation.

## Rationale
1. Aligns with project goals and constraints
2. Technical feasibility has been validated
3. Resource requirements are within budget
4. Risk level is acceptable with mitigations

## Tradeoffs
| Option | Pros | Cons |
|--------|------|------|
| Proceed | Faster delivery, lower risk | Some technical debt |
| Delay | More polish, better testing | Opportunity cost |
| Skip | No effort required | Missed feature |

## Risks
- Integration complexity may be underestimated
- Dependencies on external systems
- Potential for scope creep

## Next Steps
1. Create implementation ticket
2. Assign owner and timeline
3. Schedule review checkpoint

---
*Based on: {snippet}*
""",

    "clarify_to_testable_claim": """# Testable Claim: {anchor}

## Original Statement
{snippet}

## Clarified Claim
**Claim**: When [specific condition] is met, [specific outcome] will occur within [specific timeframe].

## Test Criteria
- **Pass condition**: Outcome matches expectation within tolerance
- **Fail condition**: Outcome deviates by more than threshold
- **Measurement method**: Automated test / manual verification

## Falsifiability
This claim can be disproven by demonstrating a counterexample where the condition is met but the outcome does not occur.

---
*Reformulated for testability*
""",

    "compare_with_criteria": """# Comparison: {anchor}

## Options
- **Option A**: First approach
- **Option B**: Alternative approach

## Weighted Criteria

| Criterion | Weight | Option A | Option B |
|-----------|--------|----------|----------|
| Complexity | 30% | 7/10 | 5/10 |
| Performance | 40% | 6/10 | 8/10 |
| Maintainability | 30% | 8/10 | 6/10 |

## Scores
- Option A: (0.3 × 7) + (0.4 × 6) + (0.3 × 8) = 6.9
- Option B: (0.3 × 5) + (0.4 × 8) + (0.3 × 6) = 6.5

## Recommendation
**Option A** scores slightly higher due to better maintainability.

---
*Based on: {snippet}*
""",

    "risk_register": """# Risk Register: {anchor}

| # | Risk | Likelihood | Impact | Score | Mitigation |
|---|------|------------|--------|-------|------------|
| 1 | Integration failure | Medium (3) | High (4) | 12 | Early integration testing |
| 2 | Performance issues | Low (2) | Medium (3) | 6 | Performance benchmarks |
| 3 | Scope creep | High (4) | Medium (3) | 12 | Strict change control |
| 4 | Resource constraints | Medium (3) | Medium (3) | 9 | Buffer in timeline |
| 5 | External dependencies | Medium (3) | High (4) | 12 | Fallback options |

## Risk Matrix
- **Critical (12+)**: Risks 1, 3, 5 require active management
- **Moderate (6-11)**: Risk 4 requires monitoring
- **Low (<6)**: Risk 2 acceptable with standard practices

---
*Based on: {snippet}*
""",

    "implementation_plan": """# Implementation Plan: {anchor}

## Overview
Step-by-step plan to implement the specified feature/change.

## Steps

### Phase 1: Preparation
1. Review existing codebase and dependencies
2. Set up development environment
3. Create feature branch

### Phase 2: Implementation
4. Implement core functionality
5. Add unit tests for new code
6. Integrate with existing systems

### Phase 3: Validation
7. Run full test suite
8. Perform code review
9. Test in staging environment

### Phase 4: Deployment
10. Deploy to production
11. Monitor for issues
12. Document changes

## Dependencies
- Access to development environment
- Required permissions and credentials
- Team availability for review

---
*Based on: {snippet}*
""",

    # Dialogue recipes
    "peer_review_objections": """# Peer Review: {anchor}

## Objection 1: Complexity Concern
**Objection**: This approach may introduce unnecessary complexity.
**Response**: The complexity is justified by the requirements. We've minimized it by focusing on essential features only.

## Objection 2: Testing Coverage
**Objection**: How will edge cases be tested?
**Response**: We'll implement property-based testing and add explicit edge case scenarios to the test suite.

## Objection 3: Maintenance Burden
**Objection**: Who will maintain this long-term?
**Response**: Documentation will be comprehensive, and the code follows established patterns familiar to the team.

---
*Based on: {snippet}*
""",

    "debate_two_options": """# Debate: {anchor}

## Option A Arguments

**Argument 1**: Simpler implementation
Option A requires fewer changes to existing code and can be delivered faster.

**Argument 2**: Proven approach
This pattern has been used successfully in similar projects.

## Option B Arguments

**Argument 1**: Better scalability
Option B handles growth scenarios more elegantly.

**Argument 2**: Modern standards
Aligns with current best practices and industry standards.

## Verdict
Both options are viable. Choose based on timeline (A) vs long-term vision (B).

---
*Based on: {snippet}*
""",

    "refine_prompt_with_constraints": """# Prompt Refinement: {anchor}

## Original Prompt
{snippet}

## Clarifying Questions
1. What is the expected output format?
2. Are there any constraints on length or complexity?
3. What context should be assumed?

## Refined Versions

### Version 1 (Concise)
Generate a brief summary of {anchor} in 2-3 sentences.

### Version 2 (Detailed)
Provide a comprehensive analysis of {anchor} including background, key points, and implications.

### Version 3 (Structured)
Create a structured breakdown of {anchor} with sections for: Overview, Details, and Recommendations.

---
*Refined for clarity*
""",

    "adversarial_test_cases": """# Adversarial Tests: {anchor}

## Test Case 1: Empty Input
**Input**: Empty or null value
**Why it might break**: Missing null checks or empty string handling
**Expected behavior**: Graceful error or default value

## Test Case 2: Extreme Values
**Input**: Maximum/minimum allowed values
**Why it might break**: Integer overflow, buffer limits
**Expected behavior**: Proper bounds checking

## Test Case 3: Malformed Data
**Input**: Invalid format or unexpected characters
**Why it might break**: Parsing errors, injection vulnerabilities
**Expected behavior**: Validation and sanitization

---
*Based on: {snippet}*
""",

    "rubric_and_scoring": """# Evaluation Rubric: {anchor}

## Criteria

### 1. Correctness (40%)
- 10: Fully correct, handles all cases
- 7: Mostly correct, minor issues
- 4: Partially correct, significant gaps
- 1: Incorrect or non-functional

### 2. Clarity (25%)
- 10: Crystal clear, well-documented
- 7: Clear with minor ambiguities
- 4: Somewhat unclear
- 1: Confusing or undocumented

### 3. Efficiency (20%)
- 10: Optimal performance
- 7: Good performance
- 4: Acceptable but slow
- 1: Unacceptably slow

### 4. Maintainability (15%)
- 10: Easy to modify and extend
- 7: Reasonably maintainable
- 4: Difficult to change
- 1: Requires rewrite to modify

## Sample Scoring
| Criterion | Score | Weighted |
|-----------|-------|----------|
| Correctness | 8 | 3.2 |
| Clarity | 7 | 1.75 |
| Efficiency | 6 | 1.2 |
| Maintainability | 8 | 1.2 |
| **Total** | | **7.35/10** |

---
*Based on: {snippet}*
""",

    "multi_role_negotiation": """# Stakeholder Negotiation: {anchor}

## Participants
- **Product**: Wants features and user value
- **Engineering**: Wants clean code and maintainability
- **Operations**: Wants reliability and observability

## Round 1

**Product**: We need this feature shipped by end of quarter.
**Engineering**: That timeline doesn't allow for proper testing.
**Operations**: We need monitoring hooks before it goes live.

## Round 2

**Product**: Can we scope down to an MVP?
**Engineering**: Yes, if we defer the advanced options.
**Operations**: MVP works if we add basic health checks.

## Resolution
Agreed on MVP scope with basic monitoring, full feature in next quarter.

---
*Based on: {snippet}*
""",

    # Sprint G: 4 diverse output shape templates
    "spec_fragment_rules": """# Spec Rules: {anchor}

## Rules

### MUST Requirements
{must_rules}

### MUST NOT Constraints
{must_not_rules}

## Tests

### Verification Tests
{verification_tests}

### Violation Detection
- Test: Detect if any MUST NOT is violated
- Expected: System should reject or warn

---
*Derived from: {snippet}*
""",

    "architecture_map": """# Architecture Map: {anchor}

## Layer Structure

| Layer | Responsibility | Inputs | Outputs |
|-------|---------------|--------|---------|
{layer_rows}

## Key Interfaces

{interfaces}

## Data Flow

1. Input arrives at top layer
2. Processing flows through middle layers
3. Output emerges from bottom layer

---
*Mapped from: {snippet}*
""",

    "interaction_trace": """# Interaction Trace: {anchor}

## Trace Steps

{trace_steps}

## State Changes

### Before
- Initial state: Ready to process

### After
- Final state: Processing complete

## Key Observations

- Each step modifies system state
- Events are logged for audit trail
- Errors are caught and handled gracefully

---
*Traced from: {snippet}*
""",

    "learning_loop_metrics": """# Learning Loop: {anchor}

## Signals

{learning_signals}

## Metrics

| Metric | How to Measure | Target |
|--------|---------------|--------|
{metric_rows}

## Feedback Path

1. Observe: Collect signals from system behavior
2. Analyze: Identify patterns and anomalies
3. Adapt: Adjust parameters based on analysis
4. Verify: Confirm improvement in target metrics

---
*Signals defined for: {snippet}*
""",
}

# Holologue templates by artifact kind
HOLOLOGUE_TEMPLATES = {
    "plan": """# Synthesis Plan

## Overview
This plan synthesizes insights from {n_items} selected items into a coherent action plan.

## Key Themes
{themes}

## Action Items
1. Consolidate the core concepts identified across items
2. Resolve any conflicts or contradictions
3. Establish clear next steps and ownership
4. Define success criteria and checkpoints

## Dependencies
- Items reference each other and should be considered as a whole
- External factors may influence priority ordering

## Timeline
- Immediate: Review and validate synthesis
- Short-term: Begin implementation of action items
- Long-term: Iterate based on feedback

---
*Synthesized from: {item_titles}*
""",

    "checklist": """# Synthesis Checklist

## Items Consolidated
{item_titles}

## Verification Checklist

- [ ] All source items have been reviewed
- [ ] Key points from each item are captured
- [ ] No critical information is missing
- [ ] Conflicts between items are resolved
- [ ] Synthesis is internally consistent

## Action Checklist

- [ ] Assign owner for follow-up
- [ ] Set deadline for completion
- [ ] Identify blockers and dependencies
- [ ] Schedule review meeting
- [ ] Document decisions made

## Quality Checklist

- [ ] Synthesis is clear and understandable
- [ ] Recommendations are actionable
- [ ] Risks have been identified
- [ ] Success criteria are defined

---
*Synthesized from {n_items} items*
""",

    "spec_fragment": """# Spec Fragment

## Source Items
{item_titles}

## Requirements

### Functional Requirements
1. MUST support the core use cases identified
2. MUST maintain consistency with existing specifications
3. SHOULD handle edge cases gracefully
4. MAY include optional enhancements

### Non-Functional Requirements
1. Performance: Response time within acceptable limits
2. Reliability: Graceful degradation on failure
3. Security: Input validation and access control

## Constraints
- Must integrate with existing systems
- Must not break backward compatibility
- Resource usage within defined limits

## Acceptance Criteria
- All functional requirements met
- Non-functional requirements verified
- Documentation complete

---
*Derived from {n_items} items*
""",

    "experiment": """# Experiment Design

## Hypothesis
Based on synthesis of {n_items} items, we hypothesize that combining these approaches will yield improved results.

## Items Under Test
{item_titles}

## Methodology
1. Establish baseline measurements
2. Apply synthesized approach
3. Measure outcomes against baseline
4. Document observations

## Variables
- **Independent**: The synthesized approach
- **Dependent**: Outcome metrics
- **Controlled**: Environment, timing, inputs

## Expected Outcomes
- Improvement over individual approaches
- New insights from combination
- Identified areas for further investigation

## Success Criteria
- Measurable improvement in target metric
- No regression in other metrics
- Reproducible results

---
*Experiment based on {n_items} items*
""",

    "story_beat": """# Story Beat

## Narrative Arc

### Setup
We began with {n_items} separate ideas, each addressing a different aspect of the problem.

### Development
{themes}

### Resolution
Through synthesis, a unified approach emerged that captures the strengths of each individual item while addressing their limitations.

## Key Characters (Concepts)
{item_titles}

## Conflict and Resolution
The tension between different approaches was resolved by finding common ground and complementary strengths.

## Takeaway
The whole is greater than the sum of its parts when items are thoughtfully combined.

---
*Narrative from {n_items} items*
""",
}


def _get_snippet(body: Optional[str], max_len: int = 100) -> str:
    """Extract a meaningful snippet from body text."""
    if not body:
        return "(no additional context)"

    # Skip Title: lines and PAGE lines
    lines = []
    for line in body.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith('title:'):
            continue
        if line.upper().startswith('PAGE'):
            continue
        lines.append(line)

    if not lines:
        return "(no additional context)"

    # Take first meaningful content
    snippet = ' '.join(lines)[:max_len]
    if len(' '.join(lines)) > max_len:
        snippet += "..."

    return snippet


def _extract_content_bullets(body: Optional[str], max_bullets: int = 5) -> List[str]:
    """
    Extract content-derived bullet points from body text.

    Sprint G2: Stub generation must be content-derived, not generic.
    This function extracts actual phrases from the input to use in output.
    """
    if not body:
        return []

    bullets = []
    lines = []

    for line in body.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith('title:'):
            continue
        if line.upper().startswith('PAGE'):
            continue
        lines.append(line)

    # Strategy 1: Look for existing bullets (- or *)
    for line in lines:
        if line.startswith('- ') or line.startswith('* '):
            bullet_text = line[2:].strip()
            if len(bullet_text) > 10:
                bullets.append(bullet_text)

    # Strategy 2: Split sentences if no bullets found
    if not bullets and lines:
        full_text = ' '.join(lines)
        # Split on periods followed by space and capital
        sentences = re.split(r'\.\s+(?=[A-Z])', full_text)
        for sent in sentences:
            sent = sent.strip().rstrip('.')
            if len(sent) > 15:
                bullets.append(sent)

    # Strategy 3: Extract key phrases if still not enough
    if len(bullets) < 2 and lines:
        # Take chunks from lines
        for line in lines[:max_bullets]:
            if len(line) > 20 and line not in bullets:
                bullets.append(line[:80] + ("..." if len(line) > 80 else ""))

    return bullets[:max_bullets]


def _generate_stub_bond_output(
    prompt_text: str,
    inputs: List[Dict[str, Any]],
    output_type: str,
    recipe_id: Optional[str],
) -> str:
    """
    Generate content-derived output using stub templates.

    Sprint G2: Output must include verbatim phrases from input body.
    Generic boilerplate like "Verify the core assumption" is NOT allowed
    unless that concept is actually in the source body.
    """
    # Get anchor, snippet, and fingerprint from first input
    if inputs:
        first_input = inputs[0]
        title = first_input.get("title", "")
        body = first_input.get("body")
        anchor = extract_anchor_phrase(title, body)
        snippet = _get_snippet(body)
        fingerprint = extract_content_fingerprint(title, body)
        content_bullets = _extract_content_bullets(body)
        key_terms = fingerprint.get("key_terms", [])
    else:
        anchor = "this item"
        snippet = "(no input provided)"
        content_bullets = []
        key_terms = []
        fingerprint = {"key_phrases": [], "key_terms": [], "content_topic": "", "body_excerpt": ""}

    # Sprint G: Get key_phrases for content-shaped diverse outputs
    key_phrases = fingerprint.get("key_phrases", [])

    # Sprint G: Handle content-derived recipe types with full content derivation
    if recipe_id == "spec_fragment_rules":
        return _enhance_spec_fragment_rules(anchor, snippet, key_phrases, content_bullets)
    elif recipe_id == "architecture_map":
        return _enhance_architecture_map(anchor, snippet, key_phrases)
    elif recipe_id == "interaction_trace":
        return _enhance_interaction_trace(anchor, snippet, key_phrases, content_bullets)
    elif recipe_id == "learning_loop_metrics":
        return _enhance_learning_loop_metrics(anchor, snippet, key_phrases)
    elif recipe_id == "clarify_to_testable_claim":
        return _enhance_clarify_claim(anchor, snippet, key_phrases, content_bullets)

    # Select template based on recipe_id and generate content-derived output
    template = STUB_TEMPLATES.get(recipe_id)

    if template:
        # For certain recipes, we enhance with content-derived bullets
        output = template.format(anchor=anchor, snippet=snippet)

        # Sprint G2: Replace generic bullets with content-derived ones
        if content_bullets and recipe_id == "expand_to_checklist":
            output = _enhance_checklist_with_content(output, content_bullets, anchor)
        elif content_bullets and recipe_id == "decision_with_reasons":
            output = _enhance_decision_with_content(output, content_bullets, anchor)
        elif content_bullets and recipe_id == "ground_in_experiment":
            output = _enhance_experiment_with_content(output, content_bullets, anchor)
        elif content_bullets and recipe_id == "derive_min_schema":
            output = _enhance_schema_with_content(output, content_bullets, key_terms, anchor)

        return output

    # Fallback: content-derived structured output
    bullet_str = "\n".join(f"- {b}" for b in content_bullets[:3]) if content_bullets else "- (no specific content extracted)"

    return f"""# Output: {anchor}

## Analysis
{snippet}

## Key Points from Source
{bullet_str}

## Derived Observations
1. The content focuses on: {anchor}
2. Key themes: {', '.join(key_terms[:3]) if key_terms else 'general concepts'}
3. Consider follow-up on the points above

---
*Generated for: {anchor}*
*Based on: {snippet}*
"""


def _enhance_checklist_with_content(output: str, bullets: List[str], anchor: str) -> str:
    """Replace generic checklist items with content-derived ones."""
    # Build content-derived checklist
    checklist_items = []
    for i, bullet in enumerate(bullets[:5]):
        # Truncate long bullets
        if len(bullet) > 60:
            bullet = bullet[:57] + "..."
        checklist_items.append(f"- [ ] Verify: {bullet}")

    # Fill remaining slots if needed
    while len(checklist_items) < 5:
        checklist_items.append(f"- [ ] Review {anchor} against requirements")

    new_checklist = "\n".join(checklist_items)

    # Replace the generic checklist section
    output = re.sub(
        r'- \[ \] Verify the core assumption holds.*?(?=\n\n|## )',
        new_checklist + "\n\n",
        output,
        flags=re.DOTALL
    )
    return output


def _enhance_decision_with_content(output: str, bullets: List[str], anchor: str) -> str:
    """Enhance decision note with content-derived rationale."""
    if len(bullets) >= 2:
        # Use actual content for rationale
        rationale_items = []
        for i, bullet in enumerate(bullets[:4], 1):
            if len(bullet) > 50:
                bullet = bullet[:47] + "..."
            rationale_items.append(f"{i}. {bullet}")

        new_rationale = "\n".join(rationale_items)

        output = re.sub(
            r'## Rationale\n1\. Aligns with project goals.*?(?=\n\n## )',
            f"## Rationale\n{new_rationale}\n\n",
            output,
            flags=re.DOTALL
        )
    return output


def _enhance_experiment_with_content(output: str, bullets: List[str], anchor: str) -> str:
    """Enhance experiment design with content-derived hypothesis."""
    if bullets:
        first_bullet = bullets[0]
        if len(first_bullet) > 80:
            first_bullet = first_bullet[:77] + "..."

        output = re.sub(
            r'## Hypothesis\nIf we implement.*?(?=\n\n## )',
            f"## Hypothesis\nIf we validate \"{first_bullet}\", then we can proceed with {anchor}.\n\n",
            output,
            flags=re.DOTALL
        )
    return output


def _enhance_schema_with_content(output: str, bullets: List[str], key_terms: List[str], anchor: str) -> str:
    """Enhance schema with content-derived entity names."""
    if key_terms:
        # Use key terms as entity names
        entity1 = key_terms[0].title() if key_terms else "PrimaryEntity"
        entity2 = key_terms[1].title() if len(key_terms) > 1 else "RelatedEntity"

        output = output.replace("PrimaryEntity", entity1)
        output = output.replace("RelatedEntity", entity2)
    return output


# Sprint G: Content-derived enhancers for diverse recipe outputs

def _enhance_clarify_claim(anchor: str, snippet: str, key_phrases: List[str], bullets: List[str]) -> str:
    """Generate content-derived testable claim with key phrases."""
    # Build claim that references key phrases
    claim_parts = []
    if key_phrases:
        for phrase in key_phrases[:3]:
            claim_parts.append(phrase)

    claim_phrase = ", ".join(claim_parts) if claim_parts else anchor

    # Build test criteria from content
    test_criteria = []
    for i, phrase in enumerate(key_phrases[:3], 1):
        test_criteria.append(f"- **Test {i}**: Verify that {phrase} behaves as specified")
    if not test_criteria:
        test_criteria = [f"- **Test 1**: Verify {anchor} works correctly"]

    # Include bullets as evidence
    evidence = []
    for bullet in bullets[:3]:
        short_bullet = bullet[:60] + "..." if len(bullet) > 60 else bullet
        evidence.append(f"- {short_bullet}")
    evidence_str = "\n".join(evidence) if evidence else f"- {snippet}"

    return f"""# Testable Claim: {anchor}

## Original Statement
{snippet}

## Key Concepts Referenced
{claim_phrase}

## Clarified Claim
**Claim**: The system correctly implements {claim_phrase} as described in the source content.

## Test Criteria
{chr(10).join(test_criteria)}

## Evidence from Source
{evidence_str}

## Falsifiability
This claim can be disproven by demonstrating that any of the referenced concepts ({claim_phrase}) do not function as described.

---
*Reformulated for testability*
"""


def _enhance_spec_fragment_rules(anchor: str, snippet: str, key_phrases: List[str], bullets: List[str]) -> str:
    """Generate content-derived MUST/MUST NOT rules and tests."""
    # Build MUST rules from key phrases and bullets
    must_rules = []
    for i, phrase in enumerate(key_phrases[:4]):
        must_rules.append(f"- MUST: Support {phrase} as described")
    for bullet in bullets[:2]:
        if len(bullet) > 60:
            bullet = bullet[:57] + "..."
        must_rules.append(f"- MUST: Implement \"{bullet}\"")

    if not must_rules:
        must_rules = [f"- MUST: Implement {anchor} correctly"]

    # Build MUST NOT rules
    must_not_rules = [
        f"- MUST NOT: Violate the core invariants of {anchor}",
        f"- MUST NOT: Skip validation of {key_phrases[0] if key_phrases else anchor}",
        "- MUST NOT: Introduce breaking changes without migration path",
    ]

    # Build verification tests
    verification_tests = []
    for i, phrase in enumerate(key_phrases[:3], 1):
        verification_tests.append(f"- Test {i}: Verify {phrase} behaves as specified")
    if not verification_tests:
        verification_tests = [f"- Test 1: Verify {anchor} works end-to-end"]

    template = STUB_TEMPLATES["spec_fragment_rules"]
    return template.format(
        anchor=anchor,
        snippet=snippet,
        must_rules="\n".join(must_rules),
        must_not_rules="\n".join(must_not_rules),
        verification_tests="\n".join(verification_tests),
    )


def _enhance_architecture_map(anchor: str, snippet: str, key_phrases: List[str]) -> str:
    """Generate content-derived architecture map."""
    # Build layer rows from key phrases
    layer_rows = []
    layer_names = ["Input", "Processing", "Storage", "Output"]
    for i, layer in enumerate(layer_names):
        phrase = key_phrases[i] if i < len(key_phrases) else anchor
        layer_rows.append(f"| {layer} | Handle {phrase} | Data/Events | Processed {phrase} |")

    # Build interfaces from key phrases
    interfaces = []
    if len(key_phrases) >= 2:
        interfaces.append(f"- {key_phrases[0]} → {key_phrases[1]}: Data transformation")
        if len(key_phrases) >= 3:
            interfaces.append(f"- {key_phrases[1]} → {key_phrases[2]}: Event propagation")
    else:
        interfaces.append(f"- {anchor} → Storage: Persistence layer")

    template = STUB_TEMPLATES["architecture_map"]
    return template.format(
        anchor=anchor,
        snippet=snippet,
        layer_rows="\n".join(layer_rows),
        interfaces="\n".join(interfaces),
    )


def _enhance_interaction_trace(anchor: str, snippet: str, key_phrases: List[str], bullets: List[str]) -> str:
    """Generate content-derived interaction trace."""
    trace_steps = []

    # Use key phrases to build meaningful trace steps
    step_num = 1
    for phrase in key_phrases[:5]:
        trace_steps.append(f"{step_num}. User/System initiates: {phrase}")
        step_num += 1
        trace_steps.append(f"{step_num}. System processes {phrase} request")
        step_num += 1

    # Add steps from bullets if we have room
    for bullet in bullets[:3]:
        if step_num <= 14:
            short_bullet = bullet[:50] + "..." if len(bullet) > 50 else bullet
            trace_steps.append(f"{step_num}. Execute: {short_bullet}")
            step_num += 1

    # Pad to at least 10 steps
    while len(trace_steps) < 10:
        trace_steps.append(f"{len(trace_steps) + 1}. Continue processing {anchor}")

    template = STUB_TEMPLATES["interaction_trace"]
    return template.format(
        anchor=anchor,
        snippet=snippet,
        trace_steps="\n".join(trace_steps[:14]),
    )


def _enhance_learning_loop_metrics(anchor: str, snippet: str, key_phrases: List[str]) -> str:
    """Generate content-derived learning signals and metrics."""
    # Build learning signals from key phrases
    signals = []
    for i, phrase in enumerate(key_phrases[:4], 1):
        if i == 1:
            signals.append(f"- Signal {i}: Observe success rate of {phrase}")
        elif i == 2:
            signals.append(f"- Signal {i}: Track errors related to {phrase}")
        else:
            signals.append(f"- Signal {i}: Monitor performance of {phrase}")

    if not signals:
        signals = [f"- Signal 1: Observe behavior of {anchor}"]

    # Build metric rows
    metric_rows = []
    metrics = [
        ("Success Rate", "Count successes / total attempts", "> 95%"),
        ("Error Rate", "Count failures / total attempts", "< 5%"),
        ("Latency", "Measure response time", "< 200ms"),
    ]
    for metric, measure, target in metrics:
        metric_rows.append(f"| {metric} | {measure} | {target} |")

    # Add content-derived metric if we have key phrases
    if key_phrases:
        metric_rows.append(f"| {key_phrases[0]} Coverage | Track coverage | > 80% |")

    template = STUB_TEMPLATES["learning_loop_metrics"]
    return template.format(
        anchor=anchor,
        snippet=snippet,
        learning_signals="\n".join(signals),
        metric_rows="\n".join(metric_rows),
    )


def _generate_stub_holologue_output(
    kind: str,
    selected_items: List[Dict[str, Any]],
) -> str:
    """Generate structured Holologue output using stub templates."""

    n_items = len(selected_items)
    item_titles = "\n".join(f"- {item.get('title', 'Untitled')}" for item in selected_items)

    # Extract themes from items
    themes = []
    for item in selected_items[:3]:  # First 3 items for themes
        anchor = extract_anchor_phrase(item.get("title", ""), item.get("body"))
        themes.append(f"- {anchor}")
    themes_str = "\n".join(themes) if themes else "- (themes to be identified)"

    template = HOLOLOGUE_TEMPLATES.get(kind, HOLOLOGUE_TEMPLATES["plan"])

    return template.format(
        n_items=n_items,
        item_titles=item_titles,
        themes=themes_str,
    )


# === OpenAI Backend ===

def _get_openai_client():
    """Get OpenAI client if available."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


def _generate_openai_bond_output(
    client,
    prompt_text: str,
    inputs: List[Dict[str, Any]],
    output_type: str,
    recipe_id: Optional[str],
) -> Optional[str]:
    """Generate output using OpenAI API."""
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Build context from inputs
    context_parts = []
    for i, item in enumerate(inputs):
        context_parts.append(f"### Input {i+1}: {item.get('title', 'Untitled')}")
        if item.get("body"):
            # Truncate long bodies
            body = item["body"][:2000]
            if len(item["body"]) > 2000:
                body += "\n...(truncated)"
            context_parts.append(body)

    context = "\n\n".join(context_parts)

    system_prompt = """You are Field-Kit v0.1. Produce ONLY the artifact body.
Follow the requested structure based on the prompt.
Don't mention being an AI. Don't add meta-commentary.
Use markdown formatting. Be concise but thorough."""

    user_prompt = f"""## Prompt
{prompt_text}

## Input Context
{context}

Generate the artifact body now:"""

    try:
        # Try with max_completion_tokens first (newer models like gpt-5.x)
        # Fall back to max_tokens for older models
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=2000,
                temperature=0.7,
            )
        except Exception:
            # Fallback for older models
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2000,
                temperature=0.7,
            )
        return response.choices[0].message.content
    except Exception as e:
        # Log error but don't crash - will fall back to stub
        print(f"[generation] OpenAI error: {e}")
        return None


def _generate_openai_holologue_output(
    client,
    kind: str,
    selected_items: List[Dict[str, Any]],
) -> Optional[str]:
    """Generate Holologue output using OpenAI API."""
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # Build context from selected items
    context_parts = []
    for i, item in enumerate(selected_items):
        context_parts.append(f"### Item {i+1}: {item.get('title', 'Untitled')}")
        if item.get("body"):
            body = item["body"][:1500]
            if len(item["body"]) > 1500:
                body += "\n...(truncated)"
            context_parts.append(body)

    context = "\n\n".join(context_parts)

    kind_instructions = {
        "plan": "Create a comprehensive plan that synthesizes the key points from all items.",
        "checklist": "Create an actionable checklist that covers all important aspects from the items.",
        "spec_fragment": "Create a specification fragment with requirements derived from the items.",
        "experiment": "Design an experiment that tests hypotheses derived from the items.",
        "story_beat": "Create a narrative that connects the themes from all items into a coherent story.",
    }

    instruction = kind_instructions.get(kind, kind_instructions["plan"])

    system_prompt = """You are Field-Kit v0.1. Produce ONLY the artifact body.
Synthesize multiple items into a single coherent output.
Don't mention being an AI. Don't add meta-commentary.
Use markdown formatting. Be thorough but focused."""

    user_prompt = f"""## Task
{instruction}

## Selected Items
{context}

Generate the {kind} artifact body now:"""

    try:
        # Try with max_completion_tokens first (newer models like gpt-5.x)
        # Fall back to max_tokens for older models
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=2500,
                temperature=0.7,
            )
        except Exception:
            # Fallback for older models
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2500,
                temperature=0.7,
            )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[generation] OpenAI error: {e}")
        return None


# === Public API ===

def generate_bond_output(
    prompt_text: str,
    inputs: List[Dict[str, Any]],
    output_type: str = "M",
    recipe_id: Optional[str] = None,
) -> str:
    """
    Generate content for a Bond output Item.

    Tries OpenAI if OPENAI_API_KEY is set, falls back to stub.

    Sprint G2: Tracks warnings when OpenAI fails and falls back to stub.

    Args:
        prompt_text: The prompt text for generation
        inputs: List of input Item dicts
        output_type: "M" or "D"
        recipe_id: Optional recipe ID for structured templates

    Returns:
        Generated body text for the output Item
    """
    _set_generation_warning(None)  # Clear previous warning

    # Try OpenAI first if available
    client = _get_openai_client()
    if client:
        result = _generate_openai_bond_output(
            client, prompt_text, inputs, output_type, recipe_id
        )
        if result:
            return result
        # OpenAI failed, set warning for UI
        _set_generation_warning("OpenAI failed → using stub mode")

    # Fall back to stub
    return _generate_stub_bond_output(prompt_text, inputs, output_type, recipe_id)


def generate_holologue_output(
    kind: str,
    selected_items: List[Dict[str, Any]],
) -> str:
    """
    Generate content for a Holologue output Item.

    Tries OpenAI if OPENAI_API_KEY is set, falls back to stub.

    Sprint G2: Tracks warnings when OpenAI fails and falls back to stub.

    Args:
        kind: Artifact kind (plan, checklist, spec_fragment, experiment, story_beat)
        selected_items: List of selected Item dicts

    Returns:
        Generated body text for the H output Item
    """
    _set_generation_warning(None)  # Clear previous warning

    # Try OpenAI first if available
    client = _get_openai_client()
    if client:
        result = _generate_openai_holologue_output(client, kind, selected_items)
        if result:
            return result
        # OpenAI failed, set warning for UI
        _set_generation_warning("OpenAI failed → using stub mode")

    # Fall back to stub
    return _generate_stub_holologue_output(kind, selected_items)
