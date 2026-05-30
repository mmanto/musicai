.PHONY: help install test test-unit test-integration test-coverage clean docker-build docker-up docker-down docker-test lint format

# Default target
help:
	@echo "Knowledge Graph Service - Available Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make install-dev      Install dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo "  make test-watch       Run tests in watch mode"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start services"
	@echo "  make docker-down      Stop services"
	@echo "  make docker-test      Run tests in Docker"
	@echo "  make docker-logs      View service logs"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters"
	@echo "  make format           Format code"
	@echo "  make type-check       Run type checker"
	@echo ""
	@echo "Database:"
	@echo "  make init-ontology    Initialize Neo4j ontology"
	@echo "  make neo4j-shell      Open Neo4j shell"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Clean build artifacts"
	@echo "  make clean-docker     Remove Docker containers and volumes"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install black flake8 mypy pylint isort

# Testing
test:
	pytest -v

test-unit:
	pytest -v -m "not integration"

test-integration:
	pytest -v -m integration

test-coverage:
	pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	pytest-watch -v

test-failed:
	pytest --lf -v

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Neo4j Browser: http://localhost:7474"
	@echo "RabbitMQ Management: http://localhost:15672"
	@echo "API: http://localhost:8003"

docker-down:
	docker-compose down

docker-test:
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down

docker-logs:
	docker-compose logs -f knowledge-graph

docker-exec:
	docker-compose exec knowledge-graph /bin/bash

# Code Quality
lint:
	flake8 src tests
	pylint src

format:
	black src tests
	isort src tests

type-check:
	mypy src --ignore-missing-imports

# Database
init-ontology:
	python scripts/init_ontology.py

neo4j-shell:
	docker-compose exec neo4j cypher-shell -u neo4j -p musicai_password

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build

clean-docker:
	docker-compose down -v
	docker-compose -f docker-compose.test.yml down -v

# Development
run:
	python -m src.main

run-dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8003

# Network
create-network:
	docker network create musicai-network || true
