#!/usr/bin/env python3
"""
Queue Lattice v0.1 Hololink Quality Acceptance Tests

Tests the non-negotiable output requirements:
1. No banned openers (How does, Compare, Trace, Provide, Give me, Define)
2. No banned phrases (opens a path, traces back, provides a foundation)
3. No quotation marks
4. Word count 9-22 per sentence
5. Each sentence contains anchor from A and B (case-insensitive)
6. Options are not near-duplicates (Jaccard < 0.35)

Run: python3 prototype/scripts/test_queue_lattice_quality.py
"""

import sys
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.hololoop_engine import (
    generate_hololoop_options,
    _word_count,
    _token_jaccard,
    _has_banned_opener,
    _has_banned_phrase,
    _contains_quotes,
    _contains_anchor,
    BANNED_OPENERS,
    BANNED_PHRASES,
)


# === Test Inputs ===
ITEM_A = {
    "id": "it_TEST_A",
    "title": "The Author Mystery",
    "body": """I didn't write this... identity of The Author... found text...
giallo... The Big Sleep... captivity mechanism... mystery of authorship...
the narrator becomes a collector... who wrote this and why...""",
}

ITEM_B = {
    "id": "it_TEST_B",
    "title": "The Collector's Role",
    "body": """I do not know the identity... collector and curator...
Scheherazade in reverse... One Thousand and One Nights... Magical Dominion...
the stories trap the teller... Arabian Nights structure...""",
}

# Literary example for diversity testing
ITEM_C = {
    "id": "it_TEST_C",
    "title": "Noir Conventions",
    "body": """Hard-boiled detective fiction... Raymond Chandler influences...
femme fatale archetype... moral ambiguity... Los Angeles as character...
the knight errant in a corrupt world...""",
}


def test_no_banned_openers():
    """Test that no options start with banned openers."""
    print("\n=== Test 1: No Banned Openers ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    banned_opener_patterns = [
        "how does", "how do", "how is", "compare", "trace", "provide",
        "give me", "define", "explain", "describe", "list", "identify",
        "summarize", "outline", "analyze", "evaluate", "discuss",
    ]

    violations = []
    for opt in options:
        fwd = opt["link_text_forward"].lower().strip()
        ret = opt["link_text_return"].lower().strip()

        for pattern in banned_opener_patterns:
            if fwd.startswith(pattern):
                violations.append(f"Option {opt['option_index']} forward starts with '{pattern}'")
            if ret.startswith(pattern):
                violations.append(f"Option {opt['option_index']} return starts with '{pattern}'")

    if violations:
        print(f"  FAIL: {len(violations)} violations found:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options avoid banned openers")
    for opt in options:
        print(f"    {opt['option_index']}. A->B: {opt['link_text_forward'][:50]}...")
    return True


def test_no_banned_phrases():
    """Test that no options contain banned system-speak phrases."""
    print("\n=== Test 2: No Banned Phrases ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    banned_phrases = [
        "opens a path", "traces back", "provides a foundation",
        "provides foundation", "relates to", "connects to", "leads into",
        "bridges the gap", "serves as", "functions as", "acts as",
        "points toward", "feeds into", "ties into", "links to",
    ]

    violations = []
    for opt in options:
        fwd = opt["link_text_forward"].lower()
        ret = opt["link_text_return"].lower()

        for phrase in banned_phrases:
            if phrase in fwd:
                violations.append(f"Option {opt['option_index']} forward contains '{phrase}'")
            if phrase in ret:
                violations.append(f"Option {opt['option_index']} return contains '{phrase}'")

    if violations:
        print(f"  FAIL: {len(violations)} violations found:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options avoid banned phrases")
    return True


def test_no_quotation_marks():
    """Test that no options contain quotation marks."""
    print("\n=== Test 3: No Quotation Marks ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    quote_pattern = re.compile(r'["\'\u201c\u201d\u2018\u2019\u00ab\u00bb]')

    violations = []
    for opt in options:
        if quote_pattern.search(opt["link_text_forward"]):
            violations.append(f"Option {opt['option_index']} forward contains quotes")
        if quote_pattern.search(opt["link_text_return"]):
            violations.append(f"Option {opt['option_index']} return contains quotes")

    if violations:
        print(f"  FAIL: {len(violations)} violations found:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options have no quotation marks")
    return True


