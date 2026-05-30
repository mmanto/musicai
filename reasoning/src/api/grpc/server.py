"""gRPC server for reasoning service."""

import logging
import json
import asyncio
from typing import Dict, Any

import grpc
from grpc import aio

# Note: Proto files would need to be compiled first with:
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. reasoning.proto

# For now, we'll create a placeholder implementation
# In production, import the generated proto files:
# from . import reasoning_pb2
# from . import reasoning_pb2_grpc

from ...symbolic.music21_analyzer import Music21Analyzer
from ...symbolic.rules_engine import RulesEngine, RuleSeverity
from ...neural.llm_client import OllamaClient
from ...neural.chain_of_thought import ChainOfThought
from ...hybrid.reasoner import HybridReasoner, ReasoningMode
from ...config import get_settings

logger = logging.getLogger(__name__)


class ReasoningServicer:
    """
    gRPC service implementation for reasoning.

    Note: This is a placeholder. In production, this would inherit from
    the generated reasoning_pb2_grpc.ReasoningServiceServicer class.
    """

    def __init__(self):
        """Initialize the servicer."""
        self.settings = get_settings()

        # Initialize components
        self.music_analyzer = Music21Analyzer()
        self.rules_engine = RulesEngine()
        self.llm_client = OllamaClient()
        self.cot_engine = ChainOfThought(self.llm_client)
        self.hybrid_reasoner = HybridReasoner(
            music_analyzer=self.music_analyzer,
            rules_engine=self.rules_engine,
            llm_client=self.llm_client,
            cot_engine=self.cot_engine
        )

        logger.info("gRPC servicer initialized")

    async def Analyze(self, request, context):
        """
        Analyze a musical piece.

        Args:
            request: AnalyzeRequest
            context: gRPC context

        Returns:
            AnalysisResponse
        """
        try:
            logger.info("Received Analyze request")

            # Extract request data
            music_data = request.music_data
            format = request.format

            # Perform analysis
            analysis = self.music_analyzer.analyze_score(music_data, format)

            # Validate
            validation = self.rules_engine.validate(
                analysis,
                min_severity=RuleSeverity.INFO
            )
            analysis["validation"] = validation

            # Create response (placeholder structure)
            # In production, use the generated response class
            response = {
                "metadata_json": json.dumps(analysis.get("metadata", {})),
                "key_analysis_json": json.dumps(analysis.get("key_analysis", {})),
                "harmonic_analysis_json": json.dumps(analysis.get("harmonic_analysis", {})),
                "melodic_analysis_json": json.dumps(analysis.get("melodic_analysis", {})),
                "validation_json": json.dumps(validation)
            }

            logger.info("Analysis completed successfully")

            return response

        except Exception as e:
            logger.error(f"Error in Analyze: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def Reason(self, request, context):
        """
        Perform hybrid reasoning.

        Args:
            request: ReasonRequest
            context: gRPC context

        Returns:
            ReasoningResponse
        """
        try:
            logger.info("Received Reason request")

            # Extract request data
            music_data = request.music_data
            query = request.query
            mode_str = request.mode
            format = request.format

            # Convert mode
            mode = ReasoningMode(mode_str)

            # Perform reasoning
            result = await self.hybrid_reasoner.reason(
                music_data=music_data,
                query=query,
                mode=mode,
                format=format
            )

            # Create response
            response = {
                "query": result.query,
                "mode": result.mode.value,
                "synthesis": result.synthesis or "",
                "confidence": result.confidence,
                "recommendations": result.recommendations,
                "symbolic_analysis_json": json.dumps(result.symbolic_analysis or {}),
                "neural_reasoning_json": json.dumps({
                    "final_answer": result.neural_reasoning.final_answer,
                    "confidence": result.neural_reasoning.total_confidence
                } if result.neural_reasoning else {})
            }

            logger.info("Reasoning completed successfully")

            return response

        except Exception as e:
            logger.error(f"Error in Reason: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def SuggestImprovements(self, request, context):
        """
        Suggest improvements for a piece.

        Args:
            request: SuggestRequest
            context: gRPC context

        Returns:
            ReasoningResponse
        """
        try:
            logger.info("Received SuggestImprovements request")

            # Extract request data
            music_data = request.music_data
            focus_areas = list(request.focus_areas) if request.focus_areas else None
            format = request.format

            # Get suggestions
            result = await self.hybrid_reasoner.analyze_and_suggest(
                music_data=music_data,
                focus_areas=focus_areas,
                format=format
            )

            # Create response
            response = {
                "query": "Suggest improvements",
                "mode": result.mode.value,
                "synthesis": result.synthesis or "",
                "confidence": result.confidence,
                "recommendations": result.recommendations,
                "symbolic_analysis_json": json.dumps(result.symbolic_analysis or {}),
                "neural_reasoning_json": ""
            }

            logger.info("Suggestions generated successfully")

            return response

        except Exception as e:
            logger.error(f"Error in SuggestImprovements: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def ValidateTheory(self, request, context):
        """
        Validate music theory rules.

        Args:
            request: ValidateRequest
            context: gRPC context

        Returns:
            ReasoningResponse
        """
        try:
            logger.info("Received ValidateTheory request")

            # Extract request data
            music_data = request.music_data
            rules = list(request.rules) if request.rules else None
            explain = request.explain
            format = request.format

            # Validate
            result = await self.hybrid_reasoner.validate_theory(
                music_data=music_data,
                rules=rules,
                explain=explain,
                format=format
            )

            # Create response
            response = {
                "query": "Validate music theory",
                "mode": result.mode.value,
                "synthesis": result.synthesis or "",
                "confidence": result.confidence,
                "recommendations": result.recommendations,
                "symbolic_analysis_json": json.dumps(result.symbolic_analysis or {}),
                "neural_reasoning_json": json.dumps({
                    "final_answer": result.neural_reasoning.final_answer
                } if result.neural_reasoning else {})
            }

            logger.info("Validation completed successfully")

            return response

        except Exception as e:
            logger.error(f"Error in ValidateTheory: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def ExplainConcept(self, request, context):
        """
        Explain a music theory concept.

        Args:
            request: ConceptRequest
            context: gRPC context

        Returns:
            ExplanationResponse
        """
        try:
            logger.info("Received ExplainConcept request")

            # Extract request data
            concept = request.concept
            context_json = request.context_json
            level = request.level

            # Parse context
            context_data = json.loads(context_json) if context_json else None

            # Get explanation
            response_llm = await self.llm_client.explain_concept(
                concept=concept,
                context=context_data,
                level=level
            )

            # Create response
            response = {
                "concept": concept,
                "explanation": response_llm.content,
                "level": level
            }

            logger.info(f"Explained concept: {concept}")

            return response

        except Exception as e:
            logger.error(f"Error in ExplainConcept: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def HealthCheck(self, request, context):
        """
        Check service health.

        Args:
            request: HealthRequest
            context: gRPC context

        Returns:
            HealthResponse
        """
        try:
            components = {
                "music_analyzer": True,
                "rules_engine": True,
                "hybrid_reasoner": True
            }

            # Check LLM
            try:
                llm_available = await self.llm_client.check_health()
                components["ollama"] = llm_available
            except:
                components["ollama"] = False

            all_healthy = all(components.values())

            response = {
                "status": "healthy" if all_healthy else "degraded",
                "service": self.settings.SERVICE_NAME,
                "version": self.settings.SERVICE_VERSION,
                "components": components
            }

            return response

        except Exception as e:
            logger.error(f"Error in HealthCheck: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))


async def serve():
    """Start the gRPC server."""
    settings = get_settings()

    server = aio.server()

    # Add servicer to server
    # In production, use:
    # reasoning_pb2_grpc.add_ReasoningServiceServicer_to_server(
    #     ReasoningServicer(), server
    # )

    # For now, just log
    logger.info("gRPC servicer would be added here")

    # Listen on port
    listen_addr = f"{settings.GRPC_HOST}:{settings.GRPC_PORT}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting gRPC server on {listen_addr}")

    await server.start()
    await server.wait_for_termination()


def main():
    """Run the gRPC server."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
