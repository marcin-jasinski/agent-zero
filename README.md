# Agent Zero (L.A.B.)

**Local Agent Builder** — A production-grade, open-source agentic RAG system with one-click deployment.

---

## ⚠️ FOR LOCAL DEVELOPMENT ONLY

> **IMPORTANT SECURITY NOTICE**
>
> Agent Zero is designed for **single-user local development and experimentation**. It is **NOT** intended for production deployment or multi-user access.
>
> **Do NOT:**
> - Expose port 8501 to the public internet
> - Use default passwords in production environments
> - Run this on a publicly accessible server
>
> **Default credentials are intentionally simple** because this is meant to run on `localhost` only. If you need to expose services externally, you MUST change all passwords and implement proper authentication.

---

## 🎯 What This Is (And Isn't)

### ✅ What Agent Zero IS:
- A **learning playground** for AI/RAG development
- A **local development environment** for single users
- A **demonstration** of agentic RAG architecture
- A **starting point** for building your own AI tools

### ❌ What Agent Zero is NOT:
- A production-ready multi-user application
- A secure system for public deployment
- A replacement for enterprise AI solutions
- Suitable for handling sensitive data in shared environments

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/agent-zero.git
cd agent-zero
```

### 2. Copy Environment File

```bash
cp .env.example .env
```

### 3. Start Services (Auto-Detect GPU)

```bash
# Windows
.\start.bat

# Linux / macOS
./start.sh
```

That's it! 🎉

**Access:**

- 📊 **A.P.I. (Chat + Admin):** http://localhost:8501
- 🔧 **Health check:** http://localhost:8501/health
- 🔌 **Ollama API:** http://localhost:11434

---

## 🖥️ Platform Support

| Platform                | GPU                 | Status          | Command       |
| ----------------------- | ------------------- | --------------- | ------------- |
| **Windows WSL 2**       | ✅ NVIDIA CUDA      | Fully supported | `.\start.bat` |
| **macOS Intel**         | ❌ None             | Fully supported | `./start.sh`  |
| **macOS Apple Silicon** | ✅ Metal (Built-in) | Fully supported | `./start.sh`  |
| **Linux NVIDIA**        | ✅ NVIDIA CUDA      | Fully supported | `./start.sh`  |
| **Linux (No GPU)**      | ❌ None             | Fully supported | `./start.sh`  |

GPU acceleration is **automatically detected**. No configuration needed!

**Apple Silicon Note:** M1/M2/M3/M4 Macs have integrated GPU with unified memory architecture, providing excellent inference performance via Metal acceleration.

See [CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md) for detailed platform-specific setup, or [APPLE_SILICON_GPU.md](APPLE_SILICON_GPU.md) for Apple Silicon details.

---

## 📋 Startup Commands

### Auto-Detect GPU (Recommended)

```bash
.\start.bat          # Windows
./start.sh           # Linux/macOS
```

### Force GPU Acceleration

```bash
.\start.bat gpu      # Windows
./start.sh gpu       # Linux/macOS
```

### Force CPU-Only Mode

```bash
.\start.bat cpu      # Windows
./start.sh cpu       # Linux/macOS
```

### Stop All Services

```bash
.\start.bat stop     # Windows
./start.sh stop      # Linux/macOS
```

---

## 🏗️ Architecture

Agent Zero is built on a modern, scalable stack:

- **Orchestration:** Docker Compose v2+
- **Backend:** Python 3.11+ with LangChain
- **LLM:** Ollama (ministral-3:3b)
- **Embeddings:** nomic-embed-text-v2-moe (768-dim)
- **Vector DB:** Qdrant (semantic search)
- **Search Engine:** Meilisearch (keyword search)
- **UI:** FastAPI + Gradio (A.P.I. Dashboard — unified Chat & Admin)
- **Observability:** Langfuse + ClickHouse

---

## 🔧 Development

### Install Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/ -v
```

### View Logs

```bash
# App logs
docker logs agent-zero-app -f

# All service logs
docker logs -f $(docker-compose ps -q)
```

---

## 📚 Documentation

