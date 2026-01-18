# Ollama Model Initialization Issue

## Problem

When the application starts, Ollama service is running but has no models loaded. This causes 404 errors when trying to use the LLM:

```
Error: 404 Client Error: Not Found for url: http://ollama:11434/api/generate
```

## Root Cause

Ollama models are not automatically pulled when the Docker container starts. They must be manually pulled before the application can use them.

## Solution

Two models need to be available in Ollama:

1. **ministral-3:3b** - For text generation (configured in `src/config.py`)
2. **nomic-embed-text-v2-moe** - For embeddings (configured in `src/config.py`)

### Manual Model Pull (Temporary Fix)

```bash
# Pull the main LLM model
docker exec agent-zero-ollama ollama pull ministral-3:3b

# Pull the embedding model
docker exec agent-zero-ollama ollama pull nomic-embed-text-v2-moe
```

### Verify Models Are Loaded

```bash
docker exec agent-zero-ollama ollama list
# or
curl http://localhost:11434/api/tags
```

## Permanent Solution (Recommended)

Update the Ollama Docker image to automatically pull models on startup.

### Option 1: Modify docker-compose.yml

Add an entrypoint script that pulls models:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: agent-zero-ollama
  entrypoint: sh -c "ollama serve & sleep 5 && ollama pull ministral-3:3b && ollama pull nomic-embed-text-v2-moe && wait"
  # ... rest of config
```

### Option 2: Create a Custom Dockerfile

Create `docker/Dockerfile.ollama`:

```dockerfile
FROM ollama/ollama:latest

# Copy a startup script
COPY docker/ollama-startup.sh /ollama-startup.sh
RUN chmod +x /ollama-startup.sh

ENTRYPOINT ["/ollama-startup.sh"]
```

Create `docker/ollama-startup.sh`:

```bash
#!/bin/bash
# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for service to be ready
sleep 5

# Pull required models
echo "Pulling required models..."
ollama pull ministral-3:3b
ollama pull nomic-embed-text-v2-moe

# Keep container running
wait $OLLAMA_PID
```

### Option 3: Update Startup Script

Enhance `src/startup.py` to automatically pull models if missing:

```python
def _initialize_ollama(self) -> None:
    """Initialize Ollama service and pull default models if needed."""
    try:
        ollama = OllamaClient()

        if not ollama.is_healthy():
            logger.warning("Ollama service not responding")
            return

        models = ollama.list_models()
        required_models = [
            self.config.ollama.model,
            self.config.ollama.embed_model
        ]

        for model in required_models:
            if model not in models:
                logger.info(f"Pulling model: {model}")
                ollama.pull_model(model)

        logger.info(f"All required models available")
    except Exception as e:
        logger.error(f"Ollama initialization failed: {e}")
```

## Current Status

Models are being pulled manually using:

```bash
docker exec agent-zero-ollama ollama pull ministral-3:3b
docker exec agent-zero-ollama ollama pull nomic-embed-text-v2-moe
```

Estimated time: 5-10 minutes depending on internet speed and disk I/O.

## Testing

Once models are loaded, test with:

```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ministral-3:3b",
    "prompt": "Hello!",
    "stream": false
  }'
```
