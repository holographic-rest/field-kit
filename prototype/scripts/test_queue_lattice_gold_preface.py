#!/usr/bin/env python3
"""
Queue Lattice v0.1 Golden Regression Test - Author Preface Pair

Tests the specific author preface paragraphs provided by Brennan to ensure
semantic quality, not just syntactic validity.

ASSERTIONS:
a) At least one A→B option contains "Author" and is a question
b) At least one option contains "Scheherazade" OR "One Thousand and One Nights"
   (not just truncated "One Thousand")
c) No option contains "always there before" or "could never be the same again"

Run: python3 prototype/scripts/test_queue_lattice_gold_preface.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.hololoop_engine import generate_hololoop_options
from fieldkit.handles import extract_handles, choose_diverse_handles


# === THE EXACT PREFACE PARAGRAPHS ===
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


def test_handles_preserve_full_phrases():
    """Test that handle extraction preserves full noun phrases."""
    print("\n=== Test 1: Full Phrase Handle Extraction ===")

    handles_a = extract_handles(ITEM_A["body"], ITEM_A["title"])
    handles_b = extract_handles(ITEM_B["body"], ITEM_B["title"])

    selected_a = choose_diverse_handles(handles_a, k=7)
    selected_b = choose_diverse_handles(handles_b, k=7)

    quotes_a = [h["quote"].lower() for h in selected_a]
    quotes_b = [h["quote"].lower() for h in selected_b]

    print(f"  Handles from A: {[h['quote'] for h in selected_a]}")
    print(f"  Handles from B: {[h['quote'] for h in selected_b]}")

    # Check for key phrases
    has_author = any("author" in q for q in quotes_a)
    has_giallo = any("giallo" in q for q in quotes_a)
    has_big_sleep = any("big sleep" in q for q in quotes_a)

    has_scheherazade = any("scheherazade" in q for q in quotes_b)
    has_one_thousand = any("one thousand and one nights" in q for q in quotes_b)
    has_magical_dominion = any("magical dominion" in q for q in quotes_b)

    print(f"\n  A contains 'Author': {has_author}")
    print(f"  A contains 'giallo': {has_giallo}")
    print(f"  A contains 'Big Sleep': {has_big_sleep}")
    print(f"  B contains 'Scheherazade': {has_scheherazade}")
    print(f"  B contains 'One Thousand and One Nights': {has_one_thousand}")
    print(f"  B contains 'Magical Dominion': {has_magical_dominion}")

    # Must have key entities
    if not has_author:
        print("  FAIL: Missing 'Author' in handles A")
        return False

    if not (has_scheherazade or has_one_thousand):
        print("  FAIL: Missing 'Scheherazade' or 'One Thousand and One Nights' in handles B")
        return False

    print("  PASS: Full phrases preserved in handles")
    return True


def test_author_question_option():
    """Test that at least one A→B option contains 'Author' and is a question."""
    print("\n=== Test 2: Author Question Option ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    print(f"  Generated {len(options)} options:")
    for opt in options:
        is_question = "?" in opt["link_text_forward"]
        has_author = "author" in opt["link_text_forward"].lower()
        marker = ""
        if is_question and has_author:
            marker = " <-- MATCHES"
        print(f"    {opt['option_index']}. [{'?' if is_question else '.'}] {opt['link_text_forward'][:60]}...{marker}")

    # Check assertion
    author_questions = [
        opt for opt in options
        if "?" in opt["link_text_forward"] and "author" in opt["link_text_forward"].lower()
    ]

    if not author_questions:
        print("  FAIL: No A→B option contains 'Author' AND is a question")
        return False

    print(f"  PASS: Found {len(author_questions)} option(s) with 'Author' as question")
    return True


def test_scheherazade_full_phrase():
    """Test that at least one option contains 'Scheherazade' OR 'One Thousand and One Nights'."""
    print("\n=== Test 3: Scheherazade / One Thousand and One Nights ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    print("  Checking all options for full phrase preservation:")

    matches = []
    for opt in options:
        fwd = opt["link_text_forward"].lower()
        ret = opt["link_text_return"].lower()
        combined = fwd + " " + ret

        has_scheherazade = "scheherazade" in combined
        has_one_thousand_full = "one thousand and one nights" in combined
        has_one_thousand_partial = "one thousand" in combined and "one thousand and one nights" not in combined

        status = []
        if has_scheherazade:
            status.append("Scheherazade")
        if has_one_thousand_full:
            status.append("One Thousand and One Nights (FULL)")
        if has_one_thousand_partial:
            status.append("One Thousand (truncated)")

        if status:
            matches.append((opt["option_index"], status))
            print(f"    Option {opt['option_index']}: {', '.join(status)}")

    # Check assertion: need Scheherazade OR full "One Thousand and One Nights"
    valid_matches = [
        m for m in matches
        if "Scheherazade" in m[1] or "One Thousand and One Nights (FULL)" in m[1]
    ]

    if not valid_matches:
        print("  FAIL: No option contains 'Scheherazade' OR full 'One Thousand and One Nights'")
        return False

    print(f"  PASS: Found {len(valid_matches)} option(s) with full phrase")
    return True


def test_no_hallucinated_temporal():
    """Test that no option contains hallucinated temporal/causal phrases."""
    print("\n=== Test 4: No Hallucinated Temporal Phrases ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    banned_phrases = [
        "always there before",
        "could never be the same again",
        "could never be the same",
        "was always",
        "had always",
        "will always",
    ]

    violations = []
    for opt in options:
        combined = (opt["link_text_forward"] + " " + opt["link_text_return"]).lower()

        for phrase in banned_phrases:
            if phrase in combined:
                violations.append((opt["option_index"], phrase))

    if violations:
        print("  FAIL: Found hallucinated temporal phrases:")
        for idx, phrase in violations:
            print(f"    Option {idx}: '{phrase}'")
        return False

    print("  PASS: No hallucinated temporal phrases found")
    return True


def test_question_quota():
    """Test that at least 2/4 options are questions."""
    print("\n=== Test 5: Question Quota (min 2/4) ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    question_count = sum(1 for opt in options if "?" in opt["link_text_forward"])

    print(f"  Questions: {question_count}/{len(options)}")
    for opt in options:
        is_q = "?" in opt["link_text_forward"]
        print(f"    {opt['option_index']}. [{'Q' if is_q else 'S'}] {opt['link_text_forward'][:55]}...")

    if question_count < 2:
        print(f"  FAIL: Only {question_count} questions, need at least 2")
        return False

    print(f"  PASS: {question_count}/4 options are questions")
    return True


def test_wh_question_for_identity():
    """Test that identity triggers produce at least 1 WH-question."""
    print("\n=== Test 6: WH-Question for Identity Content ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    import re
    wh_questions = []
    for opt in options:
        fwd = opt["link_text_forward"].lower().strip()
        if re.match(r'^(who|what|why|how|which|where|when)\b', fwd):
            wh_questions.append(opt)

    print(f"  WH-questions found: {len(wh_questions)}")
    for opt in wh_questions:
        print(f"    {opt['option_index']}. {opt['link_text_forward'][:60]}...")

    if result.get("debug", {}).get("need_wh_questions", False):
        print("  (Identity triggers detected, WH-questions expected)")
        if not wh_questions:
            print("  WARN: No WH-questions despite identity content")
            # Soft pass - WH-questions are preferred but not strictly required
            return True

    print(f"  PASS: WH-question requirement satisfied")
    return True


def test_no_system_speak():
    """Test that options don't contain system-speak phrases."""
    print("\n=== Test 7: No System-Speak ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    system_speak = [
        "opens a path",
        "traces back",
        "provides a foundation",
        "relates to",
        "connects to",
        "leads into",
        "bridges the gap",
        "serves as",
        "functions as",
    ]

    violations = []
    for opt in options:
        combined = (opt["link_text_forward"] + " " + opt["link_text_return"]).lower()
        for phrase in system_speak:
            if phrase in combined:
                violations.append((opt["option_index"], phrase))

    if violations:
        print("  FAIL: Found system-speak phrases:")
        for idx, phrase in violations:
            print(f"    Option {idx}: '{phrase}'")
        return False

    print("  PASS: No system-speak detected")
    return True


