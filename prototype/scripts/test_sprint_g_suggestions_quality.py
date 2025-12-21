#!/usr/bin/env python3
"""
Sprint G: Suggestions Quality Acceptance Test

This test validates that suggestions are:
1. Content-shaped (reference actual phrases from input via handle_quote)
2. Diverse (4 different intents)
3. Non-generic (different items produce different suggestions)
4. Handle quotes appear verbatim in source

Test fixtures:
- PAGE 1 architecture document
- Prose example

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
from fieldkit.suggestion_engine import generate_bond_suggestions, suggestions_to_legacy_format, TEST_WORDS
from fieldkit.handles import extract_handles, choose_diverse_handles


# === FIXTURE 1: PAGE 1 Architecture Document ===
FIXTURE_1_TITLE = "FIELD – Purpose of the Field Overview"
FIXTURE_1_BODY = """This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory and inference space grounded in The Entrance Way, the Gibsey Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity."""


# === FIXTURE 2: Prose Example ===
FIXTURE_2_TITLE = "User Authentication Flow"
FIXTURE_2_BODY = """The authentication system uses JWT tokens with refresh token rotation.

When a user logs in:
- Credentials are validated against the database
- A short-lived access token (15 min) is issued
- A long-lived refresh token (7 days) is stored in HttpOnly cookie
- The access token is returned in the response body

Token refresh happens automatically when the access token expires.

Security considerations:
- CSRF protection via double-submit cookie
- Rate limiting on login attempts
- Account lockout after 5 failed attempts"""


def test_handle_extraction():
    """Test: Handles are extracted correctly from content."""
    print("\n" + "-" * 70)
    print("TEST 1: Handle extraction from structured content")
    print("-" * 70)

    handles = extract_handles(FIXTURE_1_BODY, FIXTURE_1_TITLE)

    print(f"  Extracted {len(handles)} handles:")
    for h in handles[:10]:
        print(f"    [{h['kind']:8}] score={h['score']:.2f} | \"{h['quote'][:60]}...\"")

    # Must extract at least 8 handles
    assert len(handles) >= 8, f"Expected at least 8 handles, got {len(handles)}"

    # Should have colon clauses (What the field is:, How the field is:)
    colon_handles = [h for h in handles if h["kind"] == "colon"]
    print(f"\n  Found {len(colon_handles)} colon clause handles")
    assert len(colon_handles) >= 2, f"Expected at least 2 colon handles, got {len(colon_handles)}"

    return True


def test_suggestions_exactly_4():
    """Test: Suggestions return exactly 4 items."""
    print("\n" + "-" * 70)
    print("TEST 2: Generate exactly 4 suggestions")
    print("-" * 70)

    result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
    suggestions = result["suggestions"]

    assert len(suggestions) == 4, f"Expected 4 suggestions, got {len(suggestions)}"
    print(f"  Generated {len(suggestions)} suggestions (source: {result['suggestion_source']})")

    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. [{s['intent']:10}] {s['prompt_text'][:60]}...")
        print(f"     handle: \"{s['handle_quote'][:40]}...\"")

    return True


def test_handle_quote_verbatim():
    """Test: Each suggestion's handle_quote exists verbatim in source."""
    print("\n" + "-" * 70)
    print("TEST 3: handle_quote is verbatim substring of source")
    print("-" * 70)

    full_text = FIXTURE_1_TITLE + "\n" + FIXTURE_1_BODY
    full_text_lower = full_text.lower()

    result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
    suggestions = result["suggestions"]

    for i, s in enumerate(suggestions, 1):
        handle = s["handle_quote"]
        handle_lower = handle.lower()

        # Handle must appear verbatim in source (case-insensitive)
        assert handle_lower in full_text_lower, (
            f"Suggestion {i}: handle_quote \"{handle}\" not found in source"
        )
        print(f"  {i}. FOUND: \"{handle[:50]}...\"")

    print("  All handle_quotes are verbatim substrings of source")
    return True


