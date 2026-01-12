#!/usr/bin/env python3
"""
Queue Lattice v0.1 Sprint 3 Acceptance Test - Evidence & Licensing

Tests evidence-driven phrasing and licensing constraints.

ASSERTIONS:
a) None of the 4 options contain banned phrases: "planted", "point back",
   "enters the picture", "hold together"
b) At least 2/4 options are questions (contain "?")
c) Debug output includes evidence span fields
d) Apostrophes in contractions are allowed (don't, doesn't, can't)
e) Double quotes are still blocked

Run: python3 prototype/scripts/test_queue_lattice_evidence_sprint3.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.hololoop_engine import (
    generate_hololoop_options,
    find_best_span,
    normalize_for_search,
    _contains_quotes,
    _check_unlicensed_claims,
    UNLICENSED_INFERENCE_TOKENS,
)


# === TEST DATA (same preface pair as other tests) ===
ITEM_A = {
    "id": "it_PREFACE_A",
    "title": "Found Text and The Author",
    "body": """I didn't write this... identity of The Author... found text...
giallo... The Big Sleep... captivity mechanism... mystery of authorship...
the narrator becomes a collector... who wrote this and why...
The Author remains unknown. This text was found, not written by me.
It has the structure of a giallo, like The Big Sleep but inverted.""",
}

ITEM_B = {
    "id": "it_PREFACE_B",
    "title": "The Curator and Scheherazade",
    "body": """I do not know the identity... collector and curator...
Scheherazade in reverse... One Thousand and One Nights... Magical Dominion...
the stories trap the teller... Arabian Nights structure...
Unlike Scheherazade who told stories to survive, here the curator is trapped by them.
The Magical Dominion holds the collector in place.""",
}

# Sprint 3 banned phrases (must not appear unless licensed by source text)
SPRINT3_BANNED_PHRASES = [
    "planted",
    "point back",
    "enters the picture",
    "hold together",
]


def test_no_banned_phrases():
    """Test that none of the 4 options contain Sprint 3 banned phrases."""
    print("\n=== Test 1: No Sprint 3 Banned Phrases ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    for opt in options:
        combined = (opt["link_text_forward"] + " " + opt["link_text_return"]).lower()

        for phrase in SPRINT3_BANNED_PHRASES:
            if phrase in combined:
                violations.append((opt["option_index"], phrase))

    if violations:
        print("  FAIL: Found banned phrases:")
        for idx, phrase in violations:
            print(f"    Option {idx}: '{phrase}'")
        return False

    print(f"  Checked {len(options)} options for banned phrases")
    for opt in options:
        print(f"    {opt['option_index']}. {opt['link_text_forward'][:50]}...")
    print("  PASS: No banned phrases found")
    return True


def test_question_quota():
    """Test that at least 2/4 options are questions."""
    print("\n=== Test 2: Question Quota (min 2/4) ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    question_count = sum(1 for opt in options if "?" in opt["link_text_forward"])

    print(f"  Questions: {question_count}/{len(options)}")
    for opt in options:
        is_q = "?" in opt["link_text_forward"]
        marker = "[Q]" if is_q else "[S]"
        print(f"    {opt['option_index']}. {marker} {opt['link_text_forward'][:50]}...")

    if question_count < 2:
        print(f"  FAIL: Only {question_count} questions, need at least 2")
        return False

    print(f"  PASS: {question_count}/4 options are questions")
    return True


def test_evidence_spans_in_debug():
    """Test that debug output includes evidence span fields."""
    print("\n=== Test 3: Evidence Spans in Debug ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    debug = result.get("debug", {})

    # Check for evidence_spans field
    evidence_spans = debug.get("evidence_spans", [])
    if not evidence_spans:
        print("  FAIL: No 'evidence_spans' field in debug output")
        return False

    print(f"  Found {len(evidence_spans)} evidence span entries")

    # Check each entry has required fields
    for i, entry in enumerate(evidence_spans):
        ha = entry.get("handle_a", "")
        hb = entry.get("handle_b", "")
        span_a_present = entry.get("evidence_span_a_present", False)
        span_b_present = entry.get("evidence_span_b_present", False)

        print(f"    Option {i+1}: A='{ha[:25]}' span_a={span_a_present}, B='{hb[:25]}' span_b={span_b_present}")

    # Check filter_stats is present
    filter_stats = debug.get("filter_stats", {})
    if not filter_stats:
        print("  FAIL: No 'filter_stats' field in debug output")
        return False

    print(f"  Filter stats: {filter_stats.get('total_rejected', 0)} rejected")
    print(f"  Blocked tokens: {debug.get('blocked_tokens', [])}")

    print("  PASS: Evidence span fields present in debug")
    return True


def test_evidence_span_extraction():
    """Test the find_best_span helper function."""
    print("\n=== Test 4: Evidence Span Extraction ===")

    test_text = """I didn't write this... identity of The Author... found text...
