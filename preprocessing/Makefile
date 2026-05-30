# MusicAI Preprocessing - Makefile
# Commands for testing, reporting, and development

.PHONY: help test test-quick test-full coverage report report-serve clean install lint

# Default target
help:
	@echo "MusicAI Preprocessing - Available commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run all tests with coverage"
	@echo "  make test-quick   - Run tests without slow markers"
	@echo "  make test-full    - Run all tests with full reporting"
	@echo "  make coverage     - Generate coverage report only"
	@echo "  make report       - Generate Allure report"
	@echo "  make report-serve - Generate and serve Allure report"
	@echo "  make clean        - Remove generated files"
	@echo "  make lint         - Run code linting"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests with default configuration (from pyproject.toml)
test:
	pytest

# Run quick tests (exclude slow markers)
test-quick:
	pytest -m "not slow" --no-cov

# Run all tests with full reporting
test-full:
	@echo "Running full test suite with all reports..."
	@mkdir -p reports/allure-results
	pytest \
		-v \
		--tb=short \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html:reports/coverage \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=json:reports/coverage.json \
		--alluredir=reports/allure-results \
		--html=reports/pytest-report.html \
		--self-contained-html \
		--clean-alluredir
	@echo ""
	@echo "Reports generated:"
	@echo "  - Coverage HTML: reports/coverage/index.html"
	@echo "  - Coverage JSON: reports/coverage.json"
	@echo "  - Pytest HTML:   reports/pytest-report.html"
	@echo "  - Allure data:   reports/allure-results/"
	@echo ""
	@echo "Run 'make report' to generate Allure report"

# Generate coverage report
coverage:
	pytest --cov=src --cov-report=html:reports/coverage --cov-report=term-missing
	@echo ""
	@echo "Coverage report: reports/coverage/index.html"

# Generate Allure report (requires allure CLI)
report:
	@if command -v allure >/dev/null 2>&1; then \
		allure generate reports/allure-results -o reports/allure-report --clean; \
		echo ""; \
		echo "Allure report generated: reports/allure-report/index.html"; \
	else \
		echo "Error: Allure CLI not installed"; \
		echo "Install with: brew install allure (macOS) or apt install allure (Linux)"; \
		echo "Or use: npm install -g allure-commandline"; \
	fi

# Generate and serve Allure report
report-serve:
	@if command -v allure >/dev/null 2>&1; then \
		allure serve reports/allure-results; \
	else \
		echo "Error: Allure CLI not installed"; \
		echo "Install with: brew install allure (macOS) or apt install allure (Linux)"; \
	fi

# Run specific test file
test-audio:
	pytest tests/test_audio.py -v

test-tokenizer:
	pytest tests/test_tokenizer.py -v

test-api:
	pytest tests/test_api.py -v

test-messaging:
	pytest tests/test_messaging.py -v

# Clean generated files
clean:
	rm -rf reports/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned generated files"

# Lint code
lint:
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src tests; \
	elif command -v flake8 >/dev/null 2>&1; then \
		flake8 src tests; \
	else \
		echo "No linter found. Install with: pip install ruff"; \
	fi

# Watch mode (requires pytest-watch)
watch:
	@if command -v ptw >/dev/null 2>&1; then \
		ptw -- -v --tb=short; \
	else \
		echo "pytest-watch not installed. Install with: pip install pytest-watch"; \
	fi

# Run tests in Docker
docker-test:
	docker-compose run --rm preprocessing pytest
