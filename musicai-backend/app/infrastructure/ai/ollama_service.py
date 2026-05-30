"""
Ollama Service - Conversational AI for music interaction.

This service handles:
- Prompt enhancement for music generation
- Musical concept explanation
- Analysis interpretation
- Conversational interface
- Statement validation
- Contextual music dialogue
"""

import logging
import json
import re
from typing import Optional, Dict, Any, List, Tuple
import ollama

logger = logging.getLogger(__name__)


# Deterministic note and scale mapping (always correct)
NOTE_MAPPING_ES_TO_EN = {
    'do': 'C', 'do#': 'C#', 'dob': 'Cb',
    're': 'D', 're#': 'D#', 'reb': 'Db',
    'mi': 'E', 'mi#': 'E#', 'mib': 'Eb',
    'fa': 'F', 'fa#': 'F#', 'fab': 'Fb',
    'sol': 'G', 'sol#': 'G#', 'solb': 'Gb',
    'la': 'A', 'la#': 'A#', 'lab': 'Ab',
    'si': 'B', 'si#': 'B#', 'sib': 'Bb',
}

SCALE_TYPE_MAPPING_ES_TO_EN = {
    'mayor': 'major',
    'menor': 'minor',
    'pentatónica mayor': 'pentatonic major',
    'pentatonica mayor': 'pentatonic major',
    'pentatónica menor': 'pentatonic minor',
    'pentatonica menor': 'pentatonic minor',
    'pentatónica': 'pentatonic minor',  # default to minor
    'pentatonica': 'pentatonic minor',
    'armónica menor': 'harmonic minor',
    'armonica menor': 'harmonic minor',
    'melódica menor': 'melodic minor',
    'melodica menor': 'melodic minor',
    'cromática': 'chromatic',
    'cromatica': 'chromatic',
    'blues': 'blues',
    'dórica': 'dorian',
    'dorica': 'dorian',
    'frigia': 'phrygian',
    'lidia': 'lydian',
    'mixolidia': 'mixolydian',
}


def parse_music_request_deterministic(message: str) -> List[Dict[str, Any]]:
    """
    Parse music requests using deterministic regex patterns.
    This ensures accurate note and scale type mapping regardless of LLM behavior.

    Examples:
    - "muestra la escala pentatónica de la menor" -> [{"type": "scale", "tonic": "A", "scale_type": "pentatonic minor"}]
    - "escala de do mayor" -> [{"type": "scale", "tonic": "C", "scale_type": "major"}]
    """
    message_lower = message.lower()
    concepts = []

    # Pattern: "escala [type] de/en [note]" or "[note] [type]"
    # Examples: "escala pentatónica de la menor", "do mayor", "la menor pentatónica"

    # Try multiple patterns
    patterns = [
        # "escala [scale_type] de/en [note] [scale_type2]"
        r'escala\s+([\w\sáéíóú]+?)\s+(?:de|en)\s+(do|re|mi|fa|sol|la|si)(?:#|b)?\s+(mayor|menor)',
        # "escala de/en [note] [scale_type]"
        r'escala\s+(?:de|en)\s+(do|re|mi|fa|sol|la|si)(?:#|b)?\s+([\w\sáéíóú]+)',
        # "[note] [scale_type]"
        r'\b(do|re|mi|fa|sol|la|si)(?:#|b)?\s+([\w\sáéíóú]+(?:mayor|menor|pentatonica|pentatónica|armonica|armónica|melodica|melódica|cromatica|cromática|blues|dorica|dórica|frigia|lidia|mixolidia))',
        # "muestra/genera/dame [note] [scale_type]"
        r'(?:muestra|genera|dame|ver|crea)\s+(?:la\s+escala\s+)?(?:de\s+)?(do|re|mi|fa|sol|la|si)(?:#|b)?\s+([\w\sáéíóú]+)',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, message_lower)
        for match in matches:
            groups = match.groups()

            # Determine which group is note and which is scale_type
            note_str = None
            scale_type_str = None

            if len(groups) == 2:
                # Could be note+type or type+note
                if groups[0] in NOTE_MAPPING_ES_TO_EN:
                    note_str = groups[0]
                    scale_type_str = groups[1]
                elif groups[1] in NOTE_MAPPING_ES_TO_EN:
                    note_str = groups[1]
                    scale_type_str = groups[0]
                else:
                    # Assume first is note, second is type
                    note_str = groups[0] if groups[0] in NOTE_MAPPING_ES_TO_EN else groups[1]
                    scale_type_str = groups[1] if note_str == groups[0] else groups[0]
            elif len(groups) == 3:
                # Pattern with 3 groups: scale_type1, note, scale_type2
                note_str = groups[1]
                scale_type_str = f"{groups[0]} {groups[2]}".strip()

            if note_str and scale_type_str:
                # Clean scale type
                scale_type_str = scale_type_str.strip()

                # Map to English
                tonic_en = NOTE_MAPPING_ES_TO_EN.get(note_str, 'C')

                # Try exact match first, then partial match
                scale_type_en = SCALE_TYPE_MAPPING_ES_TO_EN.get(scale_type_str, None)

                if not scale_type_en:
                    # Try partial matches
                    for es_key, en_value in SCALE_TYPE_MAPPING_ES_TO_EN.items():
                        if es_key in scale_type_str:
                            scale_type_en = en_value
                            break

                if not scale_type_en:
                    scale_type_en = 'major'  # default

                concept = {
                    "type": "scale",
                    "tonic": tonic_en,
                    "scale_type": scale_type_en,
                    "description": f"{note_str} {scale_type_str}"
                }
                concepts.append(concept)
                logger.info(f"Deterministic parser found: {concept}")

    return concepts


