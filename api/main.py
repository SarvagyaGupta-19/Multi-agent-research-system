"""
FastAPI backend — exposes the research pipeline as a REST API.

Endpoints:
- POST /research       — Create a research job (returns job_id)
- GET  /research/{id}  — Get job status and result
- GET  /health         — Health check

Jobs run in background threads and results are persisted in SQLite.
"""

import logging
import threading
import traceback
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.job_store import JobStore
from config import load_settings
from graph.workflow import run_research

logger = logging.getLogger(__name__)

# --- App setup ---

app = FastAPI(
    title="Multi-Agent Research System",
    description="A 4-agent autonomous research pipeline with structured fact-checking and trust scoring.",
    version="0.3.0",
)

# Load settings on startup to configure the app and fail fast if keys are missing
try:
    settings = load_settings()
    allowed_origins = settings.ALLOWED_ORIGINS
except Exception as e:
    logger.warning("Failed to load settings on startup for CORS: %s. Defaulting to localhost.", e)
    allowed_origins = ["http://localhost:3000"]

# CORS — secured via config
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared job store (initialized on startup)
_job_store: JobStore | None = None


def _get_store() -> JobStore:
    """Get the global JobStore instance, creating it if needed."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store


# --- Pydantic models ---

class ResearchRequest(BaseModel):
    """Request body for POST /research."""
    topic: str = Field(..., min_length=1, max_length=500, description="The research topic/query.")
    style: str = Field(
        default="academic",
        description="Writing style: academic, blog, executive summary, or technical.",
    )
    model: str = Field(
        default="llama-3.3-70b-versatile",
        description="The Groq LLM model to use.",
    )
    skip_memory: bool = Field(default=False, description="If true, skip Mem0 context lookup.")
    session_id: str = Field(default="", description="Session ID for memory scoping.")


class JobCreatedResponse(BaseModel):
    """Response body for POST /research."""
    job_id: str
    status: str = "queued"
    message: str = "Research job created successfully."


class JobStatusResponse(BaseModel):
    """Response body for GET /research/{job_id}."""
    job_id: str
    status: str
    topic: str
    style: str
    created_at: str
    updated_at: str
    result: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str = "ok"
    version: str = "0.3.0"


# --- Background worker ---

def _run_research_worker(
    job_id: str, topic: str, style: str, model: str, skip_memory: bool, session_id: str,
) -> None:
    """Background worker that runs the research pipeline for a job.

    Updates job status and result/error in the store.

    Args:
        job_id: The job ID to update.
        topic: Research topic.
        style: Writing style.
        model: The Groq model to use.
        skip_memory: Whether to skip memory lookup.
        session_id: Session ID for memory scoping.
    """
    store = _get_store()

    try:
        store.update_status(job_id, "running")
        logger.info("Worker: starting research for job %s (topic='%s', model='%s')", job_id, topic, model)

        settings = load_settings()
        result = run_research(
            topic=topic,
            style=style,
            model=model,
            skip_memory=skip_memory,
            session_id=session_id,
            settings=settings,
        )

        # Convert TypedDict to regular dict for JSON serialization
        result_dict = dict(result)
        store.update_result(job_id, result_dict)

        logger.info("Worker: completed job %s", job_id)

    except Exception as e:
        if "Rate Limit Exceeded" in str(e):
            error_msg = str(e)
        else:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        store.update_error(job_id, error_msg)
        logger.error("Worker: job %s failed: %s", job_id, error_msg)


# --- Startup event ---

@app.on_event("startup")
async def startup_event():
    """Initialize the job store on app startup."""
    global _job_store
    _job_store = JobStore()
    logger.info("API: startup complete, job store initialized")


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/research", response_model=JobCreatedResponse, status_code=202)
async def create_research_job(request: ResearchRequest):
    """Create a new research job.

    The job runs asynchronously in a background thread.
    Use GET /research/{job_id} to poll for status and results.

    Returns:
        202 Accepted with job_id and queued status.
    """
    store = _get_store()

    # Validate topic
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty or whitespace.")

    # Create job in store
    job_id = store.create_job(
        topic=topic,
        style=request.style,
        session_id=request.session_id,
    )

    # Launch background worker
    worker = threading.Thread(
        target=_run_research_worker,
        args=(job_id, topic, request.style, request.model, request.skip_memory, request.session_id),
        daemon=True,
        name=f"research-worker-{job_id[:8]}",
    )
    worker.start()

    logger.info("API: created job %s, worker launched", job_id)

    return JobCreatedResponse(job_id=job_id)


@app.get("/research/{job_id}", response_model=JobStatusResponse)
async def get_research_job(job_id: str):
    """Get the status and result of a research job.

    Returns:
        200 with job status, result (if complete), or error (if failed).
        404 if job_id not found.
    """
    store = _get_store()
    job = store.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        topic=job["topic"],
        style=job["style"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        result=job.get("result"),
        error=job.get("error"),
    )
