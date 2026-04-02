"""
AI Live Assistant — FastAPI Backend
Runs the LangGraph agent with tool calling, web search, and memory.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Ensure backend package is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.routes import router
from config import settings

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown tasks."""
    logger.info("=" * 60)
    logger.info("  AI Live Assistant Starting Up")
    logger.info("=" * 60)
    logger.info(f"  Ollama URL  : {settings.OLLAMA_BASE_URL}")
    logger.info(f"  Model       : {settings.OLLAMA_MODEL}")
    logger.info(f"  ChromaDB    : {settings.CHROMA_PERSIST_DIR}")
    logger.info(f"  Conversations: {settings.CONVERSATIONS_DIR}")
    logger.info("=" * 60)

    # Ensure directories exist
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    os.makedirs(settings.CONVERSATIONS_DIR, exist_ok=True)

    # Warm up embedding model
    try:
        from memory.vector_store import _get_embedding_model
        _get_embedding_model()
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.warning(f"Embedding model warm-up failed (will retry on first request): {e}")

    logger.info("Backend ready! Visit http://localhost:8501 for the UI")

    yield  # App runs here

    logger.info("Shutting down AI Live Assistant...")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Live Assistant",
    description=(
        "A production-ready AI assistant with real-time web search, "
        "tool calling, and persistent memory powered by Ollama + LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "*",  # Allow all for dev; tighten in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api", tags=["Assistant"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "AI Live Assistant",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "chat": "/api/chat",
    }


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info",
        access_log=True,
    )
