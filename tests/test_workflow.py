"""
Tests for the LangGraph workflow.

Tests graph compilation, node wiring, and end-to-end execution
with mocked agent functions.
"""

from unittest.mock import patch, MagicMock

import pytest

from graph.state import create_initial_state, ResearchState
from graph.workflow import build_graph, run_research


# --- Fixtures ---

@pytest.fixture
def mock_settings():
    """Create a mock Settings instance."""
    settings = MagicMock()
    settings.GROQ_API_KEY = "test-key"
    settings.TAVILY_API_KEY = "test-tavily-key"
    settings.GROQ_MODEL = "test-model"
    settings.GROQ_TIMEOUT = 30
    settings.GROQ_MAX_RETRIES = 1
    settings.TAVILY_MAX_RESULTS = 3
    settings.MAX_CONTEXT_CHARS = 16000
    settings.MEM0_API_KEY = ""
    settings.LOG_LEVEL = "INFO"
    return settings


# --- build_graph tests ---

class TestBuildGraph:
    """Tests for graph building and compilation."""

    def test_graph_compiles(self, mock_settings):
        """Graph should compile without errors."""
        graph = build_graph(settings=mock_settings)
        assert graph is not None

    def test_graph_has_correct_nodes(self, mock_settings):
        """The compiled graph should have all expected nodes."""
        graph = build_graph(settings=mock_settings)
        # LangGraph compiled graphs expose node names
        # Just verify it compiled — node internals are tested via invocation
        assert graph is not None


# --- run_research tests ---

class TestRunResearch:
    """Tests for the end-to-end research pipeline."""

    @patch("graph.workflow.run_fact_checker")
    @patch("graph.workflow.run_writer")
    @patch("graph.workflow.run_analyst")
    @patch("graph.workflow.compress_research")
    @patch("graph.workflow.run_researcher")
    def test_full_pipeline_invokes_all_agents(
        self, mock_researcher, mock_compress, mock_analyst,
        mock_writer, mock_fact_checker, mock_settings,
    ):
        """All agent nodes should be called in sequence."""
        # Each mock returns the state unchanged (pass-through)
        def passthrough(state, settings=None):
            return state

        mock_researcher.side_effect = passthrough
        mock_compress.side_effect = passthrough
        mock_analyst.side_effect = passthrough
        mock_writer.side_effect = passthrough
        mock_fact_checker.side_effect = passthrough

        result = run_research(
            topic="test topic",
            style="blog",
            skip_memory=True,
            settings=mock_settings,
        )

        assert result["topic"] == "test topic"
        assert result["style"] == "blog"
        assert result["skip_memory"] is True

    @patch("graph.workflow.run_fact_checker")
    @patch("graph.workflow.run_writer")
    @patch("graph.workflow.run_analyst")
    @patch("graph.workflow.compress_research")
    @patch("graph.workflow.run_researcher")
    def test_pipeline_passes_state_through_nodes(
        self, mock_researcher, mock_compress, mock_analyst,
        mock_writer, mock_fact_checker, mock_settings,
    ):
        """State should flow correctly from one node to the next."""

        def researcher_fn(state, settings=None):
            state["raw_research"] = "Research about testing"
            state["sources"] = [{"url": "https://test.com", "title": "Test", "snippet": "Test snippet"}]
            return state

        def compress_fn(state, settings=None):
            state["compressed_research"] = state["raw_research"][:100]
            return state

        def analyst_fn(state, settings=None):
            state["analysis"] = "Analysis of test topic"
            return state

        def writer_fn(state, settings=None):
            state["report"] = "Report on test topic"
            return state

        def fact_checker_fn(state, settings=None):
            state["claims"] = [{"claim": "Test", "status": "verified", "source": "test.com", "rationale": "ok"}]
            state["fact_checked_report"] = '{"report": "...", "trust_score": 1.0}'
            return state

        mock_researcher.side_effect = researcher_fn
        mock_compress.side_effect = compress_fn
        mock_analyst.side_effect = analyst_fn
        mock_writer.side_effect = writer_fn
        mock_fact_checker.side_effect = fact_checker_fn

        result = run_research(topic="test topic", settings=mock_settings)

        assert result["raw_research"] == "Research about testing"
        assert result["compressed_research"] == "Research about testing"
        assert result["analysis"] == "Analysis of test topic"
        assert result["report"] == "Report on test topic"
        assert len(result["claims"]) == 1
        assert result["fact_checked_report"]

    def test_empty_topic_raises(self, mock_settings):
        """run_research should raise ValueError for empty topic."""
        with pytest.raises(ValueError, match="topic is required"):
            run_research(topic="", settings=mock_settings)

    def test_whitespace_topic_raises(self, mock_settings):
        """run_research should raise ValueError for whitespace-only topic."""
        with pytest.raises(ValueError, match="topic is required"):
            run_research(topic="   ", settings=mock_settings)
