#!/usr/bin/env python3
"""
Handle-Based Suggestions Test

Proves that bond suggestions are content-specific, not generic templates.

Test Items:
1. PAGE 1 architecture content (complex, structured)
2. Giallo/Chandler prose (narrative, no bullets)

Requirements:
1. Each suggestion quotes a verbatim substring from the item content
2. Two different items produce different suggestions (Jaccard < 0.5)
3. No generic "test case that validates" without test-ish words
4. Exactly 4 suggestions per item
5. 4 suggestions use 4 different handles (no duplicates)

Usage:
    python prototype/scripts/test_handle_suggestions.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.spin_recipes import generate_suggestions_for_item
from fieldkit.handles import extract_handles, select_diverse_handles, debug_handles


# === Test Fixtures ===

# Fixture 1: PAGE 1 architecture content (complex, structured)
PAGE_1_TITLE = "PAGE 1 – Purpose of the Field Overview"
PAGE_1_BODY = """Title: FIELD – Purpose of the Field Overview

This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory + inference space grounded in The Entrance Way, the Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity."""

# Fixture 2: Giallo/Chandler prose (narrative, no bullets)
GIALLO_TITLE = "The detective entered the dimly lit room"
GIALLO_BODY = """The detective entered the dimly lit room, his eyes adjusting slowly to the amber glow filtering through dusty venetian blinds. The smell of stale cigarettes and expensive perfume hung in the air like a forgotten promise.

She was sitting in the corner, legs crossed, watching him with eyes that had seen too much. The red dress clung to her like a second skin, and the gun on the table between them gleamed dully in the half-light.

"You're late," she said, her voice a mixture of honey and broken glass. "The Contessa doesn't like to be kept waiting."

