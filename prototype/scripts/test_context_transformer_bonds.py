#!/usr/bin/env python3
"""
Context Transformer Bond Tests

Tests the 3-stage Context Transformer pipeline:
1. ENCODER: Extract span-level anchors from Item content
2. DECODER: Generate one-sentence Bonds with verbatim quotes
3. VALIDATOR: Reject generic patterns, ensure content-grounding

Test cases:
1. PAGE 1 architecture content - should extract meaningful anchors
2. Butthead test - anchor from short item must appear in suggestion
3. Numeric constraint test - all bonds must have numbers
4. No banned patterns - no generic starters
5. Determinism - same input => same output

Usage:
    python prototype/scripts/test_context_transformer_bonds.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.context_transformer import (
    Anchor,
    BondSuggestion,
    extract_anchors,
    rank_anchors,
    generate_bonds,
    validate_bond,
    validate_bonds,
    transform_context,
    transform_holologue_context,
    suggestions_to_legacy_format,
    BANNED_PATTERNS,
)
import re


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

# Test fixture: Short 1-line item (butthead test)
SHORT_ITEM = "I am a butthead"


def test_encoder_page1():
    """Test ENCODER stage: anchor extraction from PAGE 1 content."""
    print("\n" + "-" * 70)
    print("TEST 1: ENCODER - PAGE 1 architecture content")
    print("-" * 70)

    anchors = extract_anchors("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    print(f"  Extracted {len(anchors)} anchors:")
    for i, a in enumerate(anchors[:8], 1):
        print(f"    {i}. [{a.source_kind}] '{a.anchor_text}'")
        print(f"       Quote: '{a.quote[:60]}...'")

    # Assertions
    assert len(anchors) >= 4, f"Expected at least 4 anchors, got {len(anchors)}"
    assert len(anchors) <= 20, f"Expected at most 20 anchors, got {len(anchors)}"

    # Should have diverse source kinds
    source_kinds = {a.source_kind for a in anchors}
    assert len(source_kinds) >= 2, \
        f"Expected at least 2 source kinds, got {source_kinds}"

    # No anchor should be PAGE pattern
    for a in anchors:
        assert not a.anchor_text.upper().startswith("PAGE"), \
            f"Anchor should not be PAGE pattern: '{a.anchor_text}'"

    # Should extract meaningful content-derived anchors
    all_anchor_text = ' '.join(a.anchor_text.lower() for a in anchors)
    expected_terms = ["field", "vault", "qdpi", "entrance", "holographic"]
    found = sum(1 for t in expected_terms if t in all_anchor_text)
    assert found >= 2, \
        f"Expected to find at least 2 of {expected_terms} in anchors, found {found}"

    print("  PASSED: Anchors are content-derived with diverse source kinds")
    return True


def test_encoder_short_item():
    """Test ENCODER stage: anchor extraction from short 1-line item."""
    print("\n" + "-" * 70)
    print("TEST 2: ENCODER - Short 1-line item (butthead test)")
    print("-" * 70)

    anchors = extract_anchors(SHORT_ITEM, None)

    print(f"  Extracted {len(anchors)} anchors:")
    for i, a in enumerate(anchors, 1):
        print(f"    {i}. [{a.source_kind}] '{a.anchor_text}'")

    # Assertions - should have at least 1 anchor
    assert len(anchors) >= 1, f"Expected at least 1 anchor, got {len(anchors)}"

    # The title should be an anchor or be referenced
    has_title_anchor = any(
        SHORT_ITEM.lower() in a.anchor_text.lower() or
        a.anchor_text.lower() in SHORT_ITEM.lower()
        for a in anchors
    )
    assert has_title_anchor, f"Short title should be an anchor"

    print("  PASSED: Short item handled correctly")
    return True


def test_decoder_bond_generation():
    """Test DECODER stage: bond generation from anchors."""
    print("\n" + "-" * 70)
    print("TEST 3: DECODER - Bond generation")
    print("-" * 70)

    anchors = extract_anchors("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)
    bonds = generate_bonds(anchors, "PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    print(f"  Generated {len(bonds)} bonds:")
    for i, b in enumerate(bonds, 1):
        print(f"    {i}. [{b.operation}] {b.display_text[:60]}...")
        print(f"       Anchor: '{b.anchor_text}'")

    # Assertions
    assert len(bonds) == 4, f"Expected exactly 4 bonds, got {len(bonds)}"

    # All 4 operations should be present
    operations = {b.operation for b in bonds}
    expected_ops = {"CLARIFY", "MAP", "TRACE", "TEST"}
    assert operations == expected_ops, \
        f"Expected operations {expected_ops}, got {operations}"

    # Each bond should have display_text <= 240 chars
    for b in bonds:
        assert len(b.display_text) <= 240, \
            f"Display text exceeds 240 chars: {len(b.display_text)}"

    print("  PASSED: Bonds generated with all 4 operations")
    return True


def test_decoder_numeric_constraint():
    """Test DECODER stage: all bonds have numeric constraints."""
    print("\n" + "-" * 70)
    print("TEST 4: DECODER - Numeric constraints")
    print("-" * 70)

    bonds = transform_context("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    print(f"  Checking {len(bonds)} bonds for numeric constraints:")
    for i, b in enumerate(bonds, 1):
        has_num = bool(re.search(r'\b\d+\b', b.display_text))
        status = "✓" if has_num else "✗"
        print(f"    {i}. {status} {b.display_text[:50]}...")

    # All bonds should have numeric constraint
    for b in bonds:
        has_numeric = bool(re.search(r'\b\d+\b', b.display_text))
        assert has_numeric, \
            f"Bond missing numeric constraint: '{b.display_text}'"

    print("  PASSED: All bonds have numeric constraints")
    return True


def test_validator_no_banned_patterns():
    """Test VALIDATOR stage: no banned patterns in output."""
    print("\n" + "-" * 70)
    print("TEST 5: VALIDATOR - No banned patterns")
    print("-" * 70)

    bonds = transform_context("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    print(f"  Checking {len(bonds)} bonds for banned patterns...")

    banned_starters = [
        "give me a test case that validates",
        "explain this",
        "walk me through",
        "tell me about",
        "help me understand",
    ]

    for b in bonds:
        display_lower = b.display_text.lower()
        for banned in banned_starters:
            assert not display_lower.startswith(banned), \
                f"Bond starts with banned pattern '{banned}': '{b.display_text}'"

    print("  PASSED: No banned patterns found")
    return True


def test_butthead_anchor_in_suggestion():
    """Test that short item title appears in suggestion (butthead test)."""
    print("\n" + "-" * 70)
    print("TEST 6: BUTTHEAD TEST - Anchor from short item in suggestion")
    print("-" * 70)

    bonds = transform_context(SHORT_ITEM, None)

    print(f"  Generated {len(bonds)} bonds for '{SHORT_ITEM}':")
    for i, b in enumerate(bonds, 1):
        print(f"    {i}. [{b.operation}] {b.display_text}")

    # At least one bond should contain the anchor text verbatim or reference it
    anchor_found = any(
        SHORT_ITEM.lower() in b.display_text.lower() or
        "butthead" in b.display_text.lower() or
        b.anchor_text.lower() in SHORT_ITEM.lower()
        for b in bonds
    )

    assert anchor_found, \
        f"Expected to find '{SHORT_ITEM}' or related anchor in suggestions"

    print("  PASSED: Short item anchor found in suggestions")
    return True


def test_determinism():
    """Test that context transformation is deterministic."""
    print("\n" + "-" * 70)
    print("TEST 7: Determinism verification")
    print("-" * 70)

    bonds1 = transform_context("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)
    bonds2 = transform_context("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)

    # Compare display_text for each bond
    for i, (b1, b2) in enumerate(zip(bonds1, bonds2)):
        assert b1.display_text == b2.display_text, \
            f"Bond {i} differs:\n  Run 1: {b1.display_text}\n  Run 2: {b2.display_text}"
        assert b1.anchor_text == b2.anchor_text, \
            f"Anchor {i} differs:\n  Run 1: {b1.anchor_text}\n  Run 2: {b2.anchor_text}"

    print("  PASSED: Same input produces same output")
    return True


def test_legacy_format_conversion():
    """Test conversion to legacy format for backward compatibility."""
    print("\n" + "-" * 70)
    print("TEST 8: Legacy format conversion")
    print("-" * 70)

    bonds = transform_context("PAGE 1 – Purpose of This Document", PAGE_1_CONTENT)
    legacy = suggestions_to_legacy_format(bonds)

    print(f"  Converted {len(legacy)} bonds to legacy format:")
    for i, s in enumerate(legacy, 1):
        print(f"    {i}. recipe_id: {s['recipe_id']}")
        print(f"       intent_type: {s['intent_type']}")
        print(f"       display_text: {s['display_text'][:40]}...")

    # Assertions
    assert len(legacy) == 4, f"Expected 4 suggestions, got {len(legacy)}"

    # Each should have required keys
    required_keys = {"display_text", "prompt_text", "intent_type", "recipe_id"}
    for s in legacy:
        assert required_keys.issubset(s.keys()), \
            f"Missing keys: {required_keys - set(s.keys())}"

    print("  PASSED: Legacy format conversion works")
    return True


def test_holologue_context():
    """Test Holologue context transformation."""
    print("\n" + "-" * 70)
    print("TEST 9: Holologue context transformation")
    print("-" * 70)

    holologue_output = """
