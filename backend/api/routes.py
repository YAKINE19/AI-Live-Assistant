"""FastAPI route definitions for the AI assistant API."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.assistant_agent import run_chat
from memory.conversation_store import (
    get_messages,
    list_sessions,
    delete_session,
    get_session_info,
    clear_all_sessions,
)
from memory.vector_store import delete_session_memories, get_memory_count
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="User question")
    session_id: Optional[str] = Field(None, description="Session ID (creates new if omitted)")


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    tool_calls_made: list[str]
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: str
    metadata: Optional[dict] = None


# ─── Health check ─────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Check API and Ollama connectivity."""
    import httpx
    ollama_ok = False
    ollama_models = []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                data = resp.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    return {
        "status": "ok",
        "ollama_connected": ollama_ok,
        "ollama_url": settings.OLLAMA_BASE_URL,
        "active_model": settings.OLLAMA_MODEL,
        "available_models": ollama_models,
        "memory_entries": get_memory_count(),
    }


# ─── Chat endpoint ────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a question to the AI assistant.
    The agent will search the web, use tools, and return a verified answer.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Create or reuse session
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Chat request: session={session_id[:8]}... question={request.question[:80]}")

    try:
        result = await run_chat(
            question=request.question.strip(),
            session_id=session_id,
        )
        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# ─── Session endpoints ────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionInfo])
async def list_all_sessions():
    """List all conversation sessions sorted by recency."""
    return list_sessions()


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get metadata for a specific session."""
    info = get_session_info(session_id)
    if info["message_count"] == 0:
        # Check if it's a brand new session vs not found
        from memory.conversation_store import _session_path
        if not _session_path(session_id).exists():
            raise HTTPException(status_code=404, detail="Session not found")
    return info


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def get_session_messages(session_id: str, limit: Optional[int] = None):
    """Get all messages for a session."""
    messages = get_messages(session_id, limit=limit)
    return messages


@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str, background_tasks: BackgroundTasks):
    """Delete a session and its associated vector memories."""
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete vector memories in background
    background_tasks.add_task(delete_session_memories, session_id)

    return {"success": True, "session_id": session_id}


@router.delete("/sessions")
async def delete_all_sessions():
    """Delete all sessions and memories."""
    count = clear_all_sessions()
    return {"success": True, "sessions_deleted": count}


# ─── Models endpoint ──────────────────────────────────────────────────────────

@router.get("/models")
async def list_models():
    """List available Ollama models."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return {
                "models": [m["name"] for m in data.get("models", [])],
                "current_model": settings.OLLAMA_MODEL,
            }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama at {settings.OLLAMA_BASE_URL}: {str(e)}",
        )
