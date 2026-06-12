"""
Text truncation and research compression utilities.

Ensures downstream agents receive manageable context sizes
without exceeding LLM token limits.
"""

import logging
from typing import TYPE_CHECKING

from config import load_settings
from graph.state import ResearchState

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)


def truncate_text(
    text: str,
    max_chars: int,
    strategy: str = "tail",
) -> str:
    """Truncate text to a maximum character count.

    Args:
        text: The text to truncate.
        max_chars: Maximum number of characters to keep.
        strategy: Truncation strategy:
            - "tail": Keep the first max_chars characters.
            - "middle": Keep first and last max_chars//2 characters.

    Returns:
        The truncated text (with marker) or original if under limit.

    Raises:
        ValueError: If strategy is not recognized or max_chars < 1.
    """
    if max_chars < 1:
        raise ValueError(f"max_chars must be >= 1, got {max_chars}")

    if not text or len(text) <= max_chars:
        return text

    if strategy == "tail":
        truncated = text[:max_chars]
        return truncated + "\n\n[... truncated ...]"

    elif strategy == "middle":
        half = max_chars // 2
        head = text[:half]
        tail = text[-half:]
        return head + "\n\n[... middle truncated ...]\n\n" + tail

    else:
        raise ValueError(
            f"Unknown truncation strategy: '{strategy}'. "
            f"Supported: 'tail', 'middle'"
        )


def compress_research(
    state: ResearchState,
    settings: "Settings | None" = None,
) -> ResearchState:
    """Compress raw research into a manageable size for downstream agents.

    If raw_research exceeds MAX_CONTEXT_CHARS, truncates it and stores
    the result in compressed_research. Otherwise, copies raw_research
    directly to compressed_research.

    Args:
        state: The current ResearchState with raw_research populated.
        settings: Optional Settings instance. If None, loads from environment.

    Returns:
        Updated ResearchState with compressed_research populated.
    """
    if settings is None:
        settings = load_settings()

    raw = state.get("raw_research", "")
    max_chars = settings.MAX_CONTEXT_CHARS

    if not raw:
        state["compressed_research"] = ""
        logger.debug("compress_research: no raw research to compress")
        return state

    if len(raw) <= max_chars:
        state["compressed_research"] = raw
        logger.debug(
            "compress_research: raw research (%d chars) within limit (%d), "
            "copying directly",
            len(raw), max_chars,
        )
    else:
        state["compressed_research"] = truncate_text(raw, max_chars, strategy="tail")
        logger.info(
            "compress_research: truncated from %d to %d chars",
            len(raw), len(state["compressed_research"]),
        )

    return state
