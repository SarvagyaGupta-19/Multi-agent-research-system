"""
Streamlit UI — frontend for the Multi-Agent Research System.

Pure API client: communicates only with the FastAPI backend via HTTP.
Imports NO agent, graph, or memory code directly.

Features:
- Topic input with style selector
- Async job submission and status polling
- Per-stage progress display
- Structured results: report, analysis, fact-check, trust score
- Source links with titles
- Download/export as markdown
- Memory comparison mode (skip_memory toggle)
"""

import json
import os
import time
import uuid

import requests
import streamlit as st

# --- Configuration ---

# Backend URL: from env, Streamlit secrets (production), or default (local dev)
def _get_api_url() -> str:
    """Resolve backend URL from environment or Streamlit secrets."""
    # 1. Env var (highest priority — works everywhere)
    url = os.environ.get("API_BASE_URL", "")
    if url:
        return url.rstrip("/")
    # 2. Streamlit secrets (Streamlit Cloud)
    try:
        url = st.secrets.get("API_BASE_URL", "")
        if url:
            return url.rstrip("/")
    except Exception:
        pass
    # 3. Default (local dev)
    return "http://localhost:8000"


API_BASE_URL = _get_api_url()

POLL_INTERVAL = 2  # seconds between status polls
MAX_POLLS = 150  # maximum polls before timeout (~5 minutes)

STYLES = ["academic", "blog", "executive summary", "technical"]


# --- Session management ---

def _get_session_id() -> str:
    """Get or create a persistent session ID for memory scoping."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


# --- API helpers ---

def _check_backend_health() -> bool:
    """Check if the backend is reachable."""
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _submit_research(topic: str, style: str, skip_memory: bool, session_id: str) -> dict | None:
    """Submit a research job to the backend.

    Returns:
        Response dict with job_id, or None on failure.
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/research",
            json={
                "topic": topic,
                "style": style,
                "skip_memory": skip_memory,
                "session_id": session_id,
            },
            timeout=15,
        )
        if resp.status_code in (200, 202):
            return resp.json()
        else:
            st.error(f"Backend returned status {resp.status_code}: {resp.text}")
            return None
    except requests.ConnectionError:
        st.error("❌ Cannot connect to the backend. Make sure the API is running.")
        return None
    except requests.Timeout:
        st.error("⏱️ Backend request timed out. Try again.")
        return None
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


