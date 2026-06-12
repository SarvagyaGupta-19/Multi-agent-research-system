"""Tests for agents/analyst.py — analysis agent with LLM integration."""

import pytest
from unittest.mock import patch, MagicMock

from agents.analyst import run_analyst, _build_analyst_prompt
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


class TestRunAnalyst:
    """Tests for the run_analyst function."""

    @patch("agents.analyst.call_llm")
    def test_successful_analysis(self, mock_call_llm):
        """With valid research, should produce analysis."""
        mock_call_llm.return_value = "## Key Themes\n- AI Safety is critical\n\n## Findings\n- Progress in RLHF"

        state = create_initial_state("AI safety")
        state["compressed_research"] = "Research data about AI safety and alignment..."
        state["sources"] = [
            {"url": "http://example.com", "title": "Source 1", "snippet": "snippet"},
        ]

        result = run_analyst(state, settings=_make_settings())

        assert result["analysis"] != ""
        assert "Key Themes" in result["analysis"]
        assert result["errors"] == []
        mock_call_llm.assert_called_once()

    @patch("agents.analyst.call_llm")
    def test_empty_research_appends_error(self, mock_call_llm):
        """With no research data, should append error and not call LLM."""
        state = create_initial_state("test")
        state["compressed_research"] = ""
        state["raw_research"] = ""

        result = run_analyst(state, settings=_make_settings())

        assert len(result["errors"]) == 1
        assert "no research data" in result["errors"][0].lower()
        mock_call_llm.assert_not_called()

    @patch("agents.analyst.call_llm")
    def test_llm_failure_appends_error(self, mock_call_llm):
        """LLM returning empty should append error."""
        mock_call_llm.return_value = ""

        state = create_initial_state("test")
        state["compressed_research"] = "Some research data"

        result = run_analyst(state, settings=_make_settings())

        assert result["analysis"] == ""
        assert len(result["errors"]) == 1
        assert "empty response" in result["errors"][0].lower()

    @patch("agents.analyst.call_llm")
    def test_falls_back_to_raw_research(self, mock_call_llm):
        """If compressed_research is empty, should use raw_research."""
        mock_call_llm.return_value = "Analysis result"

        state = create_initial_state("test")
        state["compressed_research"] = ""
        state["raw_research"] = "Raw research data"

        result = run_analyst(state, settings=_make_settings())

        assert result["analysis"] == "Analysis result"
        # Verify the prompt contains the raw research
        call_args = mock_call_llm.call_args
        assert "Raw research data" in call_args.kwargs["prompt"]

    @patch("agents.analyst.call_llm")
    def test_existing_errors_preserved(self, mock_call_llm):
        """Existing errors should not be overwritten."""
        mock_call_llm.return_value = ""

        state = create_initial_state("test")
        state["compressed_research"] = "data"
        state["errors"].append("prior error")

        result = run_analyst(state, settings=_make_settings())

        assert len(result["errors"]) == 2
        assert result["errors"][0] == "prior error"

    @patch("agents.analyst.call_llm")
    def test_style_included_in_prompt(self, mock_call_llm):
        """The style should be included in the analyst prompt."""
        mock_call_llm.return_value = "Analysis"

        state = create_initial_state("test", style="executive summary")
        state["compressed_research"] = "data"

        run_analyst(state, settings=_make_settings())

        call_args = mock_call_llm.call_args
        assert "executive summary" in call_args.kwargs["prompt"].lower()


class TestBuildAnalystPrompt:
    """Tests for the _build_analyst_prompt helper."""

    def test_includes_topic(self):
        """Prompt should include the research topic."""
        state = create_initial_state("quantum computing")
        state["compressed_research"] = "research data"
        prompt = _build_analyst_prompt(state)
        assert "quantum computing" in prompt

    def test_includes_sources(self):
        """Prompt should include source references."""
        state = create_initial_state("test")
        state["compressed_research"] = "data"
        state["sources"] = [
            {"url": "http://example.com", "title": "My Source", "snippet": "s"},
        ]
        prompt = _build_analyst_prompt(state)
        assert "My Source" in prompt
        assert "http://example.com" in prompt

    def test_no_sources_no_crash(self):
        """Prompt should work without sources."""
        state = create_initial_state("test")
        state["compressed_research"] = "data"
        state["sources"] = []
        prompt = _build_analyst_prompt(state)
        assert "data" in prompt
