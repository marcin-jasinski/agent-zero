# Cross-Platform Setup Guide: Agent Zero

Agent Zero is fully compatible with **Windows (WSL 2)**, **macOS**, and **Linux**. This guide explains setup and GPU acceleration for each platform.

## Quick Start (All Platforms)

```bash
# Auto-detect GPU and start
make start
```

This single command works everywhere and automatically:

- Detects NVIDIA GPU if available
- Enables GPU acceleration on compatible systems
- Falls back to CPU-only on unsupported systems

## Platform-Specific Guides

### 🪟 Windows with WSL 2

**Requirements:**

- Windows 10/11
- WSL 2 installed
- Docker Desktop for Windows (set to use WSL 2)
- NVIDIA drivers installed on Windows host
- NVIDIA CUDA Toolkit for WSL 2

**Setup:**

1. **Install NVIDIA GPU support for WSL 2:**

   ```
   https://developer.nvidia.com/cuda/wsl
   ```

2. **Clone Agent Zero:**

   ```bash
   cd /path/to/projects
   git clone https://github.com/yourusername/agent-zero.git
   cd agent-zero
   ```

3. **Copy environment file:**

   ```bash
   cp .env.example .env
   ```

4. **Start with GPU acceleration:**

   ```bash
   make start
   ```

   Or force GPU:

   ```bash
   make start-gpu
   ```

**Access:**

- Streamlit UI: http://localhost:8501
- Ollama API: http://localhost:11434

**Expected Behavior:**

```
✅ NVIDIA GPU detected. Starting with GPU acceleration...
```

---

### 🍎 macOS (Intel & Apple Silicon)

**Important:** macOS does NOT support NVIDIA CUDA GPUs. However:

- **Intel Macs:** CPU-only inference (still very capable)
- **Apple Silicon (M1/M2/M3/M4):** Integrated GPU with Metal support (automatic acceleration available)

Apple Silicon chips have excellent unified memory architecture and integrated GPUs that are well-suited for AI inference. Both CPU and GPU inference paths are highly optimized on these chips.

**Requirements:**

- macOS 11+
- Docker Desktop for Mac
- Homebrew (optional, for development tools)

**Setup:**

1. **Install Docker Desktop for Mac:**

   ```
   https://www.docker.com/products/docker-desktop
   ```

2. **Clone Agent Zero:**

   ```bash
   cd /path/to/projects
   git clone https://github.com/yourusername/agent-zero.git
   cd agent-zero
   ```

3. **Copy environment file:**

   ```bash
   cp .env.example .env
   ```

4. **Start in CPU-only mode:**
   ```bash
   make start
   ```

**Access:**

- Streamlit UI: http://localhost:8501
- Ollama API: http://localhost:11434

**Expected Behavior:**

```
ℹ️  No NVIDIA GPU detected. Starting in CPU-only mode...
```

**Performance Note:**
Apple Silicon (M1/M2/M3/M4) chips provide excellent inference performance through either CPU or integrated GPU paths. The unified memory architecture is particularly efficient for AI workloads. GPU acceleration via Metal is supported and will be automatically used when available.

---

### 🐧 Linux (NVIDIA GPU)

**Requirements:**

- Ubuntu 20.04+ (or similar)
- Docker and Docker Compose installed
- NVIDIA GPU (RTX 2070 Super or better recommended)
- NVIDIA drivers installed
- NVIDIA Container Runtime

**Setup:**