- **[CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md)** — Setup for Windows, macOS, Linux
- **[GPU_CROSS_PLATFORM.md](GPU_CROSS_PLATFORM.md)** — GPU configuration details
- **[CODE_REVIEW.md](CODE_REVIEW.md)** — Code quality standards
- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** — Development roadmap

---

## 🎯 Features

✅ **Local-First** — All models run locally (no cloud APIs)
✅ **Secure by Design** — Data never leaves your machine
✅ **One-Click Deploy** — Single command start/stop
✅ **GPU Acceleration** — Auto-detected NVIDIA CUDA support
✅ **Cross-Platform** — Works on Windows, macOS, Linux
✅ **RAG Pipeline** — Document ingestion, vector search, semantic retrieval
✅ **Observability** — Full execution tracing with Langfuse
✅ **Scalable** — Docker-based architecture ready for production

---

## 📦 Services

| Service          | Port  | Purpose                    |
| ---------------- | ----- | -------------------------- |
| **A.P.I. (Gradio)** | 8501 | Unified Chat + Admin UI    |
| **REST API**     | 8501  | FastAPI `/health` endpoint |
| **Ollama**       | 11434 | LLM inference & embeddings |
| **Qdrant**       | 6333  | Vector database            |
| **Meilisearch**  | 7700  | Full-text search           |
| **Langfuse**     | 3000  | Observability & monitoring |

---

## 🛑 Troubleshooting

### Docker Not Running

```bash
# macOS & Linux
systemctl start docker

# Windows (WSL 2)
# Open Docker Desktop application
```

### Service Not Starting

**Symptoms**: Container exits immediately or enters restart loop

```bash
# Check container logs
docker logs agent-zero-app -f
docker logs agent-zero-ollama -f

# Check resource limits (services may need more memory)
docker stats

# Restart specific service
docker-compose restart ollama
```

**Common causes**:
- Insufficient memory (Ollama needs ~4GB minimum)
- Port already in use (check with `netstat -tulpn | grep 8501`)
- Docker resource limits too low

### GPU Not Detected

```bash
# Verify NVIDIA drivers
nvidia-smi

# Check Docker GPU support
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**For Apple Silicon**: GPU is automatic via Metal. No configuration needed.

### Ollama Model Not Found

```bash
# Manually pull required models
docker exec agent-zero-ollama ollama pull ministral-3:3b
docker exec agent-zero-ollama ollama pull nomic-embed-text-v2-moe

# List available models
docker exec agent-zero-ollama ollama list
```

**Note**: First startup automatically pulls models, but this can take 5-10 minutes.

### Out of Memory Errors

**Symptoms**: Container killed, "OOM" in logs, services crashing

**Solutions**:
1. Increase Docker memory limit (Docker Desktop → Settings → Resources)
2. Use a smaller model: Set `OLLAMA_MODEL=llama3.2:1b` in `.env`
3. Close other applications to free RAM
4. Reduce Qdrant/Meilisearch memory limits in `docker-compose.yml`

**Minimum requirements**: 8GB RAM (16GB recommended)

### Port Conflicts

**Symptoms**: "Address already in use" error

```bash
# Find what's using the port (example: 8501)
# Linux/macOS
lsof -i :8501

# Windows
netstat -ano | findstr :8501

# Kill the process or change ports in docker-compose.yml
```

### Search Returns No Results

**Check**:
1. Documents are indexed (Knowledge Base → Documents tab)
2. Qdrant is healthy (System Health tab)
3. Meilisearch is healthy (System Health tab)
4. Embeddings model is loaded: `docker exec agent-zero-ollama ollama list`

### Chat Not Responding

**Check**:
1. Ollama service is running: `docker ps | grep ollama`
2. Model is available: `docker exec agent-zero-ollama ollama list`
3. Check logs: `docker logs agent-zero-app -f`

For more help, see [CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md#troubleshooting).

---

## 📄 License

This project is licensed under the [LICENSE](LICENSE) file.

---

## 🤝 Contributing

Contributions are welcome! Please follow the code standards in [CODE_REVIEW.md](CODE_REVIEW.md).

---

**Built with ❤️ for developers who want local AI control.**
