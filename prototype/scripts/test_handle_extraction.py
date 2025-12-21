#!/usr/bin/env python3
"""
Sprint G Test: Handle Extraction

Tests the extract_handles function for context engineering.

Test cases:
1. PAGE 1 architecture content - should extract meaningful handles
2. Messy paragraph-only sample - should find noun phrases
3. Short 1-line item - should work with minimal content

Assertions:
- handles are non-empty
- no handle starts with "This document describes"
- no handle equals "PAGE 1"
- deterministic output (same input => same handles)

Usage:
    python prototype/scripts/test_handle_extraction.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.spin_recipes import extract_handles


# Test fixture: PAGE 1 architecture content
PAGE_1_CONTENT = """PAGE 1 – Purpose of This Document

Title: FIELD – Purpose of the Field Overview

This document describes the Gibsey / Holographic Field as a single, layered system:

What the field is: a living memory + inference space grounded in The Entrance Way, the Vault, and QDPI events.

How the field is implemented: from linear algebra and GPUs up through microservices, RAG, and agents.

How a single interaction moves through the stack.

How the field learns about itself and improves over time.

This is meant to be a high-level but technically clear overview for:

Future collaborators / engineers.

BKC / research partners.

Your own architectural sanity."""

# Test fixture: Messy paragraph-only sample
MESSY_PARAGRAPHS = """
The authentication system handles user identity verification across all services.
OAuth 2.0 tokens are issued by the Identity Provider after successful login.
Session management relies on JWT tokens with configurable expiry times.
The rate limiting module prevents abuse by tracking request counts per user.
API endpoints are protected by role-based access control (RBAC).
Logging and monitoring capture all authentication events for audit purposes.
"""

# Test fixture: Short 1-line item
SHORT_ITEM = "I am a butthead"


def test_page1_handles():
    """Test handle extraction from PAGE 1 content."""
    print("\n" + "-" * 70)
    print("TEST 1: PAGE 1 architecture content")
    print("-" * 70)

    handles = extract_handles("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h}'")

    # Assertions
    assert len(handles) >= 4, f"Expected at least 4 handles, got {len(handles)}"
    assert len(handles) <= 12, f"Expected at most 12 handles, got {len(handles)}"

    # No handle should start with "This document describes"
    for h in handles:
        assert not h.lower().startswith("this document describes"), \
            f"Handle should not start with filler: '{h}'"

    # No handle should be "PAGE 1" or similar
    for h in handles:
        assert not (h.upper().startswith("PAGE") and len(h.split()) <= 2), \
            f"Handle should not be PAGE pattern: '{h}'"

    # Should extract meaningful handles like "What the field is"
    all_handles_lower = ' '.join(handles).lower()
    # Check for expected content-derived handles
    expected_handles = ["field", "vault", "qdpi", "entrance"]
    found_expected = sum(1 for e in expected_handles if e in all_handles_lower)
    assert found_expected >= 2, \
        f"Expected to find at least 2 of {expected_handles} in handles, found {found_expected}"

    print("  PASSED: Handles are content-derived, no junk patterns")
    return True


def test_messy_paragraphs():
    """Test handle extraction from messy paragraph-only content."""
    print("\n" + "-" * 70)
    print("TEST 2: Messy paragraph-only sample")
    print("-" * 70)

    handles = extract_handles("Authentication System Overview", MESSY_PARAGRAPHS)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h}'")

    # Assertions
    assert len(handles) >= 2, f"Expected at least 2 handles, got {len(handles)}"

    # Should find noun phrases from the content
    all_handles_lower = ' '.join(handles).lower()
    expected_terms = ["authentication", "oauth", "jwt", "api", "session"]
    found_terms = sum(1 for t in expected_terms if t in all_handles_lower)
    assert found_terms >= 1, \
        f"Expected to find at least 1 of {expected_terms} in handles, found {found_terms}"

    print("  PASSED: Handles extracted from paragraphs")
    return True


def test_short_item():
    """Test handle extraction from short 1-line item."""
    print("\n" + "-" * 70)
    print("TEST 3: Short 1-line item")
    print("-" * 70)

    handles = extract_handles(SHORT_ITEM, None)

    print(f"  Extracted {len(handles)} handles:")
    for i, h in enumerate(handles, 1):
        print(f"    {i}. '{h}'")

    # Assertions - should have at least 1 handle (the title itself)
    assert len(handles) >= 1, f"Expected at least 1 handle, got {len(handles)}"

    # The title should be a handle
    assert SHORT_ITEM in handles or any(SHORT_ITEM.lower() in h.lower() for h in handles), \
        f"Short title should be a handle"

    print("  PASSED: Short item handled correctly")
    return True


def test_determinism():
    """Test that handle extraction is deterministic."""
    print("\n" + "-" * 70)
    print("TEST 4: Determinism verification")
    print("-" * 70)

    handles1 = extract_handles("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)
    handles2 = extract_handles("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    assert handles1 == handles2, \
        f"Handle extraction should be deterministic:\n  Run 1: {handles1}\n  Run 2: {handles2}"

    print("  PASSED: Same input produces same output")
    return True


def test_no_junk_handles():
    """Test that no junk patterns slip through."""
    print("\n" + "-" * 70)
    print("TEST 5: No junk patterns in handles")
    print("-" * 70)

    handles = extract_handles("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    junk_patterns = [
        "this document describes",
        "this is meant to be",
        "the following",
        "page 1",
        "page 2",
    ]

    for h in handles:
        h_lower = h.lower()
        for junk in junk_patterns:
            assert not h_lower.startswith(junk), \
                f"Handle should not start with junk: '{h}'"

    print("  PASSED: No junk patterns found")
    return True


def main():
    """Run all handle extraction tests."""
    print("=" * 70)
    print("SPRINT G TEST: Handle Extraction")
    print("=" * 70)

    tests = [
        ("PAGE 1 content", test_page1_handles),
        ("Messy paragraphs", test_messy_paragraphs),
        ("Short item", test_short_item),
        ("Determinism", test_determinism),
        ("No junk patterns", test_no_junk_handles),
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
        print("All handle extraction tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
