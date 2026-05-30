"""Chain-of-Thought reasoning for complex musical analysis."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

from .llm_client import OllamaClient, Message

from ..config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ThoughtStep:
    """A single step in the chain of thought."""
    step_number: int
    question: str
    reasoning: str
    answer: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainOfThoughtResult:
    """Result of chain-of-thought reasoning."""
    query: str
    steps: List[ThoughtStep]
    final_answer: str
    total_confidence: float
    reasoning_path: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChainOfThought:
    """Chain-of-Thought reasoning engine for musical analysis."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        """
        Initialize Chain-of-Thought engine.

        Args:
            llm_client: Optional LLM client instance
        """
        self.settings = get_settings()
        self.llm_client = llm_client
        self.max_steps = self.settings.COT_MAX_STEPS
        self.temperature = self.settings.COT_TEMPERATURE
        self.use_examples = self.settings.COT_USE_EXAMPLES

        self._load_examples()

        logger.info("Chain-of-Thought engine initialized")

    def _load_examples(self) -> None:
        """Load example prompts for few-shot learning."""
        self.examples = []

        if not self.use_examples:
            return

        # Define built-in examples
        self.examples = [
            {
                "query": "Why does this chord progression sound sad?",
                "steps": [
                    "First, identify the chords in the progression",
                    "Second, analyze the key and mode",
                    "Third, examine the harmonic movement",
                    "Fourth, consider the emotional associations of minor keys",
                    "Finally, synthesize the findings"
                ],
                "reasoning": "The progression uses minor chords with descending bass movement, creating a melancholic atmosphere typical of minor mode progressions."
            },
            {
                "query": "How can I make this melody more interesting?",
                "steps": [
                    "First, analyze the current melodic contour",
                    "Second, identify repetitive patterns",
                    "Third, consider adding rhythmic variety",
                    "Fourth, explore chromatic embellishments",
                    "Finally, suggest specific improvements"
                ],
                "reasoning": "The melody can be enhanced by introducing rhythmic syncopation, adding passing tones, and creating more dynamic contour with strategic leaps."
            }
        ]

        logger.debug(f"Loaded {len(self.examples)} CoT examples")

    async def reason(
        self,
        query: str,
        context: Dict[str, Any],
        num_steps: Optional[int] = None
    ) -> ChainOfThoughtResult:
        """
        Perform chain-of-thought reasoning.

        Args:
            query: User query
            context: Musical analysis context
            num_steps: Number of reasoning steps (defaults to max_steps)

        Returns:
            Chain-of-thought result
        """
        if not self.llm_client:
            raise ValueError("LLM client not initialized")

        num_steps = num_steps or self.max_steps

        logger.info(f"Starting CoT reasoning with {num_steps} steps")

        # Step 1: Decompose the query into sub-questions
        sub_questions = await self._decompose_query(query, num_steps)

        # Step 2: Answer each sub-question
        steps = []
        accumulated_context = context.copy()

        for i, sub_question in enumerate(sub_questions):
            step = await self._answer_step(
                step_number=i + 1,
                question=sub_question,
                context=accumulated_context,
                previous_steps=steps
            )
            steps.append(step)

            # Update accumulated context with new findings
            accumulated_context[f"step_{i+1}_finding"] = step.answer

        # Step 3: Synthesize final answer
        final_answer = await self._synthesize_answer(query, steps, context)

        # Compute overall confidence
        total_confidence = sum(s.confidence for s in steps) / len(steps) if steps else 0.0

        # Extract reasoning path
        reasoning_path = [s.reasoning for s in steps]

        result = ChainOfThoughtResult(
            query=query,
            steps=steps,
            final_answer=final_answer,
            total_confidence=total_confidence,
            reasoning_path=reasoning_path,
            metadata={
                "num_steps": len(steps),
                "context_keys": list(context.keys())
            }
        )

        logger.info(f"CoT reasoning completed with confidence {total_confidence:.2f}")

        return result

    async def _decompose_query(
        self,
        query: str,
        num_steps: int
    ) -> List[str]:
        """
        Decompose complex query into sub-questions.

        Args:
            query: Original query
            num_steps: Number of sub-questions to generate

        Returns:
            List of sub-questions
        """
        system_prompt = """You are an expert at breaking down complex musical analysis questions into simpler sub-questions.

Your task is to decompose a query into a logical sequence of steps that build upon each other.
Each step should be a specific question that can be answered using musical analysis."""

        examples_text = ""
        if self.examples:
            examples_text = "\n\nExamples:\n"
            for ex in self.examples[:2]:  # Use first 2 examples
                examples_text += f"\nQuery: {ex['query']}\n"
                examples_text += "Steps:\n"
                for i, step in enumerate(ex['steps'], 1):
                    examples_text += f"{i}. {step}\n"

        user_prompt = f"""{examples_text}

