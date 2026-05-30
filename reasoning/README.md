# MusicAI Reasoning Service

Hybrid symbolic and neural reasoning service for intelligent music analysis.

## Overview

The Reasoning service combines:
- **Symbolic reasoning** using music21 for precise music theory analysis
- **Neural reasoning** using LLMs (Ollama) for interpretive insights
- **Chain-of-Thought** reasoning for complex multi-step analysis
- **Hybrid approach** synthesizing both methods

## Features

### Symbolic Analysis (music21)
- Key and harmonic analysis
- Melodic and rhythmic analysis
- Form and structure analysis
- Voice leading validation
- Music theory rule checking

### Neural Reasoning (LLM)
- Interpretive analysis and explanations
- Creative suggestions and improvements
- Concept explanations
- Comparative analysis

### Chain-of-Thought
- Multi-step reasoning
- Complex query decomposition
- Iterative refinement
- Transparent reasoning paths

### Hybrid Reasoning
- Automatic mode selection
- Synthesis of symbolic and neural insights
- Confidence scoring
- Actionable recommendations

## Architecture

```
reasoning/
├── src/
│   ├── symbolic/           # Music21 analyzer, rules engine
│   ├── neural/             # LLM client, chain-of-thought
│   ├── hybrid/             # Hybrid reasoner
│   ├── api/                # REST and gRPC APIs
│   │   ├── rest/           # FastAPI endpoints
│   │   └── grpc/           # gRPC service
│   ├── messaging/          # RabbitMQ pub/sub
│   ├── config.py           # Configuration
│   └── main.py             # Entry point
├── prompts/                # Chain-of-thought prompts
├── tests/                  # Test suite
├── Dockerfile
└── docker-compose.yml
```

## Installation

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run the service
python -m src.main
```

### Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f reasoning

# Stop
docker-compose down
```

## API Endpoints

### REST API (Port 8004)

#### Analyze Music
```bash
POST /api/v1/analyze
{
  "music_data": "<base64-encoded-musicxml>",
  "format": "musicxml"
}
```

#### Hybrid Reasoning
```bash
POST /api/v1/reason
{
  "music_data": "<base64-encoded-musicxml>",
  "query": "Why does this sound melancholic?",
  "mode": "hybrid",
  "format": "musicxml"
}
```

#### Suggest Improvements
```bash
POST /api/v1/suggest-improvements
{
  "music_data": "<base64-encoded-musicxml>",
  "focus_areas": ["harmony", "melody"]
}
```

#### Validate Theory
```bash
POST /api/v1/validate-theory
{
  "music_data": "<base64-encoded-musicxml>",
  "rules": ["parallel_fifths", "voice_range"],
  "explain": true
}
```

#### Compare Pieces
```bash
POST /api/v1/compare
{
  "music_data1": "<base64-encoded-piece1>",
  "music_data2": "<base64-encoded-piece2>",
  "aspects": ["harmony", "style"]
}
```

#### Explain Concept
```bash
POST /api/v1/explain-concept
{
  "concept": "cadence",
  "level": "intermediate"
}
```

#### Chain-of-Thought
```bash
POST /api/v1/chain-of-thought
{
  "query": "How can I improve the voice leading?",
  "context": { ... },
  "num_steps": 5,
  "iterative": false
}
```

#### List Rules
```bash
GET /api/v1/rules?category=harmony&enabled_only=true
GET /api/v1/rules/categories
```

#### Health Check
```bash
GET /api/v1/health
```

### gRPC API (Port 50054)

See `src/api/grpc/reasoning.proto` for service definition.

## Reasoning Modes

### Symbolic Only
- Fast, deterministic analysis
- Precise music theory validation
- No LLM required

### Neural Only
- Interpretive insights
- Creative suggestions
- Requires Ollama

### Hybrid (Default)
- Combines both approaches
- Best overall results
- Balanced performance

