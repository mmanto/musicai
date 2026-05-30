"""Configuration settings for knowledge-graph service."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration."""

    # Service info
    SERVICE_NAME: str = "knowledge-graph"
    SERVICE_VERSION: str = "0.1.0"

    # REST API
    REST_HOST: str = "0.0.0.0"
    REST_PORT: int = 8003

    # gRPC
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50053

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "musicai_password"
    NEO4J_DATABASE: str = "musicai"

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # RabbitMQ Queues
    QUEUE_KNOWLEDGE_FEATURES: str = "knowledge.features"
    QUEUE_KNOWLEDGE_RESPONSE: str = "knowledge.response"
    EXCHANGE_KNOWLEDGE: str = "musicai.knowledge"

    # GNN Model
    GNN_EMBEDDING_DIM: int = 256
    GNN_HIDDEN_DIM: int = 512
    GNN_NUM_LAYERS: int = 3
    GNN_DROPOUT: float = 0.1
    GNN_MODEL_PATH: str = "./models/gnn_model.pt"

    # Processing
    BATCH_SIZE: int = 32
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
