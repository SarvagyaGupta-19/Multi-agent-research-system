"""Tests for utils/truncation.py — text truncation and research compression."""

import pytest
from unittest.mock import patch

from utils.truncation import truncate_text, compress_research
from graph.state import create_initial_state
from config import Settings


def _make_settings(**overrides) -> Settings:
    """Create a test Settings instance."""
    defaults = {
        "GROQ_API_KEY": "gsk_test_key",
        "TAVILY_API_KEY": "tvly_test_key",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestTruncateText:
    """Tests for the truncate_text function."""

    def test_under_limit_unchanged(self):
        """Text under the limit should be returned unchanged."""
        text = "short text"
        result = truncate_text(text, max_chars=100)
        assert result == text

    def test_exactly_at_limit_unchanged(self):
        """Text exactly at the limit should be returned unchanged."""
        text = "A" * 100
        result = truncate_text(text, max_chars=100)
        assert result == text

    def test_empty_string_unchanged(self):
        """Empty string should be returned unchanged."""
        result = truncate_text("", max_chars=100)
        assert result == ""

    def test_tail_truncation(self):
        """Tail strategy should keep the first max_chars characters."""
        text = "A" * 200
        result = truncate_text(text, max_chars=100, strategy="tail")
        assert result.startswith("A" * 100)
        assert "[... truncated ...]" in result
        # The truncated marker adds chars beyond max_chars
        assert len(result) > 100

    def test_middle_truncation(self):
        """Middle strategy should keep first and last halves."""
        text = "AAAA" + "B" * 200 + "CCCC"
        result = truncate_text(text, max_chars=100, strategy="middle")
        assert result.startswith("A")
        assert result.endswith("C")
        assert "[... middle truncated ...]" in result

    def test_invalid_strategy_raises(self):
        """Unknown strategy should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown truncation strategy"):
            truncate_text("A" * 100, max_chars=10, strategy="random")

    def test_invalid_max_chars_raises(self):
        """max_chars < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="max_chars must be >= 1"):
            truncate_text("text", max_chars=0)

    def test_none_text_unchanged(self):
        """None text should be returned as-is (falsy)."""
        result = truncate_text(None, max_chars=100)  # type: ignore
        assert result is None


class TestCompressResearch:
    """Tests for the compress_research function."""

    def test_under_limit_copies_directly(self):
        """Research under limit should be copied to compressed_research."""
        state = create_initial_state("test")
        state["raw_research"] = "Short research text"
        settings = _make_settings(MAX_CONTEXT_CHARS=16000)

        result = compress_research(state, settings=settings)

        assert result["compressed_research"] == "Short research text"

    def test_over_limit_truncated(self):
        """Research over limit should be truncated."""
        state = create_initial_state("test")
        state["raw_research"] = "A" * 20000
        settings = _make_settings(MAX_CONTEXT_CHARS=1000)

        result = compress_research(state, settings=settings)

        assert len(result["compressed_research"]) < len(state["raw_research"])
        assert "[... truncated ...]" in result["compressed_research"]

    def test_empty_research_stays_empty(self):
        """Empty raw_research should produce empty compressed_research."""
        state = create_initial_state("test")
        state["raw_research"] = ""
        settings = _make_settings()

        result = compress_research(state, settings=settings)

        assert result["compressed_research"] == ""

    def test_state_returned(self):
        """Should return the same state dict (mutated in place)."""
        state = create_initial_state("test")
        state["raw_research"] = "data"
        settings = _make_settings()

        result = compress_research(state, settings=settings)

        assert result is state

    def test_exactly_at_limit(self):
        """Research exactly at limit should be copied, not truncated."""
        state = create_initial_state("test")
        state["raw_research"] = "A" * 1000
        settings = _make_settings(MAX_CONTEXT_CHARS=1000)

        result = compress_research(state, settings=settings)

        assert result["compressed_research"] == state["raw_research"]
        assert "[... truncated ...]" not in result["compressed_research"]