class OllamaService:
    """
    Service for Ollama LLM interactions.

    Focuses on enhancing user prompts and providing musical context.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        use_rag: bool = True
    ):
        """
        Initialize Ollama service.

        Args:
            base_url: Ollama server URL
            model: Model to use
            use_rag: Whether to use RAG for knowledge augmentation
        """
        self.base_url = base_url
        self.model = model
        self.client = ollama.Client(host=base_url)
        self.use_rag = use_rag

        # Initialize RAG service if enabled
        self.rag_service = None
        if use_rag:
            try:
                from app.infrastructure.knowledge.rag_service import get_rag_service
                self.rag_service = get_rag_service()
                if self.rag_service.is_available():
                    logger.info("RAG service enabled and available")
                else:
                    logger.warning("RAG service initialized but not available (ChromaDB may not be installed)")
            except Exception as e:
                logger.warning(f"Could not initialize RAG service: {e}")

        logger.info(f"Ollama service initialized: {model} at {base_url}")

    def enhance_music_prompt(
        self,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhance user's music generation prompt with musical details.

        Args:
            user_prompt: User's original prompt
            context: Additional context (e.g., previous generations, preferences)

        Returns:
            Dictionary with enhanced prompt and extracted parameters
        """
        try:
            system_prompt = """You are a music expert AI assistant. Your job is to enhance user prompts for the MusicGen AI model.

IMPORTANT: MusicGen works best with VERY DETAILED, SPECIFIC descriptions that include:
- Multiple instruments with playing styles
- Clear rhythmic patterns and tempo
- Melodic movement descriptions
- Harmonic progressions when relevant
- Texture and dynamics
- Specific genre characteristics

Given a user's description, create a RICH, DETAILED prompt (2-3 sentences) that describes:
1. Main instruments and their roles
2. Melodic character (flowing, staccato, rhythmic, etc.)
3. Harmonic movement or chord progressions
4. Rhythmic feel and tempo
5. Overall texture and dynamics
6. Genre-specific characteristics

Example GOOD enhanced prompt: "An upbeat jazz piano trio with a swinging rhythm at 140 BPM, featuring a melodic piano improvisation over walking bass lines and crisp hi-hat patterns, with occasional drum fills and dynamic chord voicings in the Bb major pentatonic scale"

Return your response as a JSON object:
{
    "enhanced_prompt": "A VERY detailed, rich description (2-3 sentences) for MusicGen",
    "style": "jazz",
    "instruments": ["piano", "bass", "drums"],
    "tempo": 140,
    "key": "Bb major",
    "mood": "upbeat",
    "time_signature": "4/4"
}

Make the enhanced_prompt as descriptive and musical as possible.
"""

            context_str = ""
            if context:
                context_str = f"\nContext: {json.dumps(context, indent=2)}"

            user_message = f"User wants to create: {user_prompt}{context_str}"

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                format="json"
            )

            # Parse JSON response
            result = json.loads(response['message']['content'])

            logger.info(f"Enhanced prompt: {result.get('enhanced_prompt', '')[:100]}...")
            return result

        except Exception as e:
            logger.error(f"Error enhancing prompt: {e}")
            # Return minimal fallback
            return {
                "enhanced_prompt": user_prompt,
                "style": "general",
                "tempo": 120,
                "mood": "neutral"
            }

    def explain_analysis(
        self,
        analysis_data: Dict[str, Any],
        user_question: Optional[str] = None
    ) -> str:
        """
        Explain musical analysis in user-friendly terms.

        Args:
            analysis_data: Analysis results from music21
            user_question: Optional specific question

        Returns:
            Natural language explanation
        """
        try:
            system_prompt = """You are a music theory teacher. Explain musical analysis results in a clear, friendly way that both beginners and experienced musicians can understand.

Focus on:
- What the analysis reveals about the music
- Musical characteristics in plain language
- Interesting patterns or features
"""

            analysis_str = json.dumps(analysis_data, indent=2)
            user_message = f"Analysis results:\n{analysis_str}"

            if user_question:
                user_message += f"\n\nUser's question: {user_question}"

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )

            explanation = response['message']['content']
            logger.info("Generated analysis explanation")
            return explanation

        except Exception as e:
            logger.error(f"Error explaining analysis: {e}")
            return "Analysis completed successfully. See detailed results above."

    def suggest_variations(
        self,
        current_piece_info: Dict[str, Any],
        num_suggestions: int = 3
    ) -> List[Dict[str, str]]:
        """
        Suggest musical variations based on current piece.

        Args:
            current_piece_info: Information about the current piece
            num_suggestions: Number of suggestions to generate

        Returns:
            List of variation suggestions
        """
        try:
            system_prompt = """You are a creative music composition assistant. Given a musical piece, suggest interesting variations.

Return your response as a JSON array of {num_suggestions} variation ideas:
[
    {
        "title": "Variation name",
        "description": "Brief description of the variation",
        "transformation": "Specific musical change (e.g., 'transpose up 5 semitones', 'change to 3/4 time')",
        "prompt": "Prompt for generating this variation"
    }
]

Make suggestions that are musically interesting and diverse.
"""

            piece_str = json.dumps(current_piece_info, indent=2)
            user_message = f"Current piece:\n{piece_str}\n\nSuggest {num_suggestions} variations."

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                format="json"
            )

            suggestions = json.loads(response['message']['content'])

            if isinstance(suggestions, list):
                logger.info(f"Generated {len(suggestions)} variation suggestions")
                return suggestions
            else:
                logger.warning("Unexpected suggestion format")
                return []

        except Exception as e:
            logger.error(f"Error suggesting variations: {e}")
            return []

    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_context: Optional[str] = None
    ) -> str:
        """
        General chat interaction.

        Args:
            message: User message
            conversation_history: Previous messages
            system_context: Additional system context

        Returns:
            Assistant response
        """
        try:
            system_prompt = """You are a knowledgeable and friendly music AI assistant. You help users:
- Create and generate music
- Understand musical concepts
- Analyze musical pieces
- Learn about music theory
- Explore creative variations

Be concise but informative. Use analogies to explain complex concepts.
"""

            if system_context:
                system_prompt += f"\n\nCurrent context: {system_context}"

            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            reply = response['message']['content']
            logger.info("Generated chat response")
            return reply

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return "I'm having trouble processing that request. Please try again."

    def extract_musical_parameters(self, text: str) -> Dict[str, Any]:
        """
        Extract musical parameters from natural language.

        Args:
            text: User's text input

        Returns:
            Dictionary with extracted parameters
        """
        try:
            system_prompt = """Extract musical parameters from the text. Return JSON:
{
    "tempo": 120,  // BPM or null
    "key": "C major",  // or null
    "time_signature": "4/4",  // or null
    "duration": 30,  // seconds or null
    "instruments": [],  // list of instruments
    "style": "jazz",  // genre/style or null
    "mood": "happy"  // emotional quality or null
}

Only include fields that are mentioned or clearly implied. Use null for unspecified fields.
"""

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                format="json"
            )

            params = json.loads(response['message']['content'])
            logger.info(f"Extracted parameters: {params}")
            return params

        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
            return {}

    def classify_intent(self, message: str) -> str:
        """
        Classify user intent to determine response type.

        Args:
            message: User message

        Returns:
            Intent type: 'theory_question', 'pattern_request', 'creative_generation', 'general_chat'
        """
        try:
            system_prompt = """Clasifica la intención del usuario en UNA de estas categorías:

1. theory_question: Preguntas sobre teoría musical, definiciones, comparaciones
   - Ejemplos: "¿Qué es una clave?", "Diferencia entre mayor y menor", "Explica la armonía"

2. pattern_request: Solicitud directa de generar un patrón musical específico
   - Ejemplos: "escala de do mayor", "acorde de La menor", "arpegio de Sol"

3. creative_generation: Solicitud creativa de generar música con IA
   - Ejemplos: "una melodía tranquila de piano", "música de jazz rápida"

4. general_chat: Conversación general, saludos, preguntas no musicales
   - Ejemplos: "Hola", "¿Cómo estás?", "Gracias"

Responde SOLO con el nombre de la categoría en inglés, sin explicaciones."""

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            )

            intent = response['message']['content'].strip().lower()

            # Validate response
            valid_intents = ['theory_question', 'pattern_request', 'creative_generation', 'general_chat']
            if intent not in valid_intents:
                logger.warning(f"Unexpected intent classification: {intent}, defaulting to theory_question")
                intent = 'theory_question'

            logger.info(f"Classified intent: {intent}")
            return intent

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return 'theory_question'  # Default fallback

    def extract_music_concepts(self, message: str, is_user_message: bool = True) -> List[Dict[str, Any]]:
        """
        Extract musical concepts (scales, chords, etc.) mentioned in the message.

        Args:
            message: User message or assistant response
            is_user_message: True if this is the user's original question, False if it's the assistant's response

        Returns:
            List of musical concepts with parameters for generation
        """
        try:
            # For user messages, only extract if they EXPLICITLY ask to see/show/visualize
            if is_user_message:
                lower_msg = message.lower()

                # Check if user is asking for visualization/examples
                show_keywords = ['muestra', 'muestrame', 'muéstrame', 'visualiza', 'ejemplo', 'ejemplos',
                                'ver', 'dame', 'genera', 'crea', 'escribe', 'toca']

                # Check if it's a general question without visualization request
                question_keywords = ['qué es', 'que es', 'explica', 'explicame', 'explícame',
                                    'cuéntame', 'cuentame', 'qué son', 'que son', 'diferencia',
                                    'cómo', 'como', 'por qué', 'por que', 'cuál', 'cual']

                is_question = any(keyword in lower_msg for keyword in question_keywords)
                wants_visualization = any(keyword in lower_msg for keyword in show_keywords)

                # If it's a question WITHOUT explicit visualization request, don't extract concepts
                if is_question and not wants_visualization:
                    logger.info("User asking theoretical question without visualization request - skipping concept extraction")
                    return []

            # FIRST: Try deterministic parser for accuracy
            deterministic_concepts = parse_music_request_deterministic(message)
            if deterministic_concepts:
                logger.info(f"Using deterministic parser result: {deterministic_concepts}")
                return deterministic_concepts

            system_prompt = """Identifica SOLAMENTE los conceptos musicales específicos que el usuario SOLICITA EXPLÍCITAMENTE visualizar o generar.

IMPORTANTE: NO extraigas conceptos que solo se mencionan en una explicación teórica. SOLO extrae si el usuario pide ver, mostrar, generar o visualizar ese concepto.

Devuelve un JSON array con objetos que tengan esta estructura:
[
    {
        "type": "scale",  // "scale", "chord", o "arpeggio"
        "tonic": "C",  // nota raíz en notación inglesa (C, D, E, F, G, A, B)
        "scale_type": "major",  // "major", "minor", "harmonic minor", "melodic minor", etc.
        "chord_type": null,  // tipo de acorde si type="chord"
        "description": "escala de do mayor"  // descripción en español
    }
]

Mapeo de notas español → inglés:
do→C, re→D, mi→E, fa→F, sol→G, la→A, si→B

Mapeo de tipos de escala español → inglés:
mayor→major, menor→minor, armónica→harmonic minor, melódica→melodic minor,
pentatónica→pentatonic, cromática→chromatic

Si no hay solicitud EXPLÍCITA de visualización, devuelve un array vacío: []"""

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                format="json"
            )

            concepts = json.loads(response['message']['content'])

            # Validate it's a list
            if not isinstance(concepts, list):
                concepts = []

            logger.info(f"Extracted {len(concepts)} music concepts (is_user_message={is_user_message})")
            return concepts

        except Exception as e:
            logger.error(f"Error extracting music concepts: {e}")
            return []

    def chat_music_teacher(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context_summary: Optional[str] = None
    ) -> str:
        """
        Chat as a music theory teacher with contextual awareness and RAG.

        Args:
            message: User question/message
            conversation_history: Previous conversation
            context_summary: Summary of musical context (what was shown previously)

        Returns:
            Educational response about music theory
        """
        try:
            system_prompt = """Eres un profesor de teoría musical experto y amigable. Tu objetivo es:

1. Explicar conceptos musicales de forma clara y concisa
2. Usar analogías y ejemplos cuando sea apropiado
3. Mantener un tono educativo pero accesible
4. Responder en español
5. Si mencionas escalas, acordes o patrones específicos, ser preciso con la terminología
6. VALIDAR afirmaciones del usuario - analizar si son correctas o incorrectas
7. CORREGIR errores de forma pedagógica, explicando el concepto correcto
8. Usar el contexto de lo que se mostró previamente para entender referencias como "esa escala"

Directrices:
- Sé conciso pero completo (2-4 párrafos)
- Usa términos técnicos pero explícalos
- Si comparas conceptos, hazlo de forma estructurada
- Menciona aplicaciones prácticas cuando sea relevante
- Si el usuario hace una afirmación incorrecta, corrígela gentilmente y explica por qué
- Si el usuario tiene razón, confirma y amplía el concepto

Ejemplos de validación:
Usuario: "La escala pentatónica de la menor debe comenzar con do"
Respuesta: "En realidad, la escala pentatónica de La menor comienza con LA, su tónica. Las notas son: LA - DO - RE - MI - SOL. La tónica es el punto de reposo y le da nombre a la escala. Quizás estabas pensando en la escala de Do mayor, que sí comienza con Do."

Usuario: "Esa escala debe comenzar con la tónica en la"
Respuesta (si última escala fue A pentatonic minor): "¡Correcto! La escala pentatónica de La menor comienza con su tónica LA. Las notas son: LA - DO - RE - MI - SOL. La tónica siempre es la primera nota de la escala y le da el nombre a toda la escala."

NO uses emojis excesivamente. Máximo 1-2 por respuesta."""

            # Add RAG context if available
            if self.rag_service and self.rag_service.is_available():
                rag_context = self.rag_service.get_context_for_query(message, n_results=2)
                if rag_context:
                    system_prompt += f"\n\n{rag_context}\n\nUsa este conocimiento para enriquecer tu respuesta si es relevante."
                    logger.info("Added RAG context to prompt")

            # Add conversation context if available
            if context_summary:
                system_prompt += f"\n\nCONTEXTO MUSICAL ACTUAL:\n{context_summary}\n\nUsa este contexto para entender referencias del usuario como 'esa escala', 'el acorde anterior', etc."

            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            response = self.client.chat(
                model=self.model,
                messages=messages
            )

            reply = response['message']['content']
            logger.info("Generated music teacher response with context and RAG")
            return reply

        except Exception as e:
            logger.error(f"Error in music teacher chat: {e}")
            return "Lo siento, tengo problemas para procesar tu pregunta. Por favor intenta de nuevo."

    def chat_music_teacher_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context_summary: Optional[str] = None
    ):
        """
        Stream chat as a music theory teacher (yields tokens as they're generated).

        Args:
            message: User question/message
            conversation_history: Previous conversation
            context_summary: Summary of musical context

        Yields:
            String tokens as they're generated
        """
        try:
            system_prompt = """Eres un profesor de teoría musical experto y amigable. Tu objetivo es:

1. Explicar conceptos musicales de forma clara y concisa
2. Usar analogías y ejemplos cuando sea apropiado
3. Mantener un tono educativo pero accesible
4. Responder en español
5. Si mencionas escalas, acordes o patrones específicos, ser preciso con la terminología
6. VALIDAR afirmaciones del usuario - analizar si son correctas o incorrectas
7. CORREGIR errores de forma pedagógica, explicando el concepto correcto

Directrices:
- Sé conciso pero completo (2-4 párrafos)
- Usa términos técnicos pero explícalos
- NO uses emojis excesivamente. Máximo 1-2 por respuesta
- NO uses tags especiales de ningún tipo para marcar elementos musicales
- Escribe la respuesta como texto plano sin etiquetas ni markup especial
- NUNCA uses caracteres chinos, japoneses ni ningún otro idioma que no sea español"""

            # Add RAG context if available
            if self.rag_service and self.rag_service.is_available():
                rag_context = self.rag_service.get_context_for_query(message, n_results=2)
                if rag_context:
                    system_prompt += f"\n\n{rag_context}\n\nUsa este conocimiento para enriquecer tu respuesta si es relevante."

            # Add conversation context if available
            if context_summary:
                system_prompt += f"\n\nCONTEXTO MUSICAL ACTUAL:\n{context_summary}"

            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": message})

            # Use streaming
            logger.info("Starting Ollama streaming...")
            stream = self.client.chat(
                model=self.model,
                messages=messages,
                stream=True
            )

            token_count = 0
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    token_count += 1
                    token = chunk['message']['content']
                    if token_count <= 5:  # Log first 5 tokens for debugging
                        logger.info(f"Ollama token {token_count}: '{token[:20]}...'")
                    yield token

            logger.info(f"Ollama streaming complete. Total tokens: {token_count}")

        except Exception as e:
            logger.error(f"Error in streaming music teacher chat: {e}")
            yield "Lo siento, tengo problemas para procesar tu pregunta."

    def validate_user_statement(
        self,
        statement: str,
        musical_context: Optional[str] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate a user's statement about music theory.

        Args:
            statement: User's statement to validate
            musical_context: Context about what musical concepts are being discussed

        Returns:
            (is_correct, explanation, suggested_corrections)
        """
        try:
            system_prompt = """Eres un validador de teoría musical. Analiza la afirmación del usuario y determina si es correcta o incorrecta.

Devuelve un JSON con esta estructura:
{
    "is_correct": true/false,
    "explanation": "Explicación detallada de por qué es correcto o incorrecto",
    "confidence": 0-100,  // tu nivel de confianza en la evaluación
    "corrections": ["sugerencia 1", "sugerencia 2"],  // si es incorrecto, qué debería ser
    "related_concepts": ["concepto relacionado 1", "concepto relacionado 2"]  // conceptos útiles para entender mejor
}

Ejemplos:

Afirmación: "La escala mayor tiene 7 notas"
Respuesta: {
    "is_correct": true,
    "explanation": "Correcto. Las escalas mayores diatónicas tienen 7 notas diferentes antes de llegar a la octava.",
    "confidence": 100,
    "corrections": [],
    "related_concepts": ["escala diatónica", "octava", "intervalos"]
}

Afirmación: "La escala pentatónica de la menor comienza con do"
Respuesta: {
    "is_correct": false,
    "explanation": "Incorrecto. La escala pentatónica de La menor comienza con LA, su tónica. Las notas son: LA - DO - RE - MI - SOL.",
    "confidence": 100,
    "corrections": ["La escala pentatónica de La menor comienza con LA", "La escala de Do mayor comienza con DO"],
    "related_concepts": ["tónica", "pentatónica menor", "escala menor"]
}"""

            context_message = statement
            if musical_context:
                context_message = f"Contexto musical: {musical_context}\n\nAfirmación del usuario: {statement}"

            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context_message}
                ],
                format="json"
            )

            result = json.loads(response['message']['content'])

            is_correct = result.get("is_correct", False)
            explanation = result.get("explanation", "")
            corrections = result.get("corrections", [])

            logger.info(f"Validated statement: {is_correct} (confidence: {result.get('confidence', 0)})")
            return is_correct, explanation, corrections

        except Exception as e:
            logger.error(f"Error validating statement: {e}")
            return False, "No pude validar tu afirmación. Por favor intenta reformularla.", []

    def detect_contextual_reference(self, message: str) -> bool:
        """
        Detect if the message contains contextual references like "esa escala", "el acorde anterior".

        Args:
            message: User message

        Returns:
            True if contextual reference detected
        """
        message_lower = message.lower()

        contextual_keywords = [
            "esa escala", "ese acorde", "esa progresión", "ese arpegio",
            "la escala", "el acorde", "la progresión", "el arpegio",
            "esta escala", "este acorde", "esta progresión", "este arpegio",
            "anterior", "último", "última", "que mostraste", "que me mostraste",
            "que vimos", "que acabas de mostrar", "lo que mostraste"
        ]

        return any(keyword in message_lower for keyword in contextual_keywords)

    def is_validation_question(self, message: str) -> bool:
        """
        Detect if the message is asking for validation of a statement.

        Args:
            message: User message

        Returns:
            True if validation question detected
        """
        message_lower = message.lower()

        # Keywords that indicate validation/correction questions
        validation_keywords = [
            "debe", "debería", "deberia", "tiene que", "es correcto", "está bien", "esta bien",
            "es verdad", "cierto que", "correcto que", "debo", "tengo que",
            "comienza con", "empieza con", "termina con", "contiene",
            "incluye", "tiene la nota", "no debería", "no deberia", "no debe",
            "incorrecto", "incorrecta", "error", "mal", "equivocado", "equivocada",
            "la tónica", "la tonica", "nota raíz", "nota raiz", "primer nota",
            "primera nota"
        ]

        # Question patterns that indicate validation
        question_patterns = [
            r'no\s+deber[ií]a',  # "no debería"
            r'no\s+es\s+correcto',  # "no es correcto"
            r'(?:esta|está)\s+(?:mal|bien|correcto|equivocado)',  # "está mal", "está bien"
            r'comienza\s+con',  # "comienza con"
            r'empieza\s+con',  # "empieza con"
        ]

        # Check keywords
        has_keyword = any(keyword in message_lower for keyword in validation_keywords)

        # Check patterns
        has_pattern = any(re.search(pattern, message_lower) for pattern in question_patterns)

        return has_keyword or has_pattern
