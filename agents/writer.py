"""
Writer agent — generates a polished report from analysis and research.

Takes the analyst's output and source data, then produces a
well-structured report in the requested style.
"""

import logging
from typing import TYPE_CHECKING

from agents.llm_client import call_llm
from utils.truncation import truncate_text
from config import load_settings
from graph.state import ResearchState

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_STYLE_INSTRUCTIONS = {
    "academic": (
        "Write in a formal academic style with proper citations, "
        "objective tone, and structured sections (Introduction, Analysis, "
        "Findings, Conclusion). Use precise language."
    ),
    "blog": (
        "Write in an engaging blog style that is accessible to a general "
        "audience. Use conversational tone, subheadings, and practical examples. "
        "Keep paragraphs short."
    ),
    "executive summary": (
        "Write a concise executive summary for business decision-makers. "
        "Lead with key findings and recommendations. Use bullet points "
        "for actionable items. Keep it under 500 words."
    ),
    "technical": (
        "Write in a technical style suitable for engineers and developers. "
        "Include specific details, data points, and technical terminology. "
        "Structure with clear sections."
    ),
}

_SYSTEM_PROMPT = """You are an expert research report writer. Your task is to produce a polished, well-structured report based on the analysis and research data provided.

Your report MUST:
1. Be well-organized with clear sections and headers.
2. Accurately represent the research findings without inventing information.
3. Include proper source attribution where relevant.
4. Follow the requested writing style.
5. Be comprehensive but avoid unnecessary repetition.

Do NOT fabricate facts, statistics, or sources not present in the provided data.
"""


def _build_writer_prompt(state: ResearchState, max_context_chars: int) -> str:
    """Build the writer prompt from state.

    Combines analysis, source data, and style instructions.
    Applies truncation if the combined input exceeds max_context_chars.

    Args:
        state: The current research state.
        max_context_chars: Maximum chars for the context portion of the prompt.

    Returns:
        The formatted prompt string.
    """
    analysis = state.get("analysis", "")
    style = state.get("style", "academic")
    topic = state.get("topic", "Unknown")

    # Get style-specific instructions
    style_instruction = _STYLE_INSTRUCTIONS.get(
        style.lower(),
        f"Write in a '{style}' style as specified by the user."
    )

    # Build source reference section
    source_refs = ""
    if state.get("sources"):
        source_lines = []
        for i, src in enumerate(state["sources"], 1):
            source_lines.append(
                f"[{i}] {src.get('title', 'Untitled')} — {src.get('url', 'N/A')}"
            )
        source_refs = "\n\nAvailable sources for citation:\n" + "\n".join(source_lines)

    # Combine and truncate if needed
    context = f"--- Analysis ---\n{analysis}\n{source_refs}"
    if len(context) > max_context_chars:
        context = truncate_text(context, max_context_chars, strategy="tail")
        logger.info(
            "Writer: truncated context from %d to %d chars",
            len(analysis) + len(source_refs),
            len(context),
        )

    prompt = (
        f"Write a comprehensive research report on the topic: \"{topic}\"\n\n"
        f"Style instruction: {style_instruction}\n\n"
        f"{context}\n\n"
        f"Generate the report now."
    )

    return prompt


def run_writer(state: ResearchState, settings: "Settings | None" = None) -> ResearchState:
    """Generate a polished report from analysis and research data.

    Takes the analyst's analysis and source data, then produces a
    well-structured report in the requested writing style.

    Args:
        state: The current ResearchState with analysis populated.
        settings: Optional Settings instance for LLM configuration.

    Returns:
        Updated ResearchState with report populated.
        On failure, appends error and leaves report empty.
    """
    if settings is None:
        settings = load_settings()

    analysis = state.get("analysis", "")

    if not analysis:
        error_msg = "Writer: no analysis data available for report generation"
        state["errors"].append(error_msg)
        logger.warning(error_msg)
        return state

    logger.info("Writer: starting report generation (style='%s')", state.get("style", "academic"))

    prompt = _build_writer_prompt(state, max_context_chars=settings.MAX_CONTEXT_CHARS)
    result = call_llm(
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        temperature=0.4,  # slightly higher for creative writing
        settings=settings,
    )

    if not result:
        error_msg = "Writer: LLM returned empty response"
        state["errors"].append(error_msg)
        logger.error(error_msg)
        return state

    state["report"] = result
    logger.info("Writer: completed report (%d chars)", len(result))
    return state
