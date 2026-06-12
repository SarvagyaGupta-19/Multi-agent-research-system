"""Tests for agents/researcher.py — Tavily search and error handling."""

import pytest
from unittest.mock import patch, MagicMock

from graph.state import create_initial_state
from agents.researcher import run_researcher
from config import Settings


def _make_settings(**overrides) -> Settings:
    """Create a test Settings instance with valid defaults."""
    defaults = {
        "GROQ_API_KEY": "gsk_test_key",
        "TAVILY_API_KEY": "tvly_test_key",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_tavily_response(results: list[dict]) -> dict:
    """Create a mock Tavily search response."""
    return {"results": results}


class TestRunResearcher:
    """Tests for the run_researcher function."""

    @patch("agents.researcher.TavilyClient")
    def test_successful_search(self, mock_tavily_cls):
        """Successful search should populate raw_research and sources."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.return_value = _make_tavily_response([
            {
                "url": "http://example.com/article1",
                "title": "AI Safety Overview",
                "content": "AI safety is an important field of research...",
            },
            {
                "url": "http://example.com/article2",
                "title": "AI Alignment Progress",
                "content": "Recent progress in alignment research...",
            },
        ])

        state = create_initial_state("AI safety research")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["sources"]) == 2
        assert result["sources"][0]["url"] == "http://example.com/article1"
        assert result["sources"][0]["title"] == "AI Safety Overview"
        assert "AI safety is an important" in result["sources"][0]["snippet"]
        assert "AI Safety Overview" in result["raw_research"]
        assert "AI Alignment Progress" in result["raw_research"]
        assert result["errors"] == []

    @patch("agents.researcher.TavilyClient")
    def test_empty_results(self, mock_tavily_cls):
        """Empty search results should append an error, not crash."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.return_value = _make_tavily_response([])

        state = create_initial_state("obscure topic xyz123")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert result["raw_research"] == ""
        assert result["sources"] == []
        assert len(result["errors"]) == 1
        assert "no results" in result["errors"][0].lower()

    @patch("agents.researcher.TavilyClient")
    def test_network_error_captured(self, mock_tavily_cls):
        """Network errors should be captured in errors, not raised."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.side_effect = ConnectionError("Network unreachable")

        state = create_initial_state("test topic")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["errors"]) == 1
        assert "ConnectionError" in result["errors"][0]
        assert result["raw_research"] == ""

    @patch("agents.researcher.TavilyClient")
    def test_invalid_api_key(self, mock_tavily_cls):
        """Invalid API key should be captured, not raised."""
        from tavily import InvalidAPIKeyError
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.side_effect = InvalidAPIKeyError("Invalid API key")

        state = create_initial_state("test topic")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["errors"]) == 1
        assert "invalid" in result["errors"][0].lower()

    @patch("agents.researcher.TavilyClient")
    def test_usage_limit_exceeded(self, mock_tavily_cls):
        """Usage limit error should be captured, not raised."""
        from tavily import UsageLimitExceededError
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.side_effect = UsageLimitExceededError("Usage limit exceeded")

        state = create_initial_state("test topic")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["errors"]) == 1
        assert "usage limit" in result["errors"][0].lower()

    def test_empty_topic_error(self):
        """Empty topic should append an error without calling Tavily."""
        state = create_initial_state("placeholder")
        state["topic"] = ""  # force empty after creation
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["errors"]) == 1
        assert "empty" in result["errors"][0].lower()

    @patch("agents.researcher.TavilyClient")
    def test_snippet_truncation(self, mock_tavily_cls):
        """Snippets should be truncated to 300 chars."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        long_content = "A" * 500
        mock_client.search.return_value = _make_tavily_response([
            {"url": "http://test.com", "title": "Test", "content": long_content},
        ])

        state = create_initial_state("test")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["sources"][0]["snippet"]) == 300

    @patch("agents.researcher.TavilyClient")
    def test_existing_errors_preserved(self, mock_tavily_cls):
        """Existing errors in state should be preserved, not overwritten."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.side_effect = ConnectionError("fail")

        state = create_initial_state("test")
        state["errors"].append("pre-existing error")
        settings = _make_settings()
        result = run_researcher(state, settings=settings)

        assert len(result["errors"]) == 2
        assert result["errors"][0] == "pre-existing error"

    @patch("agents.researcher.TavilyClient")
    def test_memory_context_appended_to_query(self, mock_tavily_cls):
        """Memory context should augment the search query."""
        mock_client = MagicMock()
        mock_tavily_cls.return_value = mock_client
        mock_client.search.return_value = _make_tavily_response([
            {"url": "http://test.com", "title": "Test", "content": "content"},
        ])

        state = create_initial_state("AI safety")
        state["memory_context"] = "Previous research focused on RLHF"
        settings = _make_settings()
        run_researcher(state, settings=settings)

        # Verify the query passed to Tavily includes memory context
        call_args = mock_client.search.call_args
        query = call_args.kwargs.get("query") or call_args[0][0]
        assert "RLHF" in query
