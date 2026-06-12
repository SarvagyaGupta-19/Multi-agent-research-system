"""
Researcher agent — performs web search and returns structured results.

Uses the Tavily Python SDK to search for the user's topic.
Returns structured state with raw_research, sources, and any errors.
Failures are captured in state["errors"], never raised.
"""

import logging
from typing import TYPE_CHECKING

from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError

from config import load_settings
from graph.state import ResearchState

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)


def _build_search_query(state: ResearchState) -> str:
    """Build an effective search query from state.

    Incorporates topic and optionally memory context for better results.

    Args:
        state: The current research state.

    Returns:
        A search query string.
    """
    query = state["topic"]
    if state.get("memory_context"):
        # Append memory context as additional search context
        query = f"{query} {state['memory_context'][:200]}"
    return query


def run_researcher(state: ResearchState, settings: "Settings | None" = None) -> ResearchState:
    """Execute web research for the given topic.

    Searches the web using Tavily and populates state with:
    - raw_research: Concatenated search result content
    - sources: Structured list of {url, title, snippet} dicts
    - errors: Any errors encountered (appended, not raised)

    Args:
        state: The current ResearchState. Must have 'topic' populated.
        settings: Optional Settings instance. If None, loads from environment.

    Returns:
        Updated ResearchState with research results or errors.
    """
    if settings is None:
        settings = load_settings()

    topic = state.get("topic", "")
    if not topic or not topic.strip():
        state["errors"].append("Researcher: topic is empty, cannot perform search")
        logger.error("Researcher called with empty topic")
        return state

    logger.info("Researcher: starting search for topic='%s'", topic)

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        query = _build_search_query(state)

        response = client.search(
            query=query,
            max_results=settings.TAVILY_MAX_RESULTS,
            search_depth="advanced",
            include_raw_content=False,
        )

    except MissingAPIKeyError:
        error_msg = "Researcher: Tavily API key is missing or empty"
        state["errors"].append(error_msg)
        logger.error(error_msg)
        return state
    except InvalidAPIKeyError:
        error_msg = "Researcher: Tavily API key is invalid"
        state["errors"].append(error_msg)
        logger.error(error_msg)
        return state
    except UsageLimitExceededError:
        error_msg = "Researcher: Tavily usage limit exceeded"
        state["errors"].append(error_msg)
        logger.error(error_msg)
        return state
    except Exception as e:
        # Catch-all for network errors, timeouts, unexpected SDK errors.
        # Justified: we must not crash the pipeline on any external failure.
        error_msg = f"Researcher: search failed with {type(e).__name__}: {e}"
        state["errors"].append(error_msg)
        logger.error(error_msg, exc_info=True)
        return state

    # Parse results
    results = response.get("results", [])
    if not results:
        warning_msg = f"Researcher: no results found for topic='{topic}'"
        state["errors"].append(warning_msg)
        logger.warning(warning_msg)
        state["raw_research"] = ""
        state["sources"] = []
        return state

    # Build structured sources
    sources = []
    research_parts = []

    for i, result in enumerate(results):
        url = result.get("url", "")
        title = result.get("title", f"Source {i + 1}")
        content = result.get("content", "")
        snippet = content[:300] if content else ""

        sources.append({
            "url": url,
            "title": title,
            "snippet": snippet,
        })

        # Build raw research text with source attribution
        research_parts.append(
            f"--- Source: {title} ({url}) ---\n{content}\n"
        )

    state["raw_research"] = "\n".join(research_parts)
    state["sources"] = sources

    logger.info(
        "Researcher: completed with %d sources, %d chars of research",
        len(sources),
        len(state["raw_research"]),
    )

    return state
