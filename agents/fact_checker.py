"""
Fact-checker agent — verifies claims in the writer's report against sources.

Uses a two-pass LLM approach:
1. Extract verifiable claims from the report as structured JSON.
2. Verify each claim against source data, producing ClaimItem output.

Computes a trust score and annotates the report with verification results.
Failures are non-fatal: appends to errors, leaves report unchanged.
"""

import json
import logging
from typing import TYPE_CHECKING

from agents.llm_client import call_llm
from utils.truncation import truncate_text
from graph.state import ResearchState, ClaimItem

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)


# --- System prompts ---

_EXTRACT_SYSTEM_PROMPT = """You are a fact-checking assistant. Your task is to extract verifiable factual claims from a research report.

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.

Return a JSON object with a single key "claims" containing an array of strings.
Each string should be a single, specific, verifiable factual claim from the report.

Rules:
- Extract only factual claims (not opinions, style choices, or subjective statements).
- Each claim should be self-contained and understandable without the full report.
- Extract 5-15 key claims. Prioritize the most important or specific claims.
- Do not duplicate claims.

Example output:
{"claims": ["Quantum computers can factor large numbers exponentially faster than classical computers", "Google achieved quantum supremacy in 2019 with a 53-qubit processor"]}
"""

_VERIFY_SYSTEM_PROMPT = """You are a rigorous fact-checker. Your task is to verify factual claims against provided source data.

You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.

For each claim, determine its status based on the source data:
- "verified": The claim is directly supported by the source data.
- "unverified": The claim contradicts the source data or has no supporting evidence.
- "uncertain": The source data partially supports the claim or is ambiguous.

Return a JSON object with a single key "results" containing an array of objects, each with:
- "claim": The original claim text (exact copy)
- "status": One of "verified", "unverified", "uncertain"
- "source": The URL or title of the most relevant source (or "N/A" if none)
- "rationale": A brief 1-2 sentence explanation of your verdict

Example output:
{"results": [{"claim": "Example claim", "status": "verified", "source": "https://example.com", "rationale": "Source directly states this fact."}]}
"""


def _extract_claims(report: str, settings: "Settings | None" = None) -> list[str]:
    """Extract verifiable claims from a report using LLM with JSON mode.

    Args:
        report: The writer's report text.
        settings: Optional Settings instance.

    Returns:
        List of claim strings. Empty list on failure.
    """
    prompt = (
        f"Extract the key verifiable factual claims from this research report.\n\n"
        f"--- Report ---\n{report}\n\n"
        f"Respond with JSON only."
    )

    raw = call_llm(
        prompt=prompt,
        system_prompt=_EXTRACT_SYSTEM_PROMPT,
        temperature=0.1,  # low temp for extraction accuracy
        settings=settings,
        json_mode=True,
    )

    if not raw:
        logger.error("Fact-checker: LLM returned empty response for claim extraction")
        return []

    try:
        data = json.loads(raw)
        claims = data.get("claims", [])
        if not isinstance(claims, list):
            logger.error("Fact-checker: 'claims' is not a list: %s", type(claims))
            return []
        # Filter out non-string entries
        return [c for c in claims if isinstance(c, str) and c.strip()]
    except json.JSONDecodeError as e:
        logger.error("Fact-checker: failed to parse claim extraction JSON: %s", e)
        return []


def _verify_claims(
    claims: list[str],
    sources_text: str,
    settings: "Settings | None" = None,
) -> list[ClaimItem]:
    """Verify claims against source data using LLM with JSON mode.

    Args:
        claims: List of claim strings to verify.
        sources_text: Concatenated source data for cross-reference.
        settings: Optional Settings instance.

    Returns:
        List of ClaimItem dicts. Empty list on failure.
    """
    claims_formatted = "\n".join(f"- {c}" for c in claims)

    prompt = (
        f"Verify each of the following claims against the source data provided.\n\n"
        f"--- Claims to verify ---\n{claims_formatted}\n\n"
        f"--- Source Data ---\n{sources_text}\n\n"
        f"Respond with JSON only."
    )

    raw = call_llm(
        prompt=prompt,
        system_prompt=_VERIFY_SYSTEM_PROMPT,
        temperature=0.1,
        settings=settings,
        json_mode=True,
    )

    if not raw:
        logger.error("Fact-checker: LLM returned empty response for claim verification")
        return []

    try:
        data = json.loads(raw)
        results = data.get("results", [])
        if not isinstance(results, list):
            logger.error("Fact-checker: 'results' is not a list: %s", type(results))
            return []
    except json.JSONDecodeError as e:
        logger.error("Fact-checker: failed to parse verification JSON: %s", e)
        return []

    # Normalize and validate each result into ClaimItem format
    verified_claims: list[ClaimItem] = []
    valid_statuses = {"verified", "unverified", "uncertain"}

    for item in results:
        if not isinstance(item, dict):
            continue

        status = str(item.get("status", "uncertain")).lower()
        if status not in valid_statuses:
            status = "uncertain"

        verified_claims.append(ClaimItem(
            claim=str(item.get("claim", "")),
            status=status,
            source=str(item.get("source", "N/A")),
            rationale=str(item.get("rationale", "")),
        ))

    return verified_claims


