"""REST API routes for RLHF service."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from .schemas import (
    HealthResponse, PreferenceFeedbackRequest, RatingFeedbackRequest,
    FeedbackResponse, TrainingRequest, TrainingStatus,
    EvaluateRequest, EvaluateResponse, GenerateRequest, GenerateResponse,
    FeedbackStatistics, ModelStatistics, ExperimentInfo, GenerationSample
)

from ...reward.feedback_collector import FeedbackCollector, FeedbackType
from ...reward.reward_model import RewardModel
from ...config import get_settings

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["rlhf"])

# Global components (will be properly initialized in main.py)
feedback_collector: FeedbackCollector = None
reward_model: RewardModel = None
training_jobs: Dict[str, Dict[str, Any]] = {}


def init_components():
    """Initialize API components."""
    global feedback_collector, reward_model

    feedback_collector = FeedbackCollector()
    reward_model = RewardModel(reward_type="pairwise")

    logger.info("API components initialized")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health."""
    settings = get_settings()

    components = {
        "feedback_collector": feedback_collector is not None,
        "reward_model": reward_model is not None,
    }

    all_healthy = all(components.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        components=components
    )


@router.post("/feedback/preference", response_model=FeedbackResponse)
async def submit_preference_feedback(request: PreferenceFeedbackRequest):
    """Submit preference feedback (A vs B comparison)."""
    try:
        feedback = feedback_collector.add_preference(
            feedback_id=request.feedback_id,
            music_id=request.music_id,
            user_id=request.user_id,
            preferred_id=request.preferred_id,
            rejected_id=request.rejected_id,
            aspects=request.aspects,
            confidence=request.confidence,
            comments=request.comments,
        )

        logger.info(f"Preference feedback received: {request.feedback_id}")

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            status="success",
            message="Preference feedback recorded successfully"
        )

    except Exception as e:
        logger.error(f"Error submitting preference feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/feedback/rating", response_model=FeedbackResponse)
async def submit_rating_feedback(request: RatingFeedbackRequest):
    """Submit rating feedback."""
    try:
        feedback = feedback_collector.add_rating(
            feedback_id=request.feedback_id,
            music_id=request.music_id,
            user_id=request.user_id,
            rating=request.rating,
            max_rating=request.max_rating,
            aspects=request.aspects,
            comments=request.comments,
        )

        logger.info(f"Rating feedback received: {request.feedback_id}")

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            status="success",
            message="Rating feedback recorded successfully"
        )

    except Exception as e:
        logger.error(f"Error submitting rating feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/feedback/stats", response_model=FeedbackStatistics)
async def get_feedback_statistics():
    """Get feedback statistics."""
    try:
        stats = feedback_collector.get_statistics()

        return FeedbackStatistics(**stats)

    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/train", response_model=TrainingStatus)
async def start_training(request: TrainingRequest):
    """Start a training job."""
    try:
        job_id = str(uuid.uuid4())

        # Create training job
        training_jobs[job_id] = {
            "job_id": job_id,
            "experiment_name": request.experiment_name,
            "algorithm": request.algorithm,
            "status": "pending",
            "progress": 0.0,
            "current_step": 0,
            "total_steps": request.num_steps or 10000,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "metrics": {},
        }

        logger.info(f"Training job created: {job_id}")

        return TrainingStatus(**training_jobs[job_id])

    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/train/{job_id}", response_model=TrainingStatus)
async def get_training_status(job_id: str):
    """Get training job status."""
    if job_id not in training_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    return TrainingStatus(**training_jobs[job_id])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_music(request: EvaluateRequest):
    """Evaluate music quality using reward model."""
    try:
        import torch

        # Create dummy embedding for testing
        # In production, would decode music_data and generate embeddings
        embedding = torch.randn(1, 768)

        # Evaluate
        result = reward_model.evaluate_pointwise(embedding)

        return EvaluateResponse(
            score=result.score,
            confidence=result.confidence,
            aspects=result.breakdown,
            metadata=result.metadata
        )

    except Exception as e:
        logger.error(f"Error evaluating music: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate", response_model=GenerateResponse)
async def generate_music(request: GenerateRequest):
    """Generate music using RLHF-trained model."""
    try:
        request_id = str(uuid.uuid4())

        # Generate samples (simplified)
        samples = []
        for i in range(request.num_samples):
            sample = GenerationSample(
                sample_id=f"{request_id}_{i}",
                tokens=[1, 2, 3, 4, 5],  # Placeholder
                score=0.75 + (i * 0.05),
                aspects={
                    "harmony": 0.8,
                    "melody": 0.7,
                    "rhythm": 0.75,
                }
            )
            samples.append(sample)

        return GenerateResponse(
            request_id=request_id,
            samples=samples,
            metadata={
                "prompt": request.prompt,
                "temperature": request.temperature,
                "max_length": request.max_length,
            }
        )

    except Exception as e:
        logger.error(f"Error generating music: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/experiments", response_model=list[ExperimentInfo])
async def list_experiments():
    """List all training experiments."""
    experiments = []

    for job_id, job_data in training_jobs.items():
        exp = ExperimentInfo(
            experiment_id=job_id,
            name=job_data["experiment_name"],
            algorithm=job_data["algorithm"],
            status=job_data["status"],
            metrics=job_data.get("metrics", {}),
            created_at=job_data["start_time"],
            updated_at=job_data.get("end_time", job_data["start_time"])
        )
        experiments.append(exp)

    return experiments
