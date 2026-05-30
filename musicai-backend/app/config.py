"""Application configuration using Pydantic Settings."""

from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "MusicAI"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # Ollama LLM
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1"

    # ChromaDB RAG
    chroma_persist_directory: str = "/app/chromadb_data"

    # Storage
    storage_path: str = "/app/storage"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    log_level: str = "INFO"


# Global settings instance
settings = Settings()
