"""
Correction Store - Persistent storage for user corrections.

Uses Redis to store corrections that the system can learn from.
Corrections are indexed by concept type for efficient retrieval.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import redis
from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Correction:
    """A user correction to the system's response."""
    id: str
    session_id: str
    original_response: str
    user_correction: str
    concept_type: str  # scale, chord, arpeggio, theory, etc.
    concept_details: Dict[str, Any]  # tonic, scale_type, etc.
    timestamp: str
    applied_count: int = 0  # How many times this correction was used

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Correction":
        return cls(**data)


class CorrectionStore:
    """
    Redis-based store for user corrections.

    Keys structure:
    - corrections:{concept_type}:{id} -> Correction JSON
    - corrections:index:{concept_type} -> Set of correction IDs
    - corrections:session:{session_id} -> Set of correction IDs
    - corrections:all -> Sorted set by timestamp
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the correction store."""
        settings = get_settings()
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self._client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Using in-memory fallback.")
            self._client = None
            self._memory_store: Dict[str, Any] = {
                "corrections": {},
                "by_concept": {},
                "by_session": {},
            }

    def add_correction(self, correction: Correction) -> bool:
        """
        Add a new correction to the store.

        Args:
            correction: The correction to add

        Returns:
            True if successful
        """
        try:
            if self._client:
                # Store the correction
                key = f"corrections:{correction.concept_type}:{correction.id}"
                self._client.set(key, json.dumps(correction.to_dict()))

                # Index by concept type
                self._client.sadd(f"corrections:index:{correction.concept_type}", correction.id)

                # Index by session
                self._client.sadd(f"corrections:session:{correction.session_id}", correction.id)

                # Add to global sorted set (by timestamp)
                timestamp = datetime.fromisoformat(correction.timestamp).timestamp()
                self._client.zadd("corrections:all", {correction.id: timestamp})

                logger.info(f"Stored correction {correction.id} for concept {correction.concept_type}")
                return True
            else:
                # In-memory fallback
                self._memory_store["corrections"][correction.id] = correction.to_dict()

                if correction.concept_type not in self._memory_store["by_concept"]:
                    self._memory_store["by_concept"][correction.concept_type] = set()
                self._memory_store["by_concept"][correction.concept_type].add(correction.id)

                if correction.session_id not in self._memory_store["by_session"]:
                    self._memory_store["by_session"][correction.session_id] = set()
                self._memory_store["by_session"][correction.session_id].add(correction.id)

                logger.info(f"Stored correction {correction.id} in memory")
                return True

        except Exception as e:
            logger.error(f"Error storing correction: {e}")
            return False

    def get_corrections_for_concept(
        self,
        concept_type: str,
        limit: int = 10
    ) -> List[Correction]:
        """
        Get corrections for a specific concept type.

        Args:
            concept_type: Type of concept (scale, chord, etc.)
            limit: Maximum number of corrections to return

        Returns:
            List of corrections
        """
        corrections = []
        try:
            if self._client:
                # Get correction IDs for this concept type
                ids = self._client.smembers(f"corrections:index:{concept_type}")

                for cid in list(ids)[:limit]:
                    data = self._client.get(f"corrections:{concept_type}:{cid}")
                    if data:
                        corrections.append(Correction.from_dict(json.loads(data)))
            else:
                # In-memory fallback
                ids = self._memory_store["by_concept"].get(concept_type, set())
                for cid in list(ids)[:limit]:
                    if cid in self._memory_store["corrections"]:
                        corrections.append(
                            Correction.from_dict(self._memory_store["corrections"][cid])
                        )

        except Exception as e:
            logger.error(f"Error retrieving corrections: {e}")

        return corrections

    def get_all_corrections(self, limit: int = 50) -> List[Correction]:
        """
        Get all corrections, ordered by recency.

        Args:
            limit: Maximum number to return

        Returns:
            List of corrections
        """
        corrections = []
        try:
            if self._client:
                # Get recent correction IDs
                ids = self._client.zrevrange("corrections:all", 0, limit - 1)

                for cid in ids:
                    # We need to find the concept type for this ID
                    # Check each concept type index
                    for concept_type in ["scale", "chord", "arpeggio", "theory", "general"]:
                        data = self._client.get(f"corrections:{concept_type}:{cid}")
                        if data:
                            corrections.append(Correction.from_dict(json.loads(data)))
                            break
            else:
                # In-memory fallback
                all_corrections = list(self._memory_store["corrections"].values())
                all_corrections.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                corrections = [Correction.from_dict(c) for c in all_corrections[:limit]]

        except Exception as e:
            logger.error(f"Error retrieving all corrections: {e}")

        return corrections

    def get_corrections_for_session(self, session_id: str) -> List[Correction]:
        """Get all corrections made in a session."""
        corrections = []
        try:
            if self._client:
                ids = self._client.smembers(f"corrections:session:{session_id}")
                for cid in ids:
                    for concept_type in ["scale", "chord", "arpeggio", "theory", "general"]:
                        data = self._client.get(f"corrections:{concept_type}:{cid}")
                        if data:
                            corrections.append(Correction.from_dict(json.loads(data)))
                            break
            else:
                ids = self._memory_store["by_session"].get(session_id, set())
                for cid in ids:
                    if cid in self._memory_store["corrections"]:
                        corrections.append(
                            Correction.from_dict(self._memory_store["corrections"][cid])
                        )
        except Exception as e:
            logger.error(f"Error retrieving session corrections: {e}")

        return corrections

    def increment_applied_count(self, correction_id: str, concept_type: str):
        """Increment the count of times a correction was applied."""
        try:
            if self._client:
                key = f"corrections:{concept_type}:{correction_id}"
                data = self._client.get(key)
                if data:
                    correction = json.loads(data)
                    correction["applied_count"] = correction.get("applied_count", 0) + 1
                    self._client.set(key, json.dumps(correction))
            else:
                if correction_id in self._memory_store["corrections"]:
                    self._memory_store["corrections"][correction_id]["applied_count"] += 1
        except Exception as e:
            logger.error(f"Error incrementing applied count: {e}")

    def format_corrections_for_prompt(
        self,
        concept_type: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Format corrections as context for the LLM prompt.

        Args:
            concept_type: Optional filter by concept type
            limit: Maximum corrections to include

        Returns:
            Formatted string for prompt injection
        """
        if concept_type:
            corrections = self.get_corrections_for_concept(concept_type, limit)
        else:
            corrections = self.get_all_corrections(limit)

        if not corrections:
            return ""

        lines = ["\n[CORRECCIONES ANTERIORES DEL USUARIO - IMPORTANTE: Aplica estas correcciones]"]

        for c in corrections:
            lines.append(f"- Error anterior: \"{c.original_response[:100]}...\"")
            lines.append(f"  Corrección del usuario: \"{c.user_correction}\"")
            lines.append(f"  Concepto: {c.concept_type} - {c.concept_details}")
            lines.append("")

        lines.append("[FIN DE CORRECCIONES - Evita repetir estos errores]\n")

        return "\n".join(lines)


# Global instance
_correction_store: Optional[CorrectionStore] = None


def get_correction_store() -> CorrectionStore:
    """Get the global correction store instance."""
    global _correction_store
    if _correction_store is None:
        _correction_store = CorrectionStore()
    return _correction_store
