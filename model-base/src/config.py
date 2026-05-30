"""Configuration settings for the model-base module."""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Info
    SERVICE_NAME: str = "model-base"
    SERVICE_VERSION: str = "0.1.0"

    # API Configuration
    REST_HOST: str = "0.0.0.0"
    REST_PORT: int = 8002
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50052

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    RABBITMQ_PREFETCH_COUNT: int = 5

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL: int = 3600

    # Other Modules (gRPC endpoints)
    PREPROCESSING_GRPC: str = "preprocessing:50051"
    KNOWLEDGE_GRAPH_GRPC: str = "knowledge-graph:50053"
    REASONING_GRPC: str = "reasoning:50054"

    # Model Configuration
    CHECKPOINT_DIR: str = "/app/checkpoints"

    # Transformer Architecture
    VOCAB_SIZE: int = 30000
    D_MODEL: int = 512
    N_HEADS: int = 8
    N_LAYERS: int = 12
    D_FF: int = 2048
    MAX_SEQ_LENGTH: int = 8192
    DROPOUT: float = 0.1

    # Relative Attention
    MAX_RELATIVE_POSITION: int = 512

    # Generation
    DEFAULT_TEMPERATURE: float = 1.0
    DEFAULT_TOP_K: int = 50
    DEFAULT_TOP_P: float = 0.95
    MAX_GENERATION_LENGTH: int = 2048

    # Device
    DEVICE: str = "cuda"  # cuda or cpu
    USE_FP16: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


class ModelConfig(BaseSettings):
    """Model-specific configuration."""

    vocab_size: int = 30000
    d_model: int = 512
    n_heads: int = 8
    n_layers: int = 12
    d_ff: int = 2048
    max_seq_length: int = 8192
    dropout: float = 0.1
    max_relative_position: int = 512

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModelConfig":
        return cls(
            vocab_size=settings.VOCAB_SIZE,
            d_model=settings.D_MODEL,
            n_heads=settings.N_HEADS,
            n_layers=settings.N_LAYERS,
            d_ff=settings.D_FF,
            max_seq_length=settings.MAX_SEQ_LENGTH,
            dropout=settings.DROPOUT,
            max_relative_position=settings.MAX_RELATIVE_POSITION,
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
