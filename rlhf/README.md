# MusicAI RLHF Service

Reinforcement Learning from Human Feedback service for music generation quality improvement.

## Overview

The RLHF service implements state-of-the-art reinforcement learning algorithms to fine-tune music generation models based on human feedback. It combines:
- **Reward Model**: Learned preferences for music quality
- **Training Algorithms**: PPO, DPO, and GRPO
- **Human Feedback**: Collection and management of preferences
- **Active Learning**: Smart sampling for efficient feedback collection
- **Experiment Tracking**: MLflow and TensorBoard integration

## Features

### Reward Modeling
- Pairwise comparisons (A vs B)
- Pointwise scoring (0-1 scale)
- Ranking multiple outputs
- Multi-aspect evaluation (harmony, melody, rhythm, structure, originality)

### Training Algorithms
- **PPO** (Proximal Policy Optimization): Stable policy gradient method
- **DPO** (Direct Preference Optimization): Direct preference learning without reward model
- **GRPO** (Group Relative Policy Optimization): Group-based optimization

### Feedback Collection
- Preference feedback (pairwise comparisons)
- Rating feedback (numerical scores)
- Ranking feedback (order multiple outputs)
- Binary feedback (accept/reject)

### Active Learning
- Uncertainty-based sampling
- Diversity sampling
- Smart feedback prioritization

## Architecture

```
rlhf/
├── src/
│   ├── reward/          # Reward model implementation
│   │   ├── reward_model.py
│   │   └── feedback_collector.py
│   ├── training/        # Training algorithms
│   │   ├── ppo_trainer.py
│   │   ├── dpo_trainer.py
│   │   └── trainer_base.py
│   ├── api/             # REST API
│   │   └── rest/
│   ├── messaging/       # RabbitMQ integration
│   └── config.py
├── tests/
├── Dockerfile
└── docker-compose.yml
```

## Installation

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run the service
python -m src.main
```

### Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f rlhf

# Stop
docker-compose down
```

## API Endpoints

### Health Check
```bash
GET /api/v1/health
```

### Feedback Submission

#### Preference Feedback
```bash
POST /api/v1/feedback/preference
{
  "feedback_id": "fb_123",
  "music_id": "music_456",
  "user_id": "user_789",
  "preferred_id": "output_a",
  "rejected_id": "output_b",
  "aspects": {
    "harmony": 0.9,
    "melody": 0.8
  },
  "confidence": 0.95
}
```

#### Rating Feedback
```bash
POST /api/v1/feedback/rating
{
  "feedback_id": "fb_124",
  "music_id": "music_456",
  "user_id": "user_789",
  "rating": 4.5,
  "max_rating": 5.0,
  "aspects": {
    "harmony": 4.0,
    "melody": 5.0
  }
}
```

### Training

#### Start Training Job
```bash
POST /api/v1/train
{
  "experiment_name": "ppo_run_1",
  "algorithm": "ppo",
  "num_steps": 10000,
  "batch_size": 8,
  "learning_rate": 0.00001
}
```

#### Get Training Status
```bash
GET /api/v1/train/{job_id}
```

### Evaluation

#### Evaluate Music Quality
```bash
POST /api/v1/evaluate
{
  "music_data": "base64_encoded_data",
  "format": "tokens",
  "return_aspects": true
}
```

### Generation

#### Generate Music
```bash
POST /api/v1/generate
{
  "prompt": "A jazz piece in Bb major",
  "max_length": 512,
  "temperature": 1.0,
  "num_samples": 3,
  "use_rlhf_model": true
}
```

### Statistics

#### Feedback Statistics
```bash
GET /api/v1/feedback/stats
```

#### Experiments
```bash
GET /api/v1/experiments
```

## Training Algorithms

### PPO (Proximal Policy Optimization)

Stable policy gradient method with clipped objective:

```python
from src.training import PPOTrainer, TrainingConfig

config = TrainingConfig(
    learning_rate=1e-5,
    batch_size=8,
    max_steps=10000
)

trainer = PPOTrainer(
    model=policy_model,
    reward_model=reward_model,
    config=config,
    ppo_epochs=4,
    clip_range=0.2
)

trainer.train(train_dataloader)
```

