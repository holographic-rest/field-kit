#!/usr/bin/env python3
"""
Queue Lattice v0.1 Sprint 2 Acceptance Test - Anchor Pairing

Tests embedding-based anchor pairing with MMR diversity selection.

ASSERTIONS:
a) select_anchor_pairs returns pairs with distinct B handles (coverage rule)
b) Similarity matrix is computed correctly (identical handles have sim=1.0)
c) MMR diversity selects varied pairs (not just top-k by similarity)
d) Handle normalization dedupes "One Thousand" vs "One Thousand and One Nights"
e) Integration with hololoop_engine works (debug contains anchor_pairs)

Run: python3 prototype/scripts/test_queue_lattice_pairing_sprint2.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.anchor_pairing import (
    select_anchor_pairs,
    normalize_handles,
    _normalize_handle_text,
)
from fieldkit.embeddings import (
    HashEmbeddingBackend,
    cosine_sim,
    get_hash_embedder,
)
from fieldkit.hololoop_engine import generate_hololoop_options


# === TEST DATA ===
HANDLES_A = [
    {"quote": "identity of The Author", "score": 0.9},
    {"quote": "found text", "score": 0.8},
    {"quote": "giallo", "score": 0.7},
    {"quote": "The Big Sleep", "score": 0.6},
    {"quote": "captivity mechanism", "score": 0.5},
]

HANDLES_B = [
    {"quote": "Scheherazade", "score": 0.9},
    {"quote": "One Thousand and One Nights", "score": 0.85},
    {"quote": "Magical Dominion", "score": 0.7},
    {"quote": "collector and curator", "score": 0.6},
    {"quote": "Arabian Nights structure", "score": 0.5},
]

# Test case with potential aliases
HANDLES_WITH_ALIASES = [
    {"quote": "One Thousand", "score": 0.9},
    {"quote": "One Thousand and One Nights", "score": 0.85},
    {"quote": "Scheherazade", "score": 0.7},
]

# Full item data for integration test
ITEM_A = {
    "id": "it_TEST_A",
    "title": "Found Text and The Author",
    "body": """I didn't write this... identity of The Author... found text...
giallo... The Big Sleep... captivity mechanism... mystery of authorship...
the narrator becomes a collector... who wrote this and why...""",
}

ITEM_B = {
    "id": "it_TEST_B",
    "title": "The Curator and Scheherazade",
    "body": """I do not know the identity... collector and curator...
