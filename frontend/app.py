"""
AI Live Assistant — Streamlit Frontend
Dark-themed chat UI with source citations, conversation history, and tool transparency.
"""

import time
import uuid
import requests
import streamlit as st

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Live Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = "http://localhost:8000/api"

# ─── Custom CSS (dark theme) ──────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Global ── */
:root {
    --bg-primary:    #0d1117;
    --bg-secondary:  #161b22;
    --bg-tertiary:   #21262d;
    --accent:        #58a6ff;
    --accent-green:  #3fb950;
    --accent-orange: #f78166;
    --text-primary:  #e6edf3;
    --text-secondary:#8b949e;
    --border:        #30363d;
}
html, body, .stApp { background-color: var(--bg-primary) !important; color: var(--text-primary); }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

/* ── User message ── */
.user-bubble {
    background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%);
    color: #fff;
    padding: 14px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0 8px 60px;
    max-width: 80%;
    float: right;
    clear: both;
    box-shadow: 0 2px 8px rgba(31,111,235,0.4);
    line-height: 1.6;
    font-size: 15px;
}
/* ── Assistant message ── */
.assistant-bubble {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 16px 20px;
    border-radius: 18px 18px 18px 4px;
    margin: 8px 60px 8px 0;
    max-width: 85%;
    float: left;
    clear: both;
    line-height: 1.7;
    font-size: 15px;
}
/* ── Avatars ── */
.avatar-user {
    float: right;
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    margin-left: 8px;
}
.avatar-bot {
    float: left;
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #238636, #3fb950);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    margin-right: 8px;
}
/* ── Sources ── */
.sources-container {
    background: rgba(88, 166, 255, 0.05);
    border: 1px solid rgba(88, 166, 255, 0.2);
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 13px;
    clear: both;
}
.sources-container a { color: var(--accent); text-decoration: none; }
.sources-container a:hover { text-decoration: underline; }