### DPO (Direct Preference Optimization)

Direct optimization from preferences:

```python
from src.training import DPOTrainer

trainer = DPOTrainer(
    model=policy_model,
    reward_model=reward_model,  # For evaluation only
    beta=0.1
)

trainer.train(preference_dataloader)
```

## Reward Model

The reward model evaluates music quality across multiple aspects:

```python
from src.reward import RewardModel, RewardType

# Create reward model
reward_model = RewardModel(
    reward_type=RewardType.PAIRWISE,
    num_aspects=5
)

# Evaluate single output
score = reward_model.evaluate_pointwise(embedding)
print(f"Score: {score.score}")
print(f"Aspects: {score.breakdown}")

# Compare two outputs
preference = reward_model.evaluate_pairwise(emb_a, emb_b)
print(f"Preference: {'A' if preference > 0 else 'B'}")
```

## Feedback Collection

```python
from src.reward import FeedbackCollector, FeedbackType

collector = FeedbackCollector()

# Add preference feedback
collector.add_preference(
    feedback_id="fb_1",
    music_id="music_1",
    user_id="user_1",
    preferred_id="output_a",
    rejected_id="output_b",
    confidence=0.9
)

# Get statistics
stats = collector.get_statistics()
print(f"Total feedback: {stats['total']}")
print(f"By type: {stats['by_type']}")
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REST_PORT` | REST API port | 8005 |
| `TRAINING_ALGORITHM` | Default algorithm (ppo/dpo/grpo) | ppo |
| `LEARNING_RATE` | Training learning rate | 1e-5 |
| `PPO_EPOCHS` | PPO optimization epochs | 4 |
| `DPO_BETA` | DPO regularization | 0.1 |
| `MLFLOW_TRACKING_URI` | MLflow server URL | http://localhost:5000 |
| `GPU_ENABLED` | Enable GPU training | true |

## Experiment Tracking

### MLflow

```bash
# Start MLflow server
mlflow server --host 0.0.0.0 --port 5000

# View experiments
open http://localhost:5000
```

### TensorBoard

```bash
# Start TensorBoard
tensorboard --logdir ./runs

# View metrics
open http://localhost:6006
```

## Integration with Other Services

### Model Base
- Fetches base model for training
- Submits fine-tuned models

### Reasoning
- Validates generated outputs
- Provides theory-based feedback

### RabbitMQ Events
- Publishes training updates
- Consumes feedback requests
- Event-driven architecture

## Performance

- **Feedback collection**: < 100ms per submission
- **Evaluation**: ~50ms per sample (CPU), ~10ms (GPU)
- **Training**: Depends on model size and algorithm
  - PPO: ~10-20 samples/sec
  - DPO: ~20-40 samples/sec

## Best Practices

1. **Feedback Quality**
   - Collect diverse feedback from multiple users
   - Use confidence scores to weight feedback
   - Balance preference types

2. **Training**
   - Start with DPO for quick iteration
   - Use PPO for final fine-tuning
   - Monitor reward model accuracy

3. **Evaluation**
   - Regular human evaluation
   - Track multiple quality metrics
   - Compare against baseline

4. **Active Learning**
   - Prioritize uncertain samples
   - Ensure diversity in feedback data
   - Balance exploration vs exploitation

## Troubleshooting

### Training not converging
```bash
# Reduce learning rate
LEARNING_RATE=1e-6

# Increase batch size
BATCH_SIZE=16

# Adjust PPO clip range
PPO_CLIP_RANGE=0.1
```

### Out of memory
```bash
# Reduce batch size
BATCH_SIZE=4

# Enable gradient accumulation
GRADIENT_ACCUMULATION_STEPS=8

# Use mixed precision
MIXED_PRECISION=fp16
```

## Development

### Adding New Training Algorithm

1. Inherit from `TrainerBase`
2. Implement `train_step()` method
3. Add configuration parameters
4. Register in API

### Adding New Reward Type

1. Add enum value to `RewardType`
2. Implement evaluation method in `RewardModel`
3. Update API schemas

## License

Part of the MusicAI project.

## Contact

For issues and questions, see the main MusicAI repository.
