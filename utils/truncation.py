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

    BP-08: Uses per-source fair truncation so all sources are represented.
    Previously the whole blob was head-truncated, meaning sources 2-5 could
    be entirely cut if source 1 was large.

    Each source gets an equal budget of max_chars // num_sources characters.
    If no source boundaries are detected, falls back to middle truncation.

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
        return state

    # BP-08: Split into per-source sections and budget chars fairly
    # Sections are delimited by the "--- Source:" header written by researcher.py
    import re
    sections = re.split(r"(?=--- Source:)", raw)
    sections = [s for s in sections if s.strip()]

    if not sections:
        # Fallback: no source headers found, use middle truncation to preserve edges
        state["compressed_research"] = truncate_text(raw, max_chars, strategy="middle")
        logger.info(
            "compress_research: no source sections found, middle-truncated from %d to %d chars",
            len(raw), len(state["compressed_research"]),
        )
        return state

    # Equal budget per source (minimum 200 chars per source)
    per_source_budget = max(200, max_chars // len(sections))
    compressed_parts = []
    total = 0

    for section in sections:
        if total >= max_chars:
            break
        allowed = min(per_source_budget, max_chars - total)
        chunk = section[:allowed]
        if len(section) > allowed:
            chunk += "\n[... source truncated ...]"
        compressed_parts.append(chunk)
        total += len(chunk)

    state["compressed_research"] = "\n".join(compressed_parts)
    logger.info(
        "compress_research: distributed %d sources into %d chars (max %d), "
        "budget %d chars/source",
        len(sections), len(state["compressed_research"]), max_chars, per_source_budget,
    )
    return state