/* ── Tool calls badge ── */
.tool-badge {
    display: inline-block;
    background: rgba(63,185,80,0.15);
    border: 1px solid rgba(63,185,80,0.4);
    color: #3fb950;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 12px;
    margin: 2px 3px;
    font-family: monospace;
}
/* ── Chat input ── */
.stChatInput input {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 12px !important;
    font-size: 15px !important;
}
/* ── Buttons ── */
.stButton button {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
    transition: all 0.2s;
}
.stButton button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}
/* ── Spinner ── */
.loading-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin: 8px 60px 8px 0;
    max-width: 300px;
    color: var(--text-secondary);
    font-size: 14px;
}
.dot-pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.4s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes pulse {
    0%, 100% { opacity: 0.2; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1.2); }
}
/* ── Divider ── */
hr { border-color: var(--border) !important; }
/* ── Status indicators ── */
.status-dot-green { color: #3fb950; font-size: 10px; }
.status-dot-red   { color: #f78166; font-size: 10px; }
/* ── Metrics ── */
div[data-testid="metric-container"] {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thinking" not in st.session_state:
    st.session_state.thinking = False


# ─── Helpers ──────────────────────────────────────────────────────────────────
def api_post(endpoint: str, payload: dict) -> dict | None:
    try:
        resp = requests.post(
            f"{BACKEND_URL}{endpoint}",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Is it running? `cd backend && python main.py`"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The model may be too slow — try a faster model."}
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return {"error": detail}
    except Exception as e:
        return {"error": str(e)}


def api_get(endpoint: str, timeout: int = 10) -> dict | None:
    try:
        resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def api_delete(endpoint: str) -> bool:
    try:
        resp = requests.delete(f"{BACKEND_URL}{endpoint}", timeout=10)
        return resp.status_code in (200, 204)
    except Exception:
        return False


def get_health():
    return api_get("/health", timeout=5)


def render_message(msg: dict):
    """Render a single chat message with avatar and content."""
    role = msg["role"]
    content = msg["content"]
    sources = msg.get("sources", [])
    tools = msg.get("tools", [])

    if role == "user":
        st.markdown(
            f'<div class="user-bubble">{content}</div><div style="clear:both"></div>',
            unsafe_allow_html=True,
        )
    else:
        # Assistant message
        st.markdown(
            f'<div class="assistant-bubble">{content}</div>',
            unsafe_allow_html=True,
        )

        # Tool call badges
        if tools:
            badges = "".join(f'<span class="tool-badge">⚙ {t}</span>' for t in tools)
            st.markdown(
                f'<div style="clear:both; margin: 4px 0 4px 0;">{badges}</div>',
                unsafe_allow_html=True,
            )

        # Sources
        if sources:
            source_html = '<div class="sources-container">📎 <strong>Sources:</strong><br>'
            for i, url in enumerate(sources[:8], 1):
                short = url[:70] + "..." if len(url) > 70 else url
                source_html += f'<a href="{url}" target="_blank">[{i}] {short}</a><br>'
            source_html += "</div>"
            st.markdown(source_html, unsafe_allow_html=True)

        st.markdown('<div style="clear:both"></div>', unsafe_allow_html=True)


def load_history_from_backend():
    """Load conversation history from the backend for current session."""
    data = api_get(f"/sessions/{st.session_state.session_id}/messages")
    if data and isinstance(data, list):
        st.session_state.messages = []
        for msg in data:
            entry = {"role": msg["role"], "content": msg["content"]}
            if msg.get("metadata"):
                entry["sources"] = msg["metadata"].get("sources", [])
                entry["tools"] = msg["metadata"].get("tool_calls", [])
            st.session_state.messages.append(entry)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Live Assistant")
    st.markdown("---")

    # Health status
    health = get_health()
    if health:
        ollama_ok = health.get("ollama_connected", False)
        status_icon = "🟢" if ollama_ok else "🔴"
        st.markdown(
            f"{status_icon} **Ollama** {'Connected' if ollama_ok else 'Not connected'}"
        )
        st.markdown(f"📦 **Model:** `{health.get('active_model', 'N/A')}`")
        st.markdown(f"🧠 **Memories:** {health.get('memory_entries', 0)}")
    else:
        st.markdown("🔴 **Backend** Offline")
        st.info("Start backend: `cd backend && python main.py`")

    st.markdown("---")

    # Model selector
    models_data = api_get("/models")
    if models_data and models_data.get("models"):
        available_models = models_data["models"]
        current = models_data.get("current_model", "")
        try:
            current_idx = available_models.index(current)
        except ValueError:
            current_idx = 0
        st.markdown("**Model Selection**")
        selected_model = st.selectbox(
            "Choose model",
            available_models,
            index=current_idx,
            label_visibility="collapsed",
        )
        if selected_model != current:
            st.info(f"Model switching requires restarting backend with `OLLAMA_MODEL={selected_model}`")

    st.markdown("---")

    # Conversation management
    st.markdown("**Conversations**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("🗑 Clear", use_container_width=True):
            if st.session_state.messages:
                api_delete(f"/sessions/{st.session_state.session_id}")
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()

    # Past sessions
    sessions_data = api_get("/sessions")
    if sessions_data and isinstance(sessions_data, list) and len(sessions_data) > 0:
        st.markdown("**Recent Sessions**")
        for sess in sessions_data[:8]:
            sid = sess["session_id"]
            title = sess.get("title", "Untitled")[:35]
            count = sess.get("message_count", 0)
            is_current = sid == st.session_state.session_id
            label = f"{'▶ ' if is_current else ''}{title} ({count})"
            if st.button(label, key=f"sess_{sid}", use_container_width=True):
                st.session_state.session_id = sid
                load_history_from_backend()
                st.rerun()

    st.markdown("---")

    # Tools info
    with st.expander("🛠 Available Tools"):
        st.markdown(
            """
- 🔍 **web_search** — DuckDuckGo search
- 📰 **news_search** — Latest news
- 🌐 **scrape_webpage** — Read URLs
- 🧮 **calculate** — Math expressions
- 🐍 **run_python_code** — Execute Python
- 🧠 **search_memory** — Past context
"""
        )

    with st.expander("ℹ About"):
        st.markdown(
            """
**AI Live Assistant v1.0**

Fully local, open-source AI:
- LLM: Ollama (Llama3/Mistral)
- Agent: LangGraph ReAct
- Memory: ChromaDB + sentence-transformers
- Search: DuckDuckGo
- Backend: FastAPI
- Frontend: Streamlit
"""
        )


# ─── Main chat area ───────────────────────────────────────────────────────────
# Header
col_title, col_session = st.columns([4, 1])
with col_title:
    st.markdown("# 💬 AI Live Assistant")
    st.caption("Ask anything — I'll search the web, verify facts, and cite my sources.")
with col_session:
    st.markdown(
        f'<p style="color:#8b949e; font-size:12px; text-align:right; margin-top:20px">'
        f'Session: {st.session_state.session_id[:8]}...</p>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# Load history if messages is empty but session exists
if not st.session_state.messages:
    load_history_from_backend()

# ── Message history ────────────────────────────────────────────────────────────
chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        # Welcome screen
        st.markdown(
            """
<div style="text-align:center; padding: 60px 20px; color: #8b949e;">
    <div style="font-size: 64px; margin-bottom: 20px;">🤖</div>
    <h2 style="color: #e6edf3; margin-bottom: 12px;">How can I help you today?</h2>
    <p style="font-size: 16px; max-width: 500px; margin: 0 auto;">
        I can search the web, read URLs, run calculations, execute code,
        and remember our past conversations.
    </p>
</div>
""",
            unsafe_allow_html=True,
        )

        # Example prompts
        st.markdown("### Try asking:")
        cols = st.columns(2)
        examples = [
            ("🌐 Web Search", "What are the latest developments in AI this week?"),
            ("📰 News", "What's happening with space exploration recently?"),
            ("🧮 Math", "Calculate the compound interest on $10,000 at 7% for 20 years"),
            ("🐍 Code", "Write Python code to find all prime numbers up to 100"),
            ("📊 Analysis", "Search for recent studies on intermittent fasting benefits"),
            ("💡 General", "Explain quantum computing in simple terms"),
        ]
        for i, (label, prompt) in enumerate(examples):
            col = cols[i % 2]
            with col:
                if st.button(f"{label}\n_{prompt[:45]}..._" if len(prompt) > 45 else f"{label}\n_{prompt}_",
                             key=f"example_{i}", use_container_width=True):
                    # Inject example as a chat message
                    st.session_state["pending_prompt"] = prompt
                    st.rerun()
    else:
        for msg in st.session_state.messages:
            render_message(msg)


# ─── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask me anything... (Shift+Enter for new line)", key="chat_input")

# Handle example prompt injection
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")

if prompt and prompt.strip():
    # Add user message to UI immediately
    user_msg = {"role": "user", "content": prompt.strip()}
    st.session_state.messages.append(user_msg)

    with chat_container:
        render_message(user_msg)

        # Show thinking indicator
        thinking_placeholder = st.empty()
        with thinking_placeholder.container():
            st.markdown(
                """
<div class="loading-indicator">
    <div class="dot-pulse"></div>
    <span>Thinking and searching the web...</span>
</div>
""",
                unsafe_allow_html=True,
            )

    # Call the backend
    start = time.time()
    response = api_post(
        "/chat",
        {
            "question": prompt.strip(),
            "session_id": st.session_state.session_id,
        },
    )
    elapsed = time.time() - start

    # Clear thinking indicator
    thinking_placeholder.empty()

    if response and "error" not in response:
        answer = response.get("answer", "No answer returned.")
        sources = response.get("sources", [])
        tools = response.get("tool_calls_made", [])

        assistant_msg = {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "tools": tools,
        }
        st.session_state.messages.append(assistant_msg)

        with chat_container:
            render_message(assistant_msg)

            # Stats row
            stats_parts = [f"⏱ {elapsed:.1f}s"]
            if tools:
                stats_parts.append(f"🛠 {len(tools)} tool(s)")
            if sources:
                stats_parts.append(f"📎 {len(sources)} source(s)")
            st.caption(" · ".join(stats_parts))

    else:
        error_msg = response.get("error", "Unknown error") if response else "No response from backend"
        error_entry = {
            "role": "assistant",
            "content": f"⚠️ **Error:** {error_msg}",
        }
        st.session_state.messages.append(error_entry)
        with chat_container:
            render_message(error_entry)

    st.rerun()
