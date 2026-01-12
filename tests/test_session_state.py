#!/usr/bin/env python3
"""
Field-Kit v0.1 Session State Tests (Sprint S07)

Tests for RMC-style multi-slot session memory.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fieldkit.session_state import (
    MemorySlot,
    SessionState,
    default_session_state,
    slot_attention,
    update_from_action,
    update_from_event,
    load_vault_anchors,
    get_state_influence_keywords,
    format_state_summary,
    SLOT_IDS,
)


class TestMemorySlot:
    """Tests for MemorySlot dataclass."""

    def test_slot_creation(self):
        """Test creating a memory slot."""
        slot = MemorySlot(slot_id="test_slot")
        assert slot.slot_id == "test_slot"
        assert slot.content == {}
        assert slot.recency == 0.0
        assert slot.is_pinned == False
        assert slot.embedding is None

    def test_slot_is_empty(self):
        """Test is_empty detection."""
        slot = MemorySlot(slot_id="test")
        assert slot.is_empty() == True

        slot.content = {"key": "value"}
        assert slot.is_empty() == False

        slot.content = {"key": None, "list": []}
        assert slot.is_empty() == True

    def test_slot_serialization(self):
        """Test slot to_dict and from_dict."""
        slot = MemorySlot(
            slot_id="test",
            content={"key": "value"},
            recency=5.0,
            is_pinned=True,
        )

        d = slot.to_dict()
        assert d["slot_id"] == "test"
        assert d["content"] == {"key": "value"}
        assert d["is_pinned"] == True

        restored = MemorySlot.from_dict(d)
        assert restored.slot_id == slot.slot_id
        assert restored.content == slot.content
        assert restored.is_pinned == slot.is_pinned


class TestSessionState:
    """Tests for SessionState class."""

    def test_default_state_has_6_slots(self):
        """Test default state has all 6 required slots."""
        state = default_session_state()
        assert len(state.slots) == 6
        for slot_id in SLOT_IDS:
            assert slot_id in state.slots

    def test_get_slot_creates_missing(self):
        """Test get_slot creates missing slots."""
        state = SessionState(slots={})
        slot = state.get_slot("new_slot")
        assert slot.slot_id == "new_slot"
        assert "new_slot" in state.slots

    def test_set_slot_content_updates_recency(self):
        """Test setting slot content updates recency."""
        state = default_session_state()
        state.increment_step()
        state.set_slot_content("active_page", {"item_id": "it_001"})

        slot = state.get_slot("active_page")
        assert slot.content == {"item_id": "it_001"}
        assert slot.recency == 1  # Step counter

    def test_non_empty_slots(self):
        """Test non_empty_slots returns only slots with content."""
        state = default_session_state()
        assert len(state.non_empty_slots()) == 0

        state.set_slot_content("active_page", {"item_id": "it_001"})
        assert len(state.non_empty_slots()) == 1

    def test_state_serialization(self):
        """Test state to_dict and from_dict."""
        state = default_session_state()
        state.set_slot_content("active_page", {"item_id": "it_001"})
        state.increment_step()

        d = state.to_dict()
        assert "slots" in d
        assert "step_counter" in d

        restored = SessionState.from_dict(d)
        assert restored.get_step() == state.get_step()
        assert restored.get_slot("active_page").content == {"item_id": "it_001"}

    def test_summary_hash_changes_with_content(self):
        """Test summary hash changes when content changes."""
        state = default_session_state()
        hash1 = state.summary_hash()

        state.set_slot_content("active_page", {"item_id": "it_001"})
        hash2 = state.summary_hash()

        assert hash1 != hash2


class TestSlotAttention:
    """Tests for slot attention computation."""

    def test_attention_weights_sum_to_one(self):
        """Test attention weights sum to approximately 1."""
        state = default_session_state()
        weights = slot_attention(state.slots)

        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001

    def test_attention_weights_in_range(self):
        """Test all attention weights are in [0, 1]."""
        state = default_session_state()
        state.set_slot_content("active_page", {"item_id": "it_001"})
        state.set_slot_content("entities", {"entities": ["test"]})

        weights = slot_attention(state.slots)

        for w in weights.values():
            assert 0 <= w <= 1

    def test_pinned_slots_get_higher_weight(self):
        """Test pinned slots receive higher attention weight."""
        state = default_session_state()
        state.set_slot_content("active_page", {"item_id": "it_001"}, is_pinned=False)
        state.set_slot_content("vault_anchors", {"anchors": ["x"]}, is_pinned=True)

        weights = slot_attention(state.slots)

        # Pinned vault_anchors should have higher weight
        assert weights["vault_anchors"] >= weights["active_page"]

    def test_empty_state_uniform_weights(self):
        """Test empty state gives uniform weights."""
        state = default_session_state()
        weights = slot_attention(state.slots)

        # All weights should be equal
        values = list(weights.values())
        assert all(abs(v - values[0]) < 0.001 for v in values)


class TestSlotUpdates:
    """Tests for slot update functions."""

    def test_update_from_action_subject_item(self):
        """Test update_from_action populates active_page."""
        state = default_session_state()
        state = update_from_action(
            state,
            subject_item={"id": "it_001", "title": "Test Item", "type": "Q"},
        )

        slot = state.get_slot("active_page")
        assert slot.content["item_id"] == "it_001"
        assert slot.content["title"] == "Test Item"

    def test_update_from_action_suggestions(self):
        """Test update_from_action populates open_questions."""
        state = default_session_state()
        state = update_from_action(
            state,
            suggestions=[
                {"intent": "clarify", "handle_quote": "test handle", "prompt_text": "Clarify this"},
                {"intent": "concretize", "handle_quote": "other", "prompt_text": "Concrete"},
            ],
        )

        slot = state.get_slot("open_questions")
        questions = slot.content.get("questions", [])
        # Only clarify/test intents become open questions
        assert len(questions) == 1
        assert questions[0]["intent"] == "clarify"

    def test_update_from_action_evidence(self):
        """Test update_from_action populates recent_evidence."""
        state = default_session_state()
        state = update_from_action(
            state,
            evidence_shards=[
                {"source_id": "it_001", "text_span": "some evidence", "scale": "local"},
            ],
        )

        slot = state.get_slot("recent_evidence")
        shards = slot.content.get("shards", [])
        assert len(shards) == 1
        assert shards[0]["source_id"] == "it_001"

    def test_update_from_event_item_created(self):
        """Test update_from_event handles item.created."""
        state = default_session_state()
        event = {
            "name": "item.created",
            "refs": {"item_id": "it_002", "item_type": "M", "title": "New Item"},
        }
        state = update_from_event(state, event)

        slot = state.get_slot("active_page")
        assert slot.content["item_id"] == "it_002"

    def test_update_from_event_bond_executed(self):
        """Test update_from_event handles bond.executed."""
        state = default_session_state()
        event = {
            "name": "bond.executed",
            "refs": {"bond_id": "bd_001"},
        }
        state = update_from_event(state, event)

        slot = state.get_slot("user_intent")
        assert slot.content["intent"] == "executed_bond"

    def test_load_vault_anchors(self):
        """Test load_vault_anchors populates vault_anchors slot."""
        state = default_session_state()
        curated = [
            {"id": "it_001", "title": "Curated 1", "type": "D"},
            {"id": "it_002", "title": "Curated 2", "type": "H"},
        ]
        state = load_vault_anchors(state, curated)

        slot = state.get_slot("vault_anchors")
        assert slot.is_pinned == True
        assert len(slot.content.get("anchors", [])) == 2


class TestStateInfluence:
    """Tests for state influence on suggestions."""

    def test_get_state_influence_keywords_empty(self):
        """Test empty state returns empty keywords."""
        state = default_session_state()
        keywords = get_state_influence_keywords(state)
        assert keywords == set()

    def test_get_state_influence_keywords_entities(self):
        """Test keywords extracted from entities."""
        state = default_session_state()
        state.set_slot_content("entities", {"entities": ["Field Kit", "Session State"]})

        keywords = get_state_influence_keywords(state)
        assert "field" in keywords
        assert "session" in keywords
        assert "state" in keywords

    def test_get_state_influence_keywords_open_questions(self):
        """Test keywords extracted from open questions."""
        state = default_session_state()
        state.set_slot_content("open_questions", {
            "questions": [{"handle": "RMC pattern", "intent": "clarify"}]
        })

        keywords = get_state_influence_keywords(state)
        assert "pattern" in keywords


class TestStateContinuity:
    """Tests for multi-step session continuity."""

    def test_state_changes_across_steps(self):
        """Test state changes correctly across multiple steps."""
        state = default_session_state()

        # Step 1: Navigate to item A
        state = update_from_action(
            state,
            subject_item={"id": "it_A", "title": "Item A", "type": "Q"},
        )
        step1_hash = state.summary_hash()
        step1_page = state.get_slot("active_page").content["item_id"]

        # Step 2: Receive suggestions with clarify intent
        state = update_from_action(
            state,
            suggestions=[
                {"intent": "clarify", "handle_quote": "clarify handle", "prompt_text": "Clarify A"},
            ],
            chosen_intent="clarify",
        )
        step2_hash = state.summary_hash()
        step2_intent = state.get_slot("user_intent").content.get("intent")

        # Step 3: Navigate to item B
        state = update_from_action(
            state,
            subject_item={"id": "it_B", "title": "Item B", "type": "M"},
        )
        step3_hash = state.summary_hash()
        step3_page = state.get_slot("active_page").content["item_id"]

        # Verify state evolved
        assert step1_page == "it_A"
        assert step3_page == "it_B"
        assert step2_intent == "clarify"

        # Hashes should differ at each step
        assert step1_hash != step2_hash
        assert step2_hash != step3_hash

        # Step counter should increment
        assert state.get_step() == 3

    def test_entities_accumulate(self):
        """Test entities accumulate across steps."""
        state = default_session_state()

        # Step 1: First item with handles
        state = update_from_action(
            state,
            subject_item={
                "id": "it_A",
                "title": "A",
                "handles": [{"quote": "entity one"}],
            },
        )

        # Step 2: Second item with different handles
        state = update_from_action(
            state,
            subject_item={
                "id": "it_B",
                "title": "B",
                "handles": [{"quote": "entity two"}],
            },
        )

        entities = state.get_slot("entities").content.get("entities", [])
        # Both entities should be present (merged)
        assert len(entities) == 2

    def test_open_questions_accumulate(self):
        """Test open questions accumulate and are bounded."""
        state = default_session_state()

        # Add multiple rounds of suggestions
        for i in range(10):
            state = update_from_action(
                state,
                suggestions=[
                    {"intent": "clarify", "handle_quote": f"handle {i}", "prompt_text": f"Question {i}"},
                ],
            )

        questions = state.get_slot("open_questions").content.get("questions", [])
        # Should be bounded to 5 most recent
        assert len(questions) <= 5
        # Most recent should be first
        assert "handle 9" in questions[0]["handle"]


class TestFormatting:
    """Tests for state formatting."""

    def test_format_state_summary(self):
        """Test format_state_summary produces readable output."""
        state = default_session_state()
        state.set_slot_content("active_page", {"item_id": "it_001", "title": "Test"})

        summary = format_state_summary(state)

        assert "SESSION STATE" in summary
        assert "active_page" in summary
        assert "Weight:" in summary
        assert "it_001" in summary


def run_tests():
    """Run all tests and report results."""
    passed = 0
    failed = 0
    errors = []

    # Collect all test classes
    test_classes = [
        TestMemorySlot,
        TestSessionState,
        TestSlotAttention,
        TestSlotUpdates,
        TestStateInfluence,
        TestStateContinuity,
        TestFormatting,
    ]

    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    passed += 1
                    print(f"  PASS: {cls.__name__}.{method_name}")
                except AssertionError as e:
                    failed += 1
                    errors.append(f"{cls.__name__}.{method_name}: {e}")
                    print(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                except Exception as e:
                    failed += 1
                    errors.append(f"{cls.__name__}.{method_name}: {e}")
                    print(f"  ERROR: {cls.__name__}.{method_name}: {e}")

    print(f"\n=== Results: {passed} passed, {failed} failed ===")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
