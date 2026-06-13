"""
Mem0 memory client — scoped read/write memory for the research pipeline.

Provides per-session memory using the Mem0 Platform (MemoryClient).
All failures are non-fatal: errors are logged and the pipeline continues
without memory context.

Memory flow:
- Before researcher: read_memory() retrieves prior context for the topic
- After fact_checker: write_memory() stores a summary of the research output
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

# Lazy import flag — avoid import errors if mem0ai is not installed
_mem0_available: bool | None = None


def _check_mem0_available() -> bool:
    """Check if the mem0ai package is installed."""
    global _mem0_available
    if _mem0_available is None:
        try:
            from mem0 import MemoryClient  # noqa: F401
            _mem0_available = True
        except ImportError:
            _mem0_available = False
            logger.warning(
                "Memory: mem0ai package not installed. "
                "Install with 'pip install mem0ai' to enable memory features."
            )
    return _mem0_available


def _get_client(api_key: str):
    """Create a Mem0 MemoryClient instance.

    Args:
        api_key: The Mem0 API key.

    Returns:
        A MemoryClient instance, or None if unavailable.
    """
    if not _check_mem0_available():
        return None

    from mem0 import MemoryClient
    return MemoryClient(api_key=api_key)


def read_memory(
    session_id: str,
    topic: str,
    settings: "Settings | None" = None,
) -> str:
    """Read relevant memory context for a session and topic.

    Performs a semantic search in Mem0 scoped to the session_id.
    Returns matching memories as a concatenated string for use as
    context in the researcher's search query.

    Args:
        session_id: The user or session identifier for scoping.
        topic: The current research topic (used as the search query).
        settings: Optional Settings instance for the API key.

    Returns:
        A string of relevant memory context, or empty string on failure.
        Never raises — all errors are caught and logged.
    """
    if not session_id or not session_id.strip():
        logger.debug("Memory: no session_id provided, skipping read")
        return ""

    if settings is None:
        from config import load_settings
        settings = load_settings()

    api_key = settings.MEM0_API_KEY
    if not api_key:
        logger.debug("Memory: MEM0_API_KEY not set, skipping read")
        return ""

    try:
        client = _get_client(api_key)
        if client is None:
            return ""

        results = client.search(
            query=topic,
            user_id=session_id,
            limit=5,
        )

        if not results:
            logger.debug("Memory: no relevant memories found for session=%s", session_id)
            return ""

        # Extract memory text from results
        memory_parts = []
        for item in results:
            # Mem0 returns results with 'memory' key containing the text
            memory_text = ""
            if isinstance(item, dict):
                memory_text = item.get("memory", "") or item.get("text", "")
            elif isinstance(item, str):
                memory_text = item

            if memory_text:
                memory_parts.append(memory_text)

        if not memory_parts:
            return ""

        context = "\n".join(memory_parts)
        logger.info(
            "Memory: retrieved %d memories (%d chars) for session=%s",
            len(memory_parts), len(context), session_id,
        )
        return context

    except Exception as e:
        # Non-fatal: log and return empty
        logger.warning(
            "Memory: read failed for session=%s: %s: %s",
            session_id, type(e).__name__, e,
        )
        return ""


def write_memory(
    session_id: str,
    topic: str,
    content: str,
    settings: "Settings | None" = None,
) -> bool:
    """Write research results to memory for future context.

    Stores a summary of the research output in Mem0, scoped to the
    session_id. This allows future related queries to benefit from
    prior research.

    Args:
        session_id: The user or session identifier for scoping.
        topic: The research topic.
        content: The content to store (typically a summary of the report).
        settings: Optional Settings instance for the API key.

    Returns:
        True if memory was written successfully, False otherwise.
        Never raises — all errors are caught and logged.
    """
    if not session_id or not session_id.strip():
        logger.debug("Memory: no session_id provided, skipping write")
        return False

    if not content or not content.strip():
        logger.debug("Memory: no content to write, skipping")
        return False

    if settings is None:
        from config import load_settings
        settings = load_settings()

    api_key = settings.MEM0_API_KEY
    if not api_key:
        logger.debug("Memory: MEM0_API_KEY not set, skipping write")
        return False

    try:
        client = _get_client(api_key)
        if client is None:
            return False

        # Truncate content to avoid oversized memory entries
        max_memory_chars = 2000
        if len(content) > max_memory_chars:
            content = content[:max_memory_chars] + "..."

        # Store as a message from the research system
        messages = [
            {
                "role": "user",
                "content": f"Research topic: {topic}",
            },
            {
                "role": "assistant",
                "content": content,
            },
        ]

        client.add(
            messages=messages,
            user_id=session_id,
            metadata={"topic": topic, "source": "research_pipeline"},
        )

        logger.info(
            "Memory: wrote %d chars for session=%s topic='%s'",
            len(content), session_id, topic,
        )
        return True

    except Exception as e:
        # Non-fatal: log and return False
        logger.warning(
            "Memory: write failed for session=%s: %s: %s",
            session_id, type(e).__name__, e,
        )
        return False


def build_memory_summary(topic: str, report: str, analysis: str) -> str:
    """Build a concise summary for memory storage.

    Combines topic, key analysis points, and report highlights
    into a compact string suitable for Mem0 storage.

    Args:
        topic: The research topic.
        report: The generated report.
        analysis: The analyst's analysis.

    Returns:
        A summary string for memory storage.
    """
    parts = [f"Research completed on: {topic}"]

    if analysis:
        # Take first 500 chars of analysis as key findings
        parts.append(f"Key findings: {analysis[:500]}")

    if report:
        # Take first 800 chars of report as summary
        parts.append(f"Report summary: {report[:800]}")

    return "\n\n".join(parts)
