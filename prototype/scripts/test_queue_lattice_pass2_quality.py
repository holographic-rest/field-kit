#!/usr/bin/env python3
"""
Queue Lattice PASS 2 Quality Acceptance Test

Tests that hololoop generation produces content-derived, NO-QUOTE output.

CRITICAL ASSERTIONS:
- 4 options returned
- Each option contains handles as plain text (no quotes)
- forward_text and return_text contain NO quotation marks
- Banned boilerplate phrases are absent
- At most 1 option uses "How does" framing
- >= 3 distinct handles used across 4 options
- Options differ when item content changes

Run: python3 prototype/scripts/test_queue_lattice_pass2_quality.py
"""

import sys
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.hololoop_engine import generate_hololoop_options
from fieldkit.handles import extract_handles, strip_all_quotes

# === Sample literary content for testing ===

SAMPLE_PAGE_1 = """
The Author of these tales cannot be located. What remains is a collection
of manuscripts found in an abandoned study, each one bearing marks of
multiple hands. The collector became detective, then curator, preserving
what could not be attributed. If the original writer exists, they have
chosen silence over signature.

The mystery of authorship frames every page that follows.
"""

SAMPLE_PAGE_2 = """
Scheherazade told stories to survive. Here the mechanism inverts:
stories are told because someone has already disappeared. The narrative
becomes evidence of absence. Each tale serves as testimony to a voice
that cannot defend itself.

The Giallo tradition teaches us that confusion can be design. When
The Big Sleep leaves readers bewildered, Chandler makes a virtue of
bewilderment. Perhaps these unsigned manuscripts do the same.

Magical Dominion suggests authorship itself is a kind of captivity.
"""

SAMPLE_PAGE_3_DIFFERENT = """
The infrastructure layer handles all database connections and API routing.
Kubernetes orchestration manages container lifecycle across nodes.
Load balancing distributes traffic to prevent single points of failure.

CI/CD pipelines automate the deployment of microservices.
"""

# Quote characters to check for
QUOTE_CHARS = set('"\'""''«»')

# Banned boilerplate patterns
BANNED_PATTERNS = [
    r'provide\s+evidence',
    r'validate\s+',
    r'operationalize\s+',
    r'test\s+case',
    r'checklist',
    r'schema\s+for',
    r'in\s+this\s+context',
    r'explain\s+why\s+it\s+matters',
    r'walk\s+me\s+through',
    r'give\s+me\s+a\s+',
    r'derive\s+a\s+',
    r'expand\s+.*\s+into\s+a\s+\d+',
]


def contains_quotes(text: str) -> bool:
    """Check if text contains any quotation marks."""
    return any(c in text for c in QUOTE_CHARS)


