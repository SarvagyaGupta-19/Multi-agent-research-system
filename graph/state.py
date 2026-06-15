"""
ResearchState — the structured, JSON-safe contract for the research pipeline.

This TypedDict defines the shape of state that flows through every agent
in the LangGraph workflow. All agents read from and write to this contract.
"""

from typing import TypedDict


class SourceItem(TypedDict):
    """A single source reference from web research."""
    url: str
    title: str
    snippet: str


class ClaimItem(TypedDict):
    """A single fact-checked claim from the fact-checker agent."""
    claim: str
    status: str       # "verified" | "unverified" | "uncertain"
    source: str       # URL or reference
    rationale: str    # Short explanation


class ResearchState(TypedDict):
    """The full pipeline state contract.

    Every field has a defined type and purpose:
    - topic: The user's research query
    - style: Writing style (e.g., "academic", "blog", "executive summary")
    - model: The Groq LLM model selected by the user
    - skip_memory: If True, bypass Mem0 context lookup
    - session_id: Session identifier for memory scoping
    - memory_context: Prior context retrieved from Mem0 (empty if skipped)
    - raw_research: Raw concatenated search results from the researcher
    - compressed_research: Truncated/summarized research for downstream agents
    - sources: Structured list of source references
    - analysis: Analyst agent's structured analysis output
    - report: Writer agent's generated report
    - fact_checked_report: Report after fact-checking annotations
    - claims: Structured fact-check results per claim
    - errors: Accumulated error messages from any agent
    """
    topic: str
    style: str
    model: str
    skip_memory: bool
    session_id: str
    memory_context: str
    raw_research: str
    compressed_research: str
    sources: list[SourceItem]
    analysis: str
    report: str
    fact_checked_report: str
    claims: list[ClaimItem]
    errors: list[str]


def create_initial_state(
    topic: str,
    style: str = "academic",
    model: str = "llama-3.3-70b-versatile",
    skip_memory: bool = False,
    session_id: str = "",
) -> ResearchState:
    """Create a fully initialized ResearchState with empty defaults.

    Args:
        topic: The research topic/query.
        style: The desired writing style.
        model: The LLM model to use.
        skip_memory: Whether to skip Mem0 context lookup.
        session_id: Session identifier for memory scoping.

    Returns:
        A ResearchState dict with all fields initialized.

    Raises:
        ValueError: If topic is empty or whitespace-only.
    """
    if not topic or not topic.strip():
        raise ValueError("topic is required and cannot be empty or whitespace-only")

    return ResearchState(
        topic=topic.strip(),
        style=style.strip() if style else "academic",
        model=model.strip() if model else "llama-3.3-70b-versatile",
        skip_memory=skip_memory,
        session_id=session_id,
        memory_context="",
        raw_research="",
        compressed_research="",
        sources=[],
        analysis="",
        report="",
        fact_checked_report="",
        claims=[],
        errors=[],
    )


def validate_state(state: dict) -> list[str]:
    """Validate a ResearchState dict for completeness and type correctness.

    Checks that all required fields are present and have the correct types.
    Does NOT check whether fields have meaningful content — that's the
    responsibility of individual agents.

    Args:
        state: A dict to validate against the ResearchState contract.

    Returns:
        A list of violation messages. Empty list means valid.
    """
    violations = []

    # Required field type checks
    field_types = {
        "topic": str,
        "style": str,
        "model": str,
        "skip_memory": bool,
        "session_id": str,
        "memory_context": str,
        "raw_research": str,
        "compressed_research": str,
        "sources": list,
        "analysis": str,
        "report": str,
        "fact_checked_report": str,
        "claims": list,
        "errors": list,
    }

    for field_name, expected_type in field_types.items():
        if field_name not in state:
            violations.append(f"Missing required field: '{field_name}'")
        elif not isinstance(state[field_name], expected_type):
            violations.append(
                f"Field '{field_name}' expected {expected_type.__name__}, "
                f"got {type(state[field_name]).__name__}"
            )

    # Validate source items structure if sources exist and field is present
    if "sources" in state and isinstance(state["sources"], list):
        for i, source in enumerate(state["sources"]):
            if not isinstance(source, dict):
                violations.append(f"sources[{i}] must be a dict, got {type(source).__name__}")
            else:
                for key in ("url", "title", "snippet"):
                    if key not in source:
                        violations.append(f"sources[{i}] missing required key: '{key}'")

    # Validate claim items structure if claims exist and field is present
    if "claims" in state and isinstance(state["claims"], list):
        for i, claim in enumerate(state["claims"]):
            if not isinstance(claim, dict):
                violations.append(f"claims[{i}] must be a dict, got {type(claim).__name__}")
            else:
                for key in ("claim", "status", "source", "rationale"):
                    if key not in claim:
                        violations.append(f"claims[{i}] missing required key: '{key}'")
                if "status" in claim and claim["status"] not in (
                    "verified", "unverified", "uncertain"
                ):
                    violations.append(
                        f"claims[{i}] status must be 'verified', 'unverified', "
                        f"or 'uncertain', got '{claim['status']}'"
                    )

    return violations
