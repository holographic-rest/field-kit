#!/usr/bin/env python3
"""
Sprint G: Bond Suggestions Regression Test (Handle-Based Sentence-Hyperlinks)

Tests the 2-stage handle-based pipeline for generating sentence-hyperlink suggestions:
1. Handle Picker: Extract 8-15 candidate handles from Item content
2. Diversity Selection: Pick 4 diverse handles (different kinds)
3. Sentence Composition: Compose custom sentence-hyperlinks per intent

Test cases:
1. Two different Q Items generate suggestions
2. Exactly 4 suggestions per item
3. Quoted handle exists verbatim in item body/title
4. 4 handles are distinct (no duplicates)
5. Two items' suggestions are different (Jaccard similarity < 0.6)
6. No "test case that validates" without test-ish words (anti-generic rule)

Usage:
    python prototype/scripts/test_sprint_g_bond_suggestions.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.bond_suggester import (
    extract_handles,
    select_diverse_handles,
    generate_suggestions,
    Handle,
    TEST_WORDS,
)
from fieldkit.spin_recipes import generate_suggestions_for_item


# === Test Fixtures ===

# Fixture 1: Field Overview document (complex architecture content)
FIELD_OVERVIEW_TITLE = "PAGE 1 – Purpose of the Field Overview"
FIELD_OVERVIEW_BODY = """Title: FIELD – Purpose of the Field Overview

This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory and inference space grounded in The Entrance Way, the Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity."""

# Fixture 2: Simple user input (short content)
SIMPLE_ITEM_TITLE = "I want to explore the butthead paradigm"
SIMPLE_ITEM_BODY = "I want to explore the butthead paradigm in modern software development and see how it applies to testing."


# === Test Functions ===

def test_extract_handles_field_overview():
    """Test: Handle extraction from complex architecture content."""
    print("\n" + "-" * 70)
    print("TEST 1: Handle extraction from Field Overview")
    print("-" * 70)

    handles = extract_handles(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles[:10], 1):
        print(f"    {i}. [{h.kind}] '{h.text}'")

    # Assertions
    assert len(handles) >= 6, f"Expected at least 6 handles, got {len(handles)}"
    assert len(handles) <= 20, f"Expected at most 20 handles, got {len(handles)}"

    # Should have diverse kinds
    kinds = {h.kind for h in handles}
    assert len(kinds) >= 2, f"Expected at least 2 handle kinds, got {kinds}"

    # No handle should be a PAGE pattern
    for h in handles:
        assert not h.text.upper().startswith("PAGE"), \
            f"Handle should not be PAGE pattern: '{h.text}'"

    print("  PASSED: Handles extracted with diversity and no PAGE patterns")
    return True


def test_extract_handles_short_content():
    """Test: Handle extraction from short content (butthead test)."""
    print("\n" + "-" * 70)
    print("TEST 2: Handle extraction from short content")
    print("-" * 70)

    handles = extract_handles(SIMPLE_ITEM_TITLE, SIMPLE_ITEM_BODY)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. [{h.kind}] '{h.text}'")

    # Should have at least 1 handle
    assert len(handles) >= 1, f"Expected at least 1 handle, got {len(handles)}"

    # Should contain "butthead" or related content
    all_text = " ".join(h.text.lower() for h in handles)
    assert "butthead" in all_text or "paradigm" in all_text, \
        f"Expected 'butthead' or 'paradigm' in handles"

    print("  PASSED: Short content handles extracted correctly")
    return True


def test_select_diverse_handles():
    """Test: Diversity selection picks 4 different handles."""
    print("\n" + "-" * 70)
    print("TEST 3: Diversity selection (4 handles, different kinds)")
    print("-" * 70)

    handles = extract_handles(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)
    diverse = select_diverse_handles(handles)

    print(f"  Selected {len(diverse)} diverse handles:")
    for i, h in enumerate(diverse, 1):
        print(f"    {i}. [{h.kind}] '{h.text}'")

    # Exactly 4 handles
    assert len(diverse) == 4, f"Expected 4 diverse handles, got {len(diverse)}"

    # All handles should be distinct (no duplicates)
    texts = [h.text.lower() for h in diverse]
    assert len(set(texts)) == 4, f"Expected 4 distinct handles, got duplicates: {texts}"

    print("  PASSED: 4 diverse, distinct handles selected")
    return True


def test_generate_suggestions_exactly_4():
    """Test: Generate exactly 4 suggestions per item."""
    print("\n" + "-" * 70)
    print("TEST 4: Generate exactly 4 suggestions")
    print("-" * 70)

    suggestions = generate_suggestions(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)

    print(f"  Generated {len(suggestions)} suggestions:")
    for i, s in enumerate(suggestions, 1):
        print(f"    {i}. [{s['intent']}] {s['prompt_text'][:60]}...")

    assert len(suggestions) == 4, f"Expected 4 suggestions, got {len(suggestions)}"

    print("  PASSED: Exactly 4 suggestions generated")
    return True


def test_quoted_handle_in_body():
    """Test: Each suggestion's handle exists verbatim in item body/title."""
    print("\n" + "-" * 70)
    print("TEST 5: Quoted handle exists in item content")
    print("-" * 70)

    suggestions = generate_suggestions(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)
    full_content = (FIELD_OVERVIEW_TITLE + " " + FIELD_OVERVIEW_BODY).lower()

    print(f"  Checking {len(suggestions)} suggestions for verbatim handles:")

    all_valid = True
    for i, s in enumerate(suggestions, 1):
        handle = s["handle"]
        handle_lower = handle.lower()

        # Handle should be a substring of the original content
        exists_in_content = handle_lower in full_content

        status = "OK" if exists_in_content else "FAIL"
        print(f"    {i}. [{status}] '{handle[:40]}...'")

        if not exists_in_content:
            all_valid = False

    assert all_valid, "Not all handles exist verbatim in item content"

    print("  PASSED: All handles exist in item content")
    return True