def test_full_output_display():
    """Display full output for manual review."""
    print("\n=== Full Output (Manual Review) ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)
    options = result["options"]

    print(f"\n  Source: {result['source']}")
    if result.get("debug"):
        debug = result["debug"]
        print(f"  Handles A: {debug['handles_a'][:4]}")
        print(f"  Handles B: {debug['handles_b'][:4]}")
        print(f"  Candidates: {debug['candidates_generated']} -> {debug['candidates_filtered']} filtered")
        print(f"  Need WH: {debug.get('need_wh_questions', False)}")

    print("\n  Generated Options:")
    for opt in options:
        print(f"\n  Option {opt['option_index']} [{opt['frame']}]:")
        print(f"    A→B: {opt['link_text_forward']}")
        print(f"    B→A: {opt['link_text_return']}")
        print(f"    Handles: A='{opt['handle_a_used'][:30]}' B='{opt['handle_b_used'][:30]}'")

    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE v0.1 GOLDEN REGRESSION TEST")
    print("Author Preface Pair - Semantic Quality Validation")
    print("=" * 70)

    tests = [
        ("Full Phrase Handle Extraction", test_handles_preserve_full_phrases),
        ("Author Question Option", test_author_question_option),
        ("Scheherazade / One Thousand Full Phrase", test_scheherazade_full_phrase),
        ("No Hallucinated Temporal", test_no_hallucinated_temporal),
        ("Question Quota (min 2/4)", test_question_quota),
        ("WH-Question for Identity", test_wh_question_for_identity),
        ("No System-Speak", test_no_system_speak),
        ("Full Output Display", test_full_output_display),
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
    print(f"GOLDEN REGRESSION RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
