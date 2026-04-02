# 🤖 AI Live Assistant

A **production-ready, fully local AI assistant** with real-time web search, tool calling, persistent memory, and a clean dark-mode chat UI — built entirely on free and open-source tools.

---

## ✨ Features

| Feature | Implementation |
|---------|----------------|
| Real-time Q&A | Ollama (Llama3/Mistral/Qwen) |
| Web Search | DuckDuckGo Search API |
| News Search | DuckDuckGo News API |
| Webpage Reading | BeautifulSoup + httpx |
| Calculations | AST-safe evaluator |
| Code Execution | Sandboxed subprocess |
| Semantic Memory | ChromaDB + sentence-transformers |
| Conversation History | JSON-based session store |
| Agent Framework | LangGraph ReAct |
| Backend | FastAPI |
| Frontend | Streamlit (dark theme) |

---

## 🗂 Project Structure

```
AI-Live-Assistant/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings (env-based)
│   ├── agents/
│   │   └── assistant_agent.py     # LangGraph ReAct agent
│   ├── tools/
│   │   ├── web_search.py          # DuckDuckGo search + news
│   │   ├── web_scraper.py         # Webpage content extraction
│   │   ├── calculator.py          # Safe math evaluation
│   │   └── code_executor.py       # Sandboxed Python execution
│   ├── memory/
│   │   ├── vector_store.py        # ChromaDB semantic memory
│   │   └── conversation_store.py  # JSON conversation history
│   └── api/
│       └── routes.py              # REST API endpoints
├── frontend/
│   └── app.py                     # Streamlit chat UI
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── start.sh                       # One-command launcher
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** — [python.org](https://www.python.org/downloads/)
2. **Ollama** — [ollama.ai](https://ollama.ai)

### Option A: One-Command Start (Recommended)

```bash
# Clone / navigate to project
cd "AI Live Assistant"

# Run the launcher (installs deps, pulls model, starts everything)
./start.sh
```

Open **http://localhost:8501** in your browser.

---

### Option B: Manual Setup

#### 1. Install Ollama & pull a model

```bash
# Install Ollama from https://ollama.ai, then:
ollama serve          # Start the server
ollama pull llama3    # Pull the default model (~4GB)

# Alternative lighter models:
# ollama pull mistral       # Mistral 7B
# ollama pull qwen2:7b      # Qwen2 7B
# ollama pull phi3          # Phi-3 (fastest, 3.8B)
```

#### 2. Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Configure environment

```bash
cp .env.example backend/.env
# Edit backend/.env if needed (change model, ports, etc.)
```

#### 4. Start the backend

```bash
cd backend
python main.py
# → http://localhost:8000
# → API docs: http://localhost:8000/docs
```

#### 5. Start the frontend (new terminal)

```bash
source .venv/bin/activate
cd frontend
streamlit run app.py
# → http://localhost:8501
```

---

### Option C: Docker Compose

```bash
cd docker
docker compose up --build

# On first run, the model is auto-pulled (~4GB download)
# Frontend: http://localhost:8501
# Backend:  http://localhost:8000
```

Stop everything:
```bash
docker compose down
```

---

## ⚙️ Configuration

Edit `backend/.env` (copy from `.env.example`):

```env
OLLAMA_MODEL=llama3          # Model name
OLLAMA_BASE_URL=http://localhost:11434
MAX_SEARCH_RESULTS=5         # DuckDuckGo results per query
MAX_SCRAPE_LENGTH=4000       # Chars to extract per webpage
CODE_EXECUTION_TIMEOUT=10    # Seconds for code execution
```

### Recommended Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `llama3` | 4.7GB | Medium | ⭐⭐⭐⭐⭐ |
| `llama3:8b` | 4.7GB | Medium | ⭐⭐⭐⭐⭐ |
| `mistral` | 4.1GB | Fast | ⭐⭐⭐⭐ |
| `qwen2:7b` | 4.4GB | Medium | ⭐⭐⭐⭐ |
| `phi3` | 2.3GB | Fast | ⭐⭐⭐ |
| `llama3:70b` | 40GB | Slow | ⭐⭐⭐⭐⭐ |

---

## 🔌 API Reference

### `POST /api/chat`
Send a question to the agent.

```json
// Request
{
  "question": "What are the latest AI news?",
  "session_id": "optional-uuid"  // omit to start new session
}

// Response
{
  "answer": "Here are the latest AI developments...",
  "sources": ["https://...", "https://..."],
  "tool_calls_made": ["web_search", "scrape_webpage"],
  "session_id": "uuid"
}
```

### `GET /api/health`
```json
{
  "status": "ok",
  "ollama_connected": true,
  "active_model": "llama3",
  "memory_entries": 42
}
```

### `GET /api/sessions`
List all conversation sessions.

### `GET /api/sessions/{id}/messages`
Get messages for a session.

### `DELETE /api/sessions/{id}`
Delete a session and its memories.

---

## 🏗️ Architecture

```
User Input
    │
    ▼
Streamlit UI (frontend/app.py)
    │  HTTP POST /api/chat
    ▼
FastAPI (backend/main.py)
    │
    ▼
LangGraph ReAct Agent (agents/assistant_agent.py)
    │
    ├── web_search()        → DuckDuckGo API
    ├── news_search()       → DuckDuckGo News
    ├── scrape_webpage()    → httpx + BeautifulSoup
    ├── calculate()         → AST evaluator
    ├── run_python_code()   → Sandboxed subprocess
    └── search_memory()     → ChromaDB + sentence-transformers
    │
    ▼
Ollama LLM (llama3/mistral/qwen2)
    │
    ▼
Response + Sources + Tool Calls
    │
    ▼
Save to Memory (ChromaDB vector store)
Save to History (JSON conversation store)
    │
    ▼
Return to Frontend
```

---

