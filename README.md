# Agent Zero (L.A.B.)

**Local Agent Builder** — A production-grade, open-source agentic RAG system with one-click deployment.

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

- 📊 **Streamlit UI (A.P.I.):** http://localhost:8501
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
- **UI:** Streamlit (A.P.I. Dashboard)
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
| **Streamlit UI** | 8501  | Interactive dashboard      |
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

### GPU Not Detected

```bash
# Verify NVIDIA drivers
nvidia-smi

# Check Docker GPU support
docker run --rm --runtime=nvidia nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Models Not Loading

```bash
docker exec agent-zero-ollama ollama pull ministral-3:3b
docker exec agent-zero-ollama ollama pull nomic-embed-text-v2-moe
```

For more help, see [CROSS_PLATFORM_GUIDE.md](CROSS_PLATFORM_GUIDE.md#troubleshooting).

---

## 📄 License

This project is licensed under the [LICENSE](LICENSE) file.

---

## 🤝 Contributing

Contributions are welcome! Please follow the code standards in [CODE_REVIEW.md](CODE_REVIEW.md).

---

**Built with ❤️ for developers who want local AI control.**
