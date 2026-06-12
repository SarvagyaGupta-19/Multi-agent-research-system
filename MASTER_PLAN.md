# Multi-Agent Research System — Master Plan v2
**Stack:** LangGraph + Groq + Tavily + Mem0 + Streamlit + AWS EC2 + FastAPI
**Duration:** 7 Days
**Goal:** A public, deploy-safe multi-agent research pipeline with memory, a clean API boundary, and zero last-minute deployment surprises.

---

## 0. Core Principle

> Deploy-shaped from Day 1, not patched on Day 6.

The plan is built around four engineering rules:

- Keep the frontend thin and stateless.
- Keep the backend as the single source of truth.
- Use structured outputs between components, not free-form text where the UI depends on machine-readable data.
- Treat deployment as part of development, not a final step.

This means:

- All config comes from environment variables.
- The UI never imports agents directly.
- The backend can run locally, on EC2, and behind the same API contract.
- Memory is scoped per user or session, never shared globally.
- Every external dependency call is wrapped with retries and graceful fallback.
- Job state is persisted outside process memory so EC2 restarts do not erase work.
- Long agent outputs are compressed before they reach later steps.
- Public-facing endpoints include basic abuse protection before launch.

---

## 1. Final Architecture

```text
Streamlit Cloud (Frontend)
ui/app.py
- Accepts topic + style
- Calls backend API via HTTP
- Displays progress, sources, trust score, and final report
- Reads only API_BASE_URL from secrets

        |
        | HTTPS
        v

AWS EC2 (Backend)
api/main.py
- POST /research creates a job and persists it
- GET /research/{job_id} returns status/result
- Calls graph/workflow.py -> run_research()
- Returns structured JSON

        |
        v

graph/workflow.py
LangGraph StateGraph
ResearchState flows through:
researcher -> analyst -> writer -> fact_checker

        |
        v

agents/
researcher.py
analyst.py
writer.py
fact_checker.py

        |
        v

memory/mem0_client.py
- Scoped read/write memory
- Per-session or per-user namespace
```

### Why this shape is safer

- Streamlit never holds API keys for Groq, Tavily, or Mem0.
- Long-running research does not block a single UI request.
- The same backend flow powers local dev, FastAPI, and future deploys.
- Structured state makes the API response predictable and testable.

---

## 2. Design Decisions

### 2.1 Job-based API

The backend should not rely on one long synchronous request from the UI.

- `POST /research` creates a job and returns `job_id`
- `GET /research/{job_id}` returns:
  - `queued`
  - `running`
  - `complete`
  - `failed`
- This avoids browser timeouts and makes retries possible.
- Job state should be stored in SQLite or LangGraph checkpointing, not in an in-memory Python dictionary.

### 2.2 Structured state

Keep `ResearchState` as a typed, JSON-safe contract.

Recommended fields:

- `topic`
- `style`
- `skip_memory`
- `memory_context`
- `raw_research`
- `compressed_research`
- `sources`
- `analysis`
- `report`
- `fact_checked_report`
- `claims`
- `errors`

### 2.3 User-scoped memory

Do not use one global Mem0 identity for the whole app.

Use one of:

- authenticated user ID
- anonymous session ID generated in Streamlit and passed to the backend
- generated anonymous namespace per browser session

This should be explicit in the API contract so memory reads and writes remain scoped.

This prevents cross-user contamination and makes memory behavior trustworthy.

### 2.4 Structured fact-check output

The fact-checker should return structured claim data, not just bracket tags in prose.

Each claim should include:

- claim text
- status: verified / unverified / uncertain
- source reference
- short rationale

That lets the UI compute trust score without fragile string parsing.
The output should be enforced with a schema or structured-output mode so the pipeline does not depend on free-form JSON guesses.

### 2.5 Thin frontend

Streamlit should:

- accept input
- call backend
- poll job status
- render results

It should not run LangGraph or agent logic locally.

### 2.6 Reproducible deployment

Pin:

- Python version
- backend dependencies
- frontend dependencies

Use separate requirements files for backend and frontend.

---

## 3. Repo Structure

```text
multi-agent-research/
├── agents/
│   ├── __init__.py
│   ├── researcher.py
│   ├── analyst.py
│   ├── writer.py
│   └── fact_checker.py
├── graph/
│   ├── __init__.py
│   ├── state.py
│   └── workflow.py
├── memory/
│   ├── __init__.py
│   └── mem0_client.py
├── api/
│   └── main.py
├── ui/
│   └── app.py
├── config.py
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-ui.txt
├── README.md
└── tests/
    └── test_workflow.py
```

---

## 4. Day-by-Day Plan

### Day 1 — Contract, config, and researcher

Lock the core schema first.

Tasks:

- Create repo structure
- Add config loader
- Define `ResearchState`
- Add `.env.example`
- Implement `agents/researcher.py`
- Make researcher return structured output with:
  - research text
  - source URLs
  - error list
- Validate config early and fail fast if critical keys are missing

Checkpoint:

- Researcher returns valid JSON-safe state
- Config validation passes
- No hardcoded secrets

### Day 2 — Analyst, writer, and shared LLM wrapper

Build a single Groq client wrapper used by all LLM-based agents.

Tasks:

- Implement `agents/llm_client.py`
- Add retry logic and consistent error handling
- Implement analyst agent
- Implement writer agent
- Ensure each agent appends errors instead of crashing the pipeline
- Add truncation or summarization before passing research into the writer or fact-checker if the raw context gets too large

Checkpoint:

- Researcher -> analyst -> writer can run manually in sequence
- Failures are contained and visible

### Day 3 — Fact-checker, LangGraph, and FastAPI

Make the pipeline executable as one backend flow.

Tasks:

- Implement fact-checker with structured claim output
- Build LangGraph workflow
- Add FastAPI app
- Add persistent job storage or checkpointing for `job_id` state
- Expose:
  - `POST /research`
  - `GET /research/{job_id}`
  - `GET /health`
- Return a structured JSON result from the workflow

Checkpoint:

- The backend can run end-to-end locally
- The API response is valid JSON
- The graph compiles and executes consistently

### Day 4 — Mem0 integration

Add memory in a scoped and non-blocking way.

Tasks:

- Implement Mem0 client wrapper
- Support memory read before researcher runs
- Support memory write after final output is produced
- Generate and pass a session-scoped `session_id` from the UI
- Add `skip_memory` flag for comparison mode
- Keep failures non-fatal

Checkpoint:

- Related queries show memory reuse
- Memory failures do not break the run

### Day 5 — Streamlit UI

Build the frontend as an API client.

Tasks:

- Implement `ui/app.py`
- Use `requests.post` against the backend
- Add style selector
- Add source rendering
- Add trust score
- Add per-agent progress/status display
- Add download/export support
- Add memory comparison mode if practical

Checkpoint:

- Full UI works locally against the local API
- The UI imports no agent code directly

### Day 6 — EC2 backend deployment

Move only the backend to EC2.

Tasks:

- Launch EC2 instance
- Install Python and dependencies
- Configure `.env`
- Run backend on EC2
- Add a service manager for persistence
- Add simple rate limiting before exposing the API publicly
- Test public reachability and restart safety

Checkpoint:

- Backend survives disconnects
- API works from outside the instance

### Day 7 — Streamlit Cloud deployment

Deploy the frontend separately.

Tasks:

- Push code to GitHub
- Deploy Streamlit app from `ui/app.py`
- Set `API_BASE_URL` in Streamlit secrets
- Run live end-to-end tests
- Run the memory comparison test live
- Update README with live URL and demo notes

Checkpoint:

- Public UI calls EC2 successfully
- Full pipeline works end to end

---

## 5. UI Behavior

The frontend should prioritize clarity and trust.

Required UI features:

- Topic input
- Style selector
- Progress/status display
- Research output
- Analyst output
- Writer output
- Fact-check result
- Trust score
- Source links
- Error display
- Download button

Recommended UX behavior:

- Show loading state while polling
- Keep the user informed at every stage
- Show friendly messages for empty inputs, no results, or backend failures
- Render fact-check results in a structured way, not raw model prose

---

## 6. Failure Policy

The system should degrade gracefully.

Rules:

- No agent failure should crash the full pipeline unless absolutely necessary
- External API errors should be logged into `errors`
- Memory lookup failure should fall back to no memory
- Search failure should still allow downstream agents to process what is available
- UI should surface partial results instead of hiding everything

---

## 7. Verification

Before moving to the next day, verify:

- The state contract is still JSON-safe
- Agent functions are deterministic over input state
- The backend can run locally from a single entrypoint
- The frontend can run without importing backend internals
- Memory is scoped correctly
- The fact-checker output is machine-readable
- Job state survives backend restart or worker reload
- Long runs stay within token limits after compression
- The deployed backend stays alive after disconnects
- The live frontend can reach the live backend

---

## 8. Pre-Mortem

This plan is designed to prevent the most common failure modes:

- Frontend/backend coupling
- Cross-user memory leakage
- Long-request timeouts
- Unstructured model output
- Deployment surprises from unpinned dependencies
- API key exposure in the frontend
- EC2 process death after SSH disconnect
- Memory feature that works locally but not live

---

## 9. Final Resume Bullet

> Engineered a 4-agent autonomous research pipeline using LangGraph state machines, Groq LLM inference, Tavily web search, and Mem0-based scoped memory, with structured fact-checking and trust scoring; deployed the backend on AWS EC2 and the frontend on Streamlit Cloud for public access.