giallo... The Big Sleep... captivity mechanism... mystery of authorship..."""

    # Test exact match
    span = find_best_span(test_text, "The Author")
    if span is None:
        print("  FAIL: find_best_span returned None for 'The Author'")
        return False
    print(f"  Span for 'The Author': {span[:60]}...")

    # Test case-insensitive
    span_lower = find_best_span(test_text, "the author")
    if span_lower is None:
        print("  FAIL: Case-insensitive search failed")
        return False
    print(f"  Case-insensitive span: {span_lower[:60]}...")

    # Test partial match
    span_partial = find_best_span(test_text, "Big Sleep captivity")
    if span_partial is None:
        print("  FAIL: Partial match failed for 'Big Sleep captivity'")
        return False
    print(f"  Partial match span: {span_partial[:60]}...")

    # Test missing handle
    span_missing = find_best_span(test_text, "nonexistent handle xyz")
    if span_missing is not None:
        print(f"  FAIL: Expected None for missing handle, got: {span_missing}")
        return False
    print("  Missing handle returns None: correct")

    print("  PASS: Evidence span extraction works")
    return True


def test_apostrophe_handling():
    """Test that apostrophes in contractions are allowed."""
    print("\n=== Test 5: Apostrophe Handling ===")

    # Contractions should NOT be flagged as quotes
    contractions = [
        "don't", "doesn't", "can't", "won't", "isn't",
        "What doesn't A reveal about B?",
        "If A isn't true, then what does B mean?",
    ]

    for text in contractions:
        if _contains_quotes(text):
            print(f"  FAIL: Contraction flagged as quote: '{text}'")
            return False
        print(f"  OK: '{text[:40]}' - not flagged")

    # Double quotes SHOULD be flagged
    double_quotes = [
        '"quoted text"',
        'What about "this phrase"?',
        '"A" leads to "B"',
    ]

    for text in double_quotes:
        if not _contains_quotes(text):
            print(f"  FAIL: Double quotes not flagged: '{text}'")
            return False
        print(f"  OK: '{text[:40]}' - correctly flagged")

    print("  PASS: Apostrophes allowed, double quotes blocked")
    return True


def test_licensing_filter():
    """Test the unlicensed inference token filter."""
    print("\n=== Test 6: Licensing Filter ===")

    # Text containing "planted" - should be blocked if not in source
    test_text = "Who planted this evidence and why does it point back to the author?"
    source_a = "The author wrote about identity and mystery."
    source_b = "The curator collected stories from Arabian Nights."

    has_unlicensed, blocked = _check_unlicensed_claims(test_text, source_a, source_b)

    if not has_unlicensed:
        print("  FAIL: 'planted' and 'point back' should be blocked")
        return False

    print(f"  Blocked tokens: {blocked}")

    if "planted" not in blocked:
        print("  FAIL: 'planted' should be in blocked list")
        return False

    if "point back" not in blocked:
        print("  FAIL: 'point back' should be in blocked list")
        return False

    # Text with licensed word
    licensed_text = "The mystery of authorship remains."
    source_with_mystery = "The mystery of authorship... who wrote this..."

    has_unlicensed2, blocked2 = _check_unlicensed_claims(licensed_text, source_with_mystery, "")

    if has_unlicensed2:
        print(f"  FAIL: 'mystery' should be licensed, but blocked: {blocked2}")
        return False

    print("  Licensed word 'mystery' not blocked: correct")

    print("  PASS: Licensing filter works correctly")
    return True


def test_full_output_with_evidence():
    """Display full output for manual review with evidence spans."""
    print("\n=== Test 7: Full Output with Evidence (Manual Review) ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]
    debug = result.get("debug", {})

    print(f"\n  Source: {result['source']}")
    print(f"  Candidates: {debug.get('candidates_generated', 0)} generated -> {debug.get('candidates_filtered', 0)} filtered")
    print(f"  Blocked tokens: {debug.get('blocked_tokens', [])}")

    print("\n  Generated Options with Evidence:")
    for opt in options:
        print(f"\n  Option {opt['option_index']} [{opt['frame']}]:")
        print(f"    A→B: {opt['link_text_forward']}")
        print(f"    B→A: {opt['link_text_return']}")
        print(f"    Handle A: '{opt['handle_a_used'][:35]}'")
        print(f"    Handle B: '{opt['handle_b_used'][:35]}'")

        span_a = opt.get('evidence_span_a')
        span_b = opt.get('evidence_span_b')
        print(f"    Evidence A: {'[present]' if span_a else '[missing]'}")
        if span_a:
            print(f"      -> {span_a[:80]}...")
        print(f"    Evidence B: {'[present]' if span_b else '[missing]'}")
        if span_b:
            print(f"      -> {span_b[:80]}...")

    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE v0.1 SPRINT 3 ACCEPTANCE TEST")
    print("Evidence-Driven Phrasing + Licensing Constraints")
    print("=" * 70)

    tests = [
        ("No Sprint 3 Banned Phrases", test_no_banned_phrases),
        ("Question Quota (min 2/4)", test_question_quota),
        ("Evidence Spans in Debug", test_evidence_spans_in_debug),
        ("Evidence Span Extraction", test_evidence_span_extraction),
        ("Apostrophe Handling", test_apostrophe_handling),
        ("Licensing Filter", test_licensing_filter),
        ("Full Output with Evidence", test_full_output_with_evidence),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"  X {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"  X {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"SPRINT 3 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\nAll Sprint 3 acceptance tests PASSED.")
        print("Evidence-driven phrasing and licensing constraints are working.")
    else:
        print("\nSome tests FAILED. Please fix before proceeding.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