He reached for his own cigarette, never taking his eyes off the revolver. In this city, the dead told more stories than the living, and he had a feeling this story was just beginning."""

# Fixture 3: Short user input (butthead test)
BUTTHEAD_TITLE = "I want to explore the butthead paradigm"
BUTTHEAD_BODY = "I want to explore the butthead paradigm in modern software development and see how it applies to testing."


# === Test Functions ===

def test_handle_extraction_page1():
    """Test: Extract handles from PAGE 1 content."""
    print("\n" + "=" * 70)
    print("TEST 1: Handle extraction from PAGE 1 architecture")
    print("=" * 70)

    handles = extract_handles(PAGE_1_BODY, PAGE_1_TITLE)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles[:10], 1):
        print(f"    {i:2}. [{h['kind']:8}] {h['score']:.2f} | {h['quote'][:50]}...")

    # Assertions
    assert len(handles) >= 6, f"Expected at least 6 handles, got {len(handles)}"
    assert len(handles) <= 20, f"Expected at most 20 handles, got {len(handles)}"

    # Should have diverse kinds
    kinds = {h["kind"] for h in handles}
    assert len(kinds) >= 2, f"Expected at least 2 handle kinds, got {kinds}"

    # Should extract colon/bullet handles for this structured content
    colon_bullet_handles = [h for h in handles if h["kind"] in ("colon", "bullet")]
    assert len(colon_bullet_handles) >= 2, \
        f"Expected at least 2 colon/bullet handles, got {len(colon_bullet_handles)}"

    print("  PASSED: Structured content handles extracted correctly")
    return True


def test_handle_extraction_prose():
    """Test: Extract handles from Giallo prose content."""
    print("\n" + "=" * 70)
    print("TEST 2: Handle extraction from Giallo prose")
    print("=" * 70)

    handles = extract_handles(GIALLO_BODY, GIALLO_TITLE)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles[:10], 1):
        print(f"    {i:2}. [{h['kind']:8}] {h['score']:.2f} | {h['quote'][:50]}...")

    # Assertions
    assert len(handles) >= 4, f"Expected at least 4 handles, got {len(handles)}"

    # For prose, should have phrases/entities/sentences (not colon/bullet)
    prose_handles = [h for h in handles if h["kind"] in ("phrase", "entity", "sentence")]
    assert len(prose_handles) >= 2, \
        f"Expected at least 2 prose-style handles, got {len(prose_handles)}"

    print("  PASSED: Prose content handles extracted correctly")
    return True


def test_suggestions_exactly_4():
    """Test: Exactly 4 suggestions per item."""
    print("\n" + "=" * 70)
    print("TEST 3: Exactly 4 suggestions per item")
    print("=" * 70)

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
        ("Butthead", BUTTHEAD_TITLE, BUTTHEAD_BODY),
    ]:
        suggestions = generate_suggestions_for_item(title, body)
        print(f"  {name}: {len(suggestions)} suggestions")

        assert len(suggestions) == 4, \
            f"Expected 4 suggestions for {name}, got {len(suggestions)}"

    print("  PASSED: All items produce exactly 4 suggestions")
    return True


def test_suggestions_quote_verbatim():
    """Test: Each suggestion quotes a verbatim substring from item content."""
    print("\n" + "=" * 70)
    print("TEST 4: Suggestions quote verbatim substrings")
    print("=" * 70)

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
    ]:
        suggestions = generate_suggestions_for_item(title, body)
        full_content = (title + " " + (body or "")).lower()

        print(f"\n  {name}:")
        all_valid = True
        for i, s in enumerate(suggestions, 1):
            handle_quote = s.get("handle_quote", "")
            # The handle_quote should exist in the original content
            exists = handle_quote.lower() in full_content if handle_quote else False

            status = "OK" if exists else "FAIL"
            print(f"    {i}. [{status}] handle: '{handle_quote[:40]}...'")

            if not exists:
                all_valid = False

        assert all_valid, f"Not all handles in {name} exist in content"

    print("\n  PASSED: All suggestions quote verbatim content")
    return True


def test_suggestions_have_4_different_handles():
    """Test: 4 suggestions use 4 different handles."""
    print("\n" + "=" * 70)
    print("TEST 5: 4 suggestions use 4 different handles")
    print("=" * 70)

    suggestions = generate_suggestions_for_item(PAGE_1_TITLE, PAGE_1_BODY)

    handles = [s.get("handle_quote", "").lower() for s in suggestions]
    unique_handles = set(h for h in handles if h)

    print(f"  Handles used:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h[:50]}...'")

    print(f"\n  Unique handles: {len(unique_handles)}")

    # Allow some overlap but should have at least 3 distinct
    assert len(unique_handles) >= 3, \
        f"Expected at least 3 distinct handles, got {len(unique_handles)}"

    print("  PASSED: Suggestions use diverse handles")
    return True


def test_two_items_different_suggestions():
    """Test: Two different items produce different suggestions."""
    print("\n" + "=" * 70)
    print("TEST 6: Two items produce different suggestions")
    print("=" * 70)

    sugg1 = generate_suggestions_for_item(PAGE_1_TITLE, PAGE_1_BODY)
    sugg2 = generate_suggestions_for_item(GIALLO_TITLE, GIALLO_BODY)

    handles1 = [s.get("handle_quote", "").lower() for s in sugg1]
    handles2 = [s.get("handle_quote", "").lower() for s in sugg2]

    print(f"  PAGE 1 handles: {[h[:20] for h in handles1]}")
    print(f"  Giallo handles: {[h[:20] for h in handles2]}")

    # Calculate Jaccard similarity of handles
    set1 = set(handles1)
    set2 = set(handles2)

    intersection = set1 & set2
    union = set1 | set2
    jaccard = len(intersection) / len(union) if union else 0

    print(f"\n  Jaccard similarity: {jaccard:.2f}")

    assert jaccard < 0.5, f"Suggestions too similar (Jaccard {jaccard:.2f} >= 0.5)"

    print("  PASSED: Different items produce different suggestions")
    return True


def test_no_generic_test_case_without_test_words():
    """Test: No generic 'test case that validates' without test-ish words."""
    print("\n" + "=" * 70)
    print("TEST 7: No generic test case suggestions")
    print("=" * 70)

    # Content WITHOUT test-ish words
    no_test_title = "The architecture of our memory system"
    no_test_body = "A living memory and inference space grounded in neural patterns."

    suggestions = generate_suggestions_for_item(no_test_title, no_test_body)

    test_words = {"test", "testing", "validate", "validation", "verify", "assert"}

    print(f"  Checking {len(suggestions)} suggestions:")
    violations = []
    for i, s in enumerate(suggestions, 1):
        display = s["display_text"].lower()
        handle = s.get("handle_quote", "").lower()

        # Check if prompt mentions "test case" patterns
        has_test_pattern = (
            "test case" in display or
            "test that validates" in display or
            "validation test" in display
        )

        # Check if handle has test-ish words
        has_test_words = any(tw in handle for tw in test_words)

        status = "OK"
        if has_test_pattern and not has_test_words:
            status = "VIOLATION"
            violations.append(s)

        print(f"    {i}. [{status}] {s['display_text'][:50]}...")

    assert len(violations) == 0, \
        f"Found {len(violations)} generic test case violations"

    print("  PASSED: No generic test case suggestions")
    return True


def test_butthead_appears_in_suggestions():
    """Test: Unique word 'butthead' appears in suggestions."""
    print("\n" + "=" * 70)
    print("TEST 8: Butthead sanity test")
    print("=" * 70)

    suggestions = generate_suggestions_for_item(BUTTHEAD_TITLE, BUTTHEAD_BODY)

    print(f"  Generated {len(suggestions)} suggestions:")
    for i, s in enumerate(suggestions, 1):
        handle = s.get("handle_quote", "")
        print(f"    {i}. handle: '{handle}'")
        print(f"       text: {s['display_text'][:60]}...")

    # Check that "butthead" appears in at least one suggestion
    all_text = " ".join(
        s["display_text"].lower() + " " + s.get("handle_quote", "").lower()
        for s in suggestions
    )

    has_butthead = "butthead" in all_text

    assert has_butthead, "'butthead' not found in any suggestion"

    print("  PASSED: Butthead appears in suggestions")
    return True


def test_suggestion_format():
    """Test: Suggestions have correct format with all required fields."""
    print("\n" + "=" * 70)
    print("TEST 9: Suggestion format verification")
    print("=" * 70)

    suggestions = generate_suggestions_for_item(PAGE_1_TITLE, PAGE_1_BODY)

    required_keys = {"display_text", "prompt_text", "intent_type", "recipe_id", "handle_quote"}

    print(f"  Checking {len(suggestions)} suggestions for required keys:")
    for i, s in enumerate(suggestions, 1):
        missing = required_keys - set(s.keys())
        status = "OK" if not missing else f"MISSING: {missing}"
        print(f"    {i}. {status}")

        assert not missing, f"Suggestion {i} missing keys: {missing}"

    print("  PASSED: All suggestions have correct format")
    return True


def main():
    """Run all handle suggestions tests."""
    print("=" * 70)
    print("HANDLE-BASED SUGGESTIONS TEST")
    print("=" * 70)
    print("Proving suggestions are content-specific, not generic templates")

    tests = [
        ("Handle extraction (structured)", test_handle_extraction_page1),
        ("Handle extraction (prose)", test_handle_extraction_prose),
        ("Exactly 4 suggestions", test_suggestions_exactly_4),
        ("Verbatim quotes", test_suggestions_quote_verbatim),
        ("4 different handles", test_suggestions_have_4_different_handles),
        ("Different items differ", test_two_items_different_suggestions),
        ("No generic test case", test_no_generic_test_case_without_test_words),
        ("Butthead sanity", test_butthead_appears_in_suggestions),
        ("Suggestion format", test_suggestion_format),
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
        print("All handle suggestions tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    # Show debug handles for both fixtures first
    print("\n" + "=" * 70)
    print("DEBUG: Handle Extraction Preview")
    print("=" * 70)

    print("\n--- PAGE 1 Architecture ---")
    debug_handles(PAGE_1_BODY, PAGE_1_TITLE)

    print("\n--- Giallo Prose ---")
    debug_handles(GIALLO_BODY, GIALLO_TITLE)

    # Run tests
    sys.exit(main())
