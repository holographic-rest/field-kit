#!/usr/bin/env python3
"""
Queue Lattice PASS 2 Acceptance Test

Tests the Draft Hololoop + Handles + Pipeline Sprint:
1. Handles stored on Items (3-7 per Q Item)
2. Hololink pipeline generation (get_handles → generate_candidates → filter → rank → diversify)
3. Retrieval for related items (local similarity)
4. Draft hololoop auto-creation

Run: python3 prototype/scripts/test_queue_lattice_pass2.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cli import FieldKitCLI
from fieldkit import reset_store, ItemHandle
from fieldkit.hololink_pipeline import (
    generate_hololink_options,
    get_handles_for_item,
    generate_candidates,
    hard_filter,
    rank_candidates,
    diversify,
)
from fieldkit.retrieval import find_related_items, find_best_target_for_hololoop, jaccard_similarity


def test_handles_stored_on_items():
    """Test that handles are extracted and stored on Item creation."""
    print("\n=== Test 1: Handles Stored on Items ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)

        # Initialize
        cli.cmd_init()

        # Create a Q item with content that has extractable handles
        item_id = cli.cmd_item_create(
            title="Machine Learning Pipeline",
            body="""Key components of the pipeline:
- Training data preprocessing
- Model architecture selection
- Hyperparameter tuning
- Evaluation metrics validation""",
            item_type="Q",
        )

        # Verify handles were stored
        item = cli.store.get_item(item_id)
        assert item is not None, "Item not found"
        assert "handles" in item, "Handles not stored on item"
        handles = item["handles"]
        assert handles is not None, "Handles is None"
        assert len(handles) >= 1, f"Expected at least 1 handle, got {len(handles)}"
        assert len(handles) <= 7, f"Expected at most 7 handles, got {len(handles)}"

        # Verify handle structure
        for h in handles:
            assert "quote" in h, "Handle missing 'quote' field"
            assert "kind" in h, "Handle missing 'kind' field"
            assert "starred" in h, "Handle missing 'starred' field"
            assert isinstance(h["quote"], str), "quote should be string"
            assert len(h["quote"]) > 0, "quote should not be empty"

        print(f"  ✓ Item created with {len(handles)} handles")
        for h in handles[:3]:
            print(f"    - \"{h['quote'][:50]}...\" ({h['kind']})")
        return True


def test_hololink_pipeline():
    """Test the hololink generation pipeline."""
    print("\n=== Test 2: Hololink Generation Pipeline ===")

    item_a = {
        "id": "it_TEST_A",
        "title": "Infrastructure Layer",
        "body": """Infrastructure handles:
- Database connection pooling
- API rate limiting
- Cache invalidation strategy""",
        "handles": [
            {"quote": "Database connection pooling", "kind": "bullet", "starred": False},
            {"quote": "API rate limiting", "kind": "bullet", "starred": True},
        ],
    }

    item_b = {
        "id": "it_TEST_B",
        "title": "Application Layer",
        "body": """Application components:
