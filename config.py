"""
Configuration loader for the Multi-Agent Research System.

All configuration is loaded from environment variables (via .env file).
Validates required keys at load time and fails fast with clear messages.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables.

    Required fields will cause a ConfigurationError if missing.
    Optional fields have sensible defaults.
    """
    # Required API keys
    GROQ_API_KEY: str
    TAVILY_API_KEY: str

    # Optional API keys (deferred features)
    MEM0_API_KEY: str = ""

    # Groq LLM settings
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT: int = 30
    GROQ_MAX_RETRIES: int = 3

    # Tavily search settings
    TAVILY_MAX_RESULTS: int = 5

    # Context management
    MAX_CONTEXT_CHARS: int = 16000

    # Logging
    LOG_LEVEL: str = "INFO"

    def __post_init__(self):
        """Validate settings after initialization."""
        errors = []
        if not self.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required and cannot be empty")
        if not self.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY is required and cannot be empty")
        if self.GROQ_TIMEOUT < 1:
            errors.append(f"GROQ_TIMEOUT must be >= 1, got {self.GROQ_TIMEOUT}")
        if self.GROQ_MAX_RETRIES < 0:
            errors.append(f"GROQ_MAX_RETRIES must be >= 0, got {self.GROQ_MAX_RETRIES}")
        if self.TAVILY_MAX_RESULTS < 1:
            errors.append(f"TAVILY_MAX_RESULTS must be >= 1, got {self.TAVILY_MAX_RESULTS}")
        if self.MAX_CONTEXT_CHARS < 100:
            errors.append(f"MAX_CONTEXT_CHARS must be >= 100, got {self.MAX_CONTEXT_CHARS}")
        if self.LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            errors.append(f"LOG_LEVEL must be a valid Python log level, got '{self.LOG_LEVEL}'")
        if errors:
            raise ConfigurationError(
                "Configuration validation failed:\n  - " + "\n  - ".join(errors)
            )


def _parse_int(value: str, name: str, default: int) -> int:
    """Parse an integer from an environment variable string.

    Args:
        value: The string value to parse.
        name: The variable name (for error messages).
        default: The default to return if value is empty.

    Returns:
        The parsed integer.

    Raises:
        ConfigurationError: If the value is not a valid integer.
    """
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigurationError(
            f"Environment variable {name} must be an integer, got '{value}'"
        )


def load_settings(env_path: str | None = None) -> Settings:
    """Load settings from environment variables.

    Loads a .env file if present, then reads all config from os.environ.
    Validates required keys and returns a frozen Settings instance.

    Args:
        env_path: Optional explicit path to a .env file. If None, searches
                  the current directory and parent directories.

    Returns:
        A validated, frozen Settings instance.

    Raises:
        ConfigurationError: If required keys are missing or values are invalid.
    """
    if env_path:
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Collect missing required keys for a single clear error message
    missing = []
    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    if not groq_key:
        missing.append("GROQ_API_KEY")
    if not tavily_key:
        missing.append("TAVILY_API_KEY")

    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in your .env file or environment. "
            f"See .env.example for reference."
        )

    settings = Settings(
        GROQ_API_KEY=groq_key,
        TAVILY_API_KEY=tavily_key,
        MEM0_API_KEY=os.getenv("MEM0_API_KEY", ""),
        GROQ_MODEL=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        GROQ_TIMEOUT=_parse_int(os.getenv("GROQ_TIMEOUT", ""), "GROQ_TIMEOUT", 30),
        GROQ_MAX_RETRIES=_parse_int(os.getenv("GROQ_MAX_RETRIES", ""), "GROQ_MAX_RETRIES", 3),
        TAVILY_MAX_RESULTS=_parse_int(os.getenv("TAVILY_MAX_RESULTS", ""), "TAVILY_MAX_RESULTS", 5),
        MAX_CONTEXT_CHARS=_parse_int(os.getenv("MAX_CONTEXT_CHARS", ""), "MAX_CONTEXT_CHARS", 16000),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").upper(),
    )

    logger.info("Configuration loaded successfully (model=%s)", settings.GROQ_MODEL)
    return settings