### Adaptive
- Automatically selects mode based on query
- Optimal for varied workloads

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REST_PORT` | REST API port | 8004 |
| `GRPC_PORT` | gRPC port | 50054 |
| `OLLAMA_BASE_URL` | Ollama service URL | http://localhost:11434 |
| `OLLAMA_MODEL` | LLM model to use | llama3.1:8b |
| `COT_MAX_STEPS` | Chain-of-thought steps | 5 |
| `COT_TEMPERATURE` | LLM temperature | 0.3 |
| `KNOWLEDGE_GRAPH_URL` | Knowledge graph service | http://localhost:8003 |

## Dependencies

### Core
- music21: Symbolic music analysis
- langchain: LLM orchestration
- ollama: Local LLM inference
- httpx: Async HTTP client
- tenacity: Retry logic

### API
- fastapi: REST API
- uvicorn: ASGI server
- grpcio: gRPC support
- pydantic: Data validation

### Messaging
- aio-pika: Async RabbitMQ client

## Testing

### Quick Start
```bash
# Run all basic tests using the test script
./run_tests.sh

# Or run tests directly in the Docker container
docker exec musicai-reasoning pytest tests/test_basic_*.py -v
```

### Test Suite Overview

**Total Tests**: 38 (all passing ✅)

The test suite includes:
- **test_basic_symbolic.py**: 12 tests for symbolic reasoning components
- **test_basic_hybrid.py**: 12 tests for hybrid and neural components
- **test_basic_integration.py**: 14 tests for API and service integration

### Running Specific Tests
```bash
# Run specific test file
docker exec musicai-reasoning pytest tests/test_basic_symbolic.py -v

# Run specific test class
docker exec musicai-reasoning pytest tests/test_basic_symbolic.py::TestRulesEngineBasic -v

# Run specific test
docker exec musicai-reasoning pytest tests/test_basic_symbolic.py::TestRulesEngineBasic::test_list_all_rules -v

# Run with coverage
docker exec musicai-reasoning pytest tests/test_basic_*.py --cov=src --cov-report=html
```

### Test Coverage

✅ **Core Components**
- RulesEngine (13 music theory rules)
- Music21Analyzer (symbolic analysis)
- OllamaClient (LLM client)
- ChainOfThought (multi-step reasoning)
- HybridReasoner (hybrid reasoning)

✅ **API & Integration**
- FastAPI application
- Request/Response schemas
- REST endpoints
- Module structure

✅ **Configuration**
- Settings and environment variables
- Default values

See [TEST_SUMMARY.md](tests/TEST_SUMMARY.md) for detailed test documentation.

## Integration with Other Services

### Knowledge Graph
- Queries musical concepts and relationships
- Enriches analysis with ontology data

### RabbitMQ Events
- Publishes reasoning results
- Consumes validation requests
- Event-driven architecture

### Ollama
- Local LLM inference
- No external API calls
- Privacy-preserving

## Performance

- Symbolic analysis: < 1s for typical pieces
- Neural reasoning: 2-5s depending on complexity
- Chain-of-thought: 5-15s for multi-step reasoning
- Hybrid: Combines both, 3-8s typical

## Troubleshoho

### Ollama Connection Failed
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull llama3.1:8b
```

### Music21 Import Errors
```bash
# Install system dependencies
apt-get install libsndfile1

# Or use Docker for isolated environment
```

### RabbitMQ Connection Issues
```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq

# Restart if needed
docker-compose restart rabbitmq
```

## Development

### Adding New Rules

Edit `src/symbolic/rules_engine.py`:

```python
self.register_rule(Rule(
    name="my_rule",
    description="Description of the rule",
    category="harmony",
    severity=RuleSeverity.MEDIUM,
    validator=self._check_my_rule
))
```

### Adding Chain-of-Thought Examples

Add to `src/neural/chain_of_thought.py` or create prompt templates in `prompts/`.

### Custom LLM Prompts

Modify prompts in neural reasoning methods or add system prompts in `config.py`.

## License

Part of the MusicAI project.

## Contact

For issues and questions, see the main MusicAI repository.
