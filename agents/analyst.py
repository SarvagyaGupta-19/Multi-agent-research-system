"""
Analyst agent — analyzes research data and identifies key themes.

Takes compressed research and produces a structured analysis
covering themes, patterns, contradictions, and key findings.
"""

import logging
from typing import TYPE_CHECKING

from agents.llm_client import call_llm
from graph.state import ResearchState

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior research analyst. Your task is to analyze raw research data and produce a structured analysis.

Your analysis MUST include:
1. **Key Themes**: The major themes and topics found in the research.
2. **Key Findings**: The most important facts and findings.
3. **Patterns & Trends**: Any patterns, trends, or recurring ideas.
4. **Contradictions & Gaps**: Any conflicting information or missing areas.
5. **Source Quality Assessment**: A brief evaluation of source reliability.

Format your analysis with clear headers and bullet points.
Be concise but thorough. Do NOT invent information not present in the research data.
"""


def _build_analyst_prompt(state: ResearchState) -> str:
    """Build the analyst prompt from state.

    Uses compressed_research if available, falls back to raw_research.
    Incorporates the requested style.

    Args:
        state: The current research state.

    Returns:
        The formatted prompt string.
    """
    # Prefer compressed, fall back to raw
    research = state.get("compressed_research", "") or state.get("raw_research", "")

    # Include source summary
    sources_summary = ""
    if state.get("sources"):
        source_lines = []
        for i, src in enumerate(state["sources"], 1):
            source_lines.append(f"{i}. {src.get('title', 'Untitled')} — {src.get('url', 'N/A')}")
        sources_summary = "\n\nSources referenced:\n" + "\n".join(source_lines)

    style = state.get("style", "academic")

    prompt = (
        f"Analyze the following research data on the topic: \"{state.get('topic', 'Unknown')}\"\n"
        f"Target audience style: {style}\n\n"
        f"--- Research Data ---\n{research}\n"
        f"{sources_summary}\n\n"
        f"Provide your structured analysis."
    )

    return prompt


def run_analyst(state: ResearchState, settings: "Settings | None" = None) -> ResearchState:
    """Execute analysis on the research data.

    Reads compressed_research (or raw_research) and produces a structured
    analysis covering themes, patterns, contradictions, and findings.

    Args:
        state: The current ResearchState with research data populated.
        settings: Optional Settings instance for LLM configuration.

    Returns:
        Updated ResearchState with analysis populated.
        On failure, appends error and leaves analysis empty.
    """
    research = state.get("compressed_research", "") or state.get("raw_research", "")

    if not research:
        error_msg = "Analyst: no research data available for analysis"
        state["errors"].append(error_msg)
        logger.warning(error_msg)
        return state

    logger.info(
        "Analyst: starting analysis of %d chars of research",
        len(research),
    )

    prompt = _build_analyst_prompt(state)
    result = call_llm(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        temperature=0.3,
        settings=settings,
    )

    if not result:
        error_msg = "Analyst: LLM returned empty response"
        state["errors"].append(error_msg)
        logger.error(error_msg)
        return state

    state["analysis"] = result
    logger.info("Analyst: completed analysis (%d chars)", len(result))
    return state
