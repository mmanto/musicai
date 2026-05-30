# Knowledge Graph Service

Musical knowledge ontology and Graph Neural Networks for MusicAI.

## Features

- **Music Ontology**: Comprehensive musical knowledge representation in Neo4j
  - Notes, intervals, scales, chords
  - Harmonic functions and progressions
  - Musical forms and genres
  - Theoretical rules and techniques

- **Graph Neural Networks**: Learn embeddings of musical concepts
  - GCN, GAT, GraphSAGE architectures
  - Unsupervised learning with graph autoencoders
  - Concept similarity and relationship inference

- **REST API**: Query musical knowledge and embeddings
- **gRPC**: High-performance inter-service communication
- **RabbitMQ**: Asynchronous feature enrichment

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker

```bash
# Create network (if not exists)
docker network create musicai-network

# Start services
docker-compose up -d

# Initialize ontology
docker-compose exec knowledge-graph python scripts/init_ontology.py

# Check health
curl http://localhost:8003/api/v1/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Start Neo4j (with Docker)
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/musicai_password \
  neo4j:5-community

# Initialize ontology
python scripts/init_ontology.py

# Start service
python -m src.main
```

## API Endpoints

### Health Check
```bash
GET /api/v1/health
```

### Query Concept
```bash
POST /api/v1/query/concept
{
  "concept_name": "Major",
  "max_depth": 2
}
```

### Query Relations
```bash
POST /api/v1/query/relations
{
  "from_concept": "C Major",
  "to_concept": "G Major",
  "relationship_type": "RESOLVES_TO"
}
```

### Get Concept Embedding
```bash
POST /api/v1/embeddings/concept
{
  "concept_name": "Dominant 7th"
}
```

### Find Similar Concepts
```bash
POST /api/v1/embeddings/similar
{
  "concept_name": "Major",
  "top_k": 10,
  "metric": "cosine"
}
```

### Ontology Schema
```bash
GET /api/v1/ontology/schema
```

### Ontology Statistics
```bash
GET /api/v1/ontology/stats
```

## Architecture

```
knowledge-graph/
├── src/
│   ├── graph/          # Neo4j client and ontology
│   ├── gnn/            # Graph Neural Networks
│   ├── api/            # REST and gRPC APIs
│   ├── messaging/      # RabbitMQ pub/sub
│   ├── config.py       # Configuration
│   └── main.py         # Entry point
├── scripts/
│   └── init_ontology.py  # Ontology initialization
├── tests/              # Unit tests
├── models/             # GNN model weights
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

Environment variables (see `.env.example`):

- `NEO4J_URI`: Neo4j connection URI
- `NEO4J_USER`: Neo4j username
- `NEO4J_PASSWORD`: Neo4j password
- `RABBITMQ_HOST`: RabbitMQ host
- `GNN_EMBEDDING_DIM`: Embedding dimension
- `GNN_NUM_LAYERS`: Number of GNN layers

## Music Ontology

### Node Types

- **Core**: Note, Chord, Scale, Key, Mode, Interval
- **Harmonic**: Progression, Cadence, HarmonicFunction
- **Rhythmic**: Rhythm, Meter, Tempo
- **Structural**: Form, Section, Phrase
- **Contextual**: Genre, Style, Era
- **Theoretical**: TheoreticalRule, Technique

### Relationship Types

- **Hierarchical**: CONTAINS, PART_OF, IS_A
- **Musical**: FOLLOWS, RESOLVES_TO, SIMILAR_TO, CONTRASTS_WITH
- **Functional**: FUNCTIONS_AS, IMPLIES, REQUIRES
- **Contextual**: USED_IN, CHARACTERISTIC_OF, DERIVED_FROM

## Testing

### Quick Start

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run in Docker
make docker-test
```

### Test Categories

```bash
# Unit tests only (fast)
make test-unit

# Integration tests (requires Neo4j + RabbitMQ)
make test-integration

# Specific test file
pytest tests/test_api.py -v

# Specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_check -v
```

### Test Coverage

Current test coverage includes:

- **Neo4j Client**: Connection, queries, CRUD operations (12 tests)
- **Music Ontology**: Structure, nodes, relationships (10 tests)
- **GNN Models**: Forward pass, training, architectures (8 tests)
- **Embeddings**: Generation, similarity, conversion (11 tests)
- **REST API**: All endpoints, validation, errors (15 tests)
- **RabbitMQ**: Publisher, consumer, integration (10 tests)
- **Integration**: End-to-end workflows, error handling (12 tests)

**Total: 78+ tests** with **>80% code coverage**

### Docker Testing

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests in container
docker-compose exec knowledge-graph-test pytest -v

# View coverage report
docker-compose exec knowledge-graph-test pytest --cov=src --cov-report=html

# Stop test environment
docker-compose -f docker-compose.test.yml down
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

## Neo4j Browser

Access Neo4j Browser at http://localhost:7474

Default credentials:
- Username: `neo4j`
- Password: `musicai_password`

## Integration

### Receives from Preprocessing
```python
# RabbitMQ: knowledge.features
{
  "event_type": "FEATURE_EXTRACTION_COMPLETE",
  "payload": {
    "features": {...}
  }
}
```

### Sends to Reasoning
```python
# RabbitMQ: knowledge.enriched
{
  "event_type": "FEATURES_ENRICHED",
  "payload": {
    "features": {...},
    "context": {...}
  }
}
```

## License

Part of MusicAI project.
