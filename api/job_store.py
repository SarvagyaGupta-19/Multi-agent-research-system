"""
SQLite-backed persistent job storage for the research API.

Stores job state (status, result, errors) in a local SQLite database
so that jobs survive backend restarts. Thread-safe for use with
background worker threads.
"""

import contextlib
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default DB path — relative to project root
_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "jobs.db"

# Valid job statuses
VALID_STATUSES = {"queued", "running", "complete", "failed"}


class JobStore:
    """Thread-safe SQLite job storage.

    Manages the lifecycle of research jobs:
    create → update status → store result or error.

    Args:
        db_path: Path to the SQLite database file.
            Parent directories are created automatically.
    """

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Create the jobs table if it doesn't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(self._get_conn()) as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id      TEXT PRIMARY KEY,
                        status      TEXT NOT NULL DEFAULT 'queued',
                        topic       TEXT NOT NULL,
                        style       TEXT NOT NULL DEFAULT 'academic',
                        session_id  TEXT NOT NULL DEFAULT '',
                        created_at  TEXT NOT NULL,
                        updated_at  TEXT NOT NULL,
                        result_json TEXT DEFAULT NULL,
                        error       TEXT DEFAULT NULL
                    )
                """)
        logger.info("JobStore: initialized at %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection (thread-safe mode)."""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        """Return current UTC time as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def create_job(
        self,
        topic: str,
        style: str = "academic",
        session_id: str = "",
    ) -> str:
        """Create a new job and return its ID.

        Args:
            topic: The research topic.
            style: The writing style.
            session_id: Optional session ID for memory scoping.

        Returns:
            The generated job_id (UUID4 string).
        """
        job_id = str(uuid.uuid4())
        now = self._now()

        with self._lock:
            with contextlib.closing(self._get_conn()) as conn:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO jobs (job_id, status, topic, style, session_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (job_id, "queued", topic, style, session_id, now, now),
                    )

        logger.info("JobStore: created job %s (topic='%s')", job_id, topic)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve a job by ID.

        Args:
            job_id: The job ID to look up.

        Returns:
            A dict with job fields, or None if not found.
            If result_json is present, it's parsed back to a dict.
        """
        with self._lock:
            with contextlib.closing(self._get_conn()) as conn:
                with conn:
                    row = conn.execute(
                        "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
                    ).fetchone()

        if row is None:
            return None

        job = dict(row)

        # Parse result_json back to dict if present
        if job.get("result_json"):
            try:
                job["result"] = json.loads(job["result_json"])
            except json.JSONDecodeError:
                job["result"] = None
                logger.warning("JobStore: failed to parse result_json for job %s", job_id)
        else:
            job["result"] = None

        return job

    def update_status(self, job_id: str, status: str) -> bool:
        """Update the status of a job.

        Args:
            job_id: The job ID to update.
            status: New status (queued, running, complete, failed).

        Returns:
            True if the job was found and updated, False otherwise.

        Raises:
            ValueError: If status is not valid.
        """
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}"
            )

        with self._lock:
            with contextlib.closing(self._get_conn()) as conn:
                with conn:
                    cursor = conn.execute(
                        "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                        (status, self._now(), job_id),
                    )
                    updated = cursor.rowcount > 0

        if updated:
            logger.info("JobStore: updated job %s status to '%s'", job_id, status)
        else:
            logger.warning("JobStore: job %s not found for status update", job_id)

        return updated

    def update_result(self, job_id: str, result: dict) -> bool:
        """Store the final result for a job and mark it complete.

        Args:
            job_id: The job ID to update.
            result: The result dict (ResearchState) to store as JSON.

        Returns:
            True if the job was found and updated, False otherwise.
        """
        result_json = json.dumps(result, default=str)

        with self._lock:
            with contextlib.closing(self._get_conn()) as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'complete', result_json = ?, updated_at = ?
                        WHERE job_id = ?
                        """,
                        (result_json, self._now(), job_id),
                    )
                    updated = cursor.rowcount > 0

        if updated:
            logger.info("JobStore: stored result for job %s", job_id)
        return updated

    def update_error(self, job_id: str, error: str) -> bool:
        """Store an error for a job and mark it failed.

        Args:
            job_id: The job ID to update.
            error: The error message string.

        Returns:
            True if the job was found and updated, False otherwise.
        """
        with self._lock:
            with contextlib.closing(self._get_conn()) as conn:
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'failed', error = ?, updated_at = ?
                        WHERE job_id = ?
                        """,
                        (error, self._now(), job_id),
                    )
                    updated = cursor.rowcount > 0

        if updated:
            logger.info("JobStore: stored error for job %s", job_id)
        return updated
