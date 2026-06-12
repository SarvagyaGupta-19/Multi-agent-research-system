"""
Tests for the fact-checker agent.

Tests claim extraction, verification, trust score computation,
and error handling with mocked LLM calls.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from agents.fact_checker import (
    run_fact_checker,
    _extract_claims,
    _verify_claims,
    _compute_trust_score,
    _build_sources_text,
)
from graph.state import create_initial_state


# --- Fixtures ---

@pytest.fixture
def state_with_report():
    """Create a ResearchState with report and sources populated."""
    state = create_initial_state(topic="quantum computing")
    state["report"] = (
        "Quantum computing uses qubits. "
        "Google achieved quantum supremacy in 2019. "
        "IBM has a 1000+ qubit processor."
    )
    state["sources"] = [
        {"url": "https://example.com/quantum", "title": "Quantum Overview", "snippet": "Quantum computing uses qubits for computation."},
        {"url": "https://example.com/google", "title": "Google Quantum", "snippet": "Google demonstrated quantum supremacy in 2019."},
    ]
    state["raw_research"] = "Quantum computing uses qubits for advanced computation."
    state["compressed_research"] = state["raw_research"]
    return state


@pytest.fixture
def mock_settings():
    """Create a mock Settings instance."""
    settings = MagicMock()
    settings.GROQ_API_KEY = "test-key"
    settings.GROQ_MODEL = "test-model"
    settings.GROQ_TIMEOUT = 30
    settings.GROQ_MAX_RETRIES = 1
    settings.MAX_CONTEXT_CHARS = 16000
    return settings


# --- _extract_claims tests ---

class TestExtractClaims:
    """Tests for claim extraction."""

    @patch("agents.fact_checker.call_llm")
    def test_extracts_claims_successfully(self, mock_llm, mock_settings):
        mock_llm.return_value = json.dumps({
            "claims": [
                "Quantum computing uses qubits",
                "Google achieved quantum supremacy in 2019",
            ]
        })

        claims = _extract_claims("test report", settings=mock_settings)

        assert len(claims) == 2
        assert "Quantum computing uses qubits" in claims
        mock_llm.assert_called_once()
        # Verify json_mode was passed
        _, kwargs = mock_llm.call_args
        assert kwargs.get("json_mode") is True

    @patch("agents.fact_checker.call_llm")
    def test_returns_empty_on_llm_failure(self, mock_llm, mock_settings):
        mock_llm.return_value = ""

        claims = _extract_claims("test report", settings=mock_settings)

        assert claims == []

    @patch("agents.fact_checker.call_llm")
    def test_returns_empty_on_invalid_json(self, mock_llm, mock_settings):
        mock_llm.return_value = "not valid json {{"

        claims = _extract_claims("test report", settings=mock_settings)

        assert claims == []

    @patch("agents.fact_checker.call_llm")
    def test_returns_empty_on_missing_claims_key(self, mock_llm, mock_settings):
        mock_llm.return_value = json.dumps({"data": ["claim1"]})

        claims = _extract_claims("test report", settings=mock_settings)

        assert claims == []

    @patch("agents.fact_checker.call_llm")
    def test_filters_non_string_claims(self, mock_llm, mock_settings):
        mock_llm.return_value = json.dumps({
            "claims": ["valid claim", 123, None, "", "another valid"]
        })

        claims = _extract_claims("test report", settings=mock_settings)

        assert len(claims) == 2
        assert "valid claim" in claims
        assert "another valid" in claims


# --- _verify_claims tests ---

class TestVerifyClaims:
    """Tests for claim verification."""

    @patch("agents.fact_checker.call_llm")
    def test_verifies_claims_successfully(self, mock_llm, mock_settings):
        mock_llm.return_value = json.dumps({
            "results": [
                {
                    "claim": "Test claim",
                    "status": "verified",
                    "source": "https://example.com",
                    "rationale": "Supported by source data.",
                }
            ]
        })

        results = _verify_claims(["Test claim"], "source data", settings=mock_settings)

        assert len(results) == 1
        assert results[0]["status"] == "verified"
        assert results[0]["claim"] == "Test claim"

    @patch("agents.fact_checker.call_llm")
    def test_normalizes_invalid_status(self, mock_llm, mock_settings):
        mock_llm.return_value = json.dumps({
            "results": [
                {
                    "claim": "Test claim",
                    "status": "INVALID_STATUS",
                    "source": "N/A",
                    "rationale": "Unknown.",
                }
            ]
        })

        results = _verify_claims(["Test claim"], "source data", settings=mock_settings)

        assert len(results) == 1
        assert results[0]["status"] == "uncertain"

    @patch("agents.fact_checker.call_llm")
    def test_returns_empty_on_llm_failure(self, mock_llm, mock_settings):
        mock_llm.return_value = ""

        results = _verify_claims(["Test claim"], "source data", settings=mock_settings)

        assert results == []


# --- _compute_trust_score tests ---

class TestComputeTrustScore:
    """Tests for trust score computation."""

    def test_all_verified(self):
        claims = [
            {"claim": "c1", "status": "verified", "source": "", "rationale": ""},
            {"claim": "c2", "status": "verified", "source": "", "rationale": ""},
        ]
        assert _compute_trust_score(claims) == 1.0

    def test_none_verified(self):
        claims = [
            {"claim": "c1", "status": "unverified", "source": "", "rationale": ""},
            {"claim": "c2", "status": "uncertain", "source": "", "rationale": ""},
        ]
        assert _compute_trust_score(claims) == 0.0

    def test_mixed(self):
        claims = [
            {"claim": "c1", "status": "verified", "source": "", "rationale": ""},
            {"claim": "c2", "status": "unverified", "source": "", "rationale": ""},
            {"claim": "c3", "status": "verified", "source": "", "rationale": ""},
            {"claim": "c4", "status": "uncertain", "source": "", "rationale": ""},
        ]
        assert _compute_trust_score(claims) == 0.5

    def test_empty_claims(self):
        assert _compute_trust_score([]) == 0.0


# --- _build_sources_text tests ---

class TestBuildSourcesText:
    """Tests for source text building."""

    def test_builds_from_sources_and_research(self, state_with_report):
        text = _build_sources_text(state_with_report)

        assert "Quantum Overview" in text
        assert "example.com/quantum" in text
        assert "Quantum computing uses qubits" in text

    def test_handles_empty_sources(self):
        state = create_initial_state(topic="test")
        text = _build_sources_text(state)

        assert text == ""

    def test_truncates_when_too_long(self, state_with_report):
        text = _build_sources_text(state_with_report, max_chars=50)

        assert len(text) <= 80  # 50 + truncation marker


# --- run_fact_checker integration tests ---

class TestRunFactChecker:
    """Tests for the full fact-checker pipeline."""

    @patch("agents.fact_checker.call_llm")
    def test_full_pipeline_success(self, mock_llm, state_with_report, mock_settings):
        # First call: extraction, second call: verification
        mock_llm.side_effect = [
            json.dumps({"claims": ["Qubits are used", "Google 2019"]}),
            json.dumps({
                "results": [
                    {"claim": "Qubits are used", "status": "verified", "source": "https://example.com", "rationale": "Confirmed."},
                    {"claim": "Google 2019", "status": "verified", "source": "https://example.com/google", "rationale": "Confirmed."},
                ]
            }),
        ]

        result = run_fact_checker(state_with_report, settings=mock_settings)

        assert len(result["claims"]) == 2
        assert all(c["status"] == "verified" for c in result["claims"])
        assert result["fact_checked_report"]  # non-empty

        # Parse fact_checked_report
        fc_data = json.loads(result["fact_checked_report"])
        assert fc_data["trust_score"] == 1.0
        assert len(fc_data["claims"]) == 2

    def test_no_report_returns_error(self, mock_settings):
        state = create_initial_state(topic="test")

        result = run_fact_checker(state, settings=mock_settings)

        assert "no report available" in result["errors"][-1]

    @patch("agents.fact_checker.call_llm")
    def test_extraction_failure_returns_empty_claims(self, mock_llm, state_with_report, mock_settings):
        mock_llm.return_value = ""  # Both calls fail

        result = run_fact_checker(state_with_report, settings=mock_settings)

        assert result["claims"] == []
        assert any("could not extract" in e for e in result["errors"])

    @patch("agents.fact_checker.call_llm")
    def test_verification_failure_marks_uncertain(self, mock_llm, state_with_report, mock_settings):
        # Extraction succeeds, verification fails
        mock_llm.side_effect = [
            json.dumps({"claims": ["Test claim"]}),
            "",  # Verification fails
        ]

        result = run_fact_checker(state_with_report, settings=mock_settings)

        assert len(result["claims"]) == 1
        assert result["claims"][0]["status"] == "uncertain"
        assert any("verification failed" in e for e in result["errors"])