def test_handles_are_distinct():
    """Test: All 4 handles in suggestions are distinct."""
    print("\n" + "-" * 70)
    print("TEST 6: 4 handles are distinct (no duplicates)")
    print("-" * 70)

    suggestions = generate_suggestions(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)

    handles = [s["handle"] for s in suggestions]
    print(f"  Handles:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h}'")

    unique_handles = set(h.lower() for h in handles)
    assert len(unique_handles) == 4, \
        f"Expected 4 distinct handles, got {len(unique_handles)}: {handles}"

    print("  PASSED: All 4 handles are distinct")
    return True


def test_two_items_different_suggestions():
    """Test: Two different items produce different suggestions (Jaccard < 0.6)."""
    print("\n" + "-" * 70)
    print("TEST 7: Two items produce different suggestions")
    print("-" * 70)

    sugg1 = generate_suggestions(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)
    sugg2 = generate_suggestions(SIMPLE_ITEM_TITLE, SIMPLE_ITEM_BODY)

    print(f"  Item 1 handles: {[s['handle'][:20] for s in sugg1]}")
    print(f"  Item 2 handles: {[s['handle'][:20] for s in sugg2]}")

    # Compare handles using Jaccard similarity
    set1 = set(s["handle"].lower() for s in sugg1)
    set2 = set(s["handle"].lower() for s in sugg2)

    intersection = set1 & set2
    union = set1 | set2
    jaccard = len(intersection) / len(union) if union else 0

    print(f"  Jaccard similarity: {jaccard:.2f}")

    assert jaccard < 0.6, f"Suggestions too similar (Jaccard {jaccard:.2f} >= 0.6)"

    print("  PASSED: Different items produce different suggestions")
    return True


