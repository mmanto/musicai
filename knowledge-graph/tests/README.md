# Knowledge Graph Tests

Comprehensive test suite for the Knowledge Graph service.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_neo4j_client.py     # Neo4j client tests
├── test_ontology.py         # Music ontology tests
├── test_gnn_models.py       # GNN model tests
├── test_embeddings.py       # Embedding generation tests
├── test_api.py              # REST API tests
├── test_messaging.py        # RabbitMQ messaging tests
├── test_integration.py      # End-to-end integration tests
└── README.md                # This file
```

## Test Categories

### Unit Tests
- **test_neo4j_client.py**: Neo4j connection, queries, CRUD operations
- **test_ontology.py**: Ontology structure, node types, relationships
- **test_gnn_models.py**: GNN forward pass, training, architectures
- **test_embeddings.py**: Embedding generation, similarity computation
- **test_api.py**: REST endpoints, validation, error handling
- **test_messaging.py**: RabbitMQ pub/sub, message formats

### Integration Tests
- **test_integration.py**:
  - End-to-end workflows
  - Module-to-module communication
  - Error handling
  - Performance tests

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Slow tests
pytest -m slow

# Tests requiring Neo4j
pytest -m requires_neo4j

# Tests requiring RabbitMQ
pytest -m requires_rabbitmq
```

### Specific Test Files

```bash
# Run specific test file
pytest tests/test_api.py

# Run specific test class
pytest tests/test_api.py::TestHealthEndpoint

# Run specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_check
```

### With Docker

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests in container
docker-compose exec knowledge-graph pytest

# Stop test environment
docker-compose -f docker-compose.test.yml down
```

## Test Coverage

Generate coverage report:

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=src --cov-report=xml
```

## Writing Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
import pytest

class TestMyFeature:
    """Test my feature."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected_output

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            my_function(invalid_input)
```

### Using Fixtures

```python
def test_with_neo4j_client(mock_neo4j_client):
    """Test using Neo4j client fixture."""
    # mock_neo4j_client is automatically injected
    result = mock_neo4j_client.search_by_concept("Major")
    assert result is not None
```

## Available Fixtures

See `conftest.py` for all available fixtures:

- `mock_neo4j_client`: Mocked Neo4j client
- `mock_ontology`: Mocked music ontology
- `mock_gnn_model`: Mocked GNN model
- `mock_embedder`: Mocked graph embedder
- `mock_rabbitmq_publisher`: Mocked RabbitMQ publisher
- `app_client`: FastAPI test client
- `sample_graph_data`: Sample PyTorch Geometric data
- `sample_features`: Sample musical features
- `sample_concept_data`: Sample concept data

## Test Environment Variables

Tests use these environment variables (see `conftest.py`):

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test_password
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

## Continuous Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      neo4j:
        image: neo4j:5-community
        env:
          NEO4J_AUTH: neo4j/test_password
        ports:
          - 7687:7687

      rabbitmq:
        image: rabbitmq:3-management-alpine
        ports:
          - 5672:5672

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Debugging Tests

### Run with debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

### VSCode Configuration

Create `.vscode/settings.json`:

```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "-v"
  ],
  "python.testing.unittestEnabled": false
}
```

## Common Issues

### Neo4j Connection Error

If tests fail with Neo4j connection errors:

```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start Neo4j
docker-compose up -d neo4j

# Check logs
docker-compose logs neo4j
```

### RabbitMQ Connection Error

```bash
# Check RabbitMQ is running
docker ps | grep rabbitmq

# Start RabbitMQ
docker-compose up -d rabbitmq
```

### Import Errors

```bash
# Install in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Test Metrics

Target metrics:
- **Coverage**: > 80%
- **Test count**: > 50 tests
- **Test speed**: < 30 seconds for unit tests
- **Integration tests**: < 2 minutes

Current status:
```bash
pytest --co -q  # Count tests
pytest --durations=10  # Show slowest tests
```

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure > 80% coverage
3. Add integration tests if applicable
4. Update this README if needed
5. Run full test suite before committing

```bash
# Quick pre-commit check
pytest -x --ff -v
```
