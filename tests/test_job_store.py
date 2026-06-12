"""
Tests for the SQLite job store.

Tests CRUD operations, persistence, and edge cases.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from api.job_store import JobStore, VALID_STATUSES


# --- Fixtures ---

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_jobs.db"


@pytest.fixture
def store(temp_db_path):
    """Create a JobStore with a temporary database."""
    return JobStore(db_path=temp_db_path)


# --- Creation tests ---

class TestCreateJob:
    """Tests for job creation."""

    def test_creates_job_with_id(self, store):
        job_id = store.create_job(topic="test topic")
        assert job_id
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUID4 format

    def test_creates_job_with_defaults(self, store):
        job_id = store.create_job(topic="test topic")
        job = store.get_job(job_id)

        assert job is not None
        assert job["status"] == "queued"
        assert job["topic"] == "test topic"
        assert job["style"] == "academic"
        assert job["session_id"] == ""
        assert job["result"] is None
        assert job["error"] is None

    def test_creates_job_with_custom_values(self, store):
        job_id = store.create_job(
            topic="AI research",
            style="blog",
            session_id="session-123",
        )
        job = store.get_job(job_id)

        assert job["topic"] == "AI research"
        assert job["style"] == "blog"
        assert job["session_id"] == "session-123"

    def test_creates_unique_ids(self, store):
        id1 = store.create_job(topic="topic1")
        id2 = store.create_job(topic="topic2")
        assert id1 != id2


# --- Retrieval tests ---

class TestGetJob:
    """Tests for job retrieval."""

    def test_returns_none_for_nonexistent(self, store):
        assert store.get_job("nonexistent-id") is None

    def test_retrieves_created_job(self, store):
        job_id = store.create_job(topic="test")
        job = store.get_job(job_id)

        assert job is not None
        assert job["job_id"] == job_id
        assert job["topic"] == "test"

    def test_has_timestamps(self, store):
        job_id = store.create_job(topic="test")
        job = store.get_job(job_id)

        assert job["created_at"]
        assert job["updated_at"]


# --- Status update tests ---

class TestUpdateStatus:
    """Tests for status updates."""

    def test_updates_status(self, store):
        job_id = store.create_job(topic="test")

        result = store.update_status(job_id, "running")
        assert result is True

        job = store.get_job(job_id)
        assert job["status"] == "running"

    def test_rejects_invalid_status(self, store):
        job_id = store.create_job(topic="test")

        with pytest.raises(ValueError, match="Invalid status"):
            store.update_status(job_id, "invalid_status")

    def test_returns_false_for_nonexistent(self, store):
        result = store.update_status("nonexistent", "running")
        assert result is False

    def test_all_valid_statuses(self, store):
        for status in VALID_STATUSES:
            job_id = store.create_job(topic=f"test-{status}")
            result = store.update_status(job_id, status)
            assert result is True

            job = store.get_job(job_id)
            assert job["status"] == status


# --- Result storage tests ---

class TestUpdateResult:
    """Tests for result storage."""

    def test_stores_result_and_marks_complete(self, store):
        job_id = store.create_job(topic="test")
        result_data = {
            "topic": "test",
            "report": "Test report content",
            "claims": [{"claim": "test", "status": "verified", "source": "url", "rationale": "ok"}],
        }

        success = store.update_result(job_id, result_data)
        assert success is True

        job = store.get_job(job_id)
        assert job["status"] == "complete"
        assert job["result"] is not None
        assert job["result"]["report"] == "Test report content"
        assert len(job["result"]["claims"]) == 1

    def test_returns_false_for_nonexistent(self, store):
        result = store.update_result("nonexistent", {"data": "test"})
        assert result is False


# --- Error storage tests ---

class TestUpdateError:
    """Tests for error storage."""

    def test_stores_error_and_marks_failed(self, store):
        job_id = store.create_job(topic="test")

        success = store.update_error(job_id, "Something went wrong")
        assert success is True

        job = store.get_job(job_id)
        assert job["status"] == "failed"
        assert job["error"] == "Something went wrong"

    def test_returns_false_for_nonexistent(self, store):
        result = store.update_error("nonexistent", "error")
        assert result is False


# --- Persistence tests ---

class TestPersistence:
    """Tests for data persistence across re-initialization."""

    def test_survives_reinitialization(self, temp_db_path):
        """Jobs should persist when a new JobStore is created with the same DB."""
        store1 = JobStore(db_path=temp_db_path)
        job_id = store1.create_job(topic="persistent topic")
        store1.update_result(job_id, {"report": "test report"})

        # Create a NEW store pointing to the same DB
        store2 = JobStore(db_path=temp_db_path)
        job = store2.get_job(job_id)

        assert job is not None
        assert job["topic"] == "persistent topic"
        assert job["status"] == "complete"
        assert job["result"]["report"] == "test report"