1. **Install NVIDIA Docker Runtime:**

   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   sudo apt-get update && sudo apt-get install -y nvidia-container-runtime
   ```

2. **Verify NVIDIA GPU is available:**

   ```bash
   nvidia-smi
   ```

3. **Clone Agent Zero:**

   ```bash
   cd /path/to/projects
   git clone https://github.com/yourusername/agent-zero.git
   cd agent-zero
   ```

4. **Copy environment file:**

   ```bash
   cp .env.example .env
   ```

5. **Start with GPU acceleration:**
   ```bash
   make start
   ```

**Access:**

- Streamlit UI: http://localhost:8501
- Ollama API: http://localhost:11434

**Expected Behavior:**

```
✅ NVIDIA GPU detected. Starting with GPU acceleration...
```

---

### 🐧 Linux (CPU-Only / No NVIDIA GPU)

**Requirements:**

- Linux (Ubuntu 20.04+, Debian, Fedora, etc.)
- Docker and Docker Compose installed

**Setup:**

1. **Clone Agent Zero:**

   ```bash
   cd /path/to/projects
   git clone https://github.com/yourusername/agent-zero.git
   cd agent-zero
   ```

2. **Copy environment file:**

   ```bash
   cp .env.example .env
   ```

3. **Start in CPU-only mode:**
   ```bash
   make start
   ```

**Access:**

- Streamlit UI: http://localhost:8501
- Ollama API: http://localhost:11434

**Expected Behavior:**

```
ℹ️  No NVIDIA GPU detected. Starting in CPU-only mode...
```

---

## Docker Compose Files Explained

### `docker-compose.yml` (Base)

Contains all services configured for **CPU-only operation**:

- app-agent (Streamlit UI)
- ollama (LLM inference)
- qdrant (Vector database)
- meilisearch (Search engine)
- postgres (Database)
- langfuse (Observability)
- clickhouse (Analytics)
- zookeeper (Coordination)

### `docker-compose.gpu.yml` (GPU Override)

Extends the base compose file to **add GPU support**:

- Adds `OLLAMA_GPU=1` environment variable
- Specifies NVIDIA GPU device mapping
- **Only loaded when explicitly included or auto-detected**

## Make Commands

```bash
# Auto-detect GPU and start (RECOMMENDED)
make start

# Force GPU acceleration (fails gracefully if no GPU)
make start-gpu

# Force CPU-only mode
make start-cpu

# Stop all services
make down

# View app logs
make logs

# View all service logs
make logs-all
```

## Troubleshooting

### "Docker is not running"

```bash
# macOS & Linux
docker daemon &

# Windows (WSL 2)
# Open Docker Desktop application
```

### GPU not detected (Linux)

```bash
# Verify NVIDIA drivers
nvidia-smi

# Verify NVIDIA Container Runtime
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Models not loading

```bash
# Check Ollama logs
docker logs agent-zero-ollama

# Manually pull models
docker exec agent-zero-ollama ollama pull ministral-3:3b
docker exec agent-zero-ollama ollama pull nomic-embed-text-v2-moe
```

### Port conflicts

If ports 8501, 11434, 6333, 7700 are already in use:

Edit `docker-compose.yml` and change port mappings:

```yaml
app-agent:
  ports:
    - "8502:8501" # Changed from 8501

ollama:
  ports:
    - "11435:11434" # Changed from 11434
```

## Hardware Recommendations

| Platform                | CPU      | RAM  | GPU       | Notes                             |
| ----------------------- | -------- | ---- | --------- | --------------------------------- |
| **Windows WSL 2**       | 4+ cores | 8GB+ | RTX 2070+ | GPU strongly recommended          |
| **macOS Intel**         | 4+ cores | 8GB+ | None      | CPU works fine                    |
| **macOS Apple Silicon** | 4+ cores | 8GB+ | None      | Excellent performance without GPU |
| **Linux**               | 4+ cores | 8GB+ | RTX 2070+ | GPU strongly recommended          |

## Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `OLLAMA_MODEL`: Model for text generation (default: ministral-3:3b)
- `OLLAMA_EMBED_MODEL`: Model for embeddings (default: nomic-embed-text-v2-moe)
- `LANGFUSE_ENABLED`: Enable observability (default: true)
- `LLM_GUARD_ENABLED`: Enable input/output scanning (default: false)

## More Information

- [Project README](README.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [API Documentation](docs/API.md)

---

**Happy building! 🚀**
