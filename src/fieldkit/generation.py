"""
Field-Kit v0.1 Generation Backend

Provides real content generation for Bond and Holologue outputs.

Backends:
1. Stub backend (default, no network): Deterministic structured text based on recipe_id
2. OpenAI backend (optional): Uses OPENAI_API_KEY if set

Environment variables:
- OPENAI_API_KEY: If set, enables OpenAI backend
- OPENAI_MODEL: Model to use (default: gpt-4o-mini)
"""

import os
import re
from typing import List, Dict, Any, Optional

from .spin_recipes import extract_anchor_phrase


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


def _generate_stub_bond_output(
    prompt_text: str,
    inputs: List[Dict[str, Any]],
    output_type: str,
    recipe_id: Optional[str],
) -> str:
    """Generate structured output using stub templates."""

    # Get anchor and snippet from first input
    if inputs:
        first_input = inputs[0]
        anchor = extract_anchor_phrase(
            first_input.get("title", ""),
            first_input.get("body"),
        )
        snippet = _get_snippet(first_input.get("body"))
    else:
        anchor = "this item"
        snippet = "(no input provided)"

    # Select template based on recipe_id
    template = STUB_TEMPLATES.get(recipe_id)

    if template:
        return template.format(anchor=anchor, snippet=snippet)

    # Fallback: generic structured output
    return f"""# Output: {anchor}

## Analysis
Based on the prompt: {prompt_text[:100]}...

## Key Points
- Primary consideration from the input
- Secondary implications to explore
- Potential areas for follow-up

## Recommendations
1. Review the generated content for accuracy
2. Refine based on specific needs
3. Iterate as necessary

---
*Generated for: {anchor}*
*Based on: {snippet}*
"""


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

    Args:
        prompt_text: The prompt text for generation
        inputs: List of input Item dicts
        output_type: "M" or "D"
        recipe_id: Optional recipe ID for structured templates

    Returns:
        Generated body text for the output Item
    """
    # Try OpenAI first if available
    client = _get_openai_client()
    if client:
        result = _generate_openai_bond_output(
            client, prompt_text, inputs, output_type, recipe_id
        )
        if result:
            return result

    # Fall back to stub
    return _generate_stub_bond_output(prompt_text, inputs, output_type, recipe_id)


def generate_holologue_output(
    kind: str,
    selected_items: List[Dict[str, Any]],
) -> str:
    """
    Generate content for a Holologue output Item.

    Tries OpenAI if OPENAI_API_KEY is set, falls back to stub.

    Args:
        kind: Artifact kind (plan, checklist, spec_fragment, experiment, story_beat)
        selected_items: List of selected Item dicts

    Returns:
        Generated body text for the H output Item
    """
    # Try OpenAI first if available
    client = _get_openai_client()
    if client:
        result = _generate_openai_holologue_output(client, kind, selected_items)
        if result:
            return result

    # Fall back to stub
    return _generate_stub_holologue_output(kind, selected_items)
