"""Pydantic schemas for REST API."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class MusicFormat(str, Enum):
    """Supported music formats."""
    MUSICXML = "musicxml"
    MIDI = "midi"
    ABC = "abc"


class ReasoningModeEnum(str, Enum):
    """Reasoning modes."""
    SYMBOLIC_ONLY = "symbolic_only"
    NEURAL_ONLY = "neural_only"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"


class AnalyzeRequest(BaseModel):
    """Request to analyze a musical piece."""
    music_data: str = Field(..., description="Base64-encoded music data")
    format: MusicFormat = Field(default=MusicFormat.MUSICXML, description="Music data format")


class ReasonRequest(BaseModel):
    """Request for reasoning about music."""
    music_data: str = Field(..., description="Base64-encoded music data")
    query: str = Field(..., description="User query or reasoning task")
    mode: ReasoningModeEnum = Field(
        default=ReasoningModeEnum.HYBRID,
        description="Reasoning mode to use"
    )
    format: MusicFormat = Field(default=MusicFormat.MUSICXML, description="Music data format")


class SuggestImprovementsRequest(BaseModel):
    """Request for improvement suggestions."""
    music_data: str = Field(..., description="Base64-encoded music data")
    focus_areas: Optional[List[str]] = Field(
        default=None,
        description="Areas to focus on (harmony, melody, rhythm, etc.)"
    )
    format: MusicFormat = Field(default=MusicFormat.MUSICXML, description="Music data format")


class ValidateTheoryRequest(BaseModel):
    """Request for music theory validation."""
    music_data: str = Field(..., description="Base64-encoded music data")
    rules: Optional[List[str]] = Field(
        default=None,
        description="Specific rules to validate"
    )
    explain: bool = Field(default=True, description="Whether to explain violations")
    format: MusicFormat = Field(default=MusicFormat.MUSICXML, description="Music data format")


class ComparePiecesRequest(BaseModel):
    """Request to compare two pieces."""
    music_data1: str = Field(..., description="Base64-encoded first piece")
    music_data2: str = Field(..., description="Base64-encoded second piece")
    aspects: Optional[List[str]] = Field(
        default=None,
        description="Aspects to compare (harmony, melody, etc.)"
    )
    format1: MusicFormat = Field(default=MusicFormat.MUSICXML, description="First piece format")
    format2: MusicFormat = Field(default=MusicFormat.MUSICXML, description="Second piece format")


class ExplainConceptRequest(BaseModel):
    """Request to explain a music concept."""
    concept: str = Field(..., description="Music theory concept to explain")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional musical context"
    )
    level: str = Field(
        default="intermediate",
        description="Explanation level (beginner, intermediate, advanced)"
    )


class ChainOfThoughtRequest(BaseModel):
    """Request for chain-of-thought reasoning."""
    query: str = Field(..., description="Complex query requiring multi-step reasoning")
    context: Dict[str, Any] = Field(..., description="Musical context data")
    num_steps: Optional[int] = Field(
        default=None,
        description="Number of reasoning steps"
    )
    iterative: bool = Field(
        default=False,
        description="Whether to use iterative refinement"
    )


# Response schemas

class MetadataResponse(BaseModel):
    """Metadata from analysis."""
    title: Optional[str] = None
    composer: Optional[str] = None
    time_signature: Optional[str] = None
    key_signature: Optional[str] = None
    tempo: Optional[float] = None
    parts: int = 0
    measures: int = 0


class KeyAnalysisResponse(BaseModel):
    """Key analysis results."""
    main_key: str
    mode: str
    tonic: str
    confidence: float
    modulations: List[Dict[str, Any]] = []
    relative_key: Optional[str] = None
    parallel_key: Optional[str] = None


class ValidationResponse(BaseModel):
    """Validation results."""
    total_violations: int
    severity_counts: Dict[str, int]
    quality_score: float
    violations: List[Dict[str, Any]]
    rules_checked: int


class AnalysisResponse(BaseModel):
    """Complete analysis response."""
    metadata: MetadataResponse
    key_analysis: KeyAnalysisResponse
    harmonic_analysis: Optional[Dict[str, Any]] = None
    melodic_analysis: Optional[Dict[str, Any]] = None
    rhythmic_analysis: Optional[Dict[str, Any]] = None
    form_analysis: Optional[Dict[str, Any]] = None
    voice_leading: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResponse] = None


class ThoughtStepResponse(BaseModel):
    """A single thought step."""
    step_number: int
    question: str
    reasoning: str
    answer: str
    confidence: float


class ChainOfThoughtResponse(BaseModel):
    """Chain-of-thought reasoning result."""
    query: str
    steps: List[ThoughtStepResponse]
    final_answer: str
    total_confidence: float
    reasoning_path: List[str]


class HybridReasoningResponse(BaseModel):
    """Hybrid reasoning result."""
    query: str
    mode: ReasoningModeEnum
    symbolic_analysis: Optional[Dict[str, Any]] = None
    neural_reasoning: Optional[ChainOfThoughtResponse] = None
    synthesis: Optional[str] = None
    confidence: float
    recommendations: List[str] = []
    metadata: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Service health status."""
    status: str
    service: str
    version: str
    components: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
