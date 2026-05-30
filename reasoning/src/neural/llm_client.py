"""LLM client for neural reasoning using Ollama."""

import logging
import json
from typing import Dict, List, Any, Optional, AsyncIterator
import asyncio
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message."""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class OllamaClient:
    """Client for interacting with Ollama LLM service."""

    def __init__(self):
        """Initialize Ollama client."""
        self.settings = get_settings()
        self.base_url = self.settings.OLLAMA_BASE_URL
        self.model = self.settings.OLLAMA_MODEL
        self.temperature = self.settings.OLLAMA_TEMPERATURE
        self.max_tokens = self.settings.OLLAMA_MAX_TOKENS
        self.timeout = self.settings.OLLAMA_TIMEOUT

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )

        logger.info(f"Ollama client initialized with model: {self.model}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        Generate completion from prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            LLM response
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            logger.debug(f"Sending generate request to Ollama: {self.model}")

            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()

            return LLMResponse(
                content=result["response"],
                model=result["model"],
                total_duration=result.get("total_duration"),
                load_duration=result.get("load_duration"),
                prompt_eval_count=result.get("prompt_eval_count"),
                eval_count=result.get("eval_count"),
                metadata={
                    "done": result.get("done"),
                    "context": result.get("context")
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        Chat completion with conversation history.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            LLM response
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ],
                "stream": stream,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens
                }
            }

            logger.debug(f"Sending chat request to Ollama with {len(messages)} messages")

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()

            result = response.json()

            return LLMResponse(
                content=result["message"]["content"],
                model=result["model"],
                total_duration=result.get("total_duration"),
                load_duration=result.get("load_duration"),
                prompt_eval_count=result.get("prompt_eval_count"),
                eval_count=result.get("eval_count"),
                metadata={
                    "done": result.get("done")
                }
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Stream generation token by token.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Generated text chunks
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            logger.debug("Starting streaming generation")

            async with self.client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming chunk: {line}")

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise

    async def analyze_music_context(
        self,
        context: Dict[str, Any],
        query: str
    ) -> LLMResponse:
        """
        Analyze musical context and answer queries.

        Args:
            context: Musical analysis context
            query: User query about the music

        Returns:
            LLM response with analysis
        """
        # Build system prompt
        system_prompt = """You are a music theory expert assistant. You analyze musical pieces and provide insights about harmony, melody, rhythm, form, and composition techniques.

Your responses should be:
- Technically accurate
- Well-explained for musicians
- Focused on music theory concepts
- Citing specific examples from the analysis"""

        # Build user prompt with context
        user_prompt = f"""Musical Analysis Context:
{json.dumps(context, indent=2)}

Query: {query}

