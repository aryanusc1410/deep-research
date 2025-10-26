# 🔬 Deep Research Agent

An intelligent research assistant powered by **LangGraph** that performs parallel web searches, evaluates multiple sources, and generates comprehensive reports with citations. Features dual-mode interaction (research vs chat), real-time streaming, and competitive search evaluation.

## ✨ Key Features

- **🎯 Dual Search Architecture**: Runs Tavily + SerpAPI in parallel, LLM selects best report
- **💬 Chat + Research Modes**: Toggle between deep research and quick Q&A
- **📊 Multiple Report Formats**: Bullet summaries, tables, or detailed academic reports
- **⚡ Real-Time Streaming**: Live progress updates via Server-Sent Events
- **🔗 Source Citations**: Every claim backed by verifiable references

## 🚀 Quick Setup (5 Minutes)

### Prerequisites
- Python 3.11+ and Node.js 18+
- API Keys: [OpenAI](https://platform.openai.com/api-keys) + [Tavily](https://tavily.com) (required), [SerpAPI](https://serpapi.com) (optional)

### 1. Clone & Install

```bash
git clone https://github.com/aryanusc1410/deep-research.git
cd deep-research

# Backend
python -m venv research-agent
source research-agent/bin/activate  # Windows: research-agent\Scripts\activate
pip install -r requirements.txt

# Frontend (new terminal)
cd frontend
npm install
```

### 2. Configure Environment

**`backend/.env`:**
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
SERP_API_KEY=...           # Optional
USE_DUAL_SEARCH=true
```

**`frontend/.env.local`:**
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 3. Run

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn app:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

**Open:** http://localhost:3000

## 📖 Usage

1. **Research Mode** (toggle ON): Enter query → Get sourced report with citations
2. **Chat Mode** (toggle OFF): Ask follow-ups without triggering new research
3. **Detailed Reports**: Select "Detailed report (long)" for 1500+ word analysis

## 🏗️ Tech Stack

**Backend:** FastAPI, LangGraph, LangChain, OpenAI, Tavily/SerpAPI  
**Frontend:** Next.js, React, TypeScript, SSE streaming  
**Key Pattern:** Stateful workflows with parallel search + LLM evaluation

## 🎯 What Makes It Different

1. **Competitive Evaluation**: Generates 2 complete reports from different engines, LLM picks winner
2. **Stateful Orchestration**: LangGraph manages explicit state transitions (not just prompt chaining)
3. **Hybrid Modes**: Seamlessly switch between research and chat without losing context
4. **Production SSE**: Proper streaming with backpressure handling and error recovery

## 📁 Structure

```
backend/     # FastAPI + LangGraph workflows
frontend/    # Next.js + React UI
├── app/     # Pages and routing
└── components/  # Report, Log components
```

## 🐛 Common Issues

- **Port conflicts**: Kill processes on 8000/3000
- **Missing API keys**: Check `.env` files exist and have valid keys
- **CORS errors**: Verify `NEXT_PUBLIC_BACKEND_URL` matches backend
