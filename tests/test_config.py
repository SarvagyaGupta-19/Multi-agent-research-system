"""Tests for config.py — configuration loading and validation."""

import os
import pytest
from unittest.mock import patch

from config import load_settings, Settings, ConfigurationError, _parse_int


class TestSettings:
    """Tests for the Settings dataclass validation."""

    def test_valid_settings(self):
        """Valid settings should create without error."""
        s = Settings(GROQ_API_KEY="gsk_test123", TAVILY_API_KEY="tvly_test456")
        assert s.GROQ_API_KEY == "gsk_test123"
        assert s.TAVILY_API_KEY == "tvly_test456"
        assert s.GROQ_MODEL == "llama-3.3-70b-versatile"
        assert s.GROQ_TIMEOUT == 30
        assert s.GROQ_MAX_RETRIES == 3
        assert s.TAVILY_MAX_RESULTS == 5
        assert s.MAX_CONTEXT_CHARS == 16000
        assert s.LOG_LEVEL == "INFO"
        assert s.MEM0_API_KEY == ""

    def test_missing_groq_key_raises(self):
        """Empty GROQ_API_KEY should raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
            Settings(GROQ_API_KEY="", TAVILY_API_KEY="tvly_test456")

    def test_missing_tavily_key_raises(self):
        """Empty TAVILY_API_KEY should raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="TAVILY_API_KEY"):
            Settings(GROQ_API_KEY="gsk_test123", TAVILY_API_KEY="")

    def test_both_keys_missing_raises_both(self):
        """Both keys missing should report both in the error."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(GROQ_API_KEY="", TAVILY_API_KEY="")
        assert "GROQ_API_KEY" in str(exc_info.value)
        assert "TAVILY_API_KEY" in str(exc_info.value)

    def test_invalid_timeout_raises(self):
        """Timeout < 1 should raise."""
        with pytest.raises(ConfigurationError, match="GROQ_TIMEOUT"):
            Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test", GROQ_TIMEOUT=0)

    def test_invalid_max_retries_raises(self):
        """Max retries < 0 should raise."""
        with pytest.raises(ConfigurationError, match="GROQ_MAX_RETRIES"):
            Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test", GROQ_MAX_RETRIES=-1)

    def test_invalid_max_results_raises(self):
        """Max results < 1 should raise."""
        with pytest.raises(ConfigurationError, match="TAVILY_MAX_RESULTS"):
            Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test", TAVILY_MAX_RESULTS=0)

    def test_invalid_max_context_raises(self):
        """Max context < 100 should raise."""
        with pytest.raises(ConfigurationError, match="MAX_CONTEXT_CHARS"):
            Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test", MAX_CONTEXT_CHARS=10)

    def test_invalid_log_level_raises(self):
        """Invalid log level should raise."""
        with pytest.raises(ConfigurationError, match="LOG_LEVEL"):
            Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test", LOG_LEVEL="VERBOSE")

    def test_frozen_immutable(self):
        """Settings should be immutable (frozen dataclass)."""
        s = Settings(GROQ_API_KEY="gsk_test", TAVILY_API_KEY="tvly_test")
        with pytest.raises(AttributeError):
            s.GROQ_API_KEY = "new_value"


class TestParseInt:
    """Tests for the _parse_int helper."""

    def test_valid_int(self):
        assert _parse_int("42", "TEST", 10) == 42

    def test_empty_returns_default(self):
        assert _parse_int("", "TEST", 10) == 10

    def test_invalid_raises(self):
        with pytest.raises(ConfigurationError, match="TEST"):
            _parse_int("not_a_number", "TEST", 10)


class TestLoadSettings:
    """Tests for the load_settings function."""

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "gsk_env_test",
        "TAVILY_API_KEY": "tvly_env_test",
    }, clear=False)
    def test_loads_from_env(self):
        """Should load required keys from environment."""
        s = load_settings()
        assert s.GROQ_API_KEY == "gsk_env_test"
        assert s.TAVILY_API_KEY == "tvly_env_test"

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "gsk_test",
        "TAVILY_API_KEY": "tvly_test",
        "GROQ_MODEL": "mixtral-8x7b-32768",
        "GROQ_TIMEOUT": "60",
        "LOG_LEVEL": "debug",
    }, clear=False)
    def test_loads_optional_overrides(self):
        """Should apply optional env var overrides."""
        s = load_settings()
        assert s.GROQ_MODEL == "mixtral-8x7b-32768"
        assert s.GROQ_TIMEOUT == 60
        assert s.LOG_LEVEL == "DEBUG"  # uppercased

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_raises(self):
        """Should raise when required keys are absent."""
        with pytest.raises(ConfigurationError, match="Missing required"):
            load_settings()

    @patch.dict(os.environ, {
        "GROQ_API_KEY": "gsk_test",
        "TAVILY_API_KEY": "tvly_test",
        "GROQ_TIMEOUT": "abc",
    }, clear=False)
    def test_invalid_int_raises(self):
        """Should raise when an int env var has a non-numeric value."""
        with pytest.raises(ConfigurationError, match="GROQ_TIMEOUT"):
            load_settings()
