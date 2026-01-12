#!/usr/bin/env python3
"""
Queue Lattice v0.1 Sprint 3b Acceptance Test - Handle Quality Filter

Tests that incomplete phrase handles are filtered out of anchor selection.

ASSERTIONS:
a) None of the selected Option handles end in BAD_HANDLE_TAILS tokens
b) No output contains "the structure of make you" (case-insensitive)
c) No output contains "the narrator becomes is true" (case-insensitive)
d) Debug output includes handle filter stats

Run: python3 prototype/scripts/test_queue_lattice_handle_quality_sprint3b.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.hololoop_engine import generate_hololoop_options
from fieldkit.anchor_pairing import (
    is_good_anchor_handle,
    BAD_HANDLE_TAILS,
    select_anchor_pairs,
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

# Bad patterns that should NOT appear in output
BAD_PATTERNS = [
    "the structure of make you",
    "the narrator becomes is true",
    "the narrator becomes is",
    "structure of make",
    "becomes is true",
    "becomes is",
]


def test_is_good_anchor_handle():
    """Test the is_good_anchor_handle function."""
    print("\n=== Test 1: is_good_anchor_handle Function ===")

    # Should reject incomplete phrases
    bad_handles = [
        "the structure of",
        "the narrator becomes",
        "identity of",
        "collector and",
        "stories trap the",
        "the",
        "of",
        "abc",  # too short
    ]

    # Should accept complete phrases
    good_handles = [
        "The Big Sleep",
        "identity of The Author",
        "mystery of authorship",
        "One Thousand and One Nights",
        "Scheherazade in reverse",
        "captivity mechanism",
        "Arabian Nights structure",
    ]

    passed = True

    print("  Bad handles (should reject):")
    for h in bad_handles:
        result = is_good_anchor_handle(h)
        status = "FAIL" if result else "OK"
        if result:
            passed = False
        print(f"    {status}: '{h}' -> {result}")

    print("\n  Good handles (should accept):")
    for h in good_handles:
        result = is_good_anchor_handle(h)
        status = "OK" if result else "FAIL"
        if not result:
            passed = False
        print(f"    {status}: '{h}' -> {result}")

    if not passed:
        print("  FAIL: Some handles were incorrectly classified")
        return False

    print("  PASS: Handle validation works correctly")
    return True


def test_no_bad_tail_handles():
    """Test that no selected Option handles end in BAD_HANDLE_TAILS tokens."""
    print("\n=== Test 2: No Bad Tail Handles in Options ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    for opt in options:
        for handle_key in ["handle_a_used", "handle_b_used"]:
            handle = opt.get(handle_key, "")
            if handle:
                tokens = handle.lower().split()
                if tokens:
                    last_token = tokens[-1].rstrip(".,;:!?")
                    if last_token in BAD_HANDLE_TAILS:
                        violations.append((opt["option_index"], handle_key, handle, last_token))

    if violations:
        print("  FAIL: Found handles ending in bad tail tokens:")
        for idx, key, handle, tail in violations:
            print(f"    Option {idx} {key}: '{handle}' ends with '{tail}'")
        return False

    print(f"  Checked {len(options)} options:")
    for opt in options:
        print(f"    {opt['option_index']}. A='{opt['handle_a_used'][:30]}' B='{opt['handle_b_used'][:30]}'")

    print("  PASS: No handles end in bad tail tokens")
    return True


def test_no_bad_patterns_in_output():
    """Test that no output contains the specific bad patterns."""
    print("\n=== Test 3: No Bad Patterns in Output ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    for opt in options:
        combined = (opt["link_text_forward"] + " " + opt["link_text_return"]).lower()

        for pattern in BAD_PATTERNS:
            if pattern.lower() in combined:
                violations.append((opt["option_index"], pattern))

    if violations:
        print("  FAIL: Found bad patterns in output:")
        for idx, pattern in violations:
            print(f"    Option {idx}: contains '{pattern}'")
        return False

    print(f"  Checked {len(options)} options against {len(BAD_PATTERNS)} bad patterns")
    for opt in options:
        print(f"    {opt['option_index']}. {opt['link_text_forward'][:55]}...")

    print("  PASS: No bad patterns found in output")
    return True


def test_handle_filter_stats_in_debug():
    """Test that debug output includes handle filter stats."""
    print("\n=== Test 4: Handle Filter Stats in Debug ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    debug = result.get("debug", {})

    # Check anchor_pairs debug contains handle filter info
    anchor_debug = debug

    # Look for handle_filter in the anchor debug (passed through)
    # Since we're checking hololoop_engine, we need to check anchor pairing directly
    from fieldkit.handles import extract_handles, choose_diverse_handles

    body_a = ITEM_A.get("body", "")
    body_b = ITEM_B.get("body", "")
    title_a = ITEM_A.get("title", "")
    title_b = ITEM_B.get("title", "")

    handles_a = extract_handles(body_a, title_a)
    handles_b = extract_handles(body_b, title_b)

    selected_a = choose_diverse_handles(handles_a, k=7)
    selected_b = choose_diverse_handles(handles_b, k=7)

    pairs, pairing_debug = select_anchor_pairs(selected_a, selected_b, num_pairs=6)

    handle_filter = pairing_debug.get("handle_filter", {})

    if not handle_filter:
        print("  FAIL: No 'handle_filter' in debug output")
        return False

    print("  Handle filter stats:")
    print(f"    handles_a_total: {handle_filter.get('handles_a_total', '?')}")
    print(f"    handles_a_good: {handle_filter.get('handles_a_good', '?')}")
    print(f"    handles_b_total: {handle_filter.get('handles_b_total', '?')}")
    print(f"    handles_b_good: {handle_filter.get('handles_b_good', '?')}")
    print(f"    fallback_used: {handle_filter.get('fallback_used', '?')}")

    rejected_a = pairing_debug.get("rejected_handles_a", [])
    rejected_b = pairing_debug.get("rejected_handles_b", [])

    if rejected_a:
        print(f"\n  Rejected handles from A: {rejected_a}")
    if rejected_b:
        print(f"  Rejected handles from B: {rejected_b}")

    print("\n  PASS: Handle filter stats present in debug")
    return True


def test_full_output_with_handles():
    """Display full output for manual review with handle quality info."""
    print("\n=== Test 5: Full Output with Handle Quality (Manual Review) ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]
    debug = result.get("debug", {})

    print(f"\n  Source: {result['source']}")
    print(f"  Candidates: {debug.get('candidates_generated', 0)} generated -> {debug.get('candidates_filtered', 0)} filtered")

    print("\n  Generated Options:")
    for opt in options:
        handle_a = opt["handle_a_used"]
        handle_b = opt["handle_b_used"]

        # Check if handles are good
        a_good = is_good_anchor_handle(handle_a)
        b_good = is_good_anchor_handle(handle_b)

        a_status = "OK" if a_good else "BAD"
        b_status = "OK" if b_good else "BAD"

        print(f"\n  Option {opt['option_index']} [{opt['frame']}]:")
        print(f"    A→B: {opt['link_text_forward']}")
        print(f"    B→A: {opt['link_text_return']}")
        print(f"    Handle A [{a_status}]: '{handle_a}'")
        print(f"    Handle B [{b_status}]: '{handle_b}'")

    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE v0.1 SPRINT 3b ACCEPTANCE TEST")
    print("Handle Quality Filter - No Incomplete Phrases")
    print("=" * 70)

    tests = [
        ("is_good_anchor_handle Function", test_is_good_anchor_handle),
        ("No Bad Tail Handles in Options", test_no_bad_tail_handles),
        ("No Bad Patterns in Output", test_no_bad_patterns_in_output),
        ("Handle Filter Stats in Debug", test_handle_filter_stats_in_debug),
        ("Full Output with Handle Quality", test_full_output_with_handles),
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
    print(f"SPRINT 3b RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\nAll Sprint 3b acceptance tests PASSED.")
        print("Handle quality filter prevents incomplete phrase handles.")
    else:
        print("\nSome tests FAILED. Please fix before proceeding.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