def test_word_count_9_to_22():
    """Test that all sentences are 9-22 words."""
    print("\n=== Test 4: Word Count 9-22 ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    for opt in options:
        fwd_wc = _word_count(opt["link_text_forward"])
        ret_wc = _word_count(opt["link_text_return"])

        if not (9 <= fwd_wc <= 22):
            violations.append(f"Option {opt['option_index']} forward: {fwd_wc} words (expected 9-22)")
        if not (9 <= ret_wc <= 22):
            violations.append(f"Option {opt['option_index']} return: {ret_wc} words (expected 9-22)")

    if violations:
        print(f"  FAIL: {len(violations)} violations found:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options have 9-22 words per sentence")
    for opt in options:
        fwd_wc = _word_count(opt["link_text_forward"])
        ret_wc = _word_count(opt["link_text_return"])
        print(f"    {opt['option_index']}. Forward: {fwd_wc}w, Return: {ret_wc}w")
    return True


def test_anchors_from_both_items():
    """Test that each sentence contains anchor from A and anchor from B."""
    print("\n=== Test 5: Anchors From Both Items ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    for opt in options:
        handle_a = opt["handle_a_used"].lower()
        handle_b = opt["handle_b_used"].lower()
        fwd = opt["link_text_forward"].lower()
        ret = opt["link_text_return"].lower()

        # Check forward sentence
        a_in_fwd = _contains_anchor(fwd, handle_a)
        b_in_fwd = _contains_anchor(fwd, handle_b)

        # Check return sentence
        a_in_ret = _contains_anchor(ret, handle_a)
        b_in_ret = _contains_anchor(ret, handle_b)

        if not a_in_fwd:
            violations.append(f"Option {opt['option_index']} forward missing anchor A: '{handle_a[:30]}...'")
        if not b_in_fwd:
            violations.append(f"Option {opt['option_index']} forward missing anchor B: '{handle_b[:30]}...'")
        if not a_in_ret:
            violations.append(f"Option {opt['option_index']} return missing anchor A: '{handle_a[:30]}...'")
        if not b_in_ret:
            violations.append(f"Option {opt['option_index']} return missing anchor B: '{handle_b[:30]}...'")

    if violations:
        print(f"  FAIL: {len(violations)} violations found:")
        for v in violations[:10]:  # Limit output
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options contain anchors from both items")
    for opt in options:
        print(f"    {opt['option_index']}. A='{opt['handle_a_used'][:25]}...' B='{opt['handle_b_used'][:25]}...'")
    return True


def test_no_near_duplicates():
    """Test that the 4 options are not near-duplicates (Jaccard < 0.35)."""
    print("\n=== Test 6: No Near-Duplicates ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    violations = []
    jaccard_threshold = 0.35

    for i, opt1 in enumerate(options):
        for j, opt2 in enumerate(options[i+1:], i+1):
            fwd_sim = _token_jaccard(opt1["link_text_forward"], opt2["link_text_forward"])
            ret_sim = _token_jaccard(opt1["link_text_return"], opt2["link_text_return"])

            if fwd_sim > jaccard_threshold:
                violations.append(f"Options {opt1['option_index']} & {opt2['option_index']} forward Jaccard={fwd_sim:.2f}")
            if ret_sim > jaccard_threshold:
                violations.append(f"Options {opt1['option_index']} & {opt2['option_index']} return Jaccard={ret_sim:.2f}")

    if violations:
        print(f"  FAIL: {len(violations)} near-duplicate pairs found:")
        for v in violations:
            print(f"    - {v}")
        return False

    print(f"  PASS: All {len(options)} options are sufficiently diverse")

    # Show pairwise similarities
    for i, opt1 in enumerate(options):
        for j, opt2 in enumerate(options[i+1:], i+1):
            fwd_sim = _token_jaccard(opt1["link_text_forward"], opt2["link_text_forward"])
            print(f"    {opt1['option_index']}<->{opt2['option_index']}: Jaccard={fwd_sim:.2f}")
    return True


def test_human_readable_sentences():
    """Test that sentences read like natural human thoughts."""
    print("\n=== Test 7: Human Readable Sentences ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    # Check for presence of hinge words (if, unless, so, but, yet, etc.)
    hinge_words = {'if', 'unless', 'so', 'but', 'yet', 'still', 'even', 'though',
                   'because', 'since', 'while', 'when', 'whereas', 'although',
                   'despite', 'until', 'once', 'after', 'before', 'maybe', 'suppose'}

    # Check for question marks (engagement)
    sentences_with_hinge = 0
    sentences_with_question = 0

    for opt in options:
        fwd = opt["link_text_forward"].lower()
        ret = opt["link_text_return"].lower()

        has_hinge = any(f' {word} ' in f' {fwd} ' or f' {word} ' in f' {ret} ' for word in hinge_words)
        has_question = '?' in fwd or '?' in ret

        if has_hinge:
            sentences_with_hinge += 1
        if has_question:
            sentences_with_question += 1

    print(f"  Sentences with hinge words: {sentences_with_hinge}/{len(options)}")
    print(f"  Sentences with questions: {sentences_with_question}/{len(options)}")

    # At least half should have hinge words or questions
    if sentences_with_hinge + sentences_with_question >= len(options) // 2:
        print(f"  PASS: Options use human-readable structures")
        return True
    else:
        print(f"  WARN: Options may lack human-readable engagement markers")
        return True  # Soft pass


def test_example_output():
    """Test with the specified example inputs and show output."""
    print("\n=== Test 8: Example Output ===")

    item_a = {
        "id": "it_EXAMPLE_A",
        "title": "Found Text Mystery",
        "body": """I didn't write this... identity of The Author... found text...
giallo... The Big Sleep... captivity mechanism...""",
    }

    item_b = {
        "id": "it_EXAMPLE_B",
        "title": "Curator as Scheherazade",
        "body": """I do not know the identity... collector and curator...
Scheherazade in reverse... One Thousand and One Nights... Magical Dominion...""",
    }

    result = generate_hololoop_options(item_a, item_b, return_debug=True)
    options = result["options"]

    print(f"\n  Generated {len(options)} options (source: {result['source']}):\n")

    for opt in options:
        print(f"  Option {opt['option_index']} [{opt['frame']}]:")
        print(f"    A->B: {opt['link_text_forward']}")
        print(f"    B->A: {opt['link_text_return']}")
        print(f"    Anchors: A='{opt['handle_a_used'][:30]}' B='{opt['handle_b_used'][:30]}'")
        print()

    if result.get("debug"):
        debug = result["debug"]
        print(f"  Debug info:")
        print(f"    Handles A: {debug['handles_a'][:3]}")
        print(f"    Handles B: {debug['handles_b'][:3]}")
        print(f"    Candidates: {debug['candidates_generated']} -> {debug['candidates_filtered']} filtered -> {debug.get('candidates_final', 4)} final")

    return True


def test_banned_opener_helper():
    """Unit test for _has_banned_opener helper."""
    print("\n=== Test 9: Banned Opener Helper ===")

    # Should detect banned openers
    assert _has_banned_opener("How does X relate to Y") == True
    assert _has_banned_opener("Compare X with Y") == True
    assert _has_banned_opener("Trace the connection between") == True
    assert _has_banned_opener("Provide evidence for") == True
    assert _has_banned_opener("Give me a summary of") == True
    assert _has_banned_opener("Define what X means") == True
    assert _has_banned_opener("Explain why this matters") == True

    # Should NOT detect these (valid sentences)
    assert _has_banned_opener("If X is true then Y follows") == False
    assert _has_banned_opener("The comparison reveals something") == False
    assert _has_banned_opener("Without X there would be no Y") == False
    assert _has_banned_opener("Maybe X was the excuse") == False

    print("  PASS: Banned opener detection works correctly")
    return True


def test_banned_phrase_helper():
    """Unit test for _has_banned_phrase helper."""
    print("\n=== Test 10: Banned Phrase Helper ===")

    # Should detect banned phrases
    assert _has_banned_phrase("X opens a path to Y") == True
    assert _has_banned_phrase("This traces back to the origin") == True
    assert _has_banned_phrase("X provides a foundation for Y") == True
    assert _has_banned_phrase("A relates to B") == True
    assert _has_banned_phrase("How X leads into Y") == True

    # Should NOT detect these (valid sentences)
    assert _has_banned_phrase("If X is true then Y follows") == False
    assert _has_banned_phrase("The tension between X and Y") == False
    assert _has_banned_phrase("Maybe X was just the excuse") == False

    print("  PASS: Banned phrase detection works correctly")
    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE v0.1 HOLOLINK QUALITY ACCEPTANCE TESTS")
    print("=" * 70)

    tests = [
        ("No Banned Openers", test_no_banned_openers),
        ("No Banned Phrases", test_no_banned_phrases),
        ("No Quotation Marks", test_no_quotation_marks),
        ("Word Count 9-22", test_word_count_9_to_22),
        ("Anchors From Both Items", test_anchors_from_both_items),
        ("No Near-Duplicates", test_no_near_duplicates),
        ("Human Readable Sentences", test_human_readable_sentences),
        ("Example Output", test_example_output),
        ("Banned Opener Helper", test_banned_opener_helper),
        ("Banned Phrase Helper", test_banned_phrase_helper),
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
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
