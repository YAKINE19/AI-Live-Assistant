"""ChromaDB vector store for semantic memory retrieval."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
import logging
from typing import Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from config import settings

logger = logging.getLogger(__name__)

# Singleton instances
_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_model: Optional[SentenceTransformer] = None
_collection = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformers model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _embed(text: str) -> list[float]:
    """Generate embedding for a text string."""
    model = _get_embedding_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def add_memory(
    text: str,
    session_id: str,
    role: str = "user",
    metadata: Optional[dict] = None,
) -> str:
    """
    Add a memory entry to the vector store.

    Args:
        text: The text content to store
        session_id: Session identifier
        role: 'user' or 'assistant'
        metadata: Additional metadata

    Returns:
        The ID of the stored memory
    """
    try:
        collection = _get_collection()
        embedding = _embed(text)

        # Generate stable ID from content hash
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        doc_id = f"{session_id}_{role}_{content_hash}"

        meta = {
            "session_id": session_id,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            "text_preview": text[:200],
        }
        if metadata:
            meta.update(metadata)

        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta],
        )
        return doc_id

    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        return ""


def search_memory(
    query: str,
    n_results: int = 5,
    session_id: Optional[str] = None,
) -> list[dict]:
    """
    Search for semantically similar memories.

    Args:
        query: Search query
        n_results: Number of results to return
        session_id: Optional filter by session

    Returns:
        List of matching memories with text and metadata
    """
    try:
        collection = _get_collection()

        # Check if collection has documents
        if collection.count() == 0:
            return []

        embedding = _embed(query)

        where_filter = None
        if session_id:
            where_filter = {"session_id": session_id}

        kwargs = {
            "query_embeddings": [embedding],
            "n_results": min(n_results, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = collection.query(**kwargs)

        memories = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                similarity = 1 - distance  # cosine distance to similarity
                if similarity > 0.3:  # Relevance threshold
                    memories.append(
                        {
                            "text": doc,
                            "metadata": results["metadatas"][0][i],
                            "similarity": round(similarity, 3),
                        }
                    )

        return memories

    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return []


def delete_session_memories(session_id: str) -> int:
    """Delete all memories for a session. Returns count deleted."""
    try:
        collection = _get_collection()
        results = collection.get(where={"session_id": session_id})
        if results and results.get("ids"):
            ids = results["ids"]
            collection.delete(ids=ids)
            return len(ids)
        return 0
    except Exception as e:
        logger.error(f"Failed to delete session memories: {e}")
        return 0


def get_memory_count() -> int:
    """Return total number of stored memories."""
    try:
        return _get_collection().count()
    except Exception:
        return 0