## Unified Architecture Plan

This plan synthesizes the Field architecture components:

**Layer 1 - Data**: Items, Bonds, Events stored in JSONL
**Layer 2 - Logic**: Operators execute Bonds and produce output
**Layer 3 - UI**: Display and interaction layer

Acceptance criteria:
- [ ] All items have valid IDs
- [ ] Bond execution produces output_item_id
- [ ] Events are append-only
"""

    bonds = transform_holologue_context(
        "Unified Architecture Plan",
        holologue_output,
        ["Data Objects", "Bond Ontology"]
    )

    print(f"  Generated {len(bonds)} proposals:")
    for i, b in enumerate(bonds, 1):
        print(f"    {i}. [{b.operation}] {b.display_text[:50]}...")

    # Assertions
    assert len(bonds) == 4, f"Expected 4 proposals, got {len(bonds)}"

    print("  PASSED: Holologue proposals generated")
    return True


def main():
    """Run all context transformer tests."""
    print("=" * 70)
    print("CONTEXT TRANSFORMER BOND TESTS")
    print("=" * 70)

    tests = [
        ("ENCODER: PAGE 1", test_encoder_page1),
        ("ENCODER: Short item", test_encoder_short_item),
        ("DECODER: Bond generation", test_decoder_bond_generation),
        ("DECODER: Numeric constraints", test_decoder_numeric_constraint),
        ("VALIDATOR: No banned patterns", test_validator_no_banned_patterns),
        ("BUTTHEAD TEST", test_butthead_anchor_in_suggestion),
        ("Determinism", test_determinism),
        ("Legacy format", test_legacy_format_conversion),
        ("Holologue context", test_holologue_context),
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
        print("All context transformer tests PASSED!")
        return 0
    else:
        print("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
