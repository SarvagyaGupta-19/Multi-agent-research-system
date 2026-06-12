"""Tests for agents/writer.py — report generation agent."""

import pytest
from unittest.mock import patch, MagicMock

from agents.writer import run_writer, _build_writer_prompt
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


class TestRunWriter:
    """Tests for the run_writer function."""

    @patch("agents.writer.call_llm")
    def test_successful_report(self, mock_call_llm):
        """With valid analysis, should produce a report."""
        mock_call_llm.return_value = (
            "# AI Safety Research Report\n\n"
            "## Introduction\nAI safety is a critical field..."
        )

        state = create_initial_state("AI safety", style="academic")
        state["analysis"] = "Key themes: AI safety, alignment, RLHF..."
        state["sources"] = [
            {"url": "http://example.com", "title": "Source 1", "snippet": "s"},
        ]

        result = run_writer(state, settings=_make_settings())

        assert result["report"] != ""
        assert "AI Safety" in result["report"]
        assert result["errors"] == []

    @patch("agents.writer.call_llm")
    def test_empty_analysis_appends_error(self, mock_call_llm):
        """With no analysis, should append error and not call LLM."""
        state = create_initial_state("test")
        state["analysis"] = ""

        result = run_writer(state, settings=_make_settings())

        assert len(result["errors"]) == 1
        assert "no analysis" in result["errors"][0].lower()
        mock_call_llm.assert_not_called()

    @patch("agents.writer.call_llm")
    def test_llm_failure_appends_error(self, mock_call_llm):
        """LLM returning empty should append error."""
        mock_call_llm.return_value = ""

        state = create_initial_state("test")
        state["analysis"] = "Some analysis data"

        result = run_writer(state, settings=_make_settings())

        assert result["report"] == ""
        assert len(result["errors"]) == 1
        assert "empty response" in result["errors"][0].lower()

    @patch("agents.writer.call_llm")
    def test_existing_errors_preserved(self, mock_call_llm):
        """Existing errors should be preserved."""
        mock_call_llm.return_value = ""

        state = create_initial_state("test")
        state["analysis"] = "data"
        state["errors"].append("prior error")

        result = run_writer(state, settings=_make_settings())

        assert len(result["errors"]) == 2
        assert result["errors"][0] == "prior error"

    @patch("agents.writer.call_llm")
    def test_truncation_on_large_input(self, mock_call_llm):
        """Large analysis should be truncated before passing to LLM."""
        mock_call_llm.return_value = "Report"

        state = create_initial_state("test")
        state["analysis"] = "A" * 50000
        settings = _make_settings(MAX_CONTEXT_CHARS=1000)

        run_writer(state, settings=settings)

        # The prompt passed to LLM should be truncated
        call_args = mock_call_llm.call_args
        prompt = call_args.kwargs["prompt"]
        # The full prompt includes more than just the analysis,
        # but the analysis portion should be truncated
        assert len(prompt) < 50000

    @patch("agents.writer.call_llm")
    def test_blog_style(self, mock_call_llm):
        """Blog style should use blog-specific instructions."""
        mock_call_llm.return_value = "Blog post"

        state = create_initial_state("test", style="blog")
        state["analysis"] = "analysis data"

        run_writer(state, settings=_make_settings())

        call_args = mock_call_llm.call_args
        prompt = call_args.kwargs["prompt"]
        assert "blog" in prompt.lower() or "engaging" in prompt.lower()

    @patch("agents.writer.call_llm")
    def test_custom_style(self, mock_call_llm):
        """Unknown style should pass through as user-specified."""
        mock_call_llm.return_value = "Custom report"

        state = create_initial_state("test", style="newsletter")
        state["analysis"] = "analysis data"

        run_writer(state, settings=_make_settings())

        call_args = mock_call_llm.call_args
        prompt = call_args.kwargs["prompt"]
        assert "newsletter" in prompt.lower()


class TestBuildWriterPrompt:
    """Tests for the _build_writer_prompt helper."""

    def test_includes_topic(self):
        """Prompt should include the research topic."""
        state = create_initial_state("quantum computing")
        state["analysis"] = "analysis"
        prompt = _build_writer_prompt(state, max_context_chars=16000)
        assert "quantum computing" in prompt

    def test_includes_sources(self):
        """Prompt should include source references for citation."""
        state = create_initial_state("test")
        state["analysis"] = "analysis"
        state["sources"] = [
            {"url": "http://example.com", "title": "My Source", "snippet": "s"},
        ]
        prompt = _build_writer_prompt(state, max_context_chars=16000)
        assert "My Source" in prompt
        assert "http://example.com" in prompt

    def test_truncates_large_context(self):
        """Should truncate when context exceeds max_context_chars."""
        state = create_initial_state("test")
        state["analysis"] = "B" * 50000
        prompt = _build_writer_prompt(state, max_context_chars=1000)
        assert "[... truncated ...]" in prompt

    def test_academic_style_instruction(self):
        """Academic style should include formal writing instructions."""
        state = create_initial_state("test", style="academic")
        state["analysis"] = "data"
        prompt = _build_writer_prompt(state, max_context_chars=16000)
        assert "academic" in prompt.lower() or "formal" in prompt.lower()

    def test_executive_summary_style(self):
        """Executive summary should include concise writing instructions."""
        state = create_initial_state("test", style="executive summary")
        state["analysis"] = "data"
        prompt = _build_writer_prompt(state, max_context_chars=16000)
        assert "executive" in prompt.lower() or "concise" in prompt.lower()
