"""Tests for agents/llm_client.py — Groq LLM wrapper with retry logic."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from agents.llm_client import call_llm
from config import Settings


def _make_settings(**overrides) -> Settings:
    """Create a test Settings instance."""
    defaults = {
        "GROQ_API_KEY": "gsk_test_key",
        "TAVILY_API_KEY": "tvly_test_key",
        "GROQ_MAX_RETRIES": 2,
        "GROQ_TIMEOUT": 10,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_mock_response(content: str) -> MagicMock:
    """Create a mock Groq chat completion response."""
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response


class TestCallLlm:
    """Tests for the call_llm function."""

    @patch("agents.llm_client.Groq")
    def test_successful_call(self, mock_groq_cls):
        """Successful LLM call should return the content string."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response(
            "This is the analysis result."
        )

        result = call_llm(
            prompt="Analyze this data",
            system_prompt="You are an analyst",
            settings=_make_settings(),
        )

        assert result == "This is the analysis result."
        mock_client.chat.completions.create.assert_called_once()

    @patch("agents.llm_client.Groq")
    def test_system_prompt_included(self, mock_groq_cls):
        """System prompt should be passed as the first message."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("ok")

        call_llm(
            prompt="test prompt",
            system_prompt="system instruction",
            settings=_make_settings(),
        )

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "system instruction"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "test prompt"

    @patch("agents.llm_client.Groq")
    def test_no_system_prompt(self, mock_groq_cls):
        """Without system prompt, only user message should be sent."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("ok")

        call_llm(prompt="test prompt", settings=_make_settings())

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_empty_prompt_returns_empty(self):
        """Empty prompt should return empty string without calling LLM."""
        result = call_llm(prompt="", settings=_make_settings())
        assert result == ""

    def test_whitespace_prompt_returns_empty(self):
        """Whitespace-only prompt should return empty string."""
        result = call_llm(prompt="   ", settings=_make_settings())
        assert result == ""

    @patch("agents.llm_client.Groq")
    def test_empty_response_returns_empty(self, mock_groq_cls):
        """Empty model response should return empty string."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = []
        mock_client.chat.completions.create.return_value = mock_response

        result = call_llm(prompt="test", settings=_make_settings())
        assert result == ""

    @patch("agents.llm_client.time.sleep")  # skip actual sleeping
    @patch("agents.llm_client.Groq")
    def test_retry_on_rate_limit(self, mock_groq_cls, mock_sleep):
        """Should retry on RateLimitError and succeed."""
        from groq import RateLimitError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Create a proper mock response for RateLimitError
        mock_http_response = MagicMock()
        mock_http_response.status_code = 429
        mock_http_response.headers = {}
        mock_http_response.text = "rate limited"

        rate_limit_error = RateLimitError(
            message="Rate limit exceeded",
            response=mock_http_response,
            body=None,
        )

        # Fail twice, then succeed
        mock_client.chat.completions.create.side_effect = [
            rate_limit_error,
            rate_limit_error,
            _make_mock_response("success after retries"),
        ]

        settings = _make_settings(GROQ_MAX_RETRIES=2)
        result = call_llm(prompt="test", settings=settings)

        assert result == "success after retries"
        assert mock_client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("agents.llm_client.time.sleep")
    @patch("agents.llm_client.Groq")
    def test_max_retries_exhausted(self, mock_groq_cls, mock_sleep):
        """Should return empty string when all retries are exhausted."""
        from groq import APIConnectionError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        conn_error = APIConnectionError(request=MagicMock())

        # Fail on all attempts
        mock_client.chat.completions.create.side_effect = conn_error

        settings = _make_settings(GROQ_MAX_RETRIES=1)
        result = call_llm(prompt="test", settings=settings)

        assert result == ""
        # 1 initial + 1 retry = 2 calls
        assert mock_client.chat.completions.create.call_count == 2

    @patch("agents.llm_client.Groq")
    def test_auth_error_no_retry(self, mock_groq_cls):
        """AuthenticationError should NOT be retried."""
        from groq import AuthenticationError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_http_response = MagicMock()
        mock_http_response.status_code = 401
        mock_http_response.headers = {}
        mock_http_response.text = "unauthorized"

        auth_error = AuthenticationError(
            message="Invalid API key",
            response=mock_http_response,
            body=None,
        )
        mock_client.chat.completions.create.side_effect = auth_error

        result = call_llm(prompt="test", settings=_make_settings())

        assert result == ""
        # Should only be called once (no retry)
        assert mock_client.chat.completions.create.call_count == 1

    @patch("agents.llm_client.Groq")
    def test_bad_request_no_retry(self, mock_groq_cls):
        """BadRequestError should NOT be retried."""
        from groq import BadRequestError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_http_response = MagicMock()
        mock_http_response.status_code = 400
        mock_http_response.headers = {}
        mock_http_response.text = "bad request"

        bad_req_error = BadRequestError(
            message="Bad request",
            response=mock_http_response,
            body=None,
        )
        mock_client.chat.completions.create.side_effect = bad_req_error

        result = call_llm(prompt="test", settings=_make_settings())

        assert result == ""
        assert mock_client.chat.completions.create.call_count == 1

    @patch("agents.llm_client.Groq")
    def test_unexpected_error_no_retry(self, mock_groq_cls):
        """Unexpected errors should not be retried."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("unexpected")

        result = call_llm(prompt="test", settings=_make_settings())

        assert result == ""
        assert mock_client.chat.completions.create.call_count == 1

    @patch("agents.llm_client.time.sleep")
    @patch("agents.llm_client.Groq")
    def test_exponential_backoff(self, mock_groq_cls, mock_sleep):
        """Backoff should be exponential: 1s, 2s, 4s..."""
        from groq import APIConnectionError

        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        settings = _make_settings(GROQ_MAX_RETRIES=3)
        call_llm(prompt="test", settings=settings)

        # Check backoff values: 2^0=1, 2^1=2, 2^2=4
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("agents.llm_client.Groq")
    def test_temperature_passed(self, mock_groq_cls):
        """Custom temperature should be passed to the API."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("ok")

        call_llm(prompt="test", temperature=0.7, settings=_make_settings())

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7

    @patch("agents.llm_client.Groq")
    def test_model_from_settings(self, mock_groq_cls):
        """Model name should come from settings."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_mock_response("ok")

        settings = _make_settings(GROQ_MODEL="mixtral-8x7b-32768")
        call_llm(prompt="test", settings=settings)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "mixtral-8x7b-32768"
