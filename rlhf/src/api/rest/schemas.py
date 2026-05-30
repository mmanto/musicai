"""API request/response schemas."""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class TrainingAlgorithm(str, Enum):
    """Training algorithm types."""

    PPO = "ppo"
    DPO = "dpo"
    GRPO = "grpo"


class FeedbackTypeEnum(str, Enum):
    """Feedback types for API."""

    PREFERENCE = "preference"
    RATING = "rating"
    RANKING = "ranking"
    BINARY = "binary"


# Health Check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    components: Dict[str, bool] = {}


# Feedback Schemas
class PreferenceFeedbackRequest(BaseModel):
    """Preference feedback request."""

    feedback_id: str
    music_id: str
    user_id: str
    preferred_id: str
    rejected_id: str
    aspects: Optional[Dict[str, float]] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    comments: Optional[str] = None


class RatingFeedbackRequest(BaseModel):
    """Rating feedback request."""

    feedback_id: str
    music_id: str
    user_id: str
    rating: float
    max_rating: float = 5.0
    aspects: Optional[Dict[str, float]] = None
    comments: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    feedback_id: str
    status: str
    message: str


# Training Schemas
class TrainingRequest(BaseModel):
    """Training job request."""

    experiment_name: str
    algorithm: TrainingAlgorithm
    num_steps: Optional[int] = None
    batch_size: Optional[int] = None
    learning_rate: Optional[float] = None
    use_feedback_data: bool = True
    config: Optional[Dict[str, Any]] = None


class TrainingStatus(BaseModel):
    """Training status response."""

    job_id: str
    status: str  # pending, running, completed, failed
    progress: float = Field(ge=0.0, le=1.0)
    current_step: int
    total_steps: int
    metrics: Dict[str, float] = {}
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# Evaluation Schemas
class EvaluateRequest(BaseModel):
    """Evaluation request."""

    music_data: str  # Base64-encoded
    format: str = "tokens"
    return_aspects: bool = True


class EvaluateResponse(BaseModel):
    """Evaluation response."""

    score: float
    confidence: float
    aspects: Dict[str, float] = {}
    metadata: Dict[str, Any] = {}


# Generation Schemas
class GenerateRequest(BaseModel):
    """Generation request with RLHF."""

    prompt: str
    max_length: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=1.0, ge=0.1, le=2.0)
    num_samples: int = Field(default=1, ge=1, le=10)
    use_rlhf_model: bool = True


class GenerationSample(BaseModel):
    """Single generation sample."""

    sample_id: str
    tokens: List[int]
    score: float
    aspects: Dict[str, float] = {}


class GenerateResponse(BaseModel):
    """Generation response."""

    request_id: str
    samples: List[GenerationSample]
    metadata: Dict[str, Any] = {}


# Statistics Schemas
class FeedbackStatistics(BaseModel):
    """Feedback statistics."""

    total: int
    by_type: Dict[str, int]
    unique_users: int
    unique_music: int


class ModelStatistics(BaseModel):
    """Model training statistics."""

    total_steps: int
    total_experiments: int
    best_score: Optional[float] = None
    latest_checkpoint: Optional[str] = None


# Experiment Tracking
class ExperimentInfo(BaseModel):
    """Experiment information."""

    experiment_id: str
    name: str
    algorithm: str
    status: str
    metrics: Dict[str, Any] = {}
    created_at: str
    updated_at: str
