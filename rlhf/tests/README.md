# RLHF Module - Test Suite

This directory contains the basic test suite for the RLHF (Reinforcement Learning from Human Feedback) module.

## Test Files

### 1. test_basic_reward.py (16 tests)
Tests for reward model and feedback collection components:
- **RewardModel**: Testing reward type initialization, forward pass, and evaluation methods
- **FeedbackCollector**: Testing feedback collection, statistics, and preference pair extraction
- **Configuration**: Testing settings and defaults

### 2. test_basic_training.py (10 tests)
Tests for training algorithms and trainers:
- **TrainingConfig**: Testing configuration import and defaults
- **PPOTrainer**: Testing PPO initialization and optimizer creation
- **DPOTrainer**: Testing DPO initialization and reference model
- **TrainerBase**: Testing abstract base class structure

### 3. test_basic_api.py (11 tests)
Tests for API components and service structure:
- **API Schemas**: Testing pydantic models and enums
- **Service Health**: Testing FastAPI app creation and routes
- **Module Structure**: Testing module imports and organization

## Running Tests

### Quick Start
```bash
# From the rlhf directory
./run_tests.sh
```

### Manual Execution

#### Using pytest directly:
```bash
cd /path/to/musicai/rlhf
source venv/bin/activate  # if using virtual environment
pytest tests/ -v
```

#### Using Docker:
```bash
# Build and start the container
docker-compose up -d --build

# Copy tests and run
docker cp tests musicai-rlhf:/app/
docker exec musicai-rlhf pytest tests/ -v
```

#### Run specific test file:
```bash
pytest tests/test_basic_reward.py -v
pytest tests/test_basic_training.py -v
pytest tests/test_basic_api.py -v
```

#### Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

## Test Philosophy

These are **basic functional tests** designed to:

1. ✅ **Verify Imports**: Ensure modules load without errors
2. ✅ **Test Initialization**: Confirm objects instantiate correctly
3. ✅ **Basic Functionality**: Test core methods work as expected
4. ✅ **Configuration**: Verify settings load properly

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── test_basic_reward.py     # Reward model & feedback tests
├── test_basic_training.py   # Training algorithm tests
├── test_basic_api.py        # API and service tests
├── TEST_SUMMARY.md          # Detailed test documentation
└── README.md                # This file
```

## Dependencies

Core testing dependencies (from requirements.txt):
```
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
torch>=2.1.0
```

## Common Issues

### Issue: grpcio build failures on Python 3.14
**Solution**: Use Python 3.11 or 3.12 for better compatibility:
```bash
pyenv install 3.11.8
pyenv local 3.11.8
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: CUDA/GPU not available
**Solution**: Tests run on CPU by default, no GPU required

### Issue: Import errors
**Solution**: Ensure all dependencies installed:
```bash
pip install -r requirements.txt
```

### Issue: Port conflicts during testing
**Solution**: Tests use TestClient, no actual ports are bound

## Next Steps

After basic tests pass, consider:

1. **Integration Tests**: Test complete training workflows end-to-end
2. **Performance Tests**: Benchmark reward model inference speed
3. **Data Pipeline Tests**: Test feedback processing and data loading
4. **E2E Tests**: Test full RLHF training cycles with real data
5. **Load Tests**: Test API under concurrent request load

## Test Coverage Goals

Current coverage (basic tests):
- ✅ Module imports: 100%
- ✅ Class instantiation: 100%
- ✅ Basic methods: ~60%
- ❌ Training workflows: 0%
- ❌ Integration paths: 0%

Target coverage for v1.1.0:
- Core components: 80%+
- Training workflows: 60%+
- Integration paths: 40%+

## Contributing

When adding new tests:
1. Follow existing naming patterns (`test_*`)
2. Use descriptive test names (`test_what_it_does`)
3. Add docstrings explaining what is tested
4. Group related tests in classes
5. Keep tests focused and independent

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [PyTorch Testing](https://pytorch.org/docs/stable/testing.html)
- [RLHF Overview](https://huggingface.co/blog/rlhf)
