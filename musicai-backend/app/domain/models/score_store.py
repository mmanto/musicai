"""
ScoreStore — in-memory store for uploaded score analyses.

Stores ScoreAnalysis objects keyed by score_id and maintains a
session → score mapping so the chat endpoints can look up context
with only a session_id when score_id is not sent explicitly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ScoreAnalysis:
    score_id: str
    file_name: str
    file_type: str              # "xml" | "gp"
    key: Optional[str] = None
    tempo: Optional[int] = None
    time_signature: Optional[str] = None
    note_count: Optional[int] = None
    chords: List[str] = field(default_factory=list)
    pitch_range: Optional[Dict[str, int]] = None
    # MusicXML-specific metadata
    title: Optional[str] = None
    composer: Optional[str] = None
    instruments: List[str] = field(default_factory=list)
    measure_count: Optional[int] = None
    # Structural metadata (forwarded from AlphaTab for GP files)
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    context_summary: str = ""

    def build_summary(self) -> str:
        lines = []

        # Identify the piece
        display_name = self.title or self.file_name
        lines.append(f'Partitura: "{display_name}"')
        if self.composer:
            lines.append(f"Compositor: {self.composer}")
        if self.title and self.title != self.file_name:
            lines.append(f"Archivo: {self.file_name}")

        # Musical analysis
        if self.key:
            lines.append(f"Tonalidad: {self.key}")
        if self.tempo:
            lines.append(f"Tempo: {self.tempo} BPM")
        if self.time_signature:
            lines.append(f"Compás: {self.time_signature}")
        if self.measure_count:
            lines.append(f"Compases: {self.measure_count}")
        if self.note_count:
            lines.append(f"Total de notas: {self.note_count}")
        if self.pitch_range:
            low = self.pitch_range.get("lowest")
            high = self.pitch_range.get("highest")
            if low is not None and high is not None:
                lines.append(f"Rango de altura: MIDI {low}–{high}")
        if self.chords:
            lines.append(f"Acordes principales: {', '.join(self.chords[:8])}")

        # Instrumentation — instruments field (MusicXML) takes priority over GP tracks
        if self.instruments:
            lines.append(f"Instrumentos: {', '.join(self.instruments[:8])}")
        elif self.tracks:
            names = [t.get("name", "") for t in self.tracks[:6] if t.get("name")]
            if names:
                lines.append(f"Instrumentos/pistas: {', '.join(names)}")

        # GP sections
        if self.sections:
            names = [s.get("label", "") for s in self.sections[:6] if s.get("label")]
            if names:
                lines.append(f"Secciones: {', '.join(names)}")

        return "\n".join(lines)


class ScoreStore:
    def __init__(self) -> None:
        self._scores: Dict[str, ScoreAnalysis] = {}
        # 1:1 mapping — a session has at most one active score
        self._session_to_score: Dict[str, str] = {}

    def save(self, analysis: ScoreAnalysis) -> None:
        analysis.context_summary = analysis.build_summary()
        self._scores[analysis.score_id] = analysis

    def get(self, score_id: str) -> Optional[ScoreAnalysis]:
        return self._scores.get(score_id)

    def link_to_session(self, session_id: str, score_id: str) -> bool:
        """Associate a score with a session. Returns False if score_id unknown."""
        if score_id not in self._scores:
            return False
        self._session_to_score[session_id] = score_id
        return True

    def get_by_session(self, session_id: str) -> Optional[ScoreAnalysis]:
        score_id = self._session_to_score.get(session_id)
        return self._scores.get(score_id) if score_id else None

    def unlink_session(self, session_id: str) -> None:
        self._session_to_score.pop(session_id, None)

    def list_all(self) -> List["ScoreAnalysis"]:
        return list(self._scores.values())


# Global singleton — consistent with ContextStore pattern in this codebase
score_store = ScoreStore()
