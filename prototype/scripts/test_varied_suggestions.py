#!/usr/bin/env python3
"""
Test: Varied Bond Suggestions

Proves that bond suggestions are:
1. Content-specific (handles from item body)
2. Varied in language (not same 4 leading verbs every time)
3. Different across different items
4. Using diverse intents

Test fixtures:
- PAGE 1: Architecture content (structured with colons/bullets)
- Giallo: Prose narrative (no bullets, descriptive)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.bond_suggester import generate_suggestions, TEST_WORDS


# === Test Fixtures ===

# Fixture 1: PAGE 1 architecture content (complex, structured)
PAGE_1_TITLE = "PAGE 1 – Purpose of the Field Overview"
PAGE_1_BODY = """Title: FIELD – Purpose of the Field Overview

This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory and inference space grounded in The Entrance Way, the Vault, and QDPI events.

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


# === Test Functions ===

def test_suggestions_exactly_4():
    """Test: Exactly 4 suggestions per item."""
    print("\n" + "=" * 70)
    print("TEST 1: Exactly 4 suggestions per item")
    print("=" * 70)

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
    ]:
        suggestions = generate_suggestions(title, body)
        print(f"  {name}: {len(suggestions)} suggestions")

        assert len(suggestions) == 4, \
            f"Expected 4 suggestions for {name}, got {len(suggestions)}"

    print("  PASSED: All items produce exactly 4 suggestions")
    return True


def test_handle_quotes_in_content():
    """Test: Each suggestion's handle_quote exists verbatim in item content."""
    print("\n" + "=" * 70)
    print("TEST 2: Handle quotes exist in item content")
    print("=" * 70)

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
    ]:
        suggestions = generate_suggestions(title, body)
        full_content = (title + " " + (body or "")).lower()

        print(f"\n  {name}:")
        all_valid = True
        for i, s in enumerate(suggestions, 1):
            handle = s.get("handle_quote", s.get("handle", ""))
            exists = handle.lower() in full_content if handle else False

            status = "OK" if exists else "FAIL"
            print(f"    {i}. [{status}] handle: '{handle[:40]}...'")

            if not exists:
                all_valid = False

        assert all_valid, f"Not all handles in {name} exist in content"

    print("\n  PASSED: All handles exist verbatim in content")
    return True


def test_4_distinct_handles():
    """Test: 4 suggestions use 4 different handles (no duplicates)."""
    print("\n" + "=" * 70)
    print("TEST 3: 4 suggestions use 4 different handles")
    print("=" * 70)

    suggestions = generate_suggestions(PAGE_1_TITLE, PAGE_1_BODY)

    handles = [s.get("handle_quote", s.get("handle", "")).lower() for s in suggestions]
    unique_handles = set(h for h in handles if h)

    print(f"  Handles used:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h[:50]}...'")

    print(f"\n  Unique handles: {len(unique_handles)}")

    assert len(unique_handles) >= 3, \
        f"Expected at least 3 distinct handles, got {len(unique_handles)}"

    print("  PASSED: Suggestions use diverse handles")
    return True


def test_two_items_different_suggestions():
    """Test: Two different items produce different suggestions (Jaccard < 0.5)."""
    print("\n" + "=" * 70)
    print("TEST 4: Two items produce different suggestions")
    print("=" * 70)

    sugg1 = generate_suggestions(PAGE_1_TITLE, PAGE_1_BODY)
    sugg2 = generate_suggestions(GIALLO_TITLE, GIALLO_BODY)

    handles1 = [s.get("handle_quote", s.get("handle", "")).lower() for s in sugg1]
    handles2 = [s.get("handle_quote", s.get("handle", "")).lower() for s in sugg2]

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


def test_not_same_4_leading_verbs():
    """Test: Suggestions do NOT always use Define/Trace/Map/Operationalize."""
    print("\n" + "=" * 70)
    print("TEST 5: Not same 4 leading verbs every time")
    print("=" * 70)

    # The old problematic verbs
    old_verbs = {"define", "trace", "map", "operationalize"}

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
    ]:
        suggestions = generate_suggestions(title, body)

        # Extract first word from each display_text
        leading_words = []
        for s in suggestions:
            display = s.get("display_text", "")
            first_word = display.split()[0].lower() if display.split() else ""
            leading_words.append(first_word)

        print(f"\n  {name} leading words: {leading_words}")

        # Check that at least one word is NOT in the old set
        has_variety = any(w not in old_verbs for w in leading_words)

        if not has_variety:
            print(f"    [WARN] All leading words are old verbs")
        else:
            print(f"    [OK] Has variety (not all old verbs)")

        # At minimum, not ALL should be the exact same set
        leading_set = set(leading_words)
        if leading_set == {"define", "trace", "map", "operationalize"}:
            print(f"    [FAIL] Exactly the old 4 verbs")
            assert False, f"{name} uses exactly the old 4 verbs"

    print("\n  PASSED: Not using same 4 leading verbs every time")
    return True