def _poll_job(job_id: str) -> dict | None:
    """Poll the job status endpoint.

    Returns:
        Job status dict, or None on failure.
    """
    try:
        resp = requests.get(f"{API_BASE_URL}/research/{job_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            st.error(f"Job not found: {job_id}")
            return None
        else:
            return None
    except requests.RequestException:
        return None


# --- Rendering helpers ---

def _render_trust_score(trust_score: float):
    """Render a visual trust score indicator."""
    pct = int(trust_score * 100)

    if trust_score >= 0.8:
        color = "#10b981"  # green
        label = "High"
        icon = "✅"
    elif trust_score >= 0.5:
        color = "#f59e0b"  # amber
        label = "Moderate"
        icon = "⚠️"
    else:
        color = "#ef4444"  # red
        label = "Low"
        icon = "❌"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}22, {color}11);
            border: 1px solid {color}44;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin: 10px 0;
        ">
            <div style="font-size: 2.5rem;">{icon}</div>
            <div style="font-size: 2rem; font-weight: 700; color: {color};">{pct}%</div>
            <div style="font-size: 0.9rem; color: #94a3b8; margin-top: 4px;">
                Trust Score — {label} Confidence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_claims_table(claims: list[dict]):
    """Render fact-check claims as a structured table."""
    if not claims:
        st.info("No claims were extracted for verification.")
        return

    status_icons = {
        "verified": "✅",
        "unverified": "❌",
        "uncertain": "⚠️",
    }

    for i, claim in enumerate(claims, 1):
        status = claim.get("status", "uncertain")
        icon = status_icons.get(status, "❓")

        with st.container():
            st.markdown(
                f"""
                <div style="
                    background: #1e293b;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin: 6px 0;
                    border-left: 4px solid {'#10b981' if status == 'verified' else '#f59e0b' if status == 'uncertain' else '#ef4444'};
                ">
                    <div style="font-weight: 600; color: #e2e8f0;">
                        {icon} Claim {i}: {claim.get('claim', 'N/A')}
                    </div>
                    <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px;">
                        <b>Status:</b> {status.capitalize()} &nbsp;|&nbsp;
                        <b>Source:</b> {claim.get('source', 'N/A')}
                    </div>
                    <div style="color: #64748b; font-size: 0.82rem; margin-top: 2px;">
                        {claim.get('rationale', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_sources(sources: list[dict]):
    """Render source links with titles."""
    if not sources:
        st.info("No sources available.")
        return

    for i, src in enumerate(sources, 1):
        url = src.get("url", "")
        title = src.get("title", f"Source {i}")
        snippet = src.get("snippet", "")

        st.markdown(
            f"""
            <div style="
                background: #1e293b;
                border-radius: 8px;
                padding: 10px 14px;
                margin: 4px 0;
            ">
                <a href="{url}" target="_blank" style="
                    color: #60a5fa; font-weight: 600; text-decoration: none;
                ">{i}. {title}</a>
                <div style="color: #64748b; font-size: 0.82rem; margin-top: 2px;">
                    {snippet[:150]}{'...' if len(snippet) > 150 else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _build_download_content(result: dict) -> str:
    """Build a downloadable markdown report from the result."""
    parts = [f"# Research Report: {result.get('topic', 'Unknown')}\n"]
    parts.append(f"**Style:** {result.get('style', 'academic')}\n")
    parts.append("---\n")

    report = result.get("report", "")
    if report:
        parts.append(f"## Report\n\n{report}\n\n---\n")

    analysis = result.get("analysis", "")
    if analysis:
        parts.append(f"## Analysis\n\n{analysis}\n\n---\n")

    # Sources
    sources = result.get("sources", [])
    if sources:
        parts.append("## Sources\n")
        for i, src in enumerate(sources, 1):
            parts.append(f"{i}. [{src.get('title', 'Source')}]({src.get('url', '')})\n")
        parts.append("\n---\n")

    # Fact-check
    claims = result.get("claims", [])
    if claims:
        parts.append("## Fact-Check Results\n")
        for i, c in enumerate(claims, 1):
            status = c.get("status", "uncertain").capitalize()
            parts.append(f"- **Claim {i}:** {c.get('claim', 'N/A')}\n")
            parts.append(f"  - Status: {status}\n")
            parts.append(f"  - Source: {c.get('source', 'N/A')}\n")
            parts.append(f"  - Rationale: {c.get('rationale', '')}\n\n")

    # Trust score
    fc_report = result.get("fact_checked_report", "")
    if fc_report:
        try:
            fc_data = json.loads(fc_report)
            trust = fc_data.get("trust_score", 0)
            parts.append(f"\n**Trust Score:** {int(trust * 100)}%\n")
        except (json.JSONDecodeError, TypeError):
            pass

    # Errors
    errors = result.get("errors", [])
    if errors:
        parts.append("\n## Pipeline Warnings\n")
        for err in errors:
            parts.append(f"- {err}\n")

    return "\n".join(parts)


# --- Main app ---

def main():
    """Main Streamlit application."""

    # Page config
    st.set_page_config(
        page_title="Multi-Agent Research System",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .main-title {
            background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0;
            letter-spacing: -0.02em;
        }

        .subtitle {
            color: #94a3b8;
            font-size: 1.05rem;
            margin-top: 0;
            margin-bottom: 2rem;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .status-queued { background: #334155; color: #94a3b8; }
        .status-running { background: #1e3a5f; color: #60a5fa; }
        .status-complete { background: #064e3b; color: #34d399; }
        .status-failed { background: #7f1d1d; color: #fca5a5; }

        .stDownloadButton button {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }

        div[data-testid="stExpander"] {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Header ---
    st.markdown('<div class="main-title">🔬 Multi-Agent Research System</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">'
        '4-agent pipeline: Researcher → Analyst → Writer → Fact-Checker'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        # Backend health
        backend_ok = _check_backend_health()
        if backend_ok:
            st.success("🟢 Backend connected")
        else:
            st.error("🔴 Backend unavailable")
            st.caption(f"URL: `{API_BASE_URL}`")

        st.divider()

        # Style selector
        style = st.selectbox(
            "📝 Writing Style",
            STYLES,
            index=0,
            help="Choose the tone and format of the generated report.",
        )

        # Memory toggle
        st.markdown("### 🧠 Memory")
        skip_memory = st.toggle(
            "Skip memory (comparison mode)",
            value=False,
            help="Disable Mem0 context for A/B comparison of results.",
        )

        session_id = _get_session_id()
        st.caption(f"Session: `{session_id[:8]}...`")

        st.divider()
        st.markdown(
            "<div style='color: #475569; font-size: 0.78rem;'>"
            "Built with LangGraph, Groq, Tavily, Mem0<br>"
            "Frontend: Streamlit &nbsp;|&nbsp; Backend: FastAPI"
            "</div>",
            unsafe_allow_html=True,
        )

    # --- Main content ---
    col1, col2 = st.columns([3, 1])

    with col1:
        topic = st.text_input(
            "🔍 Research Topic",
            placeholder="e.g., Latest breakthroughs in quantum computing",
            max_chars=500,
        )

    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        submit = st.button("🚀 Start Research", type="primary", use_container_width=True, disabled=not backend_ok)

    # --- Job execution ---
    if submit and topic.strip():
        _run_research_flow(topic.strip(), style, skip_memory, session_id)
    elif submit and not topic.strip():
        st.warning("Please enter a research topic.")

    # --- Show previous result if available ---
    if "last_result" in st.session_state and not submit:
        _display_results(st.session_state.last_result)


def _run_research_flow(topic: str, style: str, skip_memory: bool, session_id: str):
    """Submit a job, poll for completion, and display results."""

    # Submit job
    with st.spinner("Submitting research job..."):
        response = _submit_research(topic, style, skip_memory, session_id)

    if not response:
        return

    job_id = response.get("job_id")
    if not job_id:
        st.error("No job ID returned from backend.")
        return

    # Polling UI
    status_container = st.empty()
    progress_bar = st.progress(0, text="Initializing pipeline...")

    stage_messages = {
        "queued": ("⏳", "Job queued, waiting for worker..."),
        "running": ("🔄", "Pipeline running..."),
        "complete": ("✅", "Research complete!"),
        "failed": ("❌", "Pipeline failed."),
    }

    for poll_num in range(MAX_POLLS):
        job = _poll_job(job_id)

        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        status = job.get("status", "queued")
        icon, msg = stage_messages.get(status, ("❓", "Unknown status"))

        status_container.markdown(
            f'<span class="status-badge status-{status}">{icon} {msg}</span>',
            unsafe_allow_html=True,
        )

        # Update progress bar
        if status == "queued":
            progress_bar.progress(0.1, text="Waiting in queue...")
        elif status == "running":
            # Animate progress during running
            progress_pct = min(0.15 + (poll_num * 0.03), 0.9)
            progress_bar.progress(progress_pct, text="Agents working... Researcher → Analyst → Writer → Fact-Checker")
        elif status == "complete":
            progress_bar.progress(1.0, text="✅ All agents finished!")
            time.sleep(0.5)
            progress_bar.empty()
            status_container.empty()

            result = job.get("result")
            if result:
                st.session_state.last_result = result
                _display_results(result)
            else:
                st.warning("Job completed but no result was returned.")
            return

        elif status == "failed":
            progress_bar.empty()
            status_container.empty()
            error = job.get("error", "Unknown error")
            st.error(f"**Research pipeline failed**\n\n```\n{error[:500]}\n```")
            return

        time.sleep(POLL_INTERVAL)

    # Timeout
    progress_bar.empty()
    status_container.empty()
    st.warning(f"⏱️ Polling timed out after {MAX_POLLS * POLL_INTERVAL}s. Job may still be running — refresh to check.")


def _display_results(result: dict):
    """Display the full research results."""

    st.markdown("---")
    topic = result.get("topic", "Unknown")
    st.markdown(f"## 📄 Results: *{topic}*")

    # --- Trust Score + Stats row ---
    col_trust, col_stats = st.columns([1, 2])

    with col_trust:
        fc_report = result.get("fact_checked_report", "")
        trust_score = 0.0
        if fc_report:
            try:
                fc_data = json.loads(fc_report)
                trust_score = fc_data.get("trust_score", 0.0)
            except (json.JSONDecodeError, TypeError):
                pass
        _render_trust_score(trust_score)

    with col_stats:
        num_sources = len(result.get("sources", []))
        num_claims = len(result.get("claims", []))
        num_errors = len(result.get("errors", []))

        st.markdown(
            f"""
            <div style="background: #1e293b; border-radius: 12px; padding: 16px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 700; color: #60a5fa;">{num_sources}</div>
                        <div style="color: #94a3b8; font-size: 0.85rem;">Sources</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 700; color: #a78bfa;">{num_claims}</div>
                        <div style="color: #94a3b8; font-size: 0.85rem;">Claims Checked</div>
                    </div>
                    <div>
                        <div style="font-size: 1.8rem; font-weight: 700; color: {'#fca5a5' if num_errors > 0 else '#34d399'};">{num_errors}</div>
                        <div style="color: #94a3b8; font-size: 0.85rem;">Warnings</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Report ---
    report = result.get("report", "")
    if report:
        st.markdown("### 📝 Report")
        st.markdown(report)
    else:
        st.info("No report was generated.")

    # --- Tabs for details ---
    tab_fc, tab_analysis, tab_sources, tab_raw = st.tabs([
        "🔍 Fact-Check", "📊 Analysis", "🔗 Sources", "📄 Raw Research"
    ])

    with tab_fc:
        claims = result.get("claims", [])
        _render_claims_table(claims)

    with tab_analysis:
        analysis = result.get("analysis", "")
        if analysis:
            st.markdown(analysis)
        else:
            st.info("No analysis available.")

    with tab_sources:
        sources = result.get("sources", [])
        _render_sources(sources)

    with tab_raw:
        raw = result.get("raw_research", "") or result.get("compressed_research", "")
        if raw:
            with st.expander("View raw research data", expanded=False):
                st.text(raw[:5000])
                if len(raw) > 5000:
                    st.caption(f"... truncated ({len(raw)} total chars)")
        else:
            st.info("No raw research data available.")

    # --- Errors ---
    errors = result.get("errors", [])
    if errors:
        with st.expander(f"⚠️ Pipeline Warnings ({len(errors)})", expanded=False):
            for err in errors:
                st.warning(err)

    # --- Download ---
    st.markdown("---")
    download_content = _build_download_content(result)
    st.download_button(
        label="📥 Download Report (Markdown)",
        data=download_content,
        file_name=f"research_{topic.replace(' ', '_')[:30]}.md",
        mime="text/markdown",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