def test_four_distinct_intents():
    """Test: Suggestions use 4 different intents."""
    print("\n" + "-" * 70)
    print("TEST 4: 4 distinct intents (clarify, concretize, connect, test)")
    print("-" * 70)

    result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
    suggestions = result["suggestions"]

    intents = [s["intent"] for s in suggestions]
    unique_intents = set(intents)

    # All 4 intents should be different
    assert len(unique_intents) == 4, f"Expected 4 unique intents, got {len(unique_intents)}: {intents}"

    expected_intents = {"clarify", "concretize", "connect", "test"}
    assert unique_intents == expected_intents, f"Expected {expected_intents}, got {unique_intents}"

    print(f"  Intents: {intents}")
    print("  All 4 suggestions have distinct intents")
    return True


def test_varied_leading_verbs():
    """Test: Prompts don't all use same leading verb pattern."""
    print("\n" + "-" * 70)
    print("TEST 5: Varied leading verbs (not all Define/Trace/Connect/Test)")
    print("-" * 70)

    result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
    suggestions = result["suggestions"]

    leading_verbs = []
    for s in suggestions:
        words = s["prompt_text"].split()
        if words:
            leading_verbs.append(words[0].lower().rstrip("?:"))

    print(f"  Leading verbs: {leading_verbs}")

    # Should have at least 3 different leading verbs
    unique_verbs = set(leading_verbs)
    assert len(unique_verbs) >= 3, f"Expected at least 3 different leading verbs, got {len(unique_verbs)}: {leading_verbs}"

    # Should NOT be the generic Define/Trace/Connect/Test set
    generic_set = {"define", "trace", "connect", "test", "map", "operationalize"}
    all_generic = all(v in generic_set for v in leading_verbs)
    assert not all_generic, f"All prompts use generic verbs: {leading_verbs}"

    print("  Leading verbs are varied (not generic pattern)")
    return True


def test_different_items_different_suggestions():
    """Test: Different items produce different suggestions."""
    print("\n" + "-" * 70)
    print("TEST 6: Different items produce different suggestions")
    print("-" * 70)

    result1 = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
    result2 = generate_bond_suggestions(FIXTURE_2_TITLE, FIXTURE_2_BODY)

    prompts1 = set(s["prompt_text"] for s in result1["suggestions"])
    prompts2 = set(s["prompt_text"] for s in result2["suggestions"])

    # Should have zero overlap
    overlap = prompts1 & prompts2
    assert len(overlap) == 0, f"Items produced overlapping prompts: {overlap}"

    # Handle quotes should be different (content-specific)
    handles1 = set(s["handle_quote"].lower() for s in result1["suggestions"])
    handles2 = set(s["handle_quote"].lower() for s in result2["suggestions"])

    print(f"  Fixture 1 handles: {[h[:30] + '...' for h in handles1]}")
    print(f"  Fixture 2 handles: {[h[:30] + '...' for h in handles2]}")

    handle_overlap = handles1 & handles2
    assert len(handle_overlap) == 0, f"Items produced overlapping handles: {handle_overlap}"

    print("  Different items produce completely different suggestions")
    return True


def test_no_test_without_test_words():
    """Test: Test intent prompts require test-ish words in handle."""
    print("\n" + "-" * 70)
    print("TEST 7: Test intent requires test-ish words (or concretize fallback)")
    print("-" * 70)

    # Create content with NO test-ish words
    no_test_title = "Simple Architecture Overview"
    no_test_body = """The system has three layers:
- **Presentation layer:** UI components
- **Business layer:** Core logic
- **Data layer:** Database access

The layers communicate through well-defined interfaces."""

    result = generate_bond_suggestions(no_test_title, no_test_body)
    suggestions = result["suggestions"]

    test_suggestion = next((s for s in suggestions if s["intent"] == "test"), None)

    if test_suggestion:
        handle = test_suggestion["handle_quote"].lower()
        # If test intent exists, the handle should have test words OR
        # the fallback should have made it concretize-like
        has_test_words = any(tw in handle for tw in TEST_WORDS)

        if not has_test_words:
            # This is acceptable - fallback uses concretize pattern
            prompt_lower = test_suggestion["prompt_text"].lower()
            # Just verify it's not using "test case that validates" pattern
            assert "test case that validates" not in prompt_lower, (
                f"Test intent without test words shouldn't use 'test case' pattern"
            )
            print(f"  Test intent uses fallback pattern (no test words in handle)")
        else:
            print(f"  Test intent has test word in handle: \"{handle[:40]}\"")
    else:
        print("  No test intent found (all intents used different patterns)")

    return True


