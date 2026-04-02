import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "assistant_memory"

    # Search
    MAX_SEARCH_RESULTS: int = 5
    MAX_SCRAPE_LENGTH: int = 4000

    # Conversation
    CONVERSATIONS_DIR: str = "./conversations"
    MAX_HISTORY_TOKENS: int = 4000

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:8501"

    # Security
    CODE_EXECUTION_TIMEOUT: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
