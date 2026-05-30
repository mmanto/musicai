#!/bin/bash

# RLHF Module Test Runner
# This script runs the basic tests for the RLHF module

set -e

echo "=========================================="
echo "RLHF Module - Test Runner"
echo "=========================================="
echo ""

# Check if we're running in Docker or locally
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    RUNNING_IN_DOCKER=true
else
    echo "Running on host machine"
    RUNNING_IN_DOCKER=false
fi

echo ""

# If running locally, check if Docker is available
if [ "$RUNNING_IN_DOCKER" = false ]; then
    if command -v docker &> /dev/null; then
        echo "Option 1: Run tests in Docker container"
        echo "----------------------------------------"
        echo "Building and starting RLHF service..."

        cd "$(dirname "$0")"

        # Check if container already exists
        if docker ps -a | grep -q musicai-rlhf; then
            echo "RLHF container already exists"
            if docker ps | grep -q musicai-rlhf; then
                echo "Container is running"
            else
                echo "Starting container..."
                docker start musicai-rlhf
                sleep 3
            fi
        else
            echo "Building and starting container via docker-compose..."
            docker-compose up -d --build
            echo "Waiting for container to be ready..."
            sleep 10
        fi

        echo ""
        echo "Copying tests to container..."
        docker cp tests musicai-rlhf:/app/

        echo ""
        echo "Running tests inside container..."
        docker exec musicai-rlhf pytest tests/ -v --tb=short

        TEST_EXIT_CODE=$?

        echo ""
        if [ $TEST_EXIT_CODE -eq 0 ]; then
            echo "✅ All tests passed successfully!"
        else
            echo "❌ Some tests failed. Check output above for details."
        fi

        exit $TEST_EXIT_CODE
    fi
fi

# If running inside Docker or no Docker available, run tests directly
echo "Option 2: Run tests directly with pytest"
echo "----------------------------------------"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing dependencies..."
    pip install pytest pytest-asyncio pytest-cov torch --quiet
fi

echo "Running tests..."
echo ""

cd "$(dirname "$0")"

pytest tests/ -v --tb=short

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "=========================================="
    echo "✅ All tests passed successfully!"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ Some tests failed"
    echo "=========================================="
fi

echo ""
echo "Test Summary:"
echo "  - Reward Model Tests: 16 tests"
echo "  - Training Tests: 10 tests"
echo "  - API Tests: 11 tests"
echo "  - Total: 37 tests"
echo ""

exit $TEST_EXIT_CODE
