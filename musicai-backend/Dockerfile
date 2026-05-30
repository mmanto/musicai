FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    ffmpeg \
    fluidsynth \
    timidity \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies including ChromaDB
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir chromadb>=0.4.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/storage /app/chromadb_data

# Create non-root user for security
RUN useradd -m -u 1000 musicai && \
    chown -R musicai:musicai /app

USER musicai

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
