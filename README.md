# Multi-Agent Research System 🧠

An enterprise-grade, multi-agent AI system built to automate deep research, synthesize findings, and fact-check information using an orchestrated pipeline of specialized agents.

## 🌟 Overview

The Multi-Agent Research System takes a user's topic and processes it through a sophisticated LangGraph-powered pipeline:
1. **Researcher Agent**: Scours the internet for up-to-date data (via Tavily API).
2. **Compressor Node**: Distills the raw search data into context-dense insights to prevent context window bloat.
3. **Analyst Agent**: Reviews the compressed data, synthesizes themes, and structures a coherent narrative.
4. **Writer Agent**: Drafts a comprehensive, professionally formatted report in the requested style (Academic, Bulleted, Executive Summary).
5. **Fact-Checker Agent**: Verifies the final report against the original raw search data, calculates a Trust Score, and extracts verifiable claims.

The system utilizes **Mem0** to maintain long-term memory across sessions, allowing the agents to "remember" past research contexts for the same user or session.

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.12)
- **AI Orchestration**: LangGraph & LangChain
- **LLM Provider**: Groq (Llama-3-70b-8192 for blazing fast inference)
- **Search Engine**: Tavily
- **Long-term Memory**: Mem0 (mem0ai)
- **Database**: SQLite (Job storage & persistence)
- **Frontend**: Next.js 14, React, Tailwind CSS (Vercel deployment)
- **Production Infrastructure**: AWS EC2 (Ubuntu), Systemd, Nginx, Gunicorn

## 🚀 Live Demo

- **Frontend Application**: [https://multi-agent-research-system-bwnyl3w8j.vercel.app](https://multi-agent-research-system-bwnyl3w8j.vercel.app)
- **API Endpoint**: `http://65.1.3.210/health`

*(Note: API is rate-limited and secured via CORS to the frontend domain).*

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/SarvagyaGupta-19/Multi-agent-research-system.git
cd Multi-agent-research-system
```

### 3. Backend Setup
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set up your environment variables:
```bash
cp .env.example .env
```
Edit `.env` to include your API keys:
```env
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
MEM0_API_KEY=your_mem0_key
```

Run the backend server:
```bash
uvicorn api.main:app --reload --port 8000
```

### 4. Frontend Setup
In a new terminal window, navigate to the frontend directory:
```bash
cd frontend
npm install
```

Start the Next.js development server:
```bash
npm run dev
```
Access the application at `http://localhost:3000`.

---

## 🧪 Testing

The backend is fully covered by Pytest (150+ tests ensuring reliability).

```bash
# Run tests
pytest

# Run tests with detailed output
pytest -v
```

## 🚢 Production Deployment

For instructions on deploying the backend to AWS EC2 and the frontend to Vercel, please refer to the detailed [Deployment Guide](deploy/README.md).

## 🛡️ Security & Performance

- **Thread-safe Database**: SQLite operations are wrapped in safe connection contexts to prevent memory leaks and locks.
- **CORS Protection**: The API strictly enforces allowed origins based on environment settings.
- **DDoS Mitigation**: Nginx is configured with strict rate limiting (10 req/sec) and burst controls.
- **Non-root Execution**: Systemd enforces that the application runs safely isolated from root access.

## 📄 License

This project is open-source and available under the MIT License.
