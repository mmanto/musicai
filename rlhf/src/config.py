"""Configuration settings for RLHF service."""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration."""

    # Service info
    SERVICE_NAME: str = "rlhf"
    SERVICE_VERSION: str = "0.1.0"

    # REST API
    REST_HOST: str = "0.0.0.0"
    REST_PORT: int = 8005

    # gRPC
    GRPC_HOST: str = "0.0.0.0"
    GRPC_PORT: int = 50055

    # External Services
    MODEL_BASE_URL: str = "http://model-base:8002"
    PREPROCESSING_URL: str = "http://preprocessing:8001"
    REASONING_URL: str = "http://reasoning:8004"

    # Reward Model
    REWARD_MODEL_PATH: str = "./models/reward_model"
    REWARD_MODEL_TYPE: Literal["pairwise", "pointwise", "ranking"] = "pairwise"
    REWARD_BATCH_SIZE: int = 16
    REWARD_MAX_LENGTH: int = 2048

    # Training Configuration
    TRAINING_ALGORITHM: Literal["ppo", "dpo", "grpo"] = "ppo"
    LEARNING_RATE: float = 1e-5
    BATCH_SIZE: int = 8
    GRADIENT_ACCUMULATION_STEPS: int = 4
    MAX_STEPS: int = 10000
    SAVE_STEPS: int = 500
    EVAL_STEPS: int = 100
    WARMUP_STEPS: int = 100

    # PPO Specific
    PPO_EPOCHS: int = 4
    PPO_CLIP_RANGE: float = 0.2
    PPO_VALUE_COEF: float = 0.1
    PPO_ENTROPY_COEF: float = 0.01

    # DPO Specific
    DPO_BETA: float = 0.1
    DPO_REFERENCE_FREE: bool = False

    # Evaluation
    EVAL_BATCH_SIZE: int = 4
    HUMAN_EVAL_ENABLED: bool = True
    HUMAN_EVAL_SAMPLE_RATE: float = 0.1

    # Experiment Tracking
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "musicai-rlhf"
    USE_TENSORBOARD: bool = True
    TENSORBOARD_LOG_DIR: str = "./runs"

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # RabbitMQ Queues
    QUEUE_RLHF_TRAIN: str = "rlhf.train"
    QUEUE_RLHF_EVAL: str = "rlhf.eval"
    QUEUE_RLHF_FEEDBACK: str = "rlhf.feedback"
    EXCHANGE_RLHF: str = "musicai.rlhf"

    # Active Learning
    ACTIVE_LEARNING_ENABLED: bool = True
    UNCERTAINTY_THRESHOLD: float = 0.7
    DIVERSITY_SAMPLING: bool = True

    # Data Paths
    TRAINING_DATA_PATH: str = "./data/training"
    FEEDBACK_DATA_PATH: str = "./data/feedback"
    CHECKPOINT_DIR: str = "./models/checkpoints"

    # Processing
    MAX_WORKERS: int = 4
    GPU_ENABLED: bool = True
    MIXED_PRECISION: Literal["fp16", "bf16", "fp32"] = "fp16"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
