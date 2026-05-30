  # Reasoning Service Tests

Comprehensive test suite for the MusicAI Reasoning Service.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_symbolic.py         # Tests for symbolic reasoning (music21, rules)
├── test_neural.py           # Tests for neural reasoning (LLM, CoT)
├── test_hybrid.py           # Tests for hybrid reasoner
├── test_api.py              # Tests for REST API endpoints
├── test_messaging.py        # Tests for RabbitMQ integration
└── README.md                # This file
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run with coverage and show missing lines
pytest --cov=src --cov-report=term-missing
```

### Specific Test Suites

```bash
# Symbolic reasoning tests
pytest tests/test_symbolic.py -v

# Neural reasoning tests
pytest tests/test_neural.py -v

# Hybrid reasoner tests
pytest tests/test_hybrid.py -v

# API tests
pytest tests/test_api.py -v

# Messaging tests
pytest tests/test_messaging.py -v
```

### Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_api.py::TestHealthEndpoint -v

# Run a specific test function
pytest tests/test_api.py::TestHealthEndpoint::test_health_check_root -v
```

## Test Categories

### Unit Tests

- **test_symbolic.py**: Tests for Music21Analyzer and RulesEngine
- **test_neural.py**: Tests for OllamaClient and ChainOfThought
- **test_hybrid.py**: Tests for HybridReasoner

### Integration Tests

- **test_api.py**: End-to-end API endpoint tests
- **test_messaging.py**: RabbitMQ messaging tests

## Test Fixtures

Key fixtures available in `conftest.py`:

- `sample_musicxml`: Sample MusicXML data
- `sample_musicxml_base64`: Base64-encoded MusicXML
- `mock_music21_analyzer`: Mocked Music21Analyzer
- `mock_rules_engine`: Mocked RulesEngine
- `mock_llm_client`: Mocked Ollama LLM client
- `mock_cot_engine`: Mocked Chain-of-Thought engine
- `mock_hybrid_reasoner`: Mocked HybridReasoner
- `app_client`: FastAPI test client
- `mock_rabbitmq_connection`: Mocked RabbitMQ connection

## Test Coverage Goals

- **Symbolic reasoning**: > 90% coverage
- **Neural reasoning**: > 85% coverage (LLM calls mocked)
- **Hybrid reasoning**: > 90% coverage
- **API endpoints**: 100% coverage
- **Messaging**: > 80% coverage

## Mocking Strategy

### External Dependencies

All external services are mocked:

1. **Ollama LLM**: Mocked responses to avoid external API calls
2. **Music21**: Uses real library but with minimal test data
3. **RabbitMQ**: Fully mocked connections and channels
4. **Knowledge Graph**: Mocked HTTP client

### Why Mock?

- **Speed**: Tests run in milliseconds, not seconds
- **Reliability**: No network dependencies
- **Isolation**: Each test is independent
- **Cost**: No API usage fees

## Writing New Tests

### Basic Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestMyFeature:
    """Tests for my feature."""

    @pytest.fixture
    def my_component(self):
        """Create component instance."""
        from src.my_module import MyComponent
        return MyComponent()

    def test_initialization(self, my_component):
        """Test component initializes correctly."""
        assert my_component is not None

    @pytest.mark.asyncio
    async def test_async_method(self, my_component):
        """Test async method."""
        result = await my_component.async_method()
        assert result is not None
```

### Async Tests

Mark async tests with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result == expected
```

### Mocking External Calls

```python
@patch('src.module.external_service')
async def test_with_mock(mock_service):
    mock_service.call.return_value = "mocked response"
    result = await my_function()
    assert result == "mocked response"
```

## Continuous Integration

Tests should be run automatically on:

- Every commit
- Pull requests
- Before deployment

### CI Configuration Example

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running pytest from the project root:

```bash
cd reasoning/
pytest
```

### Async Test Failures

Ensure pytest-asyncio is installed:

```bash
pip install pytest-asyncio
```

### Music21 Errors

Music21 requires some system dependencies. If tests fail:

```bash
# Ubuntu/Debian
apt-get install libsndfile1

# macOS
brew install libsndfile
```

## Test Data

Test data is minimal and embedded in fixtures. For larger test datasets:

1. Place in `tests/data/` directory
2. Add to `.gitignore` if too large
3. Document how to generate/obtain the data

## Performance

Tests should be fast:

- **Unit tests**: < 100ms each
- **Integration tests**: < 1s each
- **Full suite**: < 30s total

If tests are slow, consider:

1. More aggressive mocking
2. Reducing test data size
3. Parallelizing with pytest-xdist

```bash
pip install pytest-xdist
pytest -n auto  # Run tests in parallel
```

## Best Practices

1. **One assertion per test**: Keep tests focused
2. **Descriptive names**: Test names should explain what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **DRY with fixtures**: Reuse setup code
5. **Mock external services**: Keep tests isolated
6. **Test edge cases**: Don't just test the happy path
7. **Keep tests fast**: Mock expensive operations

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