Scheherazade in reverse... One Thousand and One Nights... Magical Dominion...
the stories trap the teller... Arabian Nights structure...""",
}


def test_basic_pairing():
    """Test that select_anchor_pairs returns valid pairs."""
    print("\n=== Test 1: Basic Anchor Pairing ===")

    pairs, debug = select_anchor_pairs(
        HANDLES_A,
        HANDLES_B,
        num_pairs=4,
        top_k=12,
    )

    print(f"  Generated {len(pairs)} pairs:")
    for i, (ha, hb) in enumerate(pairs):
        print(f"    {i+1}. A='{ha[:30]}' → B='{hb[:30]}'")

    if len(pairs) != 4:
        print(f"  FAIL: Expected 4 pairs, got {len(pairs)}")
        return False

    # All pairs should have non-empty handles
    for ha, hb in pairs:
        if not ha or not hb:
            print(f"  FAIL: Empty handle in pair ({ha}, {hb})")
            return False

    print("  PASS: Basic pairing works")
    return True


def test_b_handle_coverage():
    """Test that pairs use distinct B handles (coverage rule)."""
    print("\n=== Test 2: B-Handle Coverage ===")

    pairs, debug = select_anchor_pairs(
        HANDLES_A,
        HANDLES_B,
        num_pairs=4,
        top_k=12,
    )

    b_handles = [hb.lower() for _, hb in pairs]
    unique_b = set(b_handles)

    print(f"  B handles used: {b_handles}")
    print(f"  Unique B handles: {len(unique_b)}/{len(pairs)}")

    # Coverage rule: prefer distinct B handles
    if len(unique_b) < 3:
        print(f"  FAIL: Poor B coverage - only {len(unique_b)} distinct B handles in 4 pairs")
        return False

    print(f"  PASS: Good B coverage ({len(unique_b)} distinct B handles)")
    return True


def test_similarity_matrix():
    """Test that similarity matrix is computed correctly."""
    print("\n=== Test 3: Similarity Matrix ===")

    # Use same handle in both lists to test self-similarity
    same_handles = [
        {"quote": "test phrase one", "score": 0.9},
        {"quote": "test phrase two", "score": 0.8},
    ]

    pairs, debug = select_anchor_pairs(
        same_handles,
        same_handles,
        num_pairs=2,
    )

    sim_matrix = debug.get("sim_matrix", [])

    if not sim_matrix:
        print("  FAIL: No similarity matrix in debug output")
        return False

    # Diagonal should be 1.0 (self-similarity)
    for i in range(len(sim_matrix)):
        if abs(sim_matrix[i][i] - 1.0) > 0.001:
            print(f"  FAIL: Self-similarity at [{i}][{i}] = {sim_matrix[i][i]}, expected 1.0")
            return False

    print(f"  Self-similarity (diagonal): all 1.0")

    # Off-diagonal should be less than 1.0
    if len(sim_matrix) > 1:
        off_diag = sim_matrix[0][1]
        if off_diag >= 1.0:
            print(f"  FAIL: Off-diagonal similarity = {off_diag}, expected < 1.0")
            return False
        print(f"  Off-diagonal similarity: {off_diag:.4f} (< 1.0)")

    print("  PASS: Similarity matrix correct")
    return True


def test_mmr_diversity():
    """Test that MMR selects diverse pairs, not just top-k by similarity."""
    print("\n=== Test 4: MMR Diversity ===")

    # Create handles where top-k by sim would all pair with same B
    handles_a = [
        {"quote": "mystery of authorship", "score": 0.9},
        {"quote": "unknown writer", "score": 0.8},
        {"quote": "identity question", "score": 0.7},
        {"quote": "found manuscript", "score": 0.6},
    ]

    handles_b = [
        {"quote": "mystery genre", "score": 0.9},  # Similar to all A handles
        {"quote": "Arabian Nights", "score": 0.8},  # Different theme
        {"quote": "captivity narrative", "score": 0.7},  # Different theme
    ]

    pairs, debug = select_anchor_pairs(
        handles_a,
        handles_b,
        num_pairs=3,
        top_k=12,
        lambda_=0.7,  # MMR balance
    )

    print(f"  Selected pairs:")
    for i, p in enumerate(debug.get("selected_pairs", [])):
        print(f"    {i+1}. A='{p['handle_a'][:25]}' B='{p['handle_b'][:25]}' sim={p['similarity']:.4f} mmr={p['mmr_score']:.4f}")

    # Check that not all pairs use the same B handle
    b_handles = [hb.lower() for _, hb in pairs]
    unique_b = set(b_handles)

    if len(unique_b) == 1:
        print("  FAIL: All pairs use same B handle (no diversity)")
        return False

    print(f"  PASS: MMR selected diverse pairs ({len(unique_b)} distinct B handles)")
    return True


def test_handle_normalization():
    """Test that handle normalization dedupes aliases."""
    print("\n=== Test 5: Handle Normalization ===")

    # Test _normalize_handle_text
    test_cases = [
        ("one thousand", "One Thousand and One Nights"),
        ("One Thousand and One Nights", "One Thousand and One Nights"),
        ("arabian nights", "One Thousand and One Nights"),
        ("the author", "identity of The Author"),
        ("Scheherazade", "Scheherazade"),  # No alias, keep as-is
    ]

    passed = True
    for input_text, expected in test_cases:
        result = _normalize_handle_text(input_text)
        if result != expected:
            print(f"  FAIL: normalize('{input_text}') = '{result}', expected '{expected}'")
            passed = False
        else:
            print(f"  normalize('{input_text[:20]}') → '{result[:30]}'")

    if not passed:
        return False

    # Test normalize_handles with deduplication
    normalized = normalize_handles(HANDLES_WITH_ALIASES)
    quotes = [h["quote"] for h in normalized]

    print(f"\n  Deduplicated handles: {quotes}")

    # Should have deduped "One Thousand" with "One Thousand and One Nights"
    if len(normalized) >= len(HANDLES_WITH_ALIASES):
        # Count how many start with "One Thousand"
        one_thousand_count = sum(1 for q in quotes if "one thousand" in q.lower())
        if one_thousand_count > 1:
            print(f"  FAIL: Expected deduplication of 'One Thousand' aliases")
            return False

    print("  PASS: Handle normalization works")
    return True


def test_integration_with_hololoop():
    """Test that anchor pairing integrates with hololoop_engine."""
    print("\n=== Test 6: Integration with Hololoop Engine ===")

    result = generate_hololoop_options(ITEM_A, ITEM_B, return_debug=True)

    debug = result.get("debug", {})
    anchor_pairs = debug.get("anchor_pairs", [])

    print(f"  Generated {len(result.get('options', []))} hololoop options")
    print(f"  Anchor pairs in debug: {len(anchor_pairs)}")

    if not anchor_pairs:
        print("  FAIL: No anchor_pairs in debug output")
        return False

    # Print anchor pairs
    for p in anchor_pairs[:4]:
        print(f"    A='{p['handle_a'][:25]}' B='{p['handle_b'][:25]}' sim={p['similarity']:.4f}")

    # Check that anchor_b_coverage is present
    b_coverage = debug.get("anchor_b_coverage", [])
    print(f"  B handles covered: {b_coverage}")

    if not b_coverage:
        print("  FAIL: No anchor_b_coverage in debug")
        return False

    print("  PASS: Integration works")
    return True


def test_determinism():
    """Test that anchor pairing is deterministic."""
    print("\n=== Test 7: Determinism ===")

    pairs1, _ = select_anchor_pairs(HANDLES_A, HANDLES_B, num_pairs=4)
    pairs2, _ = select_anchor_pairs(HANDLES_A, HANDLES_B, num_pairs=4)

    if pairs1 != pairs2:
        print("  FAIL: Pairs differ between runs:")
        print(f"    Run 1: {pairs1}")
        print(f"    Run 2: {pairs2}")
        return False

    print(f"  Pairs identical across runs: {len(pairs1)} pairs")
    print("  PASS: Anchor pairing is deterministic")
    return True


def test_empty_handles():
    """Test handling of empty or minimal handle lists."""
    print("\n=== Test 8: Edge Cases (Empty/Minimal) ===")

    # Empty handles
    pairs, debug = select_anchor_pairs([], HANDLES_B)
    if pairs:
        print(f"  FAIL: Expected empty pairs for empty handles_a, got {pairs}")
        return False
    print("  Empty handles_a: returns empty pairs")

    # Single handle each
    single_a = [{"quote": "single A", "score": 0.9}]
    single_b = [{"quote": "single B", "score": 0.9}]
    pairs, debug = select_anchor_pairs(single_a, single_b, num_pairs=4)

    if len(pairs) != 1:
        print(f"  FAIL: Expected 1 pair for single handles, got {len(pairs)}")
        return False
    print(f"  Single handles: returns 1 pair")

    print("  PASS: Edge cases handled")
    return True


def main():
    print("=" * 70)
    print("QUEUE LATTICE v0.1 SPRINT 2 ACCEPTANCE TEST")
    print("Anchor Pairing with Embeddings + MMR Diversity")
    print("=" * 70)

    tests = [
        ("Basic Anchor Pairing", test_basic_pairing),
        ("B-Handle Coverage", test_b_handle_coverage),
        ("Similarity Matrix", test_similarity_matrix),
        ("MMR Diversity", test_mmr_diversity),
        ("Handle Normalization", test_handle_normalization),
        ("Integration with Hololoop", test_integration_with_hololoop),
        ("Determinism", test_determinism),
        ("Edge Cases", test_empty_handles),
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
    print(f"SPRINT 2 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\nAll Sprint 2 acceptance tests PASSED.")
        print("Anchor pairing with embedding similarity + MMR diversity is working.")
    else:
        print("\nSome tests FAILED. Please fix before proceeding.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