Please analyze this musical piece and answer the query based on the provided analysis data."""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        return await self.chat(messages)

    async def suggest_improvements(
        self,
        analysis: Dict[str, Any],
        focus_areas: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Suggest improvements for a musical composition.

        Args:
            analysis: Musical analysis data
            focus_areas: Specific areas to focus on (harmony, melody, etc.)

        Returns:
            LLM response with suggestions
        """
        system_prompt = """You are a composition teacher providing constructive feedback. Analyze musical pieces and suggest improvements in:
- Harmony and voice leading
- Melodic development
- Rhythmic variety
- Form and structure
- Orchestration and texture

Be specific and actionable in your suggestions."""

        focus_str = ", ".join(focus_areas) if focus_areas else "all aspects"

        user_prompt = f"""Please analyze this musical composition and suggest improvements focusing on {focus_str}.

Analysis Data:
{json.dumps(analysis, indent=2)}

Provide specific, actionable suggestions for improvement."""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        return await self.chat(messages)

    async def explain_concept(
        self,
        concept: str,
        context: Optional[Dict[str, Any]] = None,
        level: str = "intermediate"
    ) -> LLMResponse:
        """
        Explain a music theory concept.

        Args:
            concept: Concept name (e.g., "cadence", "modulation")
            context: Optional musical context
            level: Explanation level (beginner, intermediate, advanced)

        Returns:
            LLM response with explanation
        """
        system_prompt = f"""You are a music theory instructor explaining concepts at a {level} level.

Your explanations should:
- Be clear and accurate
- Use appropriate terminology for the level
- Include relevant examples
- Connect to practical application"""

        user_prompt = f"Please explain the music theory concept: {concept}"

        if context:
            user_prompt += f"\n\nIn the context of:\n{json.dumps(context, indent=2)}"

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        return await self.chat(messages)

    async def compare_pieces(
        self,
        analysis1: Dict[str, Any],
        analysis2: Dict[str, Any],
        aspects: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Compare two musical pieces.

        Args:
            analysis1: Analysis of first piece
            analysis2: Analysis of second piece
            aspects: Specific aspects to compare

        Returns:
            LLM response with comparison
        """
        system_prompt = """You are a music analyst comparing pieces. Provide detailed comparisons focusing on:
- Similarities and differences
- Stylistic characteristics
- Technical approaches
- Compositional techniques"""

        aspects_str = ", ".join(aspects) if aspects else "all aspects"

        user_prompt = f"""Compare these two musical pieces, focusing on {aspects_str}.

Piece 1 Analysis:
{json.dumps(analysis1, indent=2)}

Piece 2 Analysis:
{json.dumps(analysis2, indent=2)}

Provide a detailed comparison."""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        return await self.chat(messages)

    async def generate_composition_ideas(
        self,
        constraints: Dict[str, Any],
        style: Optional[str] = None,
        num_ideas: int = 3
    ) -> LLMResponse:
        """
        Generate composition ideas based on constraints.

        Args:
            constraints: Musical constraints (key, time signature, etc.)
            style: Musical style
            num_ideas: Number of ideas to generate

        Returns:
            LLM response with composition ideas
        """
        system_prompt = """You are a creative composition assistant. Generate original musical ideas that:
- Follow given constraints
- Are musically coherent
- Show variety and creativity
- Are practical to implement"""

        style_str = f" in {style} style" if style else ""

        user_prompt = f"""Generate {num_ideas} composition ideas{style_str} with these constraints:

{json.dumps(constraints, indent=2)}

For each idea, provide:
1. Brief description
2. Key musical elements
3. Suggested approach
4. Expected character/mood"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        return await self.chat(messages, temperature=0.9)  # Higher temperature for creativity

    async def check_health(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            logger.info("Ollama service is healthy")
            return True
        except Exception as e:
            logger.error(f"Ollama service check failed: {e}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model information
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            result = response.json()
            models = result.get("models", [])

            logger.info(f"Found {len(models)} available models")
            return models

        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model_name: Name of model to pull

        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model: {model_name}")

            response = await self.client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=httpx.Timeout(600.0)  # 10 minutes for model download
            )
            response.raise_for_status()

            logger.info(f"Successfully pulled model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False

    def format_analysis_summary(self, analysis: Dict[str, Any]) -> str:
        """
        Format analysis data into a readable summary for LLM context.

        Args:
            analysis: Analysis data

        Returns:
            Formatted summary string
        """
        summary_parts = []

        # Metadata
        if "metadata" in analysis:
            meta = analysis["metadata"]
            summary_parts.append("=== Metadata ===")
            summary_parts.append(f"Title: {meta.get('title', 'Unknown')}")
            summary_parts.append(f"Composer: {meta.get('composer', 'Unknown')}")
            summary_parts.append(f"Key: {meta.get('key_signature', 'Unknown')}")
            summary_parts.append(f"Time: {meta.get('time_signature', 'Unknown')}")
            summary_parts.append("")

        # Key analysis
        if "key_analysis" in analysis:
            key = analysis["key_analysis"]
            summary_parts.append("=== Key Analysis ===")
            summary_parts.append(f"Main Key: {key.get('main_key', 'Unknown')}")
            summary_parts.append(f"Mode: {key.get('mode', 'Unknown')}")
            if key.get("modulations"):
                summary_parts.append(f"Modulations: {len(key['modulations'])}")
            summary_parts.append("")

        # Harmonic analysis
        if "harmonic_analysis" in analysis:
            harmony = analysis["harmonic_analysis"]
            summary_parts.append("=== Harmonic Analysis ===")
            summary_parts.append(f"Total Chords: {harmony.get('total_chords', 0)}")
            if harmony.get("progressions"):
                summary_parts.append(f"Common Progressions: {len(harmony['progressions'])}")
            summary_parts.append("")

        # Melodic analysis
        if "melodic_analysis" in analysis:
            melody = analysis["melodic_analysis"]
            summary_parts.append("=== Melodic Analysis ===")
            if "pitch_range" in melody:
                pr = melody["pitch_range"]
                summary_parts.append(f"Range: {pr.get('lowest')} to {pr.get('highest')}")
            summary_parts.append("")

        # Statistics
        if "statistics" in analysis:
            stats = analysis["statistics"]
            summary_parts.append("=== Statistics ===")
            summary_parts.append(f"Total Notes: {stats.get('total_notes', 0)}")
            summary_parts.append(f"Duration: {stats.get('total_duration', 0)} quarter notes")
            summary_parts.append(f"Parts: {stats.get('parts', 0)}")

        return "\n".join(summary_parts)