def test_suggestion_execution():
    """Test: Clicking suggestion produces real M output."""
    print("\n" + "-" * 70)
    print("TEST 8: Execute suggestion and verify output")
    print("-" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        cli = FieldKitCLI(data_dir)
        cli.cmd_init()

        # Create Q item with test content
        q_id = cli.cmd_item_create(
            title=FIXTURE_1_TITLE,
            body=FIXTURE_1_BODY,
            item_type="Q"
        )
        print(f"  Created Q item: {q_id}")

        # Generate suggestions
        result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY)
        legacy = suggestions_to_legacy_format(result)

        # Execute first suggestion
        suggestion = legacy[0]
        bond_id = cli.cmd_bond_create(
            input_item_ids=[q_id],
            prompt_text=suggestion["prompt_text"],
            recipe_id=suggestion["recipe_id"],
        )
        print(f"  Created Bond: {bond_id}")

        output_item_id = cli.cmd_bond_run(bond_id, output_type="M")
        print(f"  Created M output: {output_item_id}")

        # Verify output exists and is type M
        output_item = cli.store.get_item(output_item_id)
        assert output_item is not None, "Output item should exist"
        assert output_item["type"] == "M", f"Expected type M, got {output_item['type']}"

        # Verify output has substantive body
        assert len(output_item["body"]) > 50, "Output body should be substantive"
        print(f"  Output preview: {output_item['body'][:150]}...")

        # Verify bond provenance
        bond = cli.store.get_bond(bond_id)
        assert bond["status"] == "executed", "Bond should be executed"
        print("  Bond executed successfully")

    return True


def test_debug_mode():
    """Test: Debug mode returns candidate handles."""
    print("\n" + "-" * 70)
    print("TEST 9: Debug mode returns candidate handles")
    print("-" * 70)

    result = generate_bond_suggestions(FIXTURE_1_TITLE, FIXTURE_1_BODY, return_debug=True)

    assert "debug" in result, "Debug mode should include debug info"
    debug = result["debug"]

    assert "candidate_handles" in debug, "Debug should include candidate_handles"
    assert "all_handles_count" in debug, "Debug should include all_handles_count"

    handles = debug["candidate_handles"]
    print(f"  Candidate handles ({len(handles)}):")
    for i, h in enumerate(handles[:8], 1):
        print(f"    {i}. \"{h[:50]}...\"")

    assert len(handles) >= 4, f"Expected at least 4 candidate handles, got {len(handles)}"
    print("  Debug info correctly returned")

    return True


def main():
    """Run all suggestion quality tests."""
    print("=" * 70)
    print("SPRINT G: SUGGESTIONS QUALITY ACCEPTANCE TEST")
    print("=" * 70)
    print(f"\nFixture 1: {FIXTURE_1_TITLE}")
    print(f"Fixture 2: {FIXTURE_2_TITLE}")

    tests = [
        ("Handle extraction", test_handle_extraction),
        ("Exactly 4 suggestions", test_suggestions_exactly_4),
        ("Handle quote verbatim", test_handle_quote_verbatim),
        ("4 distinct intents", test_four_distinct_intents),
        ("Varied leading verbs", test_varied_leading_verbs),
        ("Different items → different suggestions", test_different_items_different_suggestions),
        ("No test without test words", test_no_test_without_test_words),
        ("Execute suggestion", test_suggestion_execution),
        ("Debug mode", test_debug_mode),
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
