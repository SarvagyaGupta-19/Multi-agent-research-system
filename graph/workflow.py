"""
LangGraph workflow — orchestrates the multi-agent research pipeline.

Wires the 4 agents (researcher → analyst → writer → fact_checker) into
a LangGraph StateGraph with memory integration and research compression.
Provides run_research() as the single entry point for the backend.

Pipeline:
  START → memory_read → researcher → compress → analyst → writer → fact_checker → memory_write → END
"""

import logging
from typing import TYPE_CHECKING

from langgraph.graph import StateGraph, START, END

from config import load_settings
from graph.state import ResearchState, create_initial_state
from agents.researcher import run_researcher
from agents.analyst import run_analyst
from agents.writer import run_writer
from agents.fact_checker import run_fact_checker
from memory.mem0_client import read_memory, write_memory, build_memory_summary
from utils.truncation import compress_research

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)


# --- Node factory functions ---

def _make_memory_read_node(settings: "Settings"):
    """Create a memory read node that loads prior context before research."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering memory_read node")

        if state.get("skip_memory", False):
            logger.info("Workflow: skip_memory=True, bypassing memory read")
            return state

        session_id = state.get("session_id", "")
        if not session_id:
            logger.debug("Workflow: no session_id, skipping memory read")
            return state

        topic = state.get("topic", "")
        context = read_memory(
            session_id=session_id,
            topic=topic,
            settings=settings,
        )

        if context:
            state["memory_context"] = context
            logger.info(
                "Workflow: loaded %d chars of memory context for session=%s",
                len(context), session_id,
            )
        else:
            logger.debug("Workflow: no memory context found")

        return state
    return node


def _make_researcher_node(settings: "Settings"):
    """Create a researcher node function with bound settings."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering researcher node")
        return run_researcher(state, settings=settings)
    return node


def _make_compress_node(settings: "Settings"):
    """Create a compression node function with bound settings."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering compress node")
        return compress_research(state, settings=settings)
    return node


def _make_analyst_node(settings: "Settings"):
    """Create an analyst node function with bound settings."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering analyst node")
        return run_analyst(state, settings=settings)
    return node


def _make_writer_node(settings: "Settings"):
    """Create a writer node function with bound settings."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering writer node")
        return run_writer(state, settings=settings)
    return node


def _make_fact_checker_node(settings: "Settings"):
    """Create a fact-checker node function with bound settings."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering fact_checker node")
        return run_fact_checker(state, settings=settings)
    return node


def _make_memory_write_node(settings: "Settings"):
    """Create a memory write node that stores research output after completion."""
    def node(state: ResearchState) -> ResearchState:
        logger.info("Workflow: entering memory_write node")

        if state.get("skip_memory", False):
            logger.info("Workflow: skip_memory=True, bypassing memory write")
            return state

        session_id = state.get("session_id", "")
        if not session_id:
            logger.debug("Workflow: no session_id, skipping memory write")
            return state

        # Only write if we have meaningful output
        report = state.get("report", "")
        if not report:
            logger.debug("Workflow: no report produced, skipping memory write")
            return state

        summary = build_memory_summary(
            topic=state.get("topic", ""),
            report=report,
            analysis=state.get("analysis", ""),
        )

        success = write_memory(
            session_id=session_id,
            topic=state.get("topic", ""),
            content=summary,
            settings=settings,
        )

        if success:
            logger.info("Workflow: memory written for session=%s", session_id)
        else:
            # Non-fatal — just log
            logger.debug("Workflow: memory write skipped or failed (non-fatal)")

        return state
    return node


def build_graph(settings: "Settings | None" = None) -> StateGraph:
    """Build and return the compiled LangGraph workflow.

    The pipeline is:
        START → memory_read → researcher → compress → analyst → writer → fact_checker → memory_write → END

    Args:
        settings: Optional Settings instance. If None, loads from environment.

    Returns:
        A compiled StateGraph ready for invocation.
    """
    if settings is None:
        settings = load_settings()

    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("memory_read", _make_memory_read_node(settings))
    graph.add_node("researcher", _make_researcher_node(settings))
    graph.add_node("compress", _make_compress_node(settings))
    graph.add_node("analyst", _make_analyst_node(settings))
    graph.add_node("writer", _make_writer_node(settings))
    graph.add_node("fact_checker", _make_fact_checker_node(settings))
    graph.add_node("memory_write", _make_memory_write_node(settings))

    # Wire edges: linear pipeline with memory bookends
    graph.add_edge(START, "memory_read")
    graph.add_edge("memory_read", "researcher")
    graph.add_edge("researcher", "compress")
    graph.add_edge("compress", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", "fact_checker")
    graph.add_edge("fact_checker", "memory_write")
    graph.add_edge("memory_write", END)

    compiled = graph.compile()
    logger.info("Workflow: graph compiled successfully")
    return compiled


def run_research(
    topic: str,
    style: str = "academic",
    skip_memory: bool = False,
    session_id: str = "",
    settings: "Settings | None" = None,
) -> ResearchState:
    """Execute the full research pipeline end-to-end.

    This is the single entry point used by the FastAPI backend.

    Args:
        topic: The research topic/query.
        style: The desired writing style (academic, blog, executive summary, technical).
        skip_memory: Whether to skip Mem0 context lookup and write.
        session_id: Session identifier for memory scoping.
        settings: Optional Settings instance. If None, loads from environment.

    Returns:
        The final ResearchState with all fields populated.

    Raises:
        ValueError: If topic is empty.
    """
    if settings is None:
        settings = load_settings()

    logger.info(
        "Workflow: starting research pipeline (topic='%s', style='%s', "
        "skip_memory=%s, session_id='%s')",
        topic, style, skip_memory, session_id or "(none)",
    )

    # Create initial state
    initial_state = create_initial_state(
        topic=topic,
        style=style,
        skip_memory=skip_memory,
        session_id=session_id,
    )

    # Build and run the graph
    compiled_graph = build_graph(settings=settings)
    final_state = compiled_graph.invoke(initial_state)

    # Log summary
    num_sources = len(final_state.get("sources", []))
    num_claims = len(final_state.get("claims", []))
    num_errors = len(final_state.get("errors", []))
    has_report = bool(final_state.get("report", ""))
    has_memory = bool(final_state.get("memory_context", ""))

    logger.info(
        "Workflow: pipeline complete — sources=%d, claims=%d, errors=%d, "
        "has_report=%s, has_memory=%s",
        num_sources, num_claims, num_errors, has_report, has_memory,
    )

    if num_errors > 0:
        logger.warning(
            "Workflow: completed with %d error(s): %s",
            num_errors,
            final_state["errors"],
        )

    return final_state
