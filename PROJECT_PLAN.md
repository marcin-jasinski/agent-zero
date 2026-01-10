# Agent Zero (L.A.B.) - Implementation Plan

**Status**: Plan Approved ✓ | Last Updated: 2026-01-10

---

## Table of Contents

1. [Project Definition](#project-definition)
2. [Implementation Phases](#implementation-phases)
3. [Validation Checkpoints](#validation-checkpoints)
4. [Critical Design Decisions](#critical-design-decisions)
5. [Progress Tracking](#progress-tracking)

---

## Project Definition

### Branding & Concept

- **Name**: Agent Zero
- **Concept**: L.A.B. (Local Agent Builder)
- **Goal**: Production-ready, local-first environment for building and testing AI agents
- **UI Dashboard**: A.P.I. (AI Playground Interface)
- **Language**: STRICTLY ENGLISH (code, comments, UI, documentation)
- **Philosophy**: "One-Click Deployment", "Secure by Design", "Local-First"

### Technical Stack

- **Orchestration**: Docker Compose v2+
- **Language**: Python 3.11+
- **Core Libraries**: LangChain, Streamlit, Pydantic, LLM Guard, Pytest
- **Infrastructure Services**:
  - `app-agent`: Python 3.11 + Streamlit (port 8501)
  - `ollama`: LLM inference (port 11434, 8GB RAM limit)
  - `qdrant`: Vector Database (port 6333, 1GB RAM limit, persistent)
  - `meilisearch`: Full-text Search (port 7700, 1GB RAM limit)
  - `postgres`: Langfuse backing DB (port 5432, internal)
  - `langfuse`: Observability & Tracing UI (port 3000)

---

## Implementation Phases

### PHASE 1: Foundation & Infrastructure

**Goal**: Establish Docker environment and project skeleton with proper development setup.

#### Step 1: Project Structure & Git Setup

✅ **COMPLETED** | Commit: 40e78e8

- [x] Create directory tree: `/src`, `/tests`, `/docker`, `/docs`, `/.devcontainer`
- [x] Initialize `pyproject.toml` with Python 3.11+ specification
- [x] Create `.env.example` with all required secrets/config
- [x] Initialize git branches: `master` (stable), `develop` (integration)
- [x] Extend `.gitignore` for Python/Docker artifacts

**Deliverable**: Clean project scaffold with no warnings from `git status` ✓

**Success Criteria**: All directories exist, `git status` shows only tracked files ✓

---

#### Step 2: Docker Compose Orchestration

- [ ] Build `docker-compose.yml` with 6 services:
  - [ ] `app-agent`: Python 3.11 + Streamlit (port 8501, 2GB RAM limit)
  - [ ] `ollama`: LLM inference (port 11434, 4GB RAM limit)
  - [ ] `qdrant`: Vector DB (port 6333, 1GB RAM limit, persistent volume)
  - [ ] `meilisearch`: Full-text search (port 7700, 512MB RAM limit)
  - [ ] `postgres`: Langfuse backing DB (port 5432, 512MB RAM limit, internal only)
  - [ ] `langfuse`: Observability UI (port 3000, depends on postgres)
- [ ] Define internal Docker DNS networking (services resolve via name)
- [ ] Add health checks for critical services (ollama, qdrant, meilisearch, postgres)
- [ ] Define named volumes for persistence (qdrant, postgres, meilisearch)
- [ ] Add resource limits to all services

**Deliverable**: `docker-compose.yml` with resource limits enforced, passes `docker-compose config` validation

**Success Criteria**: `docker-compose config` returns no errors, all services listed

---

#### Step 3: DevContainer Configuration

- [ ] Create `.devcontainer/devcontainer.json`:
  - [ ] Uses `app-agent` service as development container
  - [ ] Mounts workspace at `/workspace`
  - [ ] Configures Python interpreter from container
- [ ] Install VS Code extensions:
  - [ ] Python (ms-python.python)
  - [ ] Docker (ms-azuretools.vscode-docker)
  - [ ] Pylance (ms-python.vscode-pylance)
  - [ ] REST Client (humao.rest-client)
- [ ] Include `initializeCommand` for dependency installation

**Deliverable**: Dev experience functional: `F5` launches debugger, code changes reflected instantly

**Success Criteria**: Open in DevContainer → Debugger works → Python interpreter detected

---

#### Step 4: Configuration Management Layer

- [ ] Create `src/config.py` using `pydantic-settings`:
  - [ ] Define `DatabaseConfig` (Qdrant, Postgres)
  - [ ] Define `OllamaConfig` (host, port, model)
  - [ ] Define `MeilisearchConfig` (host, port)
  - [ ] Define `LangfuseConfig` (host, port, API key)
  - [ ] Include validation and defaults
- [ ] Create `src/logging_config.py` for structured logging
- [ ] Create `src/__init__.py` and `src/version.py`

**Deliverable**: Single source of truth for all runtime configuration, type-safe

**Success Criteria**: `from src.config import Config; Config()` succeeds and loads from `.env`

---

#### Step 5: Repository Structure Validation

- [ ] Create stub `__init__.py` in all directories
- [ ] Verify all paths referenced in Docker config exist
- [ ] Run `docker-compose build --no-cache` successfully
- [ ] Run `docker-compose up -d` and verify all services reach "healthy" status within 30 seconds

**Deliverable**: Clean startup, all services healthy

**Success Criteria**: `docker-compose ps` shows all services as "Up (healthy)", no error logs

---

### PHASE 2: Core Application Skeleton

**Goal**: Build Streamlit UI (A.P.I.) with basic multi-tab navigation and service connectivity.

#### Step 6: Streamlit UI Frame (A.P.I.)

- [ ] Create `src/ui/main.py`:
  - [ ] Configure Streamlit page (title, icon, layout)
  - [ ] Implement 4 tabs: **Chat**, **Knowledge Base**, **Settings**, **Logs**
  - [ ] Sidebar: Service health status indicators
  - [ ] Session state management for chat history
- [ ] Create `src/ui/components/`:
  - [ ] `chat_interface.py` (message display, input form)
  - [ ] `kb_manager.py` (file upload widget, document list)
  - [ ] `settings_panel.py` (model selection, LLM parameters)
  - [ ] `health_check.py` (service status badges)
- [ ] Implement error boundary UI for graceful failures

**Deliverable**: Streamlit app loads at `http://localhost:8501`

**Success Criteria**: UI accessible, all tabs visible and responsive, no Python errors on load

---

#### Step 7: Service Connectivity Layer

- [ ] Create `src/services/__init__.py`
- [ ] Create `src/services/base_client.py`:
  - [ ] Abstract client for retry logic (exponential backoff)
  - [ ] Timeout handling (configurable per service)
  - [ ] Circuit breaker pattern for cascading failures
- [ ] Implement service clients:
  - [ ] `src/services/ollama_client.py` (pull models, generate embeddings, chat)
  - [ ] `src/services/qdrant_client.py` (create collections, upsert vectors, search)
  - [ ] `src/services/meilisearch_client.py` (create indexes, index documents, search)
  - [ ] `src/services/langfuse_client.py` (initialize callback, flush traces)
- [ ] Wrap external SDKs with app-specific error handling and logging

**Deliverable**: Service clients testable in isolation (mock-friendly)

**Success Criteria**: All clients importable, no external calls on import, type hints complete

---

#### Step 8: Health Check & Startup Sequence

- [ ] Create `src/health.py`:
  - [ ] `check_ollama()` → ping endpoint
  - [ ] `check_qdrant()` → list collections
  - [ ] `check_meilisearch()` → health endpoint
  - [ ] `check_postgres()` → connection test
  - [ ] Caches results for 5 seconds
- [ ] Create `src/startup.py`:
  - [ ] Initialize Ollama with default model (e.g., `mistral`)
  - [ ] Create Qdrant collection for embeddings with proper schema
  - [ ] Create Meilisearch index for documents with searchable fields
- [ ] Add startup logs to UI "Logs" tab

**Deliverable**: UI displays green ✓/red ✗ status for each service

**Success Criteria**: Health checks return correct status, startup errors visible in UI "Logs" tab

---

### PHASE 2 Validation Checkpoint

**Phase 2 Complete When**:

- [ ] `docker-compose up -d` → all services healthy
- [ ] Navigate to `http://localhost:8501`
- [ ] UI loads with 4 tabs visible
- [ ] Sidebar shows health status (initially red for disconnected services)
- [ ] No Python errors in terminal
- [ ] DevContainer debugger functional

---

### PHASE 3: RAG Pipeline Integration

**Goal**: Implement document ingestion and retrieval augmented generation workflow.

#### Step 9: Document Ingestion Pipeline

- [ ] Create `src/core/ingest.py`:
  - [ ] `ingest_pdf()`: Extract text from PDFs (using `pypdf`)
  - [ ] `chunk_document()`: Split into overlapping chunks (500 tokens, 50 overlap)
  - [ ] `generate_embeddings()`: Call Ollama for embeddings
  - [ ] `store_in_qdrant()`: Upsert vectors with metadata
  - [ ] `store_in_meilisearch()`: Index searchable text
- [ ] Create `src/models/document.py`:
  - [ ] `DocumentChunk` dataclass: `id`, `content`, `source`, `chunk_index`, `metadata`
- [ ] Implement background job queue (use thread pool for MVP)

**Deliverable**: Upload PDF in UI → document appears in Knowledge Base

**Success Criteria**: PDF upload succeeds, document metadata stored in both Qdrant and Meilisearch

---

#### Step 10: Retrieval Engine

- [ ] Create `src/core/retrieval.py`:
  - [ ] `retrieve_relevant_docs()`: Query Qdrant by embedding similarity (top-k=5)
  - [ ] Implement hybrid search: Qdrant (semantic) + Meilisearch (keyword)
  - [ ] Return ranked list with scores
- [ ] Create `src/models/retrieval.py`:
  - [ ] `RetrievalResult` dataclass: `content`, `source`, `score`, `metadata`

**Deliverable**: Search returns ranked results from both services

**Success Criteria**: Query returns results with relevance scores, results ranked correctly

---

#### Step 11: Agent Orchestration with LangChain

- [ ] Create `src/core/agent.py`:
  - [ ] Initialize LangChain agent with Ollama as LLM
  - [ ] Define agent tools: `retrieve_documents`, `search_knowledge_base`, `echo` (test)
  - [ ] Agent memory: `ConversationBufferMemory` (session-based)
  - [ ] Implement `run_agent()` with streaming callback for UI display
- [ ] Create `src/models/agent.py`:
  - [ ] `AgentConfig` dataclass: `model_name`, `temperature`, `max_tokens`, `tools`
  - [ ] `AgentMessage` dataclass: `role`, `content`, `timestamp`, `tool_used`

**Deliverable**: Chat sends messages → agent retrieves docs → generates responses with sources

**Success Criteria**: Agent responds in chat tab, sources attributed in response

---

#### Step 12: Multi-Turn Conversation Memory

- [ ] Implement `src/core/memory.py`:
  - [ ] `ConversationManager`: Persist session history in-memory
  - [ ] Methods: `add_message()`, `get_history()`, `clear_history()`
  - [ ] Conversation summarization trigger (every 10 messages)
- [ ] Integrate into agent context window

**Deliverable**: Chat maintains multi-turn context

**Success Criteria**: Agent references previous messages correctly, context window managed

---

### PHASE 3 Validation Checkpoint

**Phase 3 Complete When**:

- [ ] Upload PDF via "Knowledge Base" tab
- [ ] Document appears in document list
- [ ] Search in KB returns results with scores
- [ ] Type message in "Chat" tab
- [ ] Agent generates response with sources attributed
- [ ] Multi-turn conversation works (agent remembers previous messages)

---

### PHASE 4: Security & Observability

**Goal**: Add LLM Guard security and Langfuse tracing for production readiness.

#### Step 13: LLM Guard Integration

- [ ] Create `src/security/guard.py`:
  - [ ] Input scanner: `scan_user_input()` → detect prompt injection, toxic content
  - [ ] Output scanner: `scan_llm_output()` → detect harmful content, PII leakage
  - [ ] Use `llm-guard` library with pre-built rules
- [ ] Implement as middleware in agent execution
- [ ] Log all blocked requests to observability layer

**Deliverable**: Malicious inputs/outputs are sanitized or blocked

**Success Criteria**: Blocked content logged, request rejected gracefully in UI

---

#### Step 14: Langfuse Observability

- [ ] Create `src/observability/langfuse_callback.py`:
  - [ ] Implement LangChain callback handler for Langfuse integration
  - [ ] Track: LLM calls, tool usage, agent decisions, execution time
  - [ ] Include custom metrics: retrieval count, answer confidence
- [ ] Configure in agent initialization
- [ ] Add Langfuse dashboard iframe to Settings tab

**Deliverable**: Langfuse shows agent traces

**Success Criteria**: Click "View Trace" in chat → Langfuse displays full execution trace

---

#### Step 15: Environment-Specific Configuration

- [ ] Implement `src/config.py` environment modes: `development`, `staging`, `production`
- [ ] Staging/production: Enable LLM Guard, require Langfuse
- [ ] Development: Optional guards, local tracing
- [ ] Add environment validation on startup

**Deliverable**: Environment-based security enforcement

**Success Criteria**: `ENV=production docker-compose up` enforces all security, `ENV=development` allows testing

---

### PHASE 4 Validation Checkpoint

**Phase 4 Complete When**:

- [ ] Malicious input test → blocked and logged
- [ ] LLM Guard metrics visible in observability
- [ ] Langfuse dashboard accessible and shows traces
- [ ] Environment modes work correctly
- [ ] Production mode enforces security requirements

---

### PHASE 5: Testing & Documentation

**Goal**: Ensure code quality and developer experience.

#### Step 16: Pytest Setup & Fixtures

- [ ] Create `tests/conftest.py`:
  - [ ] Mock Ollama client (return dummy embeddings)
  - [ ] Mock Qdrant client (in-memory storage)
  - [ ] Mock Meilisearch client (return fake results)
  - [ ] Mock Langfuse callback
- [ ] Create `tests/fixtures/`:
  - [ ] Sample PDFs, embeddings, Qdrant responses
- [ ] Implement `pytest.ini` with coverage thresholds (80% core logic)

**Deliverable**: Fast test execution without external services

**Success Criteria**: `pytest` runs in <5 seconds, 100% mocked external services

---

#### Step 17: Unit Tests for Core Modules

- [ ] `tests/core/test_ingest.py`: Verify chunking, embedding generation
- [ ] `tests/core/test_retrieval.py`: Verify ranking, hybrid search
- [ ] `tests/core/test_agent.py`: Verify tool calling, memory management
- [ ] `tests/security/test_guard.py`: Verify input/output scanning
- [ ] Each test: arrange → act → assert, no external calls

**Deliverable**: Unit tests with >80% coverage on core modules

**Success Criteria**: `pytest --cov=src core logic` ≥80%, all tests pass

---

#### Step 18: Integration Tests (Docker-dependent)

- [ ] Create `tests/integration/test_e2e_chat.py`:
  - [ ] Mark with `@pytest.mark.integration`
  - [ ] Spin up services, upload document, run chat, verify end-to-end
  - [ ] Include in CI/CD, skip locally by default
- [ ] Documentation on running: `pytest -m integration`

**Deliverable**: Integration tests pass against real Docker services

**Success Criteria**: `pytest -m integration` passes, e2e workflow verified

---

#### Step 19: Documentation & README

- [ ] Create `README.md`:
  - [ ] Badges: License, Python version, Docker, Build status
  - [ ] "What is Agent Zero?" section
  - [ ] "Quick Start" (3 steps: clone, `docker-compose up`, open `http://localhost:8501`)
  - [ ] Architecture diagram (Mermaid): UI → Services → LLMs → DBs
  - [ ] Development guide: Running tests, debugging, adding custom tools
  - [ ] API docs for service clients
  - [ ] Troubleshooting section
- [ ] Create `ARCHITECTURE.md`: Detailed layer diagrams, data flow
- [ ] Create `CONTRIBUTING.md`: Commit conventions (Conventional Commits), branch naming

**Deliverable**: New developer can run project and understand architecture in <20 minutes

**Success Criteria**: README is clear, architecture diagram is accurate, Quick Start works

---

### PHASE 5 Validation Checkpoint

**Phase 5 Complete When**:

- [ ] `pytest` runs with >80% coverage
- [ ] `pytest -m integration` passes
- [ ] README is complete and clear
- [ ] Architecture diagram is accurate
- [ ] New developer can understand project in <20 minutes

---

## Validation Checkpoints

### Summary Table

| Phase       | Checkpoint                                                        | Status               | Notes                     |
| ----------- | ----------------------------------------------------------------- | -------------------- | ------------------------- |
| **Phase 1** | `docker-compose up -d` → all services healthy, DevContainer works | 🔄 In Progress (1/5) | Infrastructure foundation |
| **Phase 2** | UI loads, services connect, health checks display correctly       | ⏳ Not Started       | Core UI & connectivity    |
| **Phase 3** | Upload PDF → search in KB → chat generates responses with sources | ⏳ Not Started       | RAG pipeline              |
| **Phase 4** | Malicious input blocked, Langfuse shows traces                    | ⏳ Not Started       | Security & observability  |
| **Phase 5** | `pytest --cov≥80%`, README clear to new developer                 | ⏳ Not Started       | Testing & docs            |

---

## Critical Design Decisions

### 1. Single Service Architecture

- **Decision**: All logic in `app-agent` container (no separate API gateway)
- **Rationale**: Simplifies deployment, reduces complexity for "One-Click Deployment"
- **Trade-off**: Vertical scaling limited; horizontal scaling requires stateless redesign later

### 2. Synchronous Execution

- **Decision**: No message queues initially; async jobs handled via threading
- **Rationale**: MVP simplicity; scales for single-user development
- **Migration Path**: Upgrade to Celery + Redis for multi-user production

### 3. Session-Based Memory

- **Decision**: In-memory conversation store per session
- **Rationale**: Fast, no schema design needed; suitable for single-user
- **Upgrade**: Migrate to SQLite (Phase 2b), then Postgres for multi-user

### 4. Dual Indexing (Meilisearch + Qdrant)

- **Decision**: Index all documents in both Meilisearch (keyword) and Qdrant (semantic)
- **Rationale**: Ensures both semantic AND keyword search work, improves recall
- **Cost**: Higher storage, but acceptable for local deployment

### 5. Langfuse Tracing for All Operations

- **Decision**: Every agent decision, tool call, and LLM interaction logged
- **Rationale**: Explainability and debugging; critical for "Secure by Design"
- **Performance**: Minimal overhead; local Langfuse instance

### 6. Environment-Specific Security

- **Decision**: `development` mode is permissive; `production` enforces all guards
- **Rationale**: Fast iteration during development; secure defaults in production
- **Implementation**: Startup validation checks environment and adjusts settings

---

## Progress Tracking

### Quick Status Reference

```
Phase 1: Foundation & Infrastructure
├─ Step 1: Project Structure ............................ ✅ COMPLETED
├─ Step 2: Docker Compose ............................... ⏳ Not Started
├─ Step 3: DevContainer ................................. ⏳ Not Started
├─ Step 4: Config Management ............................ ⏳ Not Started
└─ Step 5: Validation ................................... ⏳ Not Started

Phase 2: Core Application Skeleton
├─ Step 6: Streamlit UI .................................. ⏳ Not Started
├─ Step 7: Service Connectivity .......................... ⏳ Not Started
└─ Step 8: Health Check & Startup ........................ ⏳ Not Started

Phase 3: RAG Pipeline Integration
├─ Step 9: Document Ingestion ............................ ⏳ Not Started
├─ Step 10: Retrieval Engine ............................. ⏳ Not Started
├─ Step 11: Agent Orchestration .......................... ⏳ Not Started
└─ Step 12: Conversation Memory .......................... ⏳ Not Started

Phase 4: Security & Observability
├─ Step 13: LLM Guard Integration ........................ ⏳ Not Started
├─ Step 14: Langfuse Observability ....................... ⏳ Not Started
└─ Step 15: Environment Configuration ................... ⏳ Not Started

Phase 5: Testing & Documentation
├─ Step 16: Pytest Setup ................................. ⏳ Not Started
├─ Step 17: Unit Tests ................................... ⏳ Not Started
├─ Step 18: Integration Tests ............................ ⏳ Not Started
└─ Step 19: Documentation ................................ ⏳ Not Started
```

### Update Log

| Date       | Phase | Step | Status       | Notes                                           |
| ---------- | ----- | ---- | ------------ | ----------------------------------------------- |
| 2026-01-10 | -     | Plan | ✅ Approved  | Plan reviewed and approved                      |
| 2026-01-10 | 1     | 1    | ✅ Completed | Project structure and configuration initialized |

---

## Next Steps

1. **Await Approval**: Implementation plan is documented and ready for Phase 1 execution
2. **Phase 1 Execution**: Upon approval, execute all 5 steps in Phase 1
3. **Validation**: Test that Docker services start cleanly
4. **Phase 2 Approval**: Request confirmation before proceeding to Phase 2

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-10  
**Maintained By**: Senior AI Architect  
**Status**: Ready for Phase 1 Execution
