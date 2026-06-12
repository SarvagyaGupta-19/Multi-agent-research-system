"""
Fact-checker agent — stub for Day 3 implementation.

Will verify claims in the writer's report against sources
and produce structured fact-check results.
"""

import logging
from graph.state import ResearchState

logger = logging.getLogger(__name__)


def run_fact_checker(state: ResearchState) -> ResearchState:
    """Stub: fact-check the generated report.

    TODO (Day 3): Implement structured claim verification with:
    - Claim extraction from report
    - Source-based verification
    - Structured ClaimItem output
    - Trust score computation

    Args:
        state: The current ResearchState with report populated.

    Returns:
        Updated ResearchState (currently passes through unchanged).
    """
    logger.warning("Fact-checker: not yet implemented (Day 3)")
    return state