def contains_banned_pattern(text: str) -> bool:
    """Check if text contains banned boilerplate."""
    text_lower = text.lower()
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def test_basic_generation():
    """Test that we get 4 valid options."""
    print("\n=== Test 1: Basic Generation ===")

    item_a = {
        "id": "it_PAGE1",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_PAGE2",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b, return_debug=True)

    assert "options" in result, "Missing 'options' in result"
    assert len(result["options"]) == 4, f"Expected 4 options, got {len(result['options'])}"

    print(f"  ✓ Generated {len(result['options'])} options")
    print(f"  ✓ Source: {result.get('source', 'unknown')}")

    if "debug" in result:
        print(f"  ✓ Handles A: {result['debug']['handles_a'][:3]}...")
        print(f"  ✓ Handles B: {result['debug']['handles_b'][:3]}...")

    return True


def test_no_quotes_in_output():
    """CRITICAL: Test that NO quotation marks appear in hololink text."""
    print("\n=== Test 2: NO Quotes in Output (CRITICAL) ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_B",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b)

    quote_violations = []
    for opt in result["options"]:
        fwd = opt["link_text_forward"]
        ret = opt["link_text_return"]

        if contains_quotes(fwd):
            quote_violations.append(f"Option {opt['option_index']} forward: {fwd}")
        if contains_quotes(ret):
            quote_violations.append(f"Option {opt['option_index']} return: {ret}")

    if quote_violations:
        print("  ✗ QUOTE VIOLATIONS FOUND:")
        for v in quote_violations:
            print(f"    - {v}")
        assert False, f"Found {len(quote_violations)} quote violations"

    print("  ✓ All 4 options contain ZERO quotation marks")

    # Show samples
    for opt in result["options"][:2]:
        print(f"    Option {opt['option_index']}: {opt['link_text_forward'][:60]}...")

    return True


def test_handles_appear_verbatim():
    """Test that handles appear as plain text substrings."""
    print("\n=== Test 3: Handles Appear Verbatim ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_B",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b, return_debug=True)

    # Known handle tokens we expect to see
    expected_tokens = [
        "author", "collector", "scheherazade", "giallo",
        "big sleep", "magical dominion", "mystery", "authorship",
        "narrative", "captivity", "manuscripts", "detective"
    ]

    handles_found = 0
    for opt in result["options"]:
        fwd_lower = opt["link_text_forward"].lower()
        ret_lower = opt["link_text_return"].lower()

        for token in expected_tokens:
            if token in fwd_lower or token in ret_lower:
                handles_found += 1
                break

    assert handles_found >= 2, f"Expected at least 2 options with recognizable handles, found {handles_found}"

    print(f"  ✓ {handles_found}/4 options contain recognizable content handles")

    # Check that handle_a_used and handle_b_used are present
    for opt in result["options"]:
        ha = opt.get("handle_a_used", "")
        hb = opt.get("handle_b_used", "")
        if ha and hb:
            print(f"    Option {opt['option_index']} uses: {ha[:25]}... • {hb[:25]}...")

    return True


def test_no_banned_boilerplate():
    """Test that banned boilerplate patterns are absent."""
    print("\n=== Test 4: No Banned Boilerplate ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_B",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b)

    violations = []
    for opt in result["options"]:
        fwd = opt["link_text_forward"]
        ret = opt["link_text_return"]

        if contains_banned_pattern(fwd):
            violations.append(f"Option {opt['option_index']} forward: {fwd}")
        if contains_banned_pattern(ret):
            violations.append(f"Option {opt['option_index']} return: {ret}")

    if violations:
        print("  ✗ BOILERPLATE VIOLATIONS:")
        for v in violations:
            print(f"    - {v}")
        assert False, f"Found {len(violations)} boilerplate violations"

    print("  ✓ All options free of banned boilerplate")
    return True


def test_max_one_how_does():
    """Test that at most 1 option uses 'How does' framing."""
    print("\n=== Test 5: Max 1 'How does' Framing ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_B",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b)

    how_does_count = 0
    for opt in result["options"]:
        fwd = opt["link_text_forward"].lower()
        ret = opt["link_text_return"].lower()

        if fwd.startswith("how does") or ret.startswith("how does"):
            how_does_count += 1

    assert how_does_count <= 1, f"Expected at most 1 'How does' pattern, found {how_does_count}"

    print(f"  ✓ 'How does' framing count: {how_does_count} (max allowed: 1)")
    return True


def test_handle_diversity():
    """Test that >= 3 distinct handles are used across 4 options."""
    print("\n=== Test 6: Handle Diversity ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }
    item_b = {
        "id": "it_B",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    result = generate_hololoop_options(item_a, item_b)

    unique_handles = set()
    for opt in result["options"]:
        ha = opt.get("handle_a_used", "")
        hb = opt.get("handle_b_used", "")
        if ha:
            unique_handles.add(ha.lower()[:20])  # Truncate for comparison
        if hb:
            unique_handles.add(hb.lower()[:20])

    assert len(unique_handles) >= 3, f"Expected >= 3 distinct handles, found {len(unique_handles)}"

    print(f"  ✓ {len(unique_handles)} distinct handles used across 4 options")
    for h in list(unique_handles)[:5]:
        print(f"    - {h}...")

    return True


def test_options_differ_by_content():
    """Test that options change when item content changes."""
    print("\n=== Test 7: Options Differ by Content ===")

    item_a = {
        "id": "it_A",
        "title": "The Author Preface",
        "body": SAMPLE_PAGE_1,
    }

    # First with literary content
    item_b1 = {
        "id": "it_B1",
        "title": "Scheherazade in Reverse",
        "body": SAMPLE_PAGE_2,
    }

    # Then with technical content
    item_b2 = {
        "id": "it_B2",
        "title": "Infrastructure Layer",
        "body": SAMPLE_PAGE_3_DIFFERENT,
    }

    result1 = generate_hololoop_options(item_a, item_b1)
    result2 = generate_hololoop_options(item_a, item_b2)

    # Compare forward texts
    texts1 = set(opt["link_text_forward"].lower() for opt in result1["options"])
    texts2 = set(opt["link_text_forward"].lower() for opt in result2["options"])

    overlap = texts1 & texts2
    assert len(overlap) < 3, f"Too much overlap between different content: {len(overlap)} identical options"

    print(f"  ✓ Options change when content changes")
    print(f"    Literary content sample: {result1['options'][0]['link_text_forward'][:50]}...")
    print(f"    Technical content sample: {result2['options'][0]['link_text_forward'][:50]}...")

    return True


def test_handle_extraction_no_quotes():
    """Test that handle extraction strips all quotes."""
    print("\n=== Test 8: Handle Extraction Strips Quotes ===")

    # Content with various quote styles
    text_with_quotes = '''
    The "Author" cannot be found. 'Scheherazade' told stories.
    He called it the "Big Sleep" mystery. The 'collector' searched.
    "Giallo" framing makes confusion intentional.
    '''

    handles = extract_handles(text_with_quotes, "Test Title")

    for h in handles:
        quote = h["quote"]
        if contains_quotes(quote):
            print(f"  ✗ Handle contains quotes: {quote}")
            assert False, f"Handle contains quotes: {quote}"

    print(f"  ✓ Extracted {len(handles)} handles, all quote-free")
    for h in handles[:5]:
        print(f"    - {h['quote'][:40]}...")

    return True


def test_strip_all_quotes_function():
    """Test the strip_all_quotes utility function."""
    print("\n=== Test 9: strip_all_quotes Function ===")

    test_cases = [
        ('"The Author"', 'The Author'),
        ("'Scheherazade'", 'Scheherazade'),
        ('"Giallo" framing', 'Giallo framing'),
        ('The "Big Sleep" mystery', 'The Big Sleep mystery'),
        ('\u201cquoted\u201d text', 'quoted text'),
        ('\u00abguillemets\u00bb', 'guillemets'),
    ]

    for input_text, expected in test_cases:
        result = strip_all_quotes(input_text)
        assert result == expected, f"strip_all_quotes('{input_text}') = '{result}', expected '{expected}'"

    print("  ✓ All strip_all_quotes test cases pass")
    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE PASS 2 QUALITY ACCEPTANCE TEST")
    print("Hololoop Generation: Content-Derived, NO QUOTES")
    print("=" * 70)

    tests = [
        ("Basic Generation", test_basic_generation),
        ("NO Quotes in Output", test_no_quotes_in_output),
        ("Handles Appear Verbatim", test_handles_appear_verbatim),
        ("No Banned Boilerplate", test_no_banned_boilerplate),
        ("Max 1 'How does' Framing", test_max_one_how_does),
        ("Handle Diversity", test_handle_diversity),
        ("Options Differ by Content", test_options_differ_by_content),
        ("Handle Extraction Strips Quotes", test_handle_extraction_no_quotes),
        ("strip_all_quotes Function", test_strip_all_quotes_function),
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
                print(f"  ✗ {name} returned False")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
