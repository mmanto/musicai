# MusicAI Preprocessing Service Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy proto files and compile
COPY protos/ /app/protos/
RUN mkdir -p /app/src/api/grpc && \
    python -m grpc_tools.protoc \
    -I/app/protos \
    --python_out=/app/src/api/grpc \
    --grpc_python_out=/app/src/api/grpc \
    /app/protos/preprocessing.proto || true

# Copy application code
COPY src/ /app/src/

# Create cache directory
RUN mkdir -p /app/cache

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 8001 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
