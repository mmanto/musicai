"""REST API routes for reasoning service."""

import logging
import base64
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from .schemas import (
    AnalyzeRequest, ReasonRequest, SuggestImprovementsRequest,
    ValidateTheoryRequest, ComparePiecesRequest, ExplainConceptRequest,
    ChainOfThoughtRequest, AnalysisResponse, HybridReasoningResponse,
    ChainOfThoughtResponse, HealthResponse, ErrorResponse,
    ThoughtStepResponse
)

from ...symbolic.music21_analyzer import Music21Analyzer
from ...symbolic.rules_engine import RulesEngine, RuleSeverity
from ...neural.llm_client import OllamaClient
from ...neural.chain_of_thought import ChainOfThought
from ...hybrid.reasoner import HybridReasoner, ReasoningMode
from ...utils.pattern_parser import PatternParser
from ...config import get_settings

# Import chat teacher router
from . import chat_teacher

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["reasoning"])

# Initialize components (will be set in main.py)
music_analyzer: Music21Analyzer = None
rules_engine: RulesEngine = None
llm_client: OllamaClient = None
cot_engine: ChainOfThought = None
hybrid_reasoner: HybridReasoner = None
pattern_parser: PatternParser = None


def get_settings_dep():
    """Dependency for settings."""
    return get_settings()


def init_components():
    """Initialize API components."""
    global music_analyzer, rules_engine, llm_client, cot_engine, hybrid_reasoner, pattern_parser

    music_analyzer = Music21Analyzer()
    rules_engine = RulesEngine()
    llm_client = OllamaClient()
    cot_engine = ChainOfThought(llm_client)
    hybrid_reasoner = HybridReasoner(
        music_analyzer=music_analyzer,
        rules_engine=rules_engine,
        llm_client=llm_client,
        cot_engine=cot_engine
    )

    # Initialize pattern parser for chat teacher
    pattern_parser = PatternParser()

    # Initialize chat teacher components
    chat_teacher.init_components(music_analyzer, llm_client, pattern_parser)

    logger.info("API components initialized (including chat teacher)")


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: dict = Depends(get_settings_dep)):
    """
    Check service health.

    Returns health status of all components.
    """
    components = {
        "music_analyzer": music_analyzer is not None,
        "rules_engine": rules_engine is not None,
        "llm_client": llm_client is not None,
        "cot_engine": cot_engine is not None,
        "hybrid_reasoner": hybrid_reasoner is not None
    }

    # Check LLM availability
    if llm_client:
        try:
            llm_available = await llm_client.check_health()
            components["ollama"] = llm_available
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            components["ollama"] = False

    all_healthy = all(components.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        components=components
    )


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_music(request: AnalyzeRequest):
    """
    Analyze a musical piece using symbolic analysis.

    Provides comprehensive analysis including:
    - Key and harmonic analysis
    - Melodic analysis
    - Rhythmic analysis
    - Form analysis
    - Voice leading analysis
    - Music theory validation
    """
    try:
        # Decode music data
        music_data = base64.b64decode(request.music_data)

        # Perform analysis
        analysis = music_analyzer.analyze_score(music_data, request.format.value)

        # Validate
        validation = rules_engine.validate(analysis, min_severity=RuleSeverity.INFO)
        analysis["validation"] = validation

        logger.info("Music analysis completed successfully")

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing music: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/reason", response_model=HybridReasoningResponse)
async def reason_about_music(request: ReasonRequest):
    """
    Perform hybrid reasoning about music.

    Combines symbolic analysis with neural reasoning to answer
    complex questions about musical pieces.

    Supports multiple reasoning modes:
    - symbolic_only: Use only music21 analysis
    - neural_only: Use only LLM reasoning
    - hybrid: Combine both approaches
    - adaptive: Automatically select best mode
    """
    try:
        # Decode music data
        music_data = base64.b64decode(request.music_data)

        # Convert mode enum to ReasoningMode
        mode = ReasoningMode(request.mode.value)

        # Perform reasoning
        result = await hybrid_reasoner.reason(
            music_data=music_data,
            query=request.query,
            mode=mode,
            format=request.format.value
        )

        # Convert to response model
        response = HybridReasoningResponse(
            query=result.query,
            mode=request.mode,
            symbolic_analysis=result.symbolic_analysis,
            neural_reasoning=_convert_cot_result(result.neural_reasoning)
                if result.neural_reasoning else None,
            synthesis=result.synthesis,
            confidence=result.confidence,
            recommendations=result.recommendations,
            metadata=result.metadata
        )

        logger.info(f"Reasoning completed with mode {mode.value}")

        return response

    except Exception as e:
        logger.error(f"Error in reasoning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/suggest-improvements", response_model=HybridReasoningResponse)
async def suggest_improvements(request: SuggestImprovementsRequest):
    """
    Analyze music and suggest improvements.

    Provides specific, actionable suggestions for improving:
    - Harmony and voice leading
    - Melodic development
    - Rhythmic variety
    - Form and structure
    """
    try:
        # Decode music data
        music_data = base64.b64decode(request.music_data)

        # Get suggestions
        result = await hybrid_reasoner.analyze_and_suggest(
            music_data=music_data,
            focus_areas=request.focus_areas,
            format=request.format.value
        )

        # Convert to response
        response = HybridReasoningResponse(
            query="Suggest improvements",
            mode=ReasoningModeEnum(result.mode.value),
            symbolic_analysis=result.symbolic_analysis,
            synthesis=result.synthesis,
            confidence=result.confidence,
            recommendations=result.recommendations,
            metadata=result.metadata
        )

        logger.info("Improvement suggestions generated")

        return response

    except Exception as e:
        logger.error(f"Error suggesting improvements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/validate-theory", response_model=HybridReasoningResponse)
