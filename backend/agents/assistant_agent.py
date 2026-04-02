"""
Core AI assistant agent built with LangGraph ReAct pattern.
Supports web search, page scraping, calculation, code execution, and memory.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Optional, AsyncGenerator
from datetime import datetime

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from tools.web_search import web_search, news_search
from tools.web_scraper import scrape_webpage
from tools.calculator import calculate
from tools.code_executor import run_python_code
from memory.vector_store import add_memory, search_memory
from memory.conversation_store import (
    add_message,
    get_messages,
    build_langchain_messages,
)
from config import settings

logger = logging.getLogger(__name__)

# ─── Memory search tool (session-aware closure) ──────────────────────────────

def make_memory_search_tool(session_id: str):
    """Create a memory search tool bound to a specific session."""

    @tool
    def search_past_conversations(query: str) -> str:
        """
        Search your memory for relevant information from past conversations.
        Use this to recall previous discussions, user preferences, or facts
        shared in earlier sessions.

        Args:
            query: What to search for in past conversations

        Returns:
            Relevant past conversation excerpts
        """
        results = search_memory(query, n_results=5)
        if not results:
            return "No relevant memories found."

        lines = [f"Relevant memories for '{query}':\n"]
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            role = meta.get("role", "unknown")
            ts = meta.get("timestamp", "")[:10]
            similarity = r.get("similarity", 0)
            lines.append(
                f"[{i}] [{role.upper()}] (similarity: {similarity:.2f}, date: {ts})\n"
                f"    {r['text'][:400]}\n"
            )
        return "\n".join(lines)

    return search_past_conversations


# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligent AI assistant with access to real-time web search, \
memory, code execution, and calculation tools.

Today's date: {date}

## Your capabilities:
- **web_search**: Search the internet for current information, facts, news
- **news_search**: Find recent news articles
- **scrape_webpage**: Read the full content of any URL
- **calculate**: Evaluate mathematical expressions
- **run_python_code**: Execute Python code for analysis or demonstration
- **search_past_conversations**: Recall relevant past discussions

## Guidelines:
1. **Always search first** for factual questions requiring current data
2. **Verify answers** by scraping key sources when precision matters
3. **Cite your sources** — include URLs in your responses
4. **Use memory** to recall user preferences and prior context
5. **Be concise but thorough** — give complete answers without padding
6. **Show your reasoning** when using multiple tools

## Response format:
- Use markdown for formatting (headers, bullets, code blocks)
- Include source URLs as clickable markdown links: [Title](URL)
- For calculations, show the steps
- For code, include explanations

You are helpful, accurate, and honest. If you cannot find reliable information, say so."""


# ─── Agent factory ────────────────────────────────────────────────────────────

def _build_agent(session_id: str):
    """Build a LangGraph ReAct agent for the given session."""
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
        num_ctx=4096,
    )

    memory_tool = make_memory_search_tool(session_id)

    tools = [
        web_search,
        news_search,
        scrape_webpage,
        calculate,
        run_python_code,
        memory_tool,
    ]

    system_message = SYSTEM_PROMPT.format(date=datetime.utcnow().strftime("%Y-%m-%d"))

    agent = create_react_agent(
        llm,
        tools,
        prompt=system_message,
    )
    return agent


# ─── Main chat function ───────────────────────────────────────────────────────

async def run_chat(
    question: str,
    session_id: str,
) -> dict:
    """
    Run the assistant agent on a user question.

    Args:
        question: The user's question
        session_id: Session ID for conversation continuity

    Returns:
        dict with keys: answer, sources, tool_calls_made, session_id
    """
    # Save user message to history + vector memory
    add_message(session_id, "user", question)
    add_memory(question, session_id, role="user")

    # Build agent with session context
    agent = _build_agent(session_id)

    # Build message history for context
    history = build_langchain_messages(session_id, limit=6)  # last 6 exchanges

    # Construct messages: history + current question
    lc_messages = []
    for msg in history[:-1]:  # exclude the current question we just added
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    # Add current question
    lc_messages.append(HumanMessage(content=question))

    try:
        # Run the agent
        result = await agent.ainvoke({"messages": lc_messages})

        # Extract final answer
        final_message = result["messages"][-1]
        answer = final_message.content if hasattr(final_message, "content") else str(final_message)

        # Extract sources from tool call results
        sources = _extract_sources(result.get("messages", []))

        # Extract tool usage summary
        tool_calls_made = _extract_tool_calls(result.get("messages", []))

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        answer = (
            f"I encountered an error processing your request: {str(e)}\n\n"
            "Please ensure Ollama is running: `ollama serve` and the model is available: "
            f"`ollama pull {settings.OLLAMA_MODEL}`"
        )
        sources = []
        tool_calls_made = []

    # Save assistant answer to history + vector memory
    add_message(
        session_id,
        "assistant",
        answer,
        metadata={"sources": sources, "tool_calls": tool_calls_made},
    )
    add_memory(answer, session_id, role="assistant")

    return {
        "answer": answer,
        "sources": sources,
        "tool_calls_made": tool_calls_made,
        "session_id": session_id,
    }


def _extract_sources(messages: list) -> list[str]:
    """Extract URLs from tool messages in the agent's message list."""
    sources = []
    for msg in messages:
        # Tool result messages
        content = ""
        if hasattr(msg, "content"):
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list):
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in msg.content
                )

        # Find URLs in the content
        import re
        urls = re.findall(r"https?://[^\s\)\]\,\"\']+", content)
        for url in urls:
            # Clean trailing punctuation
            url = url.rstrip(".,;:!?)")
            if url not in sources and len(url) > 10:
                sources.append(url)

    return sources[:10]  # Cap at 10 sources


def _extract_tool_calls(messages: list) -> list[str]:
    """Extract a list of tool names called during the agent run."""
    tool_calls = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                if name and name not in tool_calls:
                    tool_calls.append(name)
        # Also check additional_kwargs for older LangChain versions
        if hasattr(msg, "additional_kwargs"):
            tcs = msg.additional_kwargs.get("tool_calls", [])
            for tc in tcs:
                name = tc.get("function", {}).get("name", "")
                if name and name not in tool_calls:
                    tool_calls.append(name)
    return tool_calls
