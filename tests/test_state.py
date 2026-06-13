"""Tests for graph/state.py — ResearchState contract, factory, and validation."""

import json
import pytest

from graph.state import (
    ResearchState,
    create_initial_state,
    validate_state,
)


class TestCreateInitialState:
    """Tests for the create_initial_state factory function."""

    def test_creates_valid_state(self):
        """Should produce a state with all fields initialized."""
        state = create_initial_state("AI safety")
        assert state["topic"] == "AI safety"
        assert state["style"] == "academic"
        assert state["skip_memory"] is False
        assert state["session_id"] == ""
        assert state["memory_context"] == ""
        assert state["raw_research"] == ""
        assert state["compressed_research"] == ""
        assert state["sources"] == []
        assert state["analysis"] == ""
        assert state["report"] == ""
        assert state["fact_checked_report"] == ""
        assert state["claims"] == []
        assert state["errors"] == []

    def test_custom_style(self):
        """Should accept and store a custom style."""
        state = create_initial_state("topic", style="blog")
        assert state["style"] == "blog"

    def test_skip_memory_flag(self):
        """Should accept skip_memory flag."""
        state = create_initial_state("topic", skip_memory=True)
        assert state["skip_memory"] is True

    def test_strips_whitespace(self):
        """Should strip whitespace from topic and style."""
        state = create_initial_state("  AI safety  ", style="  blog  ")
        assert state["topic"] == "AI safety"
        assert state["style"] == "blog"

    def test_empty_topic_raises(self):
        """Should raise ValueError for empty topic."""
        with pytest.raises(ValueError, match="topic is required"):
            create_initial_state("")

    def test_whitespace_topic_raises(self):
        """Should raise ValueError for whitespace-only topic."""
        with pytest.raises(ValueError, match="topic is required"):
            create_initial_state("   ")

    def test_empty_style_defaults(self):
        """Should default to 'academic' if style is empty."""
        state = create_initial_state("topic", style="")
        assert state["style"] == "academic"


class TestValidateState:
    """Tests for the validate_state function."""

    def test_valid_state_no_violations(self):
        """A properly created state should have zero violations."""
        state = create_initial_state("test topic")
        violations = validate_state(state)
        assert violations == []

    def test_missing_field_detected(self):
        """Should detect missing required fields."""
        state = {"topic": "test"}  # missing most fields
        violations = validate_state(state)
        assert len(violations) > 0
        # Should report at least 'style' as missing
        assert any("style" in v for v in violations)

    def test_wrong_type_detected(self):
        """Should detect wrong field types."""
        state = create_initial_state("test")
        state["sources"] = "not a list"  # type: ignore
        violations = validate_state(state)
        assert any("sources" in v and "list" in v for v in violations)

    def test_invalid_source_structure(self):
        """Should detect invalid source item structure."""
        state = create_initial_state("test")
        state["sources"] = [{"url": "http://test.com"}]  # missing title, snippet
        violations = validate_state(state)
        assert any("title" in v for v in violations)
        assert any("snippet" in v for v in violations)

    def test_invalid_claim_structure(self):
        """Should detect invalid claim item structure."""
        state = create_initial_state("test")
        state["claims"] = [{"claim": "test claim"}]  # missing status, source, rationale
        violations = validate_state(state)
        assert any("status" in v for v in violations)
        assert any("source" in v for v in violations)
        assert any("rationale" in v for v in violations)

    def test_invalid_claim_status(self):
        """Should detect invalid claim status values."""
        state = create_initial_state("test")
        state["claims"] = [{
            "claim": "test",
            "status": "maybe",  # invalid
            "source": "http://test.com",
            "rationale": "because",
        }]
        violations = validate_state(state)
        assert any("status" in v and "maybe" in v for v in violations)

    def test_valid_claim_statuses(self):
        """Should accept all valid claim status values."""
        state = create_initial_state("test")
        for status in ("verified", "unverified", "uncertain"):
            state["claims"] = [{
                "claim": "test",
                "status": status,
                "source": "http://test.com",
                "rationale": "because",
            }]
            violations = validate_state(state)
            assert not any("status" in v for v in violations)

    def test_non_dict_source_item(self):
        """Should detect non-dict items in sources list."""
        state = create_initial_state("test")
        state["sources"] = ["not a dict"]  # type: ignore
        violations = validate_state(state)
        assert any("sources[0]" in v and "dict" in v for v in violations)

    def test_non_dict_claim_item(self):
        """Should detect non-dict items in claims list."""
        state = create_initial_state("test")
        state["claims"] = [42]  # type: ignore
        violations = validate_state(state)
        assert any("claims[0]" in v and "dict" in v for v in violations)


class TestStateJsonSerialization:
    """Test that ResearchState is fully JSON-serializable."""

    def test_initial_state_serializable(self):
        """A fresh state should serialize to JSON and back."""
        state = create_initial_state("test topic")
        json_str = json.dumps(state)
        restored = json.loads(json_str)
        assert restored == state

    def test_populated_state_serializable(self):
        """A fully populated state should serialize to JSON and back."""
        state = create_initial_state("test topic", style="blog")
        state["raw_research"] = "Some research text"
        state["compressed_research"] = "Compressed text"
        state["sources"] = [
            {"url": "http://example.com", "title": "Example", "snippet": "A snippet"},
        ]
        state["analysis"] = "Key themes identified"
        state["report"] = "Final report text"
        state["fact_checked_report"] = "Fact checked report"
        state["claims"] = [{
            "claim": "AI is growing",
            "status": "verified",
            "source": "http://example.com",
            "rationale": "Multiple sources confirm",
        }]
        state["errors"] = ["Minor warning"]

        json_str = json.dumps(state)
        restored = json.loads(json_str)
        assert restored == state
