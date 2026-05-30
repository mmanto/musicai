# MusicAI Preprocessing Module

Audio tokenization, feature extraction, and MIDI conversion service for the MusicAI system.

## Overview

This module handles the first stage of the MusicAI pipeline:
- **Tokenization**: Convert MIDI/audio to BPE tokens using MidiTok
- **Feature Extraction**: Extract tempo, key, time signature, spectrograms
- **Audio-to-MIDI**: Transcribe audio using basic-pitch (Spotify)
- **Communication**: Send processed data to other modules via gRPC and RabbitMQ

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              PREPROCESSING MODULE                    │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Tokenizer  │  │   Features   │  │  Audio2MIDI │ │
│  │   (MidiTok) │  │  (librosa)   │  │(basic-pitch)│ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬─────┘ │
│         └────────────────┼─────────────────┘       │
│                          ▼                          │
│  ┌──────────────────────────────────────────────┐  │
│  │           REST API (FastAPI :8001)           │  │
│  │           gRPC Server (:50051)               │  │
│  └──────────────────────────────────────────────┘  │
│                          │                          │
│  ┌──────────────────────────────────────────────┐  │
│  │    RabbitMQ Publisher/Consumer (Messaging)   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        [Model Base] [Knowledge] [Reasoning]
         (gRPC/MQ)   Graph (MQ)   (gRPC/MQ)
```

## Quick Start

### Using Docker Compose

```bash
# Create network (first time only)
docker network create musicai-network

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f preprocessing
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Compile proto files
python -m grpc_tools.protoc -I protos \
  --python_out=src/api/grpc \
  --grpc_python_out=src/api/grpc \
  protos/preprocessing.proto

# Run the service
python -m src.main
```

## API Endpoints

### REST API (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/tokenize/midi` | Tokenize MIDI file |
| POST | `/api/v1/tokenize/audio` | Tokenize audio (via MIDI conversion) |
| POST | `/api/v1/tokenize/text` | Extract features from text description |
| POST | `/api/v1/features/extract` | Extract audio features |
| POST | `/api/v1/features/spectrogram` | Generate spectrogram |
| POST | `/api/v1/convert/audio-to-midi` | Convert audio to MIDI |

### gRPC (Port 50051)

See `protos/preprocessing.proto` for service definition.

## Communication with Other Modules

### Outgoing (to other modules)

| Target | Protocol | Route/Method |
|--------|----------|--------------|
| Model Base | RabbitMQ | `model.tokens` |
| Knowledge Graph | RabbitMQ | `knowledge.features` |
| Reasoning | gRPC | `ReanalyzeSection()` |

### Incoming (from other modules)

| Source | Protocol | Queue/Method |
|--------|----------|--------------|
| Reasoning | gRPC | `ReanalyzeSection()` |
| Any | RabbitMQ | `preprocessing.tasks` |

## Configuration

Environment variables (see `.env.example`):

```bash
# Core
SERVICE_NAME=preprocessing
REST_PORT=8001
GRPC_PORT=50051

# Infrastructure
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0

# Other modules
MODEL_BASE_GRPC=model-base:50052
KNOWLEDGE_GRAPH_GRPC=knowledge-graph:50053

# Processing
BPE_VOCAB_SIZE=30000
N_MELS=128
SAMPLE_RATE=22050
```

## Technologies

- **Tokenization**: MidiTok (BPE)
- **Audio Processing**: librosa, torchaudio
- **Audio-to-MIDI**: basic-pitch (Spotify)
- **Symbolic Music**: music21
- **API**: FastAPI, gRPC
- **Messaging**: RabbitMQ, Redis

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Example Usage

### Python Client

```python
import requests

# Tokenize MIDI
with open("music.mid", "rb") as f:
    response = requests.post(
        "http://localhost:8001/api/v1/tokenize/midi",
        files={"file": f}
    )
    result = response.json()
    print(f"Tokens: {len(result['tokens'])}")

# Extract features
with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8001/api/v1/features/extract",
        files={"file": f}
    )
    features = response.json()
    print(f"Tempo: {features['tempo']} BPM")
    print(f"Key: {features['key']}")
```

### gRPC Client

```python
import grpc
from src.api.grpc import preprocessing_pb2, preprocessing_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = preprocessing_pb2_grpc.PreprocessingServiceStub(channel)

# Extract features
with open("audio.wav", "rb") as f:
    request = preprocessing_pb2.AudioRequest(
        audio_data=f.read(),
        format="wav"
    )
    response = stub.ExtractFeatures(request)
    print(f"Tempo: {response.tempo}")
```

## License

MIT
