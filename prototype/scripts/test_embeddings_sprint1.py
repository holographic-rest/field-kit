#!/usr/bin/env python3
"""
Embeddings Sprint 1 Acceptance Test

Tests determinism, similarity sanity, shape/type, and cache behavior.
NO network calls - all tests work offline.

Run:
    source .venv/bin/activate
    python3 prototype/scripts/test_embeddings_sprint1.py

Design Notes (Why SHA256 instead of Python hash()):
    Python's built-in hash() is salted with PYTHONHASHSEED which is randomized
    by default on each process start. This means hash("hello") returns different
    values across runs, making it unsuitable for deterministic embeddings.

    SHA256 (via hashlib) is cryptographically stable:
    - Same output across runs, machines, Python versions
    - No salt or randomization
    - Well-defined specification (FIPS 180-4)

    This is critical for reproducible tests and consistent embedding behavior.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fieldkit.embeddings import (
    HashEmbeddingBackend,
    OpenAIEmbeddingBackend,
    cosine_sim,
    l2_normalize,
    pairwise_cosine_matrix,
    text_hash,
    normalize_text,
)


# =============================================================================
# Test Data
# =============================================================================

TEST_TEXTS = [
    "identity of the author",
    "who wrote this text",
    "kubernetes load balancer",
    "a detective novel mystery",
]

SIMILAR_PAIR = ("identity of the author", "who wrote this text")
DISSIMILAR_PAIR = ("identity of the author", "kubernetes load balancer")


# =============================================================================
# Test 1: Determinism
# =============================================================================

def test_determinism():
    """
    Test that HashEmbeddingBackend produces identical embeddings across calls.

    Instantiates backend twice, embeds same texts, asserts vectors are identical.
    Also checks cache_hits > 0 on second call.
    """
    print("\n=== Test 1: Determinism ===")

    # Create two separate backend instances
    backend1 = HashEmbeddingBackend(dim=256)
    backend2 = HashEmbeddingBackend(dim=256)

    # Embed with first backend
    vecs1 = backend1.embed_texts(TEST_TEXTS)

    # Embed with second backend (fresh instance, no cache)
    vecs2 = backend2.embed_texts(TEST_TEXTS)

    # Check vectors are identical
    epsilon = 1e-10
    all_identical = True

    for i, (v1, v2) in enumerate(zip(vecs1, vecs2)):
        for j, (a, b) in enumerate(zip(v1, v2)):
            if abs(a - b) > epsilon:
                print(f"  FAIL: Vector {i}, dim {j}: {a} != {b}")
                all_identical = False
                break
        if not all_identical:
            break

    if not all_identical:
        return False

    print(f"  Vectors identical across instances: PASS")

    # Test cache behavior: embed again with first backend
    backend1.cache_hits = 0
    backend1.cache_misses = 0
    vecs1_again = backend1.embed_texts(TEST_TEXTS)

    # Should have cache hits now
    if backend1.cache_hits != len(TEST_TEXTS):
        print(f"  FAIL: Expected {len(TEST_TEXTS)} cache hits, got {backend1.cache_hits}")
        return False

    print(f"  Cache hits on re-embed: {backend1.cache_hits}/{len(TEST_TEXTS)} PASS")

    # Verify vectors are still identical
    for i, (v1, v2) in enumerate(zip(vecs1, vecs1_again)):
        for j, (a, b) in enumerate(zip(v1, v2)):
            if abs(a - b) > epsilon:
                print(f"  FAIL: Cached vector {i} differs from original")
                return False

    print(f"  Cached vectors match originals: PASS")

    return True


# =============================================================================
# Test 2: Similarity Sanity
# =============================================================================

def test_similarity_sanity():
    """
    Test that cosine similarities make semantic sense.

    - Similar texts should have higher similarity
    - Identical texts should have sim ≈ 1.0
    """
    print("\n=== Test 2: Similarity Sanity ===")

    backend = HashEmbeddingBackend(dim=384)

    # Embed all texts
    all_texts = list(TEST_TEXTS) + [SIMILAR_PAIR[0], SIMILAR_PAIR[1], DISSIMILAR_PAIR[1]]
    vecs = backend.embed_texts(all_texts)

    # Get specific embeddings
    text_a = SIMILAR_PAIR[0]
    text_b = SIMILAR_PAIR[1]
    text_c = DISSIMILAR_PAIR[1]

    vec_a = backend.embed_texts([text_a])[0]
    vec_b = backend.embed_texts([text_b])[0]
    vec_c = backend.embed_texts([text_c])[0]

    # Compute similarities
    sim_similar = cosine_sim(vec_a, vec_b)
    sim_dissimilar = cosine_sim(vec_a, vec_c)
    sim_identical = cosine_sim(vec_a, vec_a)

    print(f"  sim('{text_a[:30]}...', '{text_b[:30]}...'): {sim_similar:.4f}")
    print(f"  sim('{text_a[:30]}...', '{text_c[:30]}...'): {sim_dissimilar:.4f}")
    print(f"  sim(text, text): {sim_identical:.4f}")

    # Assertions
    passed = True

    # Similar texts should have higher similarity than dissimilar
    if not (sim_similar > sim_dissimilar):
        print(f"  FAIL: Expected sim(similar) > sim(dissimilar)")
        print(f"        Got {sim_similar:.4f} <= {sim_dissimilar:.4f}")
        passed = False
    else:
        print(f"  sim(similar) > sim(dissimilar): PASS")

    # Identical texts should have sim near 1.0
    if not (sim_identical > 0.999):
        print(f"  FAIL: Expected sim(text, text) ≈ 1.0, got {sim_identical:.4f}")
        passed = False
    else:
        print(f"  sim(text, text) ≈ 1.0: PASS")

    return passed


# =============================================================================
# Test 3: Shape and Type
# =============================================================================

def test_shape_and_type():
    """
    Test that embeddings have correct shape and type.

    - Output should be (N, dim)
    - dim should match config
    - Values should be floats
    """
    print("\n=== Test 3: Shape and Type ===")

    dim = 256
    backend = HashEmbeddingBackend(dim=dim)

    vecs = backend.embed_texts(TEST_TEXTS)

    passed = True

    # Check number of vectors
    if len(vecs) != len(TEST_TEXTS):
        print(f"  FAIL: Expected {len(TEST_TEXTS)} vectors, got {len(vecs)}")
        passed = False
    else:
        print(f"  Number of vectors: {len(vecs)} PASS")

    # Check dimension of each vector
    for i, vec in enumerate(vecs):
        if len(vec) != dim:
            print(f"  FAIL: Vector {i} has dim {len(vec)}, expected {dim}")
            passed = False
            break
    else:
        print(f"  Vector dimension: {dim} PASS")

    # Check values are floats
    for i, vec in enumerate(vecs):
        for j, val in enumerate(vec):
            if not isinstance(val, float):
                print(f"  FAIL: Vector {i}[{j}] is {type(val)}, expected float")
                passed = False
                break
        if not passed:
            break
    else:
        print(f"  Values are floats: PASS")

    # Check backend.dim property
    if backend.dim != dim:
        print(f"  FAIL: backend.dim = {backend.dim}, expected {dim}")
        passed = False
    else:
        print(f"  backend.dim property: {backend.dim} PASS")

    return passed


# =============================================================================
# Test 4: Disk Cache Logic (OpenAI Backend, NO NETWORK)
# =============================================================================

def test_disk_cache_logic():
    """
    Test OpenAI backend disk cache without making network calls.

    Creates a backend with temp cache dir, manually puts a fake embedding,
    then verifies _cache_get returns it.
    """
    print("\n=== Test 4: Disk Cache Logic (No Network) ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)

        # Create backend with fake API key (won't actually call API)
        backend = OpenAIEmbeddingBackend(
            model="text-embedding-3-small",
            api_key="sk-fake-key-for-testing",
            cache_dir=cache_dir,
        )

        # Create a fake embedding
        test_text = "test cache text"
        fake_dim = backend.dim
        fake_vec = [0.1 * i for i in range(fake_dim)]

        # Put in cache
        backend._cache_put(test_text, fake_vec)

        # Get from cache
        cached_vec = backend._cache_get(test_text)

        passed = True

        # Verify we got something back
        if cached_vec is None:
            print(f"  FAIL: _cache_get returned None after _cache_put")
            passed = False
        else:
            print(f"  _cache_get returned vector: PASS")

            # Verify vector matches
            if len(cached_vec) != len(fake_vec):
                print(f"  FAIL: Cached vector length {len(cached_vec)} != {len(fake_vec)}")
                passed = False
            else:
                print(f"  Cached vector length matches: PASS")

                # Check values match
                epsilon = 1e-10
                for i, (a, b) in enumerate(zip(cached_vec, fake_vec)):
                    if abs(a - b) > epsilon:
                        print(f"  FAIL: Cached value at {i}: {a} != {b}")
                        passed = False
                        break
                else:
                    print(f"  Cached values match original: PASS")

        # Test cache miss for different text
        other_text = "completely different text"
        other_cached = backend._cache_get(other_text)

        if other_cached is not None:
            print(f"  FAIL: Expected cache miss for uncached text")
            passed = False
        else:
            print(f"  Cache miss for uncached text: PASS")

        # Verify cache file exists on disk
        cache_file = backend._cache_path(test_text)
        if not cache_file.exists():
            print(f"  FAIL: Cache file not created on disk")
            passed = False
        else:
            print(f"  Cache file created on disk: PASS")

    return passed


# =============================================================================
# Test 5: Utility Functions
# =============================================================================

def test_utility_functions():
    """
    Test utility functions: l2_normalize, text_hash, normalize_text.
    """
    print("\n=== Test 5: Utility Functions ===")

    passed = True

    # Test l2_normalize
    vec = [3.0, 4.0]
    normalized = l2_normalize(vec)
    expected_norm = 1.0
    actual_norm = sum(x * x for x in normalized) ** 0.5

    if abs(actual_norm - expected_norm) > 1e-10:
        print(f"  FAIL: l2_normalize norm = {actual_norm}, expected 1.0")
        passed = False
    else:
        print(f"  l2_normalize produces unit vector: PASS")

    # Test normalize_text
    raw = "  Hello,   World!  "
    normalized = normalize_text(raw)
    if normalized != "hello world":
        print(f"  FAIL: normalize_text('{raw}') = '{normalized}', expected 'hello world'")
        passed = False
    else:
        print(f"  normalize_text: PASS")

    # Test text_hash determinism
    text = "some test text"
    hash1 = text_hash(text)
    hash2 = text_hash(text)

    if hash1 != hash2:
        print(f"  FAIL: text_hash not deterministic")
        passed = False
    else:
        print(f"  text_hash deterministic: PASS")

    # Verify hash is 64 hex chars (sha256)
    if len(hash1) != 64:
        print(f"  FAIL: text_hash length = {len(hash1)}, expected 64")
        passed = False
    else:
        print(f"  text_hash is SHA256 (64 hex chars): PASS")

    return passed


# =============================================================================
# Test 6: Pairwise Cosine Matrix
# =============================================================================

def test_pairwise_matrix():
    """
    Test pairwise_cosine_matrix function.
    """
    print("\n=== Test 6: Pairwise Cosine Matrix ===")

    backend = HashEmbeddingBackend(dim=128)

    texts_a = ["hello world", "foo bar"]
    texts_b = ["hello world", "something else", "baz qux"]

    vecs_a = backend.embed_texts(texts_a)
    vecs_b = backend.embed_texts(texts_b)

    matrix = pairwise_cosine_matrix(vecs_a, vecs_b)

    passed = True

    # Check shape
    if len(matrix) != len(texts_a):
        print(f"  FAIL: Matrix has {len(matrix)} rows, expected {len(texts_a)}")
        passed = False
    else:
        print(f"  Matrix rows: {len(matrix)} PASS")

    if len(matrix[0]) != len(texts_b):
        print(f"  FAIL: Matrix has {len(matrix[0])} cols, expected {len(texts_b)}")
        passed = False
    else:
        print(f"  Matrix cols: {len(matrix[0])} PASS")

    # Check diagonal (first text is same in both lists)
    if abs(matrix[0][0] - 1.0) > 0.001:
        print(f"  FAIL: Expected matrix[0][0] ≈ 1.0 (same text), got {matrix[0][0]}")
        passed = False
    else:
        print(f"  matrix[0][0] ≈ 1.0 (identical text): PASS")

    return passed


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 70)
    print("EMBEDDINGS SPRINT 1 ACCEPTANCE TEST")
    print("Determinism + Similarity + Cache + Shape/Type")
    print("=" * 70)

    tests = [
        ("Determinism", test_determinism),
        ("Similarity Sanity", test_similarity_sanity),
        ("Shape and Type", test_shape_and_type),
        ("Disk Cache Logic (No Network)", test_disk_cache_logic),
        ("Utility Functions", test_utility_functions),
        ("Pairwise Cosine Matrix", test_pairwise_matrix),
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
        except Exception as e:
            failed += 1
            print(f"  X {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"SPRINT 1 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\nAll Sprint 1 acceptance tests PASSED.")
        print("Ready for Sprint 2: Embeddings integration with hololoop pairing.")
    else:
        print("\nSome tests FAILED. Please fix before proceeding.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
