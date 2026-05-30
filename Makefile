# MusicAI Stack - Makefile
# Commands for managing the complete MusicAI stack

.PHONY: help up down build logs status clean restart \
        up-infra up-services up-chat \
        logs-infra logs-services logs-chat \
        shell-backend shell-frontend \
        test health

# Default target
help:
	@echo "MusicAI Stack - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Stack Management:"
	@echo "  make up              - Start all services"
	@echo "  make up-build        - Build and start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make clean           - Stop services and remove volumes"
	@echo ""
	@echo "Partial Stack:"
	@echo "  make up-infra        - Start infrastructure only (rabbitmq, redis, neo4j, ollama)"
	@echo "  make up-services     - Start microservices only"
	@echo "  make up-chat         - Start chat application only"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs            - Follow logs for all services"
	@echo "  make logs-infra      - Follow infrastructure logs"
	@echo "  make logs-services   - Follow microservices logs"
	@echo "  make logs-chat       - Follow chat application logs"
	@echo "  make status          - Show service status"
	@echo "  make health          - Check health of all services"
	@echo ""
	@echo "Development:"
	@echo "  make shell-backend   - Open shell in backend container"
	@echo "  make shell-frontend  - Open shell in frontend container"
	@echo "  make test            - Run integration tests"
	@echo ""
	@echo "Utility:"
	@echo "  make pull            - Pull latest images"
	@echo "  make prune           - Remove unused Docker resources"

# ============================================================================
# STACK MANAGEMENT
# ============================================================================

# Start all services
up:
	@echo "Starting MusicAI Stack..."
	docker compose up -d
	@echo ""
	@echo "Services started. Access:"
	@echo "  - Frontend:        http://localhost:5173"
	@echo "  - Chat Backend:    http://localhost:8000"
	@echo "  - Reasoning API:   http://localhost:8004"
	@echo "  - RabbitMQ UI:     http://localhost:15672"
	@echo "  - Neo4j Browser:   http://localhost:7474"
	@echo ""
	@echo "NOTE: If Ollama is not accessible from containers, run:"
	@echo "  OLLAMA_HOST=0.0.0.0 ollama serve"
	@echo "Or use the docker Ollama: make up-ollama"

# Start with Docker Ollama (if host Ollama is not available)
up-ollama:
	@echo "Starting MusicAI Stack with Docker Ollama..."
	docker compose --profile ollama up -d

# Build and start all services
up-build:
	@echo "Building and starting MusicAI Stack..."
	docker compose up -d --build

# Stop all services
down:
	@echo "Stopping MusicAI Stack..."
	docker compose down

# Restart all services
restart: down up

# Stop and remove volumes (clean slate)
clean:
	@echo "Stopping services and removing volumes..."
	docker compose down -v
	@echo "Clean complete."

# ============================================================================
# PARTIAL STACK
# ============================================================================

# Infrastructure services
INFRA_SERVICES = rabbitmq redis neo4j ollama

# Microservices
MICRO_SERVICES = preprocessing model-base knowledge-graph reasoning rlhf

# Chat application
CHAT_SERVICES = musicai-backend musicai-frontend

up-infra:
	@echo "Starting infrastructure services..."
	docker compose up -d $(INFRA_SERVICES)

up-services: up-infra
	@echo "Starting microservices..."
	docker compose up -d $(MICRO_SERVICES)

up-chat: up-infra
	@echo "Starting chat application..."
	docker compose up -d $(CHAT_SERVICES)

# ============================================================================
# LOGS
# ============================================================================

logs:
	docker compose logs -f

logs-infra:
	docker compose logs -f $(INFRA_SERVICES)

logs-services:
	docker compose logs -f $(MICRO_SERVICES)

logs-chat:
	docker compose logs -f $(CHAT_SERVICES)

# Individual service logs
logs-%:
	docker compose logs -f $*

# ============================================================================
# MONITORING
# ============================================================================

status:
	@echo "MusicAI Stack Status"
	@echo "===================="
	docker compose ps

health:
	@echo "Checking service health..."
	@echo ""
	@echo "Infrastructure:"
	@curl -s http://localhost:15672/api/healthchecks/node -u guest:guest 2>/dev/null | grep -q "ok" && echo "  RabbitMQ: OK" || echo "  RabbitMQ: FAIL"
	@curl -s http://localhost:6379 2>/dev/null && echo "  Redis: OK" || redis-cli ping 2>/dev/null | grep -q "PONG" && echo "  Redis: OK" || echo "  Redis: FAIL"
	@curl -s http://localhost:7474 2>/dev/null | grep -q "neo4j" && echo "  Neo4j: OK" || echo "  Neo4j: FAIL"
	@curl -s http://localhost:11434/api/tags 2>/dev/null | grep -q "models" && echo "  Ollama: OK" || echo "  Ollama: FAIL"
	@echo ""
	@echo "Microservices:"
	@curl -sf http://localhost:8001/health 2>/dev/null && echo "  Preprocessing: OK" || echo "  Preprocessing: FAIL"
	@curl -sf http://localhost:8002/health 2>/dev/null && echo "  Model Base: OK" || echo "  Model Base: FAIL"
	@curl -sf http://localhost:8003/health 2>/dev/null && echo "  Knowledge Graph: OK" || echo "  Knowledge Graph: FAIL"
	@curl -sf http://localhost:8004/api/v1/health 2>/dev/null && echo "  Reasoning: OK" || echo "  Reasoning: FAIL"
	@curl -sf http://localhost:8005/api/v1/health 2>/dev/null && echo "  RLHF: OK" || echo "  RLHF: FAIL"
	@echo ""
	@echo "Chat Application:"
	@curl -sf http://localhost:8000/health 2>/dev/null && echo "  Backend: OK" || echo "  Backend: FAIL"
	@curl -sf http://localhost:5173 2>/dev/null && echo "  Frontend: OK" || echo "  Frontend: FAIL"

# ============================================================================
# DEVELOPMENT
# ============================================================================

shell-backend:
	docker compose exec musicai-backend /bin/bash

shell-frontend:
	docker compose exec musicai-frontend /bin/sh

shell-%:
	docker compose exec $* /bin/sh

test:
	@echo "Running integration tests..."
	docker compose -f tests/docker-compose.test.yml up --abort-on-container-exit

# ============================================================================
# UTILITY
# ============================================================================

pull:
	@echo "Pulling latest base images..."
	docker compose pull

prune:
	@echo "Removing unused Docker resources..."
	docker system prune -f
	docker volume prune -f

# Build specific service
build-%:
	docker compose build $*

# Rebuild specific service
rebuild-%:
	docker compose up -d --build $*