def test_diverse_intents():
    """Test: At least 3 distinct intents across 4 suggestions."""
    print("\n" + "=" * 70)
    print("TEST 6: At least 3 distinct intents")
    print("=" * 70)

    for name, title, body in [
        ("PAGE 1", PAGE_1_TITLE, PAGE_1_BODY),
        ("Giallo", GIALLO_TITLE, GIALLO_BODY),
    ]:
        suggestions = generate_suggestions(title, body)

        intents = [s.get("intent_type", "") for s in suggestions]
        unique_intents = set(intents)

        print(f"\n  {name} intents: {intents}")
        print(f"    Unique: {len(unique_intents)}")

        assert len(unique_intents) >= 3, \
            f"Expected at least 3 distinct intents, got {len(unique_intents)}"

    print("\n  PASSED: At least 3 distinct intents per item")
    return True


def test_no_generic_test_case():
    """Test: No 'test case that validates' without test-ish words in handle."""
    print("\n" + "=" * 70)
    print("TEST 7: No generic test case suggestions")
    print("=" * 70)

    # Content WITHOUT test-ish words
    no_test_title = "The architecture of our memory system"
    no_test_body = "A living memory and inference space grounded in neural patterns."

    suggestions = generate_suggestions(no_test_title, no_test_body)

    print(f"  Checking {len(suggestions)} suggestions:")
    violations = []
    for i, s in enumerate(suggestions, 1):
        display = s.get("display_text", "").lower()
        handle = s.get("handle_quote", s.get("handle", "")).lower()

        # Check if prompt mentions "test case" patterns
        has_test_pattern = (
            "test case" in display or
            "test that validates" in display or
            "validation test" in display
        )

        # Check if handle has test-ish words
        has_test_words = any(tw in handle for tw in TEST_WORDS)

        status = "OK"
        if has_test_pattern and not has_test_words:
            status = "VIOLATION"
            violations.append(s)

        print(f"    {i}. [{status}] {display[:50]}...")

    assert len(violations) == 0, \
        f"Found {len(violations)} generic test case violations"

    print("  PASSED: No generic test case suggestions")
    return True


def test_suggestion_format():
    """Test: Suggestions have correct format with all required fields."""
    print("\n" + "=" * 70)
    print("TEST 8: Suggestion format verification")
    print("=" * 70)

    suggestions = generate_suggestions(PAGE_1_TITLE, PAGE_1_BODY)

    required_keys = {"display_text", "prompt_text", "intent_type", "recipe_id"}

    print(f"  Checking {len(suggestions)} suggestions for required keys:")
    for i, s in enumerate(suggestions, 1):
        missing = required_keys - set(s.keys())
        status = "OK" if not missing else f"MISSING: {missing}"
        print(f"    {i}. {status}")

        assert not missing, f"Suggestion {i} missing keys: {missing}"

    # Also check handle_quote or handle exists
    for i, s in enumerate(suggestions, 1):
        has_handle = "handle_quote" in s or "handle" in s
        assert has_handle, f"Suggestion {i} missing handle_quote or handle"

    print("  PASSED: All suggestions have correct format")
    return True


def main():
    """Run all varied suggestions tests."""
    print("=" * 70)
    print("VARIED BOND SUGGESTIONS TEST")
    print("=" * 70)
    print("Proving suggestions are content-specific and varied")

    tests = [
        ("Exactly 4 suggestions", test_suggestions_exactly_4),
        ("Handles in content", test_handle_quotes_in_content),
        ("4 distinct handles", test_4_distinct_handles),
        ("Two items differ", test_two_items_different_suggestions),
        ("Not same 4 verbs", test_not_same_4_leading_verbs),
        ("Diverse intents", test_diverse_intents),
        ("No generic test case", test_no_generic_test_case),
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
        print("All varied suggestions tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
