"""Human feedback collection and management."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback."""

    PREFERENCE = "preference"  # A vs B comparison
    RATING = "rating"  # Numerical rating
    RANKING = "ranking"  # Rank multiple outputs
    BINARY = "binary"  # Accept/Reject


@dataclass
class Feedback:
    """Human feedback data structure."""

    feedback_id: str
    feedback_type: FeedbackType
    music_id: str
    user_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Preference data
    preferred_id: Optional[str] = None
    rejected_id: Optional[str] = None

    # Rating data
    rating: Optional[float] = None
    max_rating: Optional[float] = None

    # Ranking data
    rankings: Optional[List[str]] = None

    # Binary data
    accepted: Optional[bool] = None

    # Additional context
    aspects: Dict[str, float] = field(default_factory=dict)
    comments: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackCollector:
    """
    Collects and manages human feedback for music generation.

    Supports multiple feedback types:
    - Preference: Compare two outputs
    - Rating: Numerical score
    - Ranking: Order multiple outputs
    - Binary: Accept/Reject
    """

    def __init__(self):
        """Initialize feedback collector."""
        self.feedbacks: List[Feedback] = []
        logger.info("Feedback collector initialized")

    def add_preference(
        self,
        feedback_id: str,
        music_id: str,
        user_id: str,
        preferred_id: str,
        rejected_id: str,
        aspects: Optional[Dict[str, float]] = None,
        confidence: float = 1.0,
        comments: Optional[str] = None,
    ) -> Feedback:
        """
        Add preference feedback (A vs B).

        Args:
            feedback_id: Unique feedback identifier
            music_id: Music piece identifier
            user_id: User who provided feedback
            preferred_id: ID of preferred output
            rejected_id: ID of rejected output
            aspects: Quality aspect scores
            confidence: User confidence (0-1)
            comments: Optional text comments

        Returns:
            Created Feedback object
        """
        feedback = Feedback(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.PREFERENCE,
            music_id=music_id,
            user_id=user_id,
            preferred_id=preferred_id,
            rejected_id=rejected_id,
            aspects=aspects or {},
            confidence=confidence,
            comments=comments,
        )

        self.feedbacks.append(feedback)
        logger.info(f"Added preference feedback: {feedback_id}")

        return feedback

    def add_rating(
        self,
        feedback_id: str,
        music_id: str,
        user_id: str,
        rating: float,
        max_rating: float = 5.0,
        aspects: Optional[Dict[str, float]] = None,
        comments: Optional[str] = None,
    ) -> Feedback:
        """
        Add rating feedback.

        Args:
            feedback_id: Unique feedback identifier
            music_id: Music piece identifier
            user_id: User who provided feedback
            rating: Numerical rating
            max_rating: Maximum possible rating
            aspects: Quality aspect ratings
            comments: Optional text comments

        Returns:
            Created Feedback object
        """
        feedback = Feedback(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.RATING,
            music_id=music_id,
            user_id=user_id,
            rating=rating,
            max_rating=max_rating,
            aspects=aspects or {},
            comments=comments,
        )

        self.feedbacks.append(feedback)
        logger.info(f"Added rating feedback: {feedback_id} ({rating}/{max_rating})")

        return feedback

    def add_ranking(
        self,
        feedback_id: str,
        music_id: str,
        user_id: str,
        rankings: List[str],
        aspects: Optional[Dict[str, float]] = None,
        comments: Optional[str] = None,
    ) -> Feedback:
        """
        Add ranking feedback.

        Args:
            feedback_id: Unique feedback identifier
            music_id: Music piece identifier
            user_id: User who provided feedback
            rankings: Ordered list of output IDs (best first)
            aspects: Quality aspect scores
            comments: Optional text comments

        Returns:
            Created Feedback object
        """
        feedback = Feedback(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.RANKING,
            music_id=music_id,
            user_id=user_id,
            rankings=rankings,
            aspects=aspects or {},
            comments=comments,
        )

        self.feedbacks.append(feedback)
        logger.info(f"Added ranking feedback: {feedback_id} ({len(rankings)} items)")

        return feedback

    def add_binary(
        self,
        feedback_id: str,
        music_id: str,
        user_id: str,
        accepted: bool,
        aspects: Optional[Dict[str, float]] = None,
        comments: Optional[str] = None,
    ) -> Feedback:
        """
        Add binary (accept/reject) feedback.

        Args:
            feedback_id: Unique feedback identifier
            music_id: Music piece identifier
            user_id: User who provided feedback
            accepted: Whether output is accepted
            aspects: Quality aspect scores
            comments: Optional text comments

        Returns:
            Created Feedback object
        """
        feedback = Feedback(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.BINARY,
            music_id=music_id,
            user_id=user_id,
            accepted=accepted,
            aspects=aspects or {},
            comments=comments,
        )

        self.feedbacks.append(feedback)
        logger.info(f"Added binary feedback: {feedback_id} ({'accepted' if accepted else 'rejected'})")

        return feedback

    def get_feedbacks(
        self,
        feedback_type: Optional[FeedbackType] = None,
        user_id: Optional[str] = None,
        music_id: Optional[str] = None,
    ) -> List[Feedback]:
        """
        Retrieve feedbacks with optional filtering.

        Args:
            feedback_type: Filter by feedback type
            user_id: Filter by user
            music_id: Filter by music piece

        Returns:
            List of matching feedbacks
        """
        results = self.feedbacks

        if feedback_type:
            results = [f for f in results if f.feedback_type == feedback_type]

        if user_id:
            results = [f for f in results if f.user_id == user_id]

        if music_id:
            results = [f for f in results if f.music_id == music_id]

        return results

    def get_preference_pairs(self) -> List[tuple[str, str, float]]:
        """
        Get preference pairs for training.

        Returns:
            List of (preferred_id, rejected_id, confidence) tuples
        """
        pairs = []

        for feedback in self.feedbacks:
            if feedback.feedback_type == FeedbackType.PREFERENCE:
                pairs.append((
                    feedback.preferred_id,
                    feedback.rejected_id,
                    feedback.confidence
                ))

        logger.info(f"Retrieved {len(pairs)} preference pairs")
        return pairs

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Returns:
            Dictionary with statistics
        """
        if not self.feedbacks:
            return {
                "total": 0,
                "by_type": {},
                "unique_users": 0,
                "unique_music": 0,
            }

        by_type = {}
        for ftype in FeedbackType:
            count = len([f for f in self.feedbacks if f.feedback_type == ftype])
            by_type[ftype.value] = count

        unique_users = len(set(f.user_id for f in self.feedbacks))
        unique_music = len(set(f.music_id for f in self.feedbacks))

        return {
            "total": len(self.feedbacks),
            "by_type": by_type,
            "unique_users": unique_users,
            "unique_music": unique_music,
        }

    def clear(self):
        """Clear all feedback data."""
        self.feedbacks.clear()
        logger.info("Feedback collector cleared")