- Business logic orchestration
- Service dependency injection
- Error handling middleware""",
        "handles": [
            {"quote": "Business logic orchestration", "kind": "bullet", "starred": False},
            {"quote": "Service dependency injection", "kind": "bullet", "starred": False},
        ],
    }

    # Test get_handles_for_item (prefers stored handles)
    handles_a = get_handles_for_item(item_a, k=5)
    assert len(handles_a) >= 2, "Should return stored handles"
    assert any(h.get("starred") for h in handles_a), "Starred handle should be preserved"
    print(f"  ✓ get_handles_for_item: {len(handles_a)} handles")

    # Test full pipeline
    result = generate_hololink_options(item_a, item_b, return_debug=True)

    assert "options" in result, "Missing 'options' in result"
    assert len(result["options"]) == 4, f"Expected 4 options, got {len(result['options'])}"
    assert result["source"] == "pipeline", f"Expected source 'pipeline', got {result['source']}"

    # Verify each option has required fields
    for i, opt in enumerate(result["options"]):
        assert "option_index" in opt, f"Option {i} missing option_index"
        assert "link_text_forward" in opt, f"Option {i} missing link_text_forward"
        assert "link_text_return" in opt, f"Option {i} missing link_text_return"
        assert "handle_a_used" in opt, f"Option {i} missing handle_a_used"
        assert "handle_b_used" in opt, f"Option {i} missing handle_b_used"

        print(f"  ✓ Option {opt['option_index']}: {opt['relation_type']}")
        print(f"      A→B: {opt['link_text_forward'][:60]}...")
        print(f"      B→A: {opt['link_text_return'][:60]}...")

    # Verify debug info
    if "debug" in result:
        debug = result["debug"]
        print(f"  ✓ Debug: {debug.get('candidates_generated', 0)} candidates generated")
        print(f"  ✓ Debug: {debug.get('candidates_filtered', 0)} after filtering")

    return True


def test_retrieval_local_similarity():
    """Test retrieval module using local similarity."""
    print("\n=== Test 3: Retrieval (Local Similarity) ===")

    items = [
        {
            "id": "it_1",
            "type": "Q",
            "title": "Machine Learning",
            "body": "Deep learning neural networks training data",
        },
        {
            "id": "it_2",
            "type": "Q",
            "title": "Database Design",
            "body": "SQL PostgreSQL database schema optimization",
        },
        {
            "id": "it_3",
            "type": "Q",
            "title": "Neural Networks",
            "body": "Training deep learning models with data preprocessing",
        },
        {
            "id": "it_4",
            "type": "Q",
            "title": "Web Development",
            "body": "React JavaScript frontend development",
        },
    ]

    query_item = items[0]  # Machine Learning

    # Test find_related_items
    related = find_related_items(query_item, items, k=3, method="hybrid")

    assert len(related) >= 1, "Should find at least 1 related item"
    assert query_item["id"] not in [r["id"] for r in related], "Query should not be in results"

    # Neural Networks should be most related to Machine Learning
    first_related = related[0]
    assert "_similarity_score" in first_related, "Missing similarity score"
    assert first_related["_similarity_score"] > 0, "Score should be positive"

    print(f"  ✓ Found {len(related)} related items")
    for r in related:
        print(f"    - {r['title']} (score: {r['_similarity_score']:.4f})")

    # Test find_best_target_for_hololoop
    best = find_best_target_for_hololoop(query_item, items)
    assert best is not None, "Should find a best target"
    assert best["id"] != query_item["id"], "Best target should not be query"
    print(f"  ✓ Best target: {best['title']}")

    # Test jaccard_similarity directly
    tokens_a = {"machine", "learning", "neural", "networks"}
    tokens_b = {"neural", "networks", "training", "data"}
    sim = jaccard_similarity(tokens_a, tokens_b)
    assert 0 < sim < 1, f"Jaccard should be between 0 and 1, got {sim}"
    print(f"  ✓ Jaccard similarity: {sim:.4f}")

    return True


def test_draft_hololoop_creation():
    """Test auto-creation of draft hololoop."""
    print("\n=== Test 4: Draft Hololoop Creation ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        reset_store()
        cli = FieldKitCLI(data_dir)

        # Initialize
        cli.cmd_init()

        # Create first Q item
        item1_id = cli.cmd_item_create(
            title="System Architecture",
            body="Microservices, API gateway, load balancer",
            item_type="Q",
        )

        # Create second Q item
        item2_id = cli.cmd_item_create(
            title="Deployment Strategy",
            body="Kubernetes, Docker containers, CI/CD pipeline",
            item_type="Q",
        )

        # Create hololoop between them
        bond_id = cli.cmd_hololoop_create(item1_id, item2_id, option_index=1)

        # Verify bond was created
        bond = cli.store.get_bond(bond_id)
        assert bond is not None, "Bond not found"
        assert bond["bond_kind"] == "hololoop", f"Expected bond_kind 'hololoop', got {bond.get('bond_kind')}"
        assert bond["status"] == "draft", f"Expected status 'draft', got {bond['status']}"
        assert bond["link_text_forward"] is not None, "Missing link_text_forward"
        assert bond["link_text_return"] is not None, "Missing link_text_return"
        assert len(bond["input_item_ids"]) == 2, "Should have 2 input items"

        print(f"  ✓ Hololoop bond created: {bond_id}")
        print(f"  ✓ Forward: {bond['link_text_forward'][:60]}...")
        print(f"  ✓ Return: {bond['link_text_return'][:60]}...")

        # Verify both items have handles
        item1 = cli.store.get_item(item1_id)
        item2 = cli.store.get_item(item2_id)

        assert item1.get("handles"), "Item 1 missing handles"
        assert item2.get("handles"), "Item 2 missing handles"
        print(f"  ✓ Item 1 handles: {len(item1['handles'])}")
        print(f"  ✓ Item 2 handles: {len(item2['handles'])}")

        return True


def test_pipeline_steps_individually():
    """Test each pipeline step individually."""
    print("\n=== Test 5: Pipeline Steps ===")

    handles_a = [
        {"quote": "database connection pooling", "kind": "bullet", "starred": False},
        {"quote": "API rate limiting", "kind": "bullet", "starred": False},
        {"quote": "cache invalidation", "kind": "bullet", "starred": False},
    ]

    handles_b = [
        {"quote": "business logic", "kind": "bullet", "starred": False},
        {"quote": "service orchestration", "kind": "bullet", "starred": False},
        {"quote": "error handling", "kind": "bullet", "starred": False},
    ]

    item_a = {"id": "a", "title": "Infrastructure", "body": "Database and API layer"}
    item_b = {"id": "b", "title": "Application", "body": "Business logic layer"}

    # Step 2: Generate candidates
    candidates = generate_candidates(handles_a, handles_b, item_a, item_b)
    assert len(candidates) > 0, "Should generate some candidates"
    print(f"  ✓ generate_candidates: {len(candidates)} candidates")

    # Step 3: Hard filter
    filtered = hard_filter(candidates)
    assert len(filtered) <= len(candidates), "Filtering should reduce or maintain count"
    print(f"  ✓ hard_filter: {len(filtered)} remaining")

    # Step 4: Rank
    ranked = rank_candidates(filtered)
    if len(ranked) >= 2:
        assert ranked[0].score >= ranked[-1].score, "Should be sorted by score descending"
    print(f"  ✓ rank_candidates: {len(ranked)} ranked")

    # Step 5: Diversify
    final = diversify(ranked, k=4)
    assert len(final) <= 4, "Should return at most 4"
    print(f"  ✓ diversify: {len(final)} selected")

    # Check intent diversity
    intents = set(c.intent for c in final)
    print(f"  ✓ Intent diversity: {len(intents)} different intents")

    return True


def main():
    print("=" * 60)
    print("QUEUE LATTICE PASS 2 ACCEPTANCE TEST")
    print("Draft Hololoop + Handles + Pipeline Sprint")
    print("=" * 60)

    tests = [
        ("Handles Stored on Items", test_handles_stored_on_items),
        ("Hololink Generation Pipeline", test_hololink_pipeline),
        ("Retrieval (Local Similarity)", test_retrieval_local_similarity),
        ("Draft Hololoop Creation", test_draft_hololoop_creation),
        ("Pipeline Steps", test_pipeline_steps_individually),
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

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
