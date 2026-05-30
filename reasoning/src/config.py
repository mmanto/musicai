"""Configuration settings for reasoning service."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration."""

    # Service info
    SERVICE_NAME: str = "reasoning"
    SERVICE_VERSION: str = "0.1.0"

    # REST API
    REST_HOST: str = "0.0.0.0"
    REST_PORT: int = 8004

    # gRPC
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50054

    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_TOKENS: int = 2048
    OLLAMA_TIMEOUT: int = 120

    # Knowledge Graph
    KNOWLEDGE_GRAPH_URL: str = "http://knowledge-graph:8003"
    KNOWLEDGE_GRAPH_GRPC: str = "knowledge-graph:50053"

    # Redis (for corrections/learning storage)
    REDIS_URL: str = "redis://redis:6379/0"

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # RabbitMQ Queues
    QUEUE_REASONING_GENERATED: str = "reasoning.generated"
    QUEUE_REASONING_VALIDATE: str = "reasoning.validate"
    QUEUE_REASONING_RESPONSE: str = "reasoning.response"
    EXCHANGE_REASONING: str = "musicai.reasoning"

    # Chain of Thought
    COT_MAX_STEPS: int = 5
    COT_TEMPERATURE: float = 0.3
    COT_USE_EXAMPLES: bool = True

    # Music21 settings
    MUSIC21_CACHE_DIR: str = "./cache/music21"
    MUSIC21_USE_LILYPOND: bool = False

    # Processing
    BATCH_SIZE: int = 16
    MAX_WORKERS: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
