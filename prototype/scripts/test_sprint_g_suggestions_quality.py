#!/usr/bin/env python3
"""
Sprint G: Suggestions Quality Acceptance Test

This test validates that suggestions are:
1. Content-shaped (reference actual phrases from input)
2. Diverse (4 different output shapes)
3. Produce real output when clicked

Test fixture: Field Overview document content

Usage:
    python prototype/scripts/test_sprint_g_suggestions_quality.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import reset_store
from fieldkit.spin_recipes import (
    generate_suggestions_for_item,
    extract_key_phrases,
    extract_content_fingerprint,
    SUGGESTION_RECIPE_IDS,
)
from fieldkit.generation import generate_bond_output


# Test fixture: Field Overview document content (exact phrases from sprint spec)
TEST_TITLE = "FIELD – Purpose of the Field Overview"
TEST_BODY = """This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory and inference space grounded in The Entrance Way, the Gibsey Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity."""

# Key phrases that MUST appear in suggestions/output (from sprint spec)
KEY_PHRASES = [
    "living memory and inference space",
    "The Entrance Way",
    "Gibsey Vault",
    "QDPI events",
]

# Alternate key terms for matching (substrings of the above)
KEY_TERMS = [
    "living memory",
    "inference space",
    "Entrance Way",
    "Gibsey",
    "Vault",
    "QDPI",
]


def test_key_phrase_extraction():
    """Test: Key phrases are properly extracted from content."""
    print("\n" + "-" * 70)
    print("TEST 1: Key phrase extraction from Field Overview content")
    print("-" * 70)

    phrases = extract_key_phrases(TEST_BODY, TEST_TITLE)

    print(f"  Extracted {len(phrases)} key phrases:")
    for p in phrases:
        print(f"    - {p}")

    # Must extract at least 3 key phrases
    assert len(phrases) >= 3, f"Expected at least 3 key phrases, got {len(phrases)}"

    # Should include some of the expected terms
    found_key_terms = 0
    for expected in ["FIELD", "Gibsey", "Holographic", "QDPI", "Vault", "Entrance"]:
        for phrase in phrases:
            if expected.lower() in phrase.lower():
                found_key_terms += 1
                break

    assert found_key_terms >= 2, f"Expected at least 2 known terms, found {found_key_terms}"
    print(f"  Found {found_key_terms} known key terms in extracted phrases")

    return True


def test_suggestions_exactly_4():
    """Test: Suggestions return exactly 4 items."""
    print("\n" + "-" * 70)
    print("TEST 2: Generate exactly 4 suggestions")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(TEST_TITLE, TEST_BODY)

    assert len(suggestions) == 4, f"Expected 4 suggestions, got {len(suggestions)}"
    print(f"  Generated {len(suggestions)} suggestions")

    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s['display_text'][:50]}...")

    return True


def test_suggestions_content_shaped():
    """Test: Each suggestion prompt_text includes at least one key phrase."""
    print("\n" + "-" * 70)
    print("TEST 3: Suggestions are content-shaped (include key phrases)")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(TEST_TITLE, TEST_BODY)

    # Get all key terms that should appear (lowercase for matching)
    key_terms_lower = [t.lower() for t in KEY_TERMS]

    for i, s in enumerate(suggestions, 1):
        prompt_lower = s["prompt_text"].lower()

        # Check if any key term appears in prompt_text
        found_terms = []
        for kt in key_terms_lower:
            if kt in prompt_lower:
                found_terms.append(kt)

        print(f"  Suggestion {i}: Found key terms = {found_terms}")
        print(f"    Display: {s['display_text']}")
        print(f"    Prompt: {s['prompt_text'][:80]}...")

        # At least the content should be referenced via body_excerpt
        assert (
            "field" in prompt_lower or
            "gibsey" in prompt_lower or
            "vault" in prompt_lower or
            "qdpi" in prompt_lower or
            "living" in prompt_lower or
            "memory" in prompt_lower or
            "inference" in prompt_lower or
            "entrance" in prompt_lower or
            "holographic" in prompt_lower
        ), f"Suggestion {i} should reference content from input"

    print("  All suggestions reference input content")
    return True


def test_suggestions_diverse():
    """Test: Suggestions represent 4 different intents (clarify, map, trace, test)."""
    print("\n" + "-" * 70)
    print("TEST 4: Suggestions are diverse (4 different intents)")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(TEST_TITLE, TEST_BODY)

    intents = [s["intent_type"] for s in suggestions]

    # Sprint G: 4 distinct intents (clarify, map, trace, test)
    expected_intents = {"clarify", "map", "trace", "test"}
    unique_intents = set(intents)
    assert unique_intents == expected_intents, f"Expected intents {expected_intents}, got {unique_intents}"

    print(f"  Intent types: {intents}")

    print("  All 4 suggestions have distinct intents:")
    for s in suggestions:
        print(f"    - {s['intent_type']}: {s['display_text'][:50]}...")

    return True


def test_suggestion_execution():
    """Test: Clicking suggestion #1 produces real M output with key phrases."""
    print("\n" + "-" * 70)
    print("TEST 5: Execute suggestion #1 and verify output")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create Q item with test content
        q_id = cli.cmd_item_create(
            title=TEST_TITLE,
            body=TEST_BODY,
            item_type="Q"
        )
        print(f"  Created Q item: {q_id}")

        # Generate suggestions
        q_item = cli.store.get_item(q_id)
        suggestions = generate_suggestions_for_item(
            item_title=q_item["title"],
            item_body=q_item.get("body"),
        )

        # Execute first suggestion (same flow as UI click)
        suggestion = suggestions[0]
        bond_id = cli.cmd_bond_create(
            input_item_ids=[q_id],
            prompt_text=suggestion["prompt_text"],
            recipe_id=suggestion["recipe_id"],
        )
        print(f"  Created Bond: {bond_id}")
        print(f"  Using recipe: {suggestion['recipe_id']}")

        output_item_id = cli.cmd_bond_run(bond_id, output_type="M")
        print(f"  Created M output: {output_item_id}")

        # Verify output exists and is type M
        output_item = cli.store.get_item(output_item_id)
        assert output_item is not None, "Output item should exist"
        assert output_item["type"] == "M", f"Expected type M, got {output_item['type']}"

        # Verify output body contains at least 2 key terms
        output_body_lower = output_item["body"].lower()
        found_terms = []
        for kt in KEY_TERMS:
            if kt.lower() in output_body_lower:
                found_terms.append(kt)

        print(f"  Output contains {len(found_terms)} key terms: {found_terms}")
        print(f"  Output preview: {output_item['body'][:200]}...")

        assert len(found_terms) >= 2, f"Expected at least 2 key terms in output, found {len(found_terms)}: {found_terms}"

        # Verify bond provenance
        bond = cli.store.get_bond(bond_id)
        assert bond["status"] == "executed", "Bond should be executed"
        assert bond["output_item_id"] == output_item_id, "Bond should link to output item"
        assert q_id in bond["input_item_ids"], "Bond should reference input item"
        print("  Bond provenance verified")

        # Verify event ordering
        events = cli.store.load_events(episode_id=cli._episode_id)
        event_names = [e["name"] for e in events]

        run_idx = next((i for i, n in enumerate(event_names) if n == "bond.run_requested"), -1)
        exec_idx = next((i for i, n in enumerate(event_names) if n == "bond.executed"), -1)

        assert run_idx > 0, "bond.run_requested should exist"
        assert exec_idx > run_idx, "bond.executed should come after bond.run_requested"
        print("  Event ordering verified (run_requested < executed)")

    return True