async def validate_theory(request: ValidateTheoryRequest):
    """
    Validate music theory rules.

    Checks for common violations:
    - Parallel fifths and octaves
    - Voice leading issues
    - Voice range problems
    - Dissonance treatment

    Optionally provides explanations using neural reasoning.
    """
    try:
        # Decode music data
        music_data = base64.b64decode(request.music_data)

        # Validate
        result = await hybrid_reasoner.validate_theory(
            music_data=music_data,
            rules=request.rules,
            explain=request.explain,
            format=request.format.value
        )

        # Convert to response
        response = HybridReasoningResponse(
            query="Validate music theory",
            mode=ReasoningModeEnum(result.mode.value),
            symbolic_analysis=result.symbolic_analysis,
            neural_reasoning=_convert_cot_result(result.neural_reasoning)
                if result.neural_reasoning else None,
            synthesis=result.synthesis,
            confidence=result.confidence,
            recommendations=result.recommendations,
            metadata=result.metadata
        )

        logger.info("Theory validation completed")

        return response

    except Exception as e:
        logger.error(f"Error validating theory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/compare", response_model=HybridReasoningResponse)
async def compare_pieces(request: ComparePiecesRequest):
    """
    Compare two musical pieces.

    Analyzes similarities and differences in:
    - Harmonic language
    - Melodic style
    - Rhythmic patterns
    - Form and structure
    """
    try:
        # Decode music data
        music_data1 = base64.b64decode(request.music_data1)
        music_data2 = base64.b64decode(request.music_data2)

        # Compare
        result = await hybrid_reasoner.compare_pieces(
            music_data1=music_data1,
            music_data2=music_data2,
            aspects=request.aspects,
            format1=request.format1.value,
            format2=request.format2.value
        )

        # Convert to response
        response = HybridReasoningResponse(
            query="Compare pieces",
            mode=ReasoningModeEnum(result.mode.value),
            symbolic_analysis=result.symbolic_analysis,
            synthesis=result.synthesis,
            confidence=result.confidence,
            recommendations=result.recommendations,
            metadata=result.metadata
        )

        logger.info("Piece comparison completed")

        return response

    except Exception as e:
        logger.error(f"Error comparing pieces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/explain-concept")
async def explain_concept(request: ExplainConceptRequest):
    """
    Explain a music theory concept.

    Provides clear explanations of concepts like:
    - Cadences
    - Modulations
    - Chord progressions
    - Voice leading principles
    """
    try:
        if not llm_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service not available"
            )

        # Get explanation
        response = await llm_client.explain_concept(
            concept=request.concept,
            context=request.context,
            level=request.level
        )

        logger.info(f"Explained concept: {request.concept}")

        return {
            "concept": request.concept,
            "level": request.level,
            "explanation": response.content,
            "model": response.model
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining concept: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/chain-of-thought", response_model=ChainOfThoughtResponse)
async def chain_of_thought_reasoning(request: ChainOfThoughtRequest):
    """
    Perform chain-of-thought reasoning.

    Breaks down complex queries into logical steps and reasons
    through them systematically.

    Useful for:
    - Complex analytical questions
    - Multi-step problem solving
    - Detailed explanations
    """
    try:
        if not cot_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chain-of-thought engine not available"
            )

        # Perform reasoning
        if request.iterative:
            result = await cot_engine.iterative_refinement(
                query=request.query,
                context=request.context,
                num_iterations=2
            )
        else:
            result = await cot_engine.reason(
                query=request.query,
                context=request.context,
                num_steps=request.num_steps
            )

        # Convert to response
        response = _convert_cot_result(result)

        logger.info("Chain-of-thought reasoning completed")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chain-of-thought: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/rules")
async def list_rules(category: str = None, enabled_only: bool = False):
    """
    List available music theory rules.

    Filter by category:
    - voice_leading
    - harmony
    - melody
    - counterpoint
    - range
    """
    try:
        rules = rules_engine.list_rules(
            category=category,
            enabled_only=enabled_only
        )

        logger.info(f"Listed {len(rules)} rules")

        return {
            "total": len(rules),
            "category": category,
            "rules": rules
        }

    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/rules/categories")
async def list_rule_categories():
    """Get list of rule categories."""
    try:
        categories = rules_engine.get_categories()

        return {
            "categories": categories
        }

    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/rules/{rule_name}/enable")
async def enable_rule(rule_name: str):
    """Enable a specific rule."""
    try:
        rules_engine.enable_rule(rule_name)

        logger.info(f"Enabled rule: {rule_name}")

        return {"status": "enabled", "rule": rule_name}

    except Exception as e:
        logger.error(f"Error enabling rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/rules/{rule_name}/disable")
async def disable_rule(rule_name: str):
    """Disable a specific rule."""
    try:
        rules_engine.disable_rule(rule_name)

        logger.info(f"Disabled rule: {rule_name}")

        return {"status": "disabled", "rule": rule_name}

    except Exception as e:
        logger.error(f"Error disabling rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


def _convert_cot_result(result) -> ChainOfThoughtResponse:
    """Convert ChainOfThoughtResult to response model."""
    if result is None:
        return None

    return ChainOfThoughtResponse(
        query=result.query,
        steps=[
            ThoughtStepResponse(
                step_number=step.step_number,
                question=step.question,
                reasoning=step.reasoning,
                answer=step.answer,
                confidence=step.confidence
            )
            for step in result.steps
        ],
        final_answer=result.final_answer,
        total_confidence=result.total_confidence,
        reasoning_path=result.reasoning_path
    )


# Import here to avoid circular import
from .schemas import ReasoningModeEnum
