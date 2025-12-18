#!/usr/bin/env python3
"""
Sprint G Test: Generation Quality

This script verifies the generation quality improvements:
1. PAGE titles extract meaningful anchors (from Title: line in body)
2. Suggestions include the meaningful anchor (never PAGE 1)
3. Generated output contains structure markers
4. Stub backend produces real structured content

Usage:
    python prototype/scripts/test_sprint_g_generation_quality.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit.spin_recipes import (
    normalize_title_for_anchor,
    extract_anchor_phrase,
    generate_suggestions_for_item,
)
from fieldkit.generation import (
    generate_bond_output,
    generate_holologue_output,
)


# Sample architecture page content
SAMPLE_PAGE_TITLE = "PAGE 1 – Purpose of This Document"
SAMPLE_PAGE_BODY = """PAGE 1 – Purpose of This Document

Title: FIELD – Purpose of the Field Overview

This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory + inference space grounded in The Entrance Way, the Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity.
"""


def test_sprint_g_generation_quality():
    """Run Sprint G Generation Quality tests."""
    print("=" * 70)
    print("SPRINT G TEST: Generation Quality")
    print("=" * 70)

    # === Step 1: Test normalize_title_for_anchor ===
    print("\n" + "-" * 70)
    print("STEP 1: Test normalize_title_for_anchor")
    print("-" * 70)

    # Test PAGE X patterns
    assert normalize_title_for_anchor("PAGE 1 – Purpose") == "Purpose", \
        f"Should strip PAGE 1 – : got '{normalize_title_for_anchor('PAGE 1 – Purpose')}'"
    print("  ✓ 'PAGE 1 – Purpose' -> 'Purpose'")

    assert normalize_title_for_anchor("PAGE 2: Second Chapter") == "Second Chapter", \
        f"Should strip PAGE 2: : got '{normalize_title_for_anchor('PAGE 2: Second Chapter')}'"
    print("  ✓ 'PAGE 2: Second Chapter' -> 'Second Chapter'")

    assert normalize_title_for_anchor("PAGE 10 - Ten") == "Ten", \
        f"Should strip PAGE 10 - : got '{normalize_title_for_anchor('PAGE 10 - Ten')}'"
    print("  ✓ 'PAGE 10 - Ten' -> 'Ten'")

    # Test numeric prefix
    assert normalize_title_for_anchor("01 - Introduction") == "Introduction", \
        f"Should strip 01 - : got '{normalize_title_for_anchor('01 - Introduction')}'"
    print("  ✓ '01 - Introduction' -> 'Introduction'")

    # Test case insensitivity
    assert normalize_title_for_anchor("page 1 – Purpose") == "Purpose", \
        f"Should handle lowercase page: got '{normalize_title_for_anchor('page 1 – Purpose')}'"
    print("  ✓ Case insensitive: 'page 1 – Purpose' -> 'Purpose'")

    # Test non-PAGE title (should be unchanged)
    assert normalize_title_for_anchor("API Rate Limiting") == "API Rate Limiting", \
        f"Non-PAGE title should be unchanged: got '{normalize_title_for_anchor('API Rate Limiting')}'"
    print("  ✓ Non-PAGE title unchanged")

    # === Step 2: Test extract_anchor_phrase with Title: line ===
    print("\n" + "-" * 70)
    print("STEP 2: Test extract_anchor_phrase with Title: line")
    print("-" * 70)

    # Architecture page format: should extract from Title: line
    anchor = extract_anchor_phrase(SAMPLE_PAGE_TITLE, SAMPLE_PAGE_BODY)
    print(f"  Input title: '{SAMPLE_PAGE_TITLE}'")
    print(f"  Input body has Title: line")
    print(f"  Extracted anchor: '{anchor}'")

    assert "PAGE" not in anchor.upper(), \
        f"Anchor must NOT contain PAGE: got '{anchor}'"
    print("  ✓ Anchor does not contain 'PAGE'")

    assert "FIELD" in anchor or "Purpose of the Field Overview" in anchor, \
        f"Anchor should contain meaningful title from Title: line: got '{anchor}'"
    print("  ✓ Anchor contains meaningful title text")

    # Test without Title: line but with PAGE title
    body_no_title = "Some content about architecture."
    anchor2 = extract_anchor_phrase("PAGE 3 – Architecture", body_no_title)
    print(f"\n  Input title: 'PAGE 3 – Architecture' (no Title: line)")
    print(f"  Extracted anchor: '{anchor2}'")
    assert "PAGE" not in anchor2.upper(), \
        f"Anchor must NOT contain PAGE: got '{anchor2}'"
    assert "Architecture" in anchor2, \
        f"Should extract normalized title: got '{anchor2}'"
    print("  ✓ Falls back to normalized title")

    # === Step 3: Test suggestions never include PAGE ===
    print("\n" + "-" * 70)
    print("STEP 3: Test suggestions never include PAGE anchors")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(
        item_title=SAMPLE_PAGE_TITLE,
        item_body=SAMPLE_PAGE_BODY,
    )

    assert len(suggestions) == 4, f"Should generate 4 suggestions, got {len(suggestions)}"
    print(f"  Generated {len(suggestions)} suggestions")

    for i, s in enumerate(suggestions, 1):
        prompt = s["prompt_text"]
        # Check that PAGE is not in the prompt (as the anchor)
        assert "PAGE 1" not in prompt, \
            f"Suggestion {i} should not have 'PAGE 1' as anchor: {prompt}"
        print(f"  {i}. [{s['recipe_id']}] {prompt[:60]}...")

    print("  ✓ No suggestions contain 'PAGE 1' as anchor")

    # === Step 4: Test stub generation produces structured output ===
    print("\n" + "-" * 70)
    print("STEP 4: Test stub generation produces structured output")
    print("-" * 70)

    # Test expand_to_checklist recipe
    input_items = [{
        "id": "it_test",
        "title": SAMPLE_PAGE_TITLE,
        "body": SAMPLE_PAGE_BODY,
        "type": "Q",
    }]

    output = generate_bond_output(
        prompt_text="Expand into checklist",
        inputs=input_items,
        output_type="M",
        recipe_id="expand_to_checklist",
    )

    print(f"  Recipe: expand_to_checklist")
    print(f"  Output length: {len(output)} chars")
    print(f"  Output preview: {output[:200]}...")

    # Check structure markers
    assert "# Checklist" in output or "Checklist:" in output, \
        f"expand_to_checklist should produce Checklist heading: {output[:200]}"
    assert "- [ ]" in output or "- " in output, \
        f"Should have checkbox or list items: {output[:300]}"
    print("  ✓ Checklist structure present")

    # Check anchor appears (should be FIELD or similar, not PAGE)
    assert "PAGE 1" not in output, \
        f"Output should not have PAGE 1 as anchor: {output[:300]}"
    print("  ✓ No PAGE 1 in output")

    # Test ground_in_experiment recipe
    output2 = generate_bond_output(
        prompt_text="Propose experiment",
        inputs=input_items,
        output_type="M",
        recipe_id="ground_in_experiment",
    )

    print(f"\n  Recipe: ground_in_experiment")
    print(f"  Output preview: {output2[:200]}...")

    assert "Hypothesis" in output2 or "Method" in output2 or "Experiment" in output2, \
        f"ground_in_experiment should have experiment headings: {output2[:300]}"
    print("  ✓ Experiment structure present")

    # Test derive_min_schema recipe
    output3 = generate_bond_output(
        prompt_text="Derive schema",
        inputs=input_items,
        output_type="M",
        recipe_id="derive_min_schema",
    )

    print(f"\n  Recipe: derive_min_schema")
    print(f"  Output preview: {output3[:200]}...")

    assert "Entities" in output3 or "Fields" in output3 or "Schema" in output3, \
        f"derive_min_schema should have schema headings: {output3[:300]}"
    print("  ✓ Schema structure present")

    # Test decision_with_reasons recipe
    output4 = generate_bond_output(
        prompt_text="Decision",
        inputs=input_items,
        output_type="M",
        recipe_id="decision_with_reasons",
    )

    print(f"\n  Recipe: decision_with_reasons")
    print(f"  Output preview: {output4[:200]}...")

    assert "Decision" in output4 or "Rationale" in output4 or "Recommendation" in output4, \
        f"decision_with_reasons should have decision headings: {output4[:300]}"
    print("  ✓ Decision structure present")

    # === Step 5: Test Holologue generation ===
    print("\n" + "-" * 70)
    print("STEP 5: Test Holologue generation")
    print("-" * 70)

    selected_items = [
        {"id": "it_1", "title": "Item One", "body": "First item content"},
        {"id": "it_2", "title": "Item Two", "body": "Second item content"},
    ]

    holo_output = generate_holologue_output(
        kind="plan",
        selected_items=selected_items,
    )

    print(f"  Kind: plan")
    print(f"  Output length: {len(holo_output)} chars")
    print(f"  Output preview: {holo_output[:200]}...")

    assert "Plan" in holo_output or "Synthesis" in holo_output or "Overview" in holo_output, \
        f"Plan output should have plan headings: {holo_output[:300]}"
    print("  ✓ Plan structure present")

    holo_checklist = generate_holologue_output(
        kind="checklist",
        selected_items=selected_items,
    )

    print(f"\n  Kind: checklist")
    print(f"  Output preview: {holo_checklist[:200]}...")

    assert "Checklist" in holo_checklist or "- [ ]" in holo_checklist, \
        f"Checklist output should have checklist structure: {holo_checklist[:300]}"
    print("  ✓ Checklist structure present")

    # === Step 6: Full CLI integration test ===
    print("\n" + "-" * 70)
    print("STEP 6: Full CLI integration test")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create item with PAGE title
        item_id = cli.cmd_item_create(
            title=SAMPLE_PAGE_TITLE,
            body=SAMPLE_PAGE_BODY,
        )
        print(f"  Created item: {item_id}")

        # Get suggestions
        suggestions = cli.cmd_suggestions_show(item_id)
        print(f"  Got {len(suggestions)} suggestions")

        # Verify no PAGE in suggestions
        for s in suggestions:
            assert "PAGE 1" not in s["prompt_text"], \
                f"Suggestion should not have PAGE 1: {s['prompt_text']}"
        print("  ✓ No PAGE 1 in suggestions")

        # Create and run bond
        bond_id = cli.cmd_bond_create(
            input_item_ids=[item_id],
            prompt_text=suggestions[0]["prompt_text"],
            intent_type=suggestions[0]["intent_type"],
            recipe_id=suggestions[0]["recipe_id"],
        )
        print(f"  Created bond: {bond_id}")

        output_item_id = cli.cmd_bond_run(bond_id, output_type="M")
        print(f"  Bond executed, output: {output_item_id}")

        # Verify output item has real content
        output_item = cli.store.get_item(output_item_id)
        output_body = output_item["body"]

        print(f"  Output body length: {len(output_body)} chars")
        print(f"  Output body preview: {output_body[:150]}...")

        assert "Generated content for prompt" not in output_body, \
            f"Output should not have placeholder text: {output_body[:200]}"
        print("  ✓ No placeholder text in output")

        assert len(output_body) > 100, \
            f"Output should be substantial (>100 chars): {len(output_body)} chars"
        print("  ✓ Output is substantial")

        # Check output title doesn't have PAGE
        output_title = output_item["title"]
        assert "PAGE 1" not in output_title, \
            f"Output title should not have PAGE 1: {output_title}"
        print(f"  ✓ Output title: '{output_title}'")

    # === Final Summary ===
    print("\n" + "=" * 70)
    print("SPRINT G TEST COMPLETE - ALL ASSERTIONS PASSED!")
    print("=" * 70)

    print("\nSummary:")
    print("  - normalize_title_for_anchor: VERIFIED")
    print("  - extract_anchor_phrase (Title: line): VERIFIED")
    print("  - Suggestions never include PAGE: VERIFIED")
    print("  - Stub generation (expand_to_checklist): VERIFIED")
    print("  - Stub generation (ground_in_experiment): VERIFIED")
    print("  - Stub generation (derive_min_schema): VERIFIED")
    print("  - Stub generation (decision_with_reasons): VERIFIED")
    print("  - Holologue generation: VERIFIED")
    print("  - CLI integration (no placeholder text): VERIFIED")

    return True


if __name__ == "__main__":
    try:
        success = test_sprint_g_generation_quality()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