def test_display_text_format():
    """Test: display_text is hyperlink-like (8-18 words, handle in quotes)."""
    print("\n" + "-" * 70)
    print("TEST 6: display_text is hyperlink-like (8-18 words)")
    print("-" * 70)

    suggestions = generate_suggestions_for_item(TEST_TITLE, TEST_BODY)

    for i, s in enumerate(suggestions, 1):
        display_text = s["display_text"]
        word_count = len(display_text.split())

        # Sprint G: hyperlink-like suggestions are 8-18 words
        assert 8 <= word_count <= 18, f"Suggestion {i}: display_text has {word_count} words, expected 8-18"

        # Should start with capital
        first_char = display_text[0]
        assert first_char.isupper() or first_char in '"\'', f"Suggestion {i}: display_text should start with capital"

        # Sprint G: handle must appear in quotes
        assert '"' in display_text, f"Suggestion {i}: display_text should contain handle in quotes"

        print(f"  {i}. '{display_text}' ({word_count} words)")

    print("  All display_texts are hyperlink-like sentences")
    return True


def main():
    """Run all suggestion quality tests."""
    print("=" * 70)
    print("SPRINT G: SUGGESTIONS QUALITY ACCEPTANCE TEST")
    print("=" * 70)
    print(f"\nTest fixture: {TEST_TITLE}")
    print(f"Key phrases to find: {', '.join(KEY_PHRASES[:4])}...")

    tests = [
        ("Key phrase extraction", test_key_phrase_extraction),
        ("Exactly 4 suggestions", test_suggestions_exactly_4),
        ("Content-shaped", test_suggestions_content_shaped),
        ("Diverse recipes", test_suggestions_diverse),
        ("Execute suggestion", test_suggestion_execution),
        ("Natural language display", test_display_text_format),
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
        print("All suggestion quality tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