def test_anti_generic_rule():
    """Test: No 'test case that validates' without test-ish words."""
    print("\n" + "-" * 70)
    print("TEST 8: Anti-generic rule (no test case without test words)")
    print("-" * 70)

    # Content WITHOUT test-ish words
    no_test_title = "The architecture of our memory system"
    no_test_body = "A living memory and inference space grounded in neural patterns."

    suggestions = generate_suggestions(no_test_title, no_test_body)

    print(f"  Checking {len(suggestions)} suggestions for anti-generic rule:")

    violations = []
    for i, s in enumerate(suggestions, 1):
        prompt = s["prompt_text"].lower()
        handle = s["handle"].lower()

        # Check if prompt contains "test case" patterns
        has_test_pattern = (
            "test case" in prompt or
            "test that validates" in prompt or
            "validation test" in prompt
        )

        # Check if handle has test-ish words
        has_test_words = any(tw in handle for tw in TEST_WORDS)

        status = "OK"
        if has_test_pattern and not has_test_words:
            status = "VIOLATION"
            violations.append(s)

        print(f"    {i}. [{status}] {s['prompt_text'][:50]}...")

    assert len(violations) == 0, \
        f"Found {len(violations)} anti-generic violations: {[v['prompt_text'][:50] for v in violations]}"

    print("  PASSED: No anti-generic violations")
    return True


def test_intents_are_diverse():
    """Test: Suggestions have diverse intents (at least 3 unique)."""
    print("\n" + "-" * 70)
    print("TEST 9: At least 3 distinct intents")
    print("-" * 70)

    suggestions = generate_suggestions(FIELD_OVERVIEW_TITLE, FIELD_OVERVIEW_BODY)

    intents = [s.get("intent", s.get("intent_type", "")).replace("_", " ").title() for s in suggestions]
    print(f"  Intents: {intents}")

    unique_intents = set(intents)
    print(f"  Unique intents: {len(unique_intents)}")

    # Varied system uses different intents based on content (not fixed 4)
    assert len(unique_intents) >= 3, \
        f"Expected at least 3 distinct intents, got {len(unique_intents)}: {unique_intents}"

    print("  PASSED: At least 3 distinct intents")
    return True


def test_legacy_format_compatibility():
    """Test: generate_suggestions_for_item returns legacy format."""
    print("\n" + "-" * 70)
    print("TEST 10: Legacy format compatibility")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(
        FIELD_OVERVIEW_TITLE,
        FIELD_OVERVIEW_BODY,
    )

    print(f"  Generated {len(suggestions)} suggestions in legacy format:")
    for i, s in enumerate(suggestions, 1):
        print(f"    {i}. display_text: {s['display_text'][:50]}...")
        print(f"       intent_type: {s['intent_type']}, recipe_id: {s['recipe_id']}")

    # Check legacy format keys
    required_keys = {"display_text", "prompt_text", "intent_type", "recipe_id"}
    for s in suggestions:
        missing = required_keys - set(s.keys())
        assert not missing, f"Missing legacy keys: {missing}"

    assert len(suggestions) == 4, f"Expected 4 suggestions, got {len(suggestions)}"

    print("  PASSED: Legacy format compatible")
    return True


def main():
    """Run all bond suggestions tests."""
    print("=" * 70)
    print("SPRINT G: BOND SUGGESTIONS REGRESSION TEST")
    print("=" * 70)
    print("Testing 2-stage handle-based sentence-hyperlink pipeline")

    tests = [
        ("Handle extraction (complex)", test_extract_handles_field_overview),
        ("Handle extraction (short)", test_extract_handles_short_content),
        ("Diversity selection", test_select_diverse_handles),
        ("Exactly 4 suggestions", test_generate_suggestions_exactly_4),
        ("Quoted handle in body", test_quoted_handle_in_body),
        ("Handles are distinct", test_handles_are_distinct),
        ("Two items differ", test_two_items_different_suggestions),
        ("Anti-generic rule", test_anti_generic_rule),
        ("Intents are diverse", test_intents_are_diverse),
        ("Legacy format", test_legacy_format_compatibility),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            test_fn()
            results[name] = True
        except AssertionError as e:
            print(f"\n  [FAIL] {e}")
            results[name] = False
        except Exception as e:
            print(f"\n  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All bond suggestions tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