def _compute_trust_score(claims: list[ClaimItem]) -> float:
    """Compute trust score as ratio of verified claims to total claims.

    Args:
        claims: List of verified ClaimItem dicts.

    Returns:
        Trust score between 0.0 and 1.0. Returns 0.0 if no claims.
    """
    if not claims:
        return 0.0

    verified = sum(1 for c in claims if c["status"] == "verified")
    return round(verified / len(claims), 2)


def _build_sources_text(state: ResearchState, max_chars: int = 12000) -> str:
    """Build a text representation of sources for verification.

    Combines source snippets and raw research data, truncated to max_chars.

    Args:
        state: The current ResearchState.
        max_chars: Maximum characters for the source text.

    Returns:
        Formatted source text string.
    """
    parts = []

    # Add source snippets
    for src in state.get("sources", []):
        parts.append(
            f"Source: {src.get('title', 'Untitled')} ({src.get('url', 'N/A')})\n"
            f"{src.get('snippet', '')}\n"
        )

    # Add compressed or raw research
    research = state.get("compressed_research", "") or state.get("raw_research", "")
    if research:
        parts.append(f"--- Full Research Context ---\n{research}")

    combined = "\n".join(parts)
    if len(combined) > max_chars:
        combined = truncate_text(combined, max_chars, strategy="tail")

    return combined


def run_fact_checker(
    state: ResearchState,
    settings: "Settings | None" = None,
) -> ResearchState:
    """Fact-check the generated report against source data.

    Two-pass process:
    1. Extract verifiable claims from the report.
    2. Verify each claim against source data.

    Populates state with:
    - claims: List of ClaimItem dicts with verification results.
    - fact_checked_report: JSON string with report, claims, and trust_score.

    Args:
        state: The current ResearchState with report populated.
        settings: Optional Settings instance for LLM configuration.

    Returns:
        Updated ResearchState with fact-check results.
        On failure, appends error and leaves state unchanged.
    """
    report = state.get("report", "")

    if not report:
        error_msg = "Fact-checker: no report available to fact-check"
        state["errors"].append(error_msg)
        logger.warning(error_msg)
        return state

    logger.info("Fact-checker: starting fact-check of report (%d chars)", len(report))

    # --- Pass 1: Extract claims ---
    raw_claims = _extract_claims(report, settings=settings)

    if not raw_claims:
        error_msg = "Fact-checker: could not extract any claims from the report"
        state["errors"].append(error_msg)
        logger.warning(error_msg)
        # Still return a valid state with empty claims
        state["claims"] = []
        state["fact_checked_report"] = json.dumps({
            "report": report,
            "claims": [],
            "trust_score": 0.0,
        })
        return state

    logger.info("Fact-checker: extracted %d claims", len(raw_claims))

    # --- Pass 2: Verify claims ---
    sources_text = _build_sources_text(state)
    verified_claims = _verify_claims(raw_claims, sources_text, settings=settings)

    if not verified_claims:
        # Verification failed but extraction succeeded — create uncertain claims
        error_msg = "Fact-checker: claim verification failed, marking all as uncertain"
        state["errors"].append(error_msg)
        logger.warning(error_msg)
        verified_claims = [
            ClaimItem(
                claim=c,
                status="uncertain",
                source="N/A",
                rationale="Verification failed due to an internal error.",
            )
            for c in raw_claims
        ]

    trust_score = _compute_trust_score(verified_claims)

    state["claims"] = verified_claims
    state["fact_checked_report"] = json.dumps({
        "report": report,
        "claims": verified_claims,
        "trust_score": trust_score,
    })

    logger.info(
        "Fact-checker: completed — %d claims, trust_score=%.2f",
        len(verified_claims),
        trust_score,
    )

    return state
