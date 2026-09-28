"""
FastAPI backend — exposes the research pipeline as a REST API.

Endpoints:
- POST   /research       — Create a research job (returns job_id)
- GET    /research/{id}  — Get job status and result
- DELETE /research/{id}  — Cancel a running job         [BP-02]
- GET    /health         — Health check

Jobs run in a bounded ThreadPoolExecutor (max 5 concurrent).  [BP-01]
"""

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor  # BP-01: bounded thread pool
from contextlib import asynccontextmanager           # BP-18: modern lifespan
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.job_store import JobStore
from config import load_settings
from graph.workflow import run_research

logger = logging.getLogger(__name__)

# BP-01: Bounded thread pool — max 5 concurrent research jobs.
# Prevents unbounded thread spawning under load.
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="research-worker")

# BP-18: Modern lifespan replaces deprecated @app.on_event("startup")
@asynccontextmanager
async def lifespan(app_instance: "FastAPI"):
    """Initialize shared resources on startup, clean up on shutdown."""
    global _job_store
    _job_store = JobStore()
    logger.info("API: startup complete, job store initialized (lifespan)")
    yield
    # Graceful shutdown: stop accepting new jobs, wait for running ones
    _executor.shutdown(wait=False)
    logger.info("API: shutdown complete")


# --- App setup ---

app = FastAPI(
    title="Multi-Agent Research System",
    description="A 4-agent autonomous research pipeline with structured fact-checking and trust scoring.",
    version="0.3.0",
    lifespan=lifespan,  # BP-18: use lifespan instead of on_event
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

# BP-09: Valid style and model values as Literal types to prevent arbitrary strings
# reaching the Groq SDK (which would cause BadRequestError crashes).
ALLOWED_STYLES = Literal["academic", "blog", "executive summary", "technical", "summary"]
ALLOWED_MODELS = Literal[
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


class ResearchRequest(BaseModel):
    """Request body for POST /research."""
    topic: str = Field(..., min_length=1, max_length=500, description="The research topic/query.")
    style: ALLOWED_STYLES = Field(
        default="academic",
        description="Writing style: academic, blog, executive summary, technical, or summary.",
    )
    model: ALLOWED_MODELS = Field(
        default="qwen/qwen3.8-27b",
        description="The Groq LLM model to use.",
    )
    skip_memory: bool = Field(default=False, description="If true, skip Mem0 context lookup.")
    session_id: str = Field(default="", max_length=128, description="Session ID for memory scoping.")


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

    Checks for cancellation (BP-02) before starting and marks job as
    cancelled if flagged. Runs inside a bounded ThreadPoolExecutor (BP-01).

    Args:
        job_id: The job ID to update.
        topic: Research topic.
        style: Writing style.
        model: The Groq model to use.
        skip_memory: Whether to skip memory lookup.
        session_id: Session ID for memory scoping.
    """
    store = _get_store()

    # BP-02: Check for pre-start cancellation (user cancelled before worker dequeued)
    if store.is_cancelled(job_id):
        logger.info("Worker: job %s was cancelled before starting, skipping", job_id)
        return

    try:
        store.update_status(job_id, "running")
        logger.info("Worker: starting research for job %s (topic='%s', model='%s')", job_id, topic, model)

        settings = load_settings()

        # BP-02: Check cancellation again before the long pipeline call
        if store.is_cancelled(job_id):
            logger.info("Worker: job %s cancelled mid-start, aborting", job_id)
            return

        result = run_research(
            topic=topic,
            style=style,
            model=model,
            skip_memory=skip_memory,
            session_id=session_id,
            settings=settings,
        )

        # BP-02: Final cancellation check before storing result
        if store.is_cancelled(job_id):
            logger.info("Worker: job %s cancelled post-pipeline, discarding result", job_id)
            return

        # Convert TypedDict to regular dict for JSON serialization
        result_dict = dict(result)
        store.update_result(job_id, result_dict)

        logger.info("Worker: completed job %s", job_id)

    except Exception as e:
        # Don't overwrite a cancelled status with failed
        if store.is_cancelled(job_id):
            logger.info("Worker: job %s was cancelled, ignoring exception: %s", job_id, e)
            return
        err_str = str(e)
        if "Rate Limit Exceeded" in err_str or "Bad Request" in err_str:
            error_msg = err_str
        else:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        store.update_error(job_id, error_msg)
        logger.error("Worker: job %s failed: %s", job_id, error_msg)


# Removed: @app.on_event("startup") — BP-18: replaced with lifespan context manager above

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

    # BP-01: Submit to bounded ThreadPoolExecutor instead of raw Thread
    _executor.submit(
        _run_research_worker,
        job_id, topic, request.style, request.model, request.skip_memory, request.session_id,
    )

    logger.info("API: created job %s, submitted to thread pool", job_id)

    return JobCreatedResponse(job_id=job_id)


@app.delete("/research/{job_id}", status_code=200)  # BP-02: Cancel endpoint
async def cancel_research_job(job_id: str):
    """Cancel a queued or running research job.

    Marks the job as 'cancelled' in the store. The background worker
    checks this flag and exits early. The LLM pipeline call itself
    cannot be interrupted mid-call, but all subsequent stages are skipped.

    Returns:
        200 with confirmation, or 404 if not found, 409 if already terminal.
    """
    store = _get_store()
    cancelled = store.cancel_job(job_id)

    if not cancelled:
        job = store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is already in terminal state '{job['status']}' and cannot be cancelled.",
        )

    logger.info("API: cancelled job %s", job_id)
    return {"job_id": job_id, "status": "cancelled", "message": "Job cancellation requested."}


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
