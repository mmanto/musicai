# MusicAI Model Base Module

Music Transformer with relative attention for autoregressive music generation.

## Overview

This module implements the core Music Transformer model:
- **Relative Attention**: O(L*D) memory complexity for long sequences
- **Autoregressive Generation**: Token-by-token music generation
- **Streaming**: Stream tokens during generation
- **Communication**: Receives from Preprocessing, sends to Reasoning/RLHF

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              MODEL BASE MODULE                       │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │           Music Transformer                    │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Relative Multi-Head Attention O(L*D)  │  │  │
│  │  │  12-24 Transformer Decoder Layers      │  │  │
│  │  │  Pre-LayerNorm Architecture            │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│                          │                          │
│  ┌──────────────────────────────────────────────┐  │
│  │           REST API (FastAPI :8002)           │  │
│  │           gRPC Server (:50052)               │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Using Docker Compose

```bash
# Start with GPU
docker-compose up -d

# Check logs
docker-compose logs -f model-base
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Run service
python -m src.main
```

## API Endpoints

### REST API (Port 8002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/generate` | Generate from tokens |
| POST | `/api/v1/generate/stream` | Stream generation |
| POST | `/api/v1/continue` | Continue sequence |
| POST | `/api/v1/embeddings` | Get embeddings |
| GET | `/api/v1/model/info` | Model info |

### Example Usage

```python
import requests

# Generate music
response = requests.post(
    "http://localhost:8002/api/v1/generate",
    json={
        "input_tokens": [1, 2, 3, 4, 5],
        "max_length": 256,
        "temperature": 0.9,
        "top_k": 50,
    }
)
result = response.json()
print(f"Generated: {len(result['generated_tokens'])} tokens")
```

## Model Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| VOCAB_SIZE | 30000 | Vocabulary size |
| D_MODEL | 512 | Model dimension |
| N_HEADS | 8 | Attention heads |
| N_LAYERS | 12 | Transformer layers |
| D_FF | 2048 | Feed-forward dim |
| MAX_SEQ_LENGTH | 8192 | Max sequence |

## Communication

### Incoming
- **Preprocessing** (RabbitMQ): `model.tokens` queue

### Outgoing
- **Reasoning** (RabbitMQ): `reasoning.generated`
- **RLHF** (RabbitMQ): `rlhf.output`

## Hardware Requirements

- **GPU**: NVIDIA with 8GB+ VRAM (16GB+ recommended)
- **RAM**: 16GB+
- **Storage**: 10GB+ for checkpoints

## License

MIT
