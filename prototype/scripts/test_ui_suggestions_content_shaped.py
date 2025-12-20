#!/usr/bin/env python3
"""
Test: UI Suggestions are Content-Shaped

Verifies that suggestions generated for an Item contain anchor phrases
from the Item's body content.

Sanity test from spec:
- Create an item with "butthead" in the body
- Verify suggestions contain "butthead" verbatim

Requirements:
- Suggestions must reflect the actual content of the item
- Anchor phrase extraction must work correctly
- All 4 suggestions must contain the anchor phrase
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.spin_recipes import generate_suggestions_for_item, extract_anchor_phrase


def test_anchor_phrase_extraction():
    """Test that anchor phrases are correctly extracted.

    In the actual UI flow:
    - User types in composer (becomes body)
    - Title is derived from first line of body
    - So title and body both contain the key content
    """
    print("\n=== Testing Anchor Phrase Extraction ===")

    # Test cases that match actual UI flow where title is derived from body
    test_cases = [
        {
            "title": "butthead research project",
            "body": "butthead research project",
            "expected_contains": "butthead",
        },
        {
            "title": "I think butthead is interesting",
            "body": "I think butthead is an interesting concept to explore",
            "expected_contains": "butthead",
        },
        {
            "title": "PAGE 1 - Notes",
            "body": "Title: My butthead analysis\nThe main concept is...",
            "expected_contains": "butthead",
        },
        {
            "title": "First line has butthead in it",
            "body": "First line has butthead in it\nSecond line is different",
            "expected_contains": "butthead",
        },
    ]

    all_passed = True

    for i, tc in enumerate(test_cases, 1):
        anchor = extract_anchor_phrase(tc["title"], tc.get("body"))
        contains = tc["expected_contains"].lower() in anchor.lower()

        status = "PASS" if contains else "FAIL"
        print(f"\n  Test {i}: {status}")
        print(f"    Title: {tc['title'][:40]}...")
        print(f"    Body: {(tc.get('body') or 'None')[:40]}...")
        print(f"    Anchor: '{anchor}'")
        print(f"    Contains '{tc['expected_contains']}': {contains}")

        if not contains:
            all_passed = False

    return all_passed


def test_suggestions_contain_anchor():
    """Test that all suggestions contain the anchor phrase verbatim."""
    print("\n=== Testing Suggestions Contain Anchor ===")

    # The "butthead" sanity test from the spec
    # In actual UI flow, title is derived from body first line
    item_body = "I want to explore the butthead paradigm in modern software"
    item_title = item_body[:60]  # How ui_v2/app.py derives title

    anchor = extract_anchor_phrase(item_title, item_body)
    suggestions = generate_suggestions_for_item(item_title, item_body)

    print(f"\n  Item Title: {item_title}")
    print(f"  Item Body: {item_body}")
    print(f"  Extracted Anchor: '{anchor}'")
    print(f"  Generated {len(suggestions)} suggestions")

    all_contain = True

    for i, s in enumerate(suggestions, 1):
        contains = anchor in s["prompt_text"]
        status = "PASS" if contains else "FAIL"
        print(f"\n    Suggestion {i}: {status}")
        print(f"      Prompt: {s['prompt_text']}")
        print(f"      Contains anchor '{anchor}': {contains}")

        if not contains:
            all_contain = False

    return all_contain


def test_diverse_unique_content_words():
    """Test with various unique content words."""
    print("\n=== Testing Diverse Content Words ===")

    test_words = ["butthead", "xyzzy123", "flibbertigibbet", "quantum-flux"]
    all_passed = True

    for word in test_words:
        item_title = f"Exploring {word}"
        item_body = f"A deep dive into {word} and its implications"

        anchor = extract_anchor_phrase(item_title, item_body)
        suggestions = generate_suggestions_for_item(item_title, item_body)

        # Check if all suggestions contain the anchor
        all_contain = all(anchor in s["prompt_text"] for s in suggestions)

        status = "PASS" if all_contain else "FAIL"
        print(f"\n  Word '{word}': {status}")
        print(f"    Anchor: '{anchor}'")

        if not all_contain:
            all_passed = False
            for s in suggestions:
                if anchor not in s["prompt_text"]:
                    print(f"    MISSING in: {s['prompt_text'][:60]}...")

    return all_passed


def test_exactly_four_suggestions():
    """Test that exactly 4 suggestions are generated."""
    print("\n=== Testing Exactly 4 Suggestions ===")

    suggestions = generate_suggestions_for_item("Test item", "Test body content")

    count = len(suggestions)
    passed = count == 4

    print(f"  Expected: 4")
    print(f"  Got: {count}")
    print(f"  Status: {'PASS' if passed else 'FAIL'}")

    return passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Test: UI Suggestions are Content-Shaped")
    print("=" * 60)

    results = {
        "Anchor phrase extraction": test_anchor_phrase_extraction(),
        "Suggestions contain anchor": test_suggestions_contain_anchor(),
        "Diverse unique words": test_diverse_unique_content_words(),
        "Exactly 4 suggestions": test_exactly_four_suggestions(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