Now decompose this query into exactly {num_steps} logical steps:

Query: {query}

Respond with a JSON array of {num_steps} sub-questions, like:
["Step 1 question", "Step 2 question", ...]"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        response = await self.llm_client.chat(
            messages,
            temperature=self.temperature
        )

        # Parse sub-questions from response
        try:
            # Try to extract JSON array from response
            content = response.content.strip()

            # Find JSON array in response
            start = content.find("[")
            end = content.rfind("]") + 1

            if start >= 0 and end > start:
                sub_questions = json.loads(content[start:end])
            else:
                # Fallback: split by numbered lines
                lines = content.split("\n")
                sub_questions = []
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith("-")):
                        # Remove numbering
                        clean = line.lstrip("0123456789.-) ").strip()
                        if clean:
                            sub_questions.append(clean)

            # Ensure we have the right number of steps
            if len(sub_questions) != num_steps:
                logger.warning(f"Expected {num_steps} steps, got {len(sub_questions)}")
                # Trim or pad as needed
                sub_questions = sub_questions[:num_steps]
                while len(sub_questions) < num_steps:
                    sub_questions.append(f"Additional analysis step {len(sub_questions) + 1}")

            return sub_questions

        except Exception as e:
            logger.error(f"Error parsing sub-questions: {e}")
            # Return default decomposition
            return [
                f"Step {i+1}: Analyze aspect of the query"
                for i in range(num_steps)
            ]

    async def _answer_step(
        self,
        step_number: int,
        question: str,
        context: Dict[str, Any],
        previous_steps: List[ThoughtStep]
    ) -> ThoughtStep:
        """
        Answer a single reasoning step.

        Args:
            step_number: Current step number
            question: Sub-question to answer
            context: Musical context
            previous_steps: Previous reasoning steps

        Returns:
            Thought step with answer
        """
        system_prompt = f"""You are a music theory expert answering step {step_number} of a multi-step analysis.

Provide:
1. Clear reasoning for this step
2. A specific answer based on the musical context
3. How confident you are (0-1)

Be concise but thorough."""

        # Build context from previous steps
        previous_context = ""
        if previous_steps:
            previous_context = "\n\nPrevious steps:\n"
            for step in previous_steps:
                previous_context += f"{step.step_number}. {step.question}\n"
                previous_context += f"   Answer: {step.answer}\n"

        context_summary = self._summarize_context(context)

        user_prompt = f"""Context:
{context_summary}
{previous_context}

Question for step {step_number}: {question}

Provide your reasoning and answer in this format:
REASONING: [your reasoning process]
ANSWER: [specific answer]
CONFIDENCE: [0.0 to 1.0]"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        response = await self.llm_client.chat(
            messages,
            temperature=self.temperature
        )

        # Parse response
        reasoning, answer, confidence = self._parse_step_response(response.content)

        return ThoughtStep(
            step_number=step_number,
            question=question,
            reasoning=reasoning,
            answer=answer,
            confidence=confidence,
            metadata={
                "model": response.model,
                "duration": response.total_duration
            }
        )

    def _parse_step_response(self, content: str) -> tuple[str, str, float]:
        """Parse reasoning, answer, and confidence from LLM response."""
        reasoning = ""
        answer = ""
        confidence = 0.7  # Default confidence

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if line.upper().startswith("REASONING:"):
                current_section = "reasoning"
                reasoning = line.split(":", 1)[1].strip()
            elif line.upper().startswith("ANSWER:"):
                current_section = "answer"
                answer = line.split(":", 1)[1].strip()
            elif line.upper().startswith("CONFIDENCE:"):
                current_section = "confidence"
                conf_str = line.split(":", 1)[1].strip()
                try:
                    confidence = float(conf_str)
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
                except ValueError:
                    pass
            elif line and current_section:
                # Continue previous section
                if current_section == "reasoning":
                    reasoning += " " + line
                elif current_section == "answer":
                    answer += " " + line

        # If parsing failed, use entire response as answer
        if not answer:
            answer = content.strip()

        return reasoning or "Analysis performed", answer, confidence

    async def _synthesize_answer(
        self,
        original_query: str,
        steps: List[ThoughtStep],
        context: Dict[str, Any]
    ) -> str:
        """
        Synthesize final answer from reasoning steps.

        Args:
            original_query: Original user query
            steps: Completed reasoning steps
            context: Musical context

        Returns:
            Final synthesized answer
        """
        system_prompt = """You are a music theory expert synthesizing insights from a multi-step analysis.

Your task is to:
1. Integrate findings from all reasoning steps
2. Answer the original query comprehensively
3. Provide actionable insights
4. Keep the answer clear and well-structured"""

        # Compile all step findings
        steps_summary = "\n\n".join([
            f"Step {s.step_number}: {s.question}\n"
            f"Finding: {s.answer}\n"
            f"Reasoning: {s.reasoning}"
            for s in steps
        ])

        user_prompt = f"""Original Query: {original_query}

