"""Configuration settings for the preprocessing module."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Info
    SERVICE_NAME: str = "preprocessing"
    SERVICE_VERSION: str = "0.1.0"

    # API Configuration
    REST_HOST: str = "0.0.0.0"
    REST_PORT: int = 8001
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50051

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    RABBITMQ_PREFETCH_COUNT: int = 10

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL: int = 3600  # 1 hour

    # Other Modules (gRPC endpoints)
    MODEL_BASE_GRPC: str = "model-base:50052"
    KNOWLEDGE_GRAPH_GRPC: str = "knowledge-graph:50053"
    REASONING_GRPC: str = "reasoning:50054"

    # Processing
    AUDIO_CACHE_DIR: str = "/app/cache"
    MAX_AUDIO_DURATION: int = 600  # 10 minutes max
    SAMPLE_RATE: int = 22050

    # Tokenizer
    BPE_VOCAB_SIZE: int = 30000
    MAX_SEQ_LENGTH: int = 8192

    # Feature Extraction
    N_MELS: int = 128
    N_FFT: int = 2048
    HOP_LENGTH: int = 512

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
