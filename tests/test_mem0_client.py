"""
Tests for the Mem0 memory client.

Tests read_memory, write_memory, and build_memory_summary with
mocked MemoryClient to avoid actual API calls.
"""

import logging
from unittest.mock import patch, MagicMock

import pytest

from memory.mem0_client import read_memory, write_memory, build_memory_summary


# --- Fixtures ---

@pytest.fixture
def mock_settings():
    """Create a mock Settings instance with MEM0_API_KEY."""
    settings = MagicMock()
    settings.MEM0_API_KEY = "test-mem0-key"
    settings.GROQ_API_KEY = "test-groq-key"
    settings.TAVILY_API_KEY = "test-tavily-key"
    return settings


@pytest.fixture
def mock_settings_no_key():
    """Create a mock Settings instance without MEM0_API_KEY."""
    settings = MagicMock()
    settings.MEM0_API_KEY = ""
    return settings


# --- read_memory tests ---

class TestReadMemory:
    """Tests for memory reading."""

    @patch("memory.mem0_client._get_client")
    def test_reads_memory_successfully(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": "Previous research on quantum computing found 5 key trends."},
            {"memory": "Quantum error correction is a major focus area."},
        ]
        mock_get_client.return_value = mock_client

        result = read_memory(
            session_id="session-123",
            topic="quantum computing",
            settings=mock_settings,
        )

        assert "quantum computing" in result
        assert "error correction" in result
        mock_client.search.assert_called_once_with(
            query="quantum computing",
            filters={"user_id": "session-123"},
            limit=5,
        )

    @patch("memory.mem0_client._get_client")
    def test_returns_empty_on_no_results(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_get_client.return_value = mock_client

        result = read_memory("session-123", "unknown topic", settings=mock_settings)

        assert result == ""

    def test_returns_empty_without_session_id(self, mock_settings):
        result = read_memory("", "topic", settings=mock_settings)
        assert result == ""

    def test_returns_empty_without_api_key(self, mock_settings_no_key):
        result = read_memory("session-123", "topic", settings=mock_settings_no_key)
        assert result == ""

    @patch("memory.mem0_client._get_client")
    def test_handles_api_error_gracefully(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API connection failed")
        mock_get_client.return_value = mock_client

        result = read_memory("session-123", "topic", settings=mock_settings)

        assert result == ""

    @patch("memory.mem0_client._get_client")
    def test_handles_string_results(self, mock_get_client, mock_settings):
        """Some Mem0 versions return strings instead of dicts."""
        mock_client = MagicMock()
        mock_client.search.return_value = [
            "A string memory result",
        ]
        mock_get_client.return_value = mock_client

        result = read_memory("session-123", "topic", settings=mock_settings)

        assert "A string memory result" in result

    @patch("memory.mem0_client._get_client")
    def test_returns_empty_when_client_unavailable(self, mock_get_client, mock_settings):
        mock_get_client.return_value = None

        result = read_memory("session-123", "topic", settings=mock_settings)

        assert result == ""


# --- write_memory tests ---

class TestWriteMemory:
    """Tests for memory writing."""

    @patch("memory.mem0_client._get_client")
    def test_writes_memory_successfully(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = write_memory(
            session_id="session-123",
            topic="quantum computing",
            content="Research found 5 key trends in quantum computing.",
            settings=mock_settings,
        )

        assert result is True
        mock_client.add.assert_called_once()
        call_kwargs = mock_client.add.call_args[1]
        assert call_kwargs["user_id"] == "session-123"
        assert call_kwargs["metadata"]["topic"] == "quantum computing"

    def test_returns_false_without_session_id(self, mock_settings):
        result = write_memory("", "topic", "content", settings=mock_settings)
        assert result is False

    def test_returns_false_without_content(self, mock_settings):
        result = write_memory("session-123", "topic", "", settings=mock_settings)
        assert result is False

    def test_returns_false_without_api_key(self, mock_settings_no_key):
        result = write_memory("session-123", "topic", "content", settings=mock_settings_no_key)
        assert result is False

    @patch("memory.mem0_client._get_client")
    def test_handles_api_error_gracefully(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_client.add.side_effect = Exception("API write failed")
        mock_get_client.return_value = mock_client

        result = write_memory("session-123", "topic", "content", settings=mock_settings)

        assert result is False

    @patch("memory.mem0_client._get_client")
    def test_truncates_long_content(self, mock_get_client, mock_settings):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        long_content = "x" * 5000
        write_memory("session-123", "topic", long_content, settings=mock_settings)

        call_args = mock_client.add.call_args
        messages = call_args[1]["messages"]
        # The assistant message content should be truncated
        assistant_content = messages[1]["content"]
        assert len(assistant_content) <= 2004  # 2000 + "..."

    @patch("memory.mem0_client._get_client")
    def test_returns_false_when_client_unavailable(self, mock_get_client, mock_settings):
        mock_get_client.return_value = None

        result = write_memory("session-123", "topic", "content", settings=mock_settings)

        assert result is False


# --- build_memory_summary tests ---

class TestBuildMemorySummary:
    """Tests for memory summary building."""

    def test_builds_full_summary(self):
        summary = build_memory_summary(
            topic="quantum computing",
            report="This is the report content.",
            analysis="This is the analysis content.",
        )

        assert "quantum computing" in summary
        assert "report content" in summary
        assert "analysis content" in summary

    def test_builds_with_empty_analysis(self):
        summary = build_memory_summary(
            topic="topic",
            report="Report here.",
            analysis="",
        )

        assert "topic" in summary
        assert "Report here" in summary

    def test_builds_with_empty_report(self):
        summary = build_memory_summary(
            topic="topic",
            report="",
            analysis="Analysis here.",
        )

        assert "topic" in summary
        assert "Analysis here" in summary

    def test_truncates_long_content(self):
        long_report = "x" * 2000
        long_analysis = "y" * 2000

        summary = build_memory_summary(
            topic="topic",
            report=long_report,
            analysis=long_analysis,
        )

        # Should contain truncated versions
        assert len(summary) < 4000  # Much less than 4000 chars total