Analysis Steps and Findings:
{steps_summary}

Based on these findings, provide a comprehensive answer to the original query.
Integrate all the insights and provide a clear, actionable response."""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]

        response = await self.llm_client.chat(
            messages,
            temperature=self.temperature
        )

        return response.content

    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Summarize musical context for prompts."""
        summary_parts = []

        # Key musical elements
        if "key_analysis" in context:
            key = context["key_analysis"]
            summary_parts.append(f"Key: {key.get('main_key', 'Unknown')}")

        if "metadata" in context:
            meta = context["metadata"]
            if meta.get("time_signature"):
                summary_parts.append(f"Time: {meta['time_signature']}")

        if "harmonic_analysis" in context:
            harmony = context["harmonic_analysis"]
            summary_parts.append(f"Chords: {harmony.get('total_chords', 0)}")

        if "melodic_analysis" in context:
            melody = context["melodic_analysis"]
            if "pitch_range" in melody:
                pr = melody["pitch_range"]
                summary_parts.append(f"Range: {pr.get('lowest')} to {pr.get('highest')}")

        if not summary_parts:
            summary_parts.append("Musical analysis data available")

        return " | ".join(summary_parts)

    def explain_reasoning(self, result: ChainOfThoughtResult) -> str:
        """
        Generate human-readable explanation of reasoning process.

        Args:
            result: Chain-of-thought result

        Returns:
            Formatted explanation
        """
        explanation = [
            f"Question: {result.query}",
            "",
            "Reasoning Process:",
            ""
        ]

        for step in result.steps:
            explanation.append(f"Step {step.step_number}: {step.question}")
            explanation.append(f"  Reasoning: {step.reasoning}")
            explanation.append(f"  Answer: {step.answer}")
            explanation.append(f"  Confidence: {step.confidence:.2f}")
            explanation.append("")

        explanation.extend([
            "Final Answer:",
            result.final_answer,
            "",
            f"Overall Confidence: {result.total_confidence:.2f}"
        ])

        return "\n".join(explanation)

    async def iterative_refinement(
        self,
        query: str,
        context: Dict[str, Any],
        num_iterations: int = 2
    ) -> ChainOfThoughtResult:
        """
        Perform iterative refinement of reasoning.

        Args:
            query: User query
            context: Musical context
            num_iterations: Number of refinement iterations

        Returns:
            Refined chain-of-thought result
        """
        logger.info(f"Starting iterative refinement with {num_iterations} iterations")

        # First pass
        result = await self.reason(query, context)

        # Refinement iterations
        for iteration in range(1, num_iterations):
            logger.debug(f"Refinement iteration {iteration}")

            # Add previous result to context
            enhanced_context = context.copy()
            enhanced_context["previous_analysis"] = {
                "answer": result.final_answer,
                "confidence": result.total_confidence,
                "steps": [
                    {"question": s.question, "answer": s.answer}
                    for s in result.steps
                ]
            }

            # Ask LLM to refine
            refined_query = f"Refine and improve this analysis: {query}"
            result = await self.reason(refined_query, enhanced_context)

        logger.info("Iterative refinement completed")
        return result

    def export_result(self, result: ChainOfThoughtResult, format: str = "json") -> str:
        """
        Export reasoning result in various formats.

        Args:
            result: Chain-of-thought result
            format: Export format (json, markdown, text)

        Returns:
            Formatted export string
        """
        if format == "json":
            return json.dumps({
                "query": result.query,
                "steps": [
                    {
                        "step_number": s.step_number,
                        "question": s.question,
                        "reasoning": s.reasoning,
                        "answer": s.answer,
                        "confidence": s.confidence
                    }
                    for s in result.steps
                ],
                "final_answer": result.final_answer,
                "total_confidence": result.total_confidence,
                "reasoning_path": result.reasoning_path
            }, indent=2)

        elif format == "markdown":
            md = [
                f"# Chain-of-Thought Analysis",
                "",
                f"**Query:** {result.query}",
                "",
                "## Reasoning Steps",
                ""
            ]

            for step in result.steps:
                md.extend([
                    f"### Step {step.step_number}: {step.question}",
                    "",
                    f"**Reasoning:** {step.reasoning}",
                    "",
                    f"**Answer:** {step.answer}",
                    "",
                    f"*Confidence: {step.confidence:.2f}*",
                    ""
                ])

            md.extend([
                "## Final Answer",
                "",
                result.final_answer,
                "",
                f"**Overall Confidence:** {result.total_confidence:.2f}"
            ])

            return "\n".join(md)

        else:  # text
            return self.explain_reasoning(result)
