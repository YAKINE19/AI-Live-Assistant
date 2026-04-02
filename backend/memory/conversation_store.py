"""JSON-based conversation history store with session management."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

CONVERSATIONS_DIR = Path(settings.CONVERSATIONS_DIR)


def _session_path(session_id: str) -> Path:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return CONVERSATIONS_DIR / f"{safe_id}.json"


def _load_session(session_id: str) -> dict:
    """Load a session file, returning empty structure if not found."""
    path = _session_path(session_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load session {session_id}: {e}")
    return {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": [],
    }


def _save_session(session_id: str, data: dict) -> None:
    """Save session data to disk."""
    path = _session_path(session_id)
    data["updated_at"] = datetime.utcnow().isoformat()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Failed to save session {session_id}: {e}")


def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Add a message to the conversation history.

    Args:
        session_id: Session identifier
        role: 'user' or 'assistant'
        content: Message content
        metadata: Optional extra data (sources, tool_calls, etc.)

    Returns:
        The message dict that was saved
    """
    data = _load_session(session_id)

    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if metadata:
        message["metadata"] = metadata

    data["messages"].append(message)

    # Auto-generate title from first user message
    if role == "user" and data["title"] == "New Conversation":
        title = content[:60].strip()
        if len(content) > 60:
            title += "..."
        data["title"] = title

    _save_session(session_id, data)
    return message


def get_messages(
    session_id: str,
    limit: Optional[int] = None,
) -> list[dict]:
    """
    Retrieve messages for a session.

    Args:
        session_id: Session identifier
        limit: Optional max number of recent messages to return

    Returns:
        List of message dicts
    """
    data = _load_session(session_id)
    messages = data.get("messages", [])
    if limit:
        messages = messages[-limit:]
    return messages


def get_session_info(session_id: str) -> dict:
    """Get metadata for a session (without full message content)."""
    data = _load_session(session_id)
    messages = data.get("messages", [])
    return {
        "session_id": session_id,
        "title": data.get("title", "Untitled"),
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "message_count": len(messages),
    }


def list_sessions() -> list[dict]:
    """List all sessions, sorted by most recently updated."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in CONVERSATIONS_DIR.glob("*.json"):
        session_id = path.stem
        try:
            info = get_session_info(session_id)
            sessions.append(info)
        except Exception as e:
            logger.error(f"Failed to read session {session_id}: {e}")

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session and its messages. Returns True if deleted."""
    path = _session_path(session_id)
    if path.exists():
        try:
            path.unlink()
            return True
        except IOError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
    return False


def clear_all_sessions() -> int:
    """Delete all sessions. Returns count deleted."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in CONVERSATIONS_DIR.glob("*.json"):
        try:
            path.unlink()
            count += 1
        except IOError:
            pass
    return count


def build_langchain_messages(session_id: str, limit: int = 10) -> list[dict]:
    """
    Build a list of LangChain-compatible message dicts for chat history.

    Args:
        session_id: Session identifier
        limit: Max number of recent exchanges to include

    Returns:
        List of {"role": ..., "content": ...} dicts
    """
    messages = get_messages(session_id, limit=limit * 2)
    return [{"role": m["role"], "content": m["content"]} for m in messages]
