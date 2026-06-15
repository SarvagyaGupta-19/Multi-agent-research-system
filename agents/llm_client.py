"""
Shared Groq LLM client wrapper with retry logic and error handling.

All LLM-based agents use this single client to ensure consistent
timeout, retry, and error handling behavior.
"""

import logging
import time
from typing import TYPE_CHECKING

from groq import Groq
from groq import (
    RateLimitError,
    APIConnectionError,
    InternalServerError,
    AuthenticationError,
    BadRequestError,
    APIStatusError,
)

from config import load_settings

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

# Errors that are safe to retry (transient failures)
_RETRYABLE_ERRORS = (RateLimitError, APIConnectionError, InternalServerError)

# Errors that should NOT be retried (permanent failures)
_NON_RETRYABLE_ERRORS = (AuthenticationError, BadRequestError)


def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.3,
    settings: "Settings | None" = None,
    json_mode: bool = False,
    model_override: str | None = None,
) -> str:
    """Call the Groq LLM with retry logic and error handling.

    Retries on transient errors (rate limits, connection issues, server errors)
    with exponential backoff. Does NOT retry on authentication or bad request
    errors.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt for role/instruction.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        settings: Optional Settings instance. If None, loads from environment.
        json_mode: If True, constrains the model to output valid JSON via
            response_format={"type": "json_object"}. The prompt or system
            prompt MUST mention "JSON" for this to work reliably.
        model_override: Optional model name to use instead of settings.GROQ_MODEL.

    Returns:
        The LLM response content string.
        Returns empty string on exhausted retries or permanent failure, EXCEPT for
        rate limits which will raise an Exception to halt the pipeline immediately.
    """
    if settings is None:
        settings = load_settings()

    if not prompt or not prompt.strip():
        logger.warning("LLM client: called with empty prompt, returning empty")
        return ""

    client = Groq(
        api_key=settings.GROQ_API_KEY,
        timeout=settings.GROQ_TIMEOUT,
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Build optional kwargs
    create_kwargs = {
        "model": model_override if model_override else settings.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        create_kwargs["response_format"] = {"type": "json_object"}

    max_retries = settings.GROQ_MAX_RETRIES
    last_error = None

    for attempt in range(max_retries + 1):  # attempt 0 is the first try
        try:
            response = client.chat.completions.create(**create_kwargs)

            # Extract content from the response
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                logger.debug(
                    "LLM client: success on attempt %d, response length=%d",
                    attempt + 1,
                    len(content),
                )
                return content
            else:
                logger.warning("LLM client: empty response from model on attempt %d", attempt + 1)
                return ""

        except _NON_RETRYABLE_ERRORS as e:
            # Permanent failure — do not retry
            logger.error(
                "LLM client: non-retryable error (%s): %s",
                type(e).__name__, e,
            )
            return ""

        except _RETRYABLE_ERRORS as e:
            last_error = e
            if attempt < max_retries:
                # Exponential backoff: 2^attempt seconds, capped at 16s
                backoff = min(2 ** attempt, 16)
                logger.warning(
                    "LLM client: retryable error on attempt %d/%d (%s): %s. "
                    "Retrying in %ds...",
                    attempt + 1, max_retries + 1,
                    type(e).__name__, e,
                    backoff,
                )
                time.sleep(backoff)
            else:
                logger.error(
                    "LLM client: max retries (%d) exhausted. Last error: %s: %s",
                    max_retries + 1,
                    type(e).__name__, e,
                )

        except Exception as e:
            # Unexpected error — log and do not retry
            # Justified catch-all: we must not crash the pipeline on unknown SDK errors
            logger.error(
                "LLM client: unexpected error (%s): %s",
                type(e).__name__, e,
                exc_info=True,
            )
            return ""

    # All retries exhausted
    logger.error(
        "LLM client: all %d attempts failed. Last error: %s",
        max_retries + 1,
        last_error,
    )
    
    # If the job failed specifically because of a rate limit, raise an exception
    # to halt the pipeline and report the exact wait time to the user.
    if isinstance(last_error, RateLimitError):
        error_message = str(last_error)
        try:
            if hasattr(last_error, 'body') and isinstance(last_error.body, dict):
                error_message = last_error.body.get('error', {}).get('message', error_message)
        except Exception:
            pass
        raise Exception(f"Rate Limit Exceeded: {error_message}")

    return ""
