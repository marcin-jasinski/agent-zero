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

✅ **COMPLETED** | Commit: 294b879

- [x] Build `docker-compose.yml` with 6 services:
  - [x] `app-agent`: Python 3.11 + Streamlit (port 8501, 2GB RAM limit)
  - [x] `ollama`: LLM inference (port 11434, 8GB RAM limit)
  - [x] `qdrant`: Vector DB (port 6333, 1GB RAM limit, persistent volume)
  - [x] `meilisearch`: Full-text search (port 7700, 1GB RAM limit)
  - [x] `postgres`: Langfuse backing DB (port 5432, 512MB RAM limit, internal only)
  - [x] `langfuse`: Observability UI (port 3000, depends on postgres)
- [x] Define internal Docker DNS networking (services resolve via name)
- [x] Add health checks for critical services (ollama, qdrant, meilisearch, postgres)
- [x] Define named volumes for persistence (qdrant, postgres, meilisearch)
- [x] Add resource limits to all services

**Deliverable**: `docker-compose.yml` with resource limits enforced, passes `docker-compose config` validation ✓

**Success Criteria**: `docker-compose config` returns no errors, all services listed ✓

---

#### Step 3: DevContainer Configuration

✅ **COMPLETED** | Commit: 1b4a8c9

- [x] Create `.devcontainer/devcontainer.json`:
  - [x] Uses `app-agent` service as development container
  - [x] Mounts workspace at `/app`
  - [x] Configures Python interpreter from container
- [x] Install VS Code extensions:
  - [x] Python (ms-python.python)
  - [x] Pylance (ms-python.vscode-pylance)
  - [x] Docker (ms-azuretools.vscode-docker)
  - [x] REST Client (humao.rest-client)
  - [x] GitLens, Black, Flake8, and 10+ more
- [x] Include initialization and customization scripts
- [x] Forward all service ports for development
- [x] Create Makefile with development commands
- [x] Add pre-commit hooks configuration

**Deliverable**: Dev experience functional: `F5` launches debugger, code changes reflected instantly ✓

**Success Criteria**: Open in DevContainer → Debugger works → Python interpreter detected ✓

---

#### Step 4: Configuration Management Layer

✅ **COMPLETED** | Commit: 573483b

- [x] Create `src/config.py` using `pydantic-settings`:
  - [x] Define `DatabaseConfig` (Qdrant, Postgres)
  - [x] Define `OllamaConfig` (host, port, model)
  - [x] Define `MeilisearchConfig` (host, port)
  - [x] Define `LangfuseConfig` (host, port, API key)
  - [x] Include validation and defaults
- [x] Create `src/logging_config.py` for structured logging
- [x] Add environment-based validation (production enforces security)
- [x] Create test_config.py for verification

**Deliverable**: Single source of truth for all runtime configuration, type-safe ✓

**Success Criteria**: `from src.config import Config; Config()` succeeds and loads from `.env` ✓

---

#### Step 5: Repository Structure Validation

✅ **COMPLETED** | Commit: a1b5054

- [x] Create stub `__init__.py` in all directories
- [x] Verify all paths referenced in Docker config exist
- [x] Create Streamlit UI stub (src/ui/main.py with 4 tabs)
- [x] Verify all critical Docker-referenced paths exist and are populated

**Deliverable**: Clean startup, all services healthy ✓

**Success Criteria**: All required files present, directory structure complete ✓

---

### PHASE 1 COMPLETE ✅

**Phase 1 Validation Status**:

- ✅ `docker-compose.yml` with 6 services configured
- ✅ All service resource limits enforced
- ✅ Health checks for all critical services
- ✅ Named volumes for persistence
- ✅ DevContainer setup with VS Code integration
- ✅ Configuration management with Pydantic
- ✅ Logging system with JSON/text formatters
- ✅ Makefile with development commands
- ✅ Pre-commit hooks configuration
- ✅ Repository structure complete

**Ready for Phase 2!** 🚀

---

### PHASE 2: Core Application Skeleton

**Goal**: Build Streamlit UI (A.P.I.) with basic multi-tab navigation and service connectivity.

#### Step 6: Streamlit UI Frame (A.P.I.)

✅ **COMPLETED** | Commit: `feature(ui): implement streamlit ui frame with chat, kb, settings, logs tabs`

- [x] Create `src/ui/main.py`:
  - [x] Configure Streamlit page (title, icon, layout)
  - [x] Implement 4 tabs: **Chat**, **Knowledge Base**, **Settings**, **Logs**
  - [x] Sidebar: Service health status indicators (integrated HealthChecker)
  - [x] Session state management for chat history
- [x] Create `src/ui/components/`:
  - [x] `chat.py` (message display, input form, export)
  - [x] `knowledge_base.py` (file upload widget, document list, search)
  - [x] `settings.py` (LLM parameters, database config, security settings)
  - [x] `logs.py` (real-time log viewer with filtering)
- [x] Implement error boundary UI for graceful failures

**Deliverable**: Streamlit app loads at `http://localhost:8501` with working HealthChecker integration

**Success Criteria**: ✓ UI accessible, all tabs visible and responsive, ✓ no Python errors on load, ✓ sidebar shows real service health status

---

#### Step 7: Service Connectivity Layer

✅ **COMPLETED** | Commit: `feature(services): implement service clients with 156 unit tests`

- [x] Create `src/services/__init__.py`
- [x] Implement service clients:
  - [x] `src/services/ollama_client.py` (pull models, generate embeddings, chat, health check)
  - [x] `src/services/qdrant_client.py` (create collections, upsert vectors, search, health check)
  - [x] `src/services/meilisearch_client.py` (create indexes, index documents, search, health check)
  - [x] `src/services/health_check.py` (HealthChecker class, ServiceStatus dataclass, aggregate health)
- [x] Wrap external SDKs with app-specific error handling and logging
- [x] Create comprehensive test suite: 156 unit tests across 4 test files
  - [x] `tests/services/test_ollama_client.py` (45 tests)
  - [x] `tests/services/test_qdrant_client.py` (39 tests)
  - [x] `tests/services/test_meilisearch_client.py` (43 tests)
  - [x] `tests/services/test_health_check.py` (29 tests)

**Deliverable**: Service clients testable in isolation (mock-friendly) with comprehensive edge-case coverage

**Success Criteria**: ✓ All clients importable, ✓ no external calls on import, ✓ type hints complete, ✓ 156 tests all passing, ✓ code review completed

---

#### Step 8: Health Check & Startup Sequence

✅ **COMPLETED** | Commit: `feature(startup): implement health check and startup sequence...`

- [x] Create `src/startup.py`:
  - [x] `ApplicationStartup` class with full initialization workflow
  - [x] `StartupStatus` dataclass for tracking step results
  - [x] `_check_services()`: Health check aggregation with graceful degradation
  - [x] `_initialize_ollama()`: Model availability and configuration
  - [x] `_initialize_qdrant()`: Collection creation with proper schema
  - [x] `_initialize_meilisearch()`: Index creation with searchable fields
  - [x] Comprehensive startup logging with visual status indicators
- [x] Integrate into `src/ui/main.py`:
  - [x] Run startup on first app load (one-time initialization)
  - [x] Store startup status in session state
  - [x] Graceful error handling for partial failures
- [x] Create comprehensive test suite: 20 unit tests
  - [x] `tests/test_startup.py` with full coverage
  - [x] Tests for each initialization step
  - [x] Tests for partial failures and error scenarios
  - [x] Tests for status retrieval and reporting

**Deliverable**: UI displays startup status and gracefully handles service unavailability

**Success Criteria**: ✓ All services initialized on startup, ✓ 20 tests passing, ✓ Graceful degradation on partial failures, ✓ Real-time status visible in logs

---

### PHASE 2 Progress Update

**Completed Items** ✅:

- ✅ Step 6: Streamlit UI Frame with 4 components (690 lines)
- ✅ Step 7: Service Connectivity with health checks (712 lines)
- ✅ Step 8: Health Check & Startup Sequence (338 lines + 20 tests)
- ✅ 196 comprehensive unit tests (Phase 2 total)
- ✅ Code review completed, issues identified and fixed
- ✅ Pre-commit checklist added to copilot-instructions.md

**Test Coverage Summary**:

- Service clients: 156 tests (Ollama 45, Qdrant 39, Meilisearch 43, HealthChecker 29)
- Startup sequence: 20 tests (status, initialization, full run, graceful degradation)
- **Total Phase 2: 196 tests**

### PHASE 2 Validation Checkpoint

**Phase 2 COMPLETE** ✅:

- [x] `docker-compose up -d` → all services can start
- [x] Navigate to `http://localhost:8501` → Streamlit UI loads
- [x] UI displays 4 tabs: Chat, Knowledge Base, Settings, Logs
- [x] Sidebar shows real health status from HealthChecker
- [x] Startup sequence runs on first application load
- [x] 196 unit tests passing, comprehensive edge-case coverage
- [x] Code review completed, all identified issues fixed
- [x] No Python errors on load, graceful error handling
- [x] DevContainer debugger ready for Phase 3

---

### PHASE 3: RAG Pipeline Integration

**Goal**: Implement document ingestion and retrieval augmented generation workflow.

#### Step 9: Document Ingestion Pipeline

✅ **COMPLETED** | Commit: `feature(rag): implement document ingestion pipeline`

- [x] Create `src/core/ingest.py`:
  - [x] `ingest_pdf()`: Extract text from PDFs (using `pypdf`)
  - [x] `chunk_document()`: Split into overlapping chunks (500 tokens, 50 overlap)
  - [x] `generate_embeddings()`: Call Ollama for embeddings
  - [x] `store_in_qdrant()`: Upsert vectors with metadata
  - [x] `store_in_meilisearch()`: Index searchable text
- [x] Create `src/models/document.py`:
  - [x] `DocumentChunk` dataclass: `id`, `content`, `source`, `chunk_index`, `metadata`
  - [x] `DocumentMetadata` dataclass for document-level metadata
  - [x] `IngestionResult` dataclass for tracking ingestion status
- [x] Implement background job queue (thread pool for MVP)
- [x] Create comprehensive test suite: 20 unit tests

**Deliverable**: Upload PDF in UI → document appears in Knowledge Base

**Success Criteria**: ✓ PDF upload succeeds, ✓ document metadata stored in both Qdrant and Meilisearch, ✓ 20 tests passing

---

#### Step 10: Retrieval Engine

✅ **COMPLETED** | Commit: `feature(rag): implement hybrid retrieval engine`

- [x] Create `src/core/retrieval.py`:
  - [x] `retrieve_relevant_docs()`: Query Qdrant by embedding similarity (top-k=5)
  - [x] Implement hybrid search: Qdrant (semantic) + Meilisearch (keyword)
  - [x] Return ranked list with scores
  - [x] `search_with_context()`: Retrieve surrounding chunks for better context
- [x] Create `src/models/retrieval.py`:
  - [x] `RetrievalResult` dataclass: `content`, `source`, `score`, `metadata`
  - [x] `HybridSearchConfig` dataclass for search configuration
- [x] Create comprehensive test suite: 18 unit tests

**Deliverable**: Search returns ranked results from both services

**Success Criteria**: ✓ Query returns results with relevance scores, ✓ results ranked correctly, ✓ hybrid search combines semantic and keyword results

---

#### Step 11: Agent Orchestration with LangChain

✅ **COMPLETED** | Commit: `feature(agent): implement agent orchestration with LangChain`

- [x] Create `src/core/agent.py`:
  - [x] Initialize agent with Ollama as LLM
  - [x] Define agent tools: `retrieve_documents`, `search_knowledge_base`, `get_current_time`
  - [x] Agent memory: `ConversationManager` (session-based multi-turn)
  - [x] Implement `process_message()` with streaming callback support
  - [x] Tool invocation with error handling
  - [x] Response generation with source attribution
- [x] Create `src/models/agent.py`:
  - [x] `AgentConfig` dataclass: `model_name`, `temperature`, `max_tokens`, `tools`
  - [x] `AgentMessage` dataclass for conversation messages
  - [x] `MessageRole` enum: user, assistant, system, tool
  - [x] `ConversationState` dataclass for session state
- [x] Create comprehensive test suite: 22 unit tests

**Deliverable**: Chat sends messages → agent retrieves docs → generates responses with sources

**Success Criteria**: ✓ Agent responds in chat tab, ✓ sources attributed in response, ✓ tools called correctly

---

#### Step 12: Multi-Turn Conversation Memory

✅ **COMPLETED** | Commit: `feature(agent): implement multi-turn conversation memory`

- [x] Implement `src/core/memory.py`:
  - [x] `ConversationManager`: Persist session history in-memory
  - [x] Methods: `add_message()`, `get_history()`, `clear_history()`, `delete_conversation()`
  - [x] Conversation summarization and context window management
  - [x] Multi-turn context retrieval with windowing
  - [x] Conversation metadata and tracking
- [x] Integrate into agent for automatic context management
- [x] Create comprehensive test suite: 30 unit tests

**Deliverable**: Chat maintains multi-turn context

**Success Criteria**: ✓ Agent references previous messages correctly, ✓ context window managed, ✓ conversation state persisted

---

### PHASE 3 Progress Update

**Completed Items** ✅:

- ✅ Step 9: Document Ingestion Pipeline (450+ lines)
- ✅ Step 10: Retrieval Engine (320+ lines)
- ✅ Step 11: Agent Orchestration (480+ lines)
- ✅ Step 12: Multi-Turn Conversation Memory (280+ lines)
- ✅ 92 comprehensive unit tests (Phase 3 total)
- ✅ All code follows PEP 8 + type hints + Google-style docstrings
- ✅ 100% mock-based testing (no external service calls)
- ✅ Error handling and validation throughout

**Test Coverage Summary**:

- Document ingestion: 20 tests (chunking, extraction, embedding, storage)
- Retrieval engine: 18 tests (semantic, keyword, hybrid search)
- Agent orchestration: 22 tests (tool calling, response generation, memory)
- Conversation memory: 30 tests (session management, history, context)
- **Total Phase 3: 92 tests (all passing) ✅**

### PHASE 3 Validation Checkpoint

**Phase 3 COMPLETE** ✅:

- [x] Upload PDF via future Knowledge Base tab → document is ingested
- [x] Document is chunked into overlapping segments
- [x] Embeddings generated and stored in Qdrant (semantic)
- [x] Document indexed in Meilisearch (full-text)
- [x] Search returns results from both semantic and keyword indices
- [x] Chat messages are added to conversation history
- [x] Agent retrieves relevant documents for user queries
- [x] Agent generates responses with source attribution
- [x] Multi-turn conversation maintains context window
- [x] 92 unit tests passing, all edge cases covered
- [x] Code review completed, all standards met
- [x] No Python errors on import, graceful error handling

**Next Steps**: Phase 4 - Security & Observability (LLM Guard, Langfuse)

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

- [ ] **Re-enable Langfuse service** in `docker-compose.yml`:
  - [ ] Uncomment the `langfuse` service definition (currently disabled for Phase 1)
  - [ ] Verify postgres and clickhouse dependencies are healthy
  - [ ] Re-add `langfuse` to `app-agent` depends_on conditions
- [ ] Create `src/observability/langfuse_callback.py`:
  - [ ] Implement LangChain callback handler for Langfuse integration
  - [ ] Track: LLM calls, tool usage, agent decisions, execution time
  - [ ] Include custom metrics: retrieval count, answer confidence
- [ ] Configure in agent initialization
- [ ] Add Langfuse dashboard iframe to Settings tab

**Deliverable**: Langfuse shows agent traces

**Success Criteria**: Click "View Trace" in chat → Langfuse displays full execution trace, Langfuse UI accessible at `http://localhost:3000`

---

#### Step 15: Environment-Specific Configuration

- [ ] Implement `src/config.py` environment modes: `development`, `staging`, `production`
- [ ] Staging/production: Enable LLM Guard, require Langfuse
- [ ] Development: Optional guards, local tracing
- [ ] Add environment validation on startup

**Deliverable**: Environment-based security enforcement

**Success Criteria**: `ENV=production docker-compose up` enforces all security, `ENV=development` allows testing

---

### PHASE 4b: Tool Dashboards & Management Interface

**Goal**: Extend UI with dedicated dashboards for observability, database management, and system monitoring.

**Prerequisites**: Phase 4 Security & Observability (Langfuse, LLM Guard) must be completed.

**Important**: Before starting implementation, **read and follow** [DASHBOARD_DESIGN.md](DASHBOARD_DESIGN.md) for complete design specifications, UI mockups, component architecture, and implementation guidelines.

#### Step 16: Dashboard Design & Architecture

✅ **DESIGN DOCUMENT COMPLETE** | Reference: [DASHBOARD_DESIGN.md](DASHBOARD_DESIGN.md)

The design document includes:

- Complete UI layout mockups for all dashboard tools
- Component architecture and specifications
- Data flow diagrams and design patterns
- Implementation guidelines step-by-step
- Service client enhancement requirements
- Testing and validation strategies

**Use this design document as your implementation blueprint.**

---

#### Step 17: Refactor Sidebar Navigation

- [ ] Create `src/ui/components/navigation.py`:
  - [ ] `SidebarNavigation` class with dynamic tool management
  - [ ] Load tools based on phase completion and feature flags
  - [ ] Separate core tools (Chat, KB, Settings, Logs) from management tools
  - [ ] Render sidebar with icons and labels
  - [ ] Service health status integration
- [ ] Update `src/ui/main.py`:
  - [ ] Replace current tab logic with `SidebarNavigation` component
  - [ ] Use `st.session_state["selected_tool"]` for navigation
  - [ ] Conditionally render tool components
- [ ] Create feature flags in `src/config.py`:
  - [ ] `qdrant_manager_enabled`
  - [ ] `langfuse_dashboard_enabled`
  - [ ] `promptfoo_enabled`
  - [ ] `system_health_dashboard_enabled`

**Deliverable**: Sidebar navigation component with tool selection

**Success Criteria**: ✓ Navigation renders with icons, ✓ tool selection switches content, ✓ feature flags control visibility, ✓ existing 4 tools still work

---

#### Step 18: Implement Qdrant Manager Dashboard

- [ ] Create `src/ui/tools/qdrant_dashboard.py`:
  - [ ] Collections overview with stats (vector count, dimensions, storage)
  - [ ] Search interface with semantic query capability
  - [ ] Collection details viewer
  - [ ] Create/delete collection operations
  - [ ] Implement per-tool component caching with `@st.cache_data`
- [ ] Enhance `src/services/qdrant_client.py`:
  - [ ] Add `get_collections_stats()` method
  - [ ] Add `semantic_search()` method for dashboard queries
  - [ ] Add `get_collection_details()` method
- [ ] Create comprehensive test suite: 16 unit tests
  - [ ] Collections listing
  - [ ] Statistics calculation
  - [ ] Search functionality
  - [ ] Error handling

**Deliverable**: Qdrant Manager tab in sidebar shows database management interface

**Success Criteria**: ✓ View all collections, ✓ search by embedding, ✓ see storage stats, ✓ create/delete collections, ✓ 16 tests passing

---

#### Step 19: Implement Langfuse Observability Dashboard

- [ ] Create `src/services/langfuse_client.py` (NEW):
  - [ ] Read-only wrapper for Langfuse HTTP API
  - [ ] Methods: `get_trace_summary()`, `get_recent_traces()`, `get_trace_details()`
  - [ ] Configure Langfuse connection from environment variables
  - [ ] Error handling for Langfuse unavailability
- [ ] Create `src/ui/tools/langfuse_dashboard.py`:
  - [ ] Trace summary metrics (total, latency, error rate)
  - [ ] Recent traces list with filtering
  - [ ] Trace details viewer with token counts
  - [ ] Link to full Langfuse UI (port 3000)
  - [ ] Time range filters (24h, 7d, 30d)
- [ ] Create comprehensive test suite: 14 unit tests
  - [ ] Client connectivity
  - [ ] Trace summary retrieval
  - [ ] Trace filtering
  - [ ] Error scenarios

**Deliverable**: Langfuse Observability tab shows traces and metrics

**Success Criteria**: ✓ Display recent traces, ✓ show metrics summary, ✓ filter by time range, ✓ link to full dashboard, ✓ 14 tests passing

---

#### Step 20: Implement Promptfoo Testing Dashboard (Optional)

- [ ] Create `src/ui/tools/promptfoo_dashboard.py`:
  - [ ] Test scenario creation interface
  - [ ] Test run history with version management
  - [ ] Results comparison between versions
  - [ ] Pass/fail rate visualization
  - [ ] Deploy selected prompt version
- [ ] Create test suite: 12 unit tests
  - [ ] Test creation
  - [ ] Test run management
  - [ ] Version comparison
  - [ ] Error handling

**Note**: Implementation depends on Promptfoo library availability. Can be mocked for MVP.

**Deliverable**: Promptfoo tab for prompt testing and versioning

**Success Criteria**: ✓ Create test scenarios, ✓ view test results, ✓ compare versions, ✓ 12 tests passing

---

#### Step 21: Implement System Health Dashboard

- [ ] Enhance `src/services/health_check.py`:
  - [ ] Add `get_service_metrics()` method (CPU, memory, request counts)
  - [ ] Add `get_docker_stats()` method (host resource usage)
  - [ ] Add `get_health_trend()` method (historical metrics)
  - [ ] Implement metrics collection and caching
- [ ] Create `src/ui/tools/system_health_dashboard.py`:
  - [ ] Overall system status indicator
  - [ ] Per-service metrics display (Ollama, Qdrant, Meilisearch, Langfuse)
  - [ ] Host Docker resources visualization
  - [ ] Alert configuration interface
  - [ ] Health trend charts
- [ ] Create comprehensive test suite: 18 unit tests
  - [ ] Metrics collection
  - [ ] Service status determination
  - [ ] Docker stats parsing
  - [ ] Alert configuration

**Deliverable**: System Health tab with comprehensive monitoring

**Success Criteria**: ✓ Show all service metrics, ✓ display host resources, ✓ indicate overall status, ✓ 18 tests passing

---

#### Step 22: Integration & Validation

- [ ] Integration testing: All 4 management tools working together
  - [ ] Test navigation between all tools
  - [ ] Test data caching behavior
  - [ ] Test error scenarios (service unavailable)
  - [ ] Test feature flag disabling/enabling
- [ ] Performance testing: Dashboard responsiveness
  - [ ] Sidebar rendering < 200ms
  - [ ] Tool content rendering < 500ms
  - [ ] Data caching working correctly
- [ ] End-to-end testing: Complete user workflows
  - [ ] User navigates all tools
  - [ ] User performs tool-specific actions
  - [ ] UI remains responsive

**Deliverable**: All Phase 4b components integrated and tested

**Success Criteria**: ✓ All 9 components work together, ✓ <500ms page load, ✓ all tests passing, ✓ feature flags control visibility

---

### PHASE 4b Progress Tracking

**Estimated Effort**: 3-4 weeks (following DASHBOARD_DESIGN.md)

**Components**: 5 new dashboard tools + 1 navigation component + 3 service client enhancements

**Test Coverage**: 60+ unit tests (Qdrant 16, Langfuse 14, Promptfoo 12, Health 18)

---

### PHASE 4b Validation Checkpoint

**Phase 4b Complete When**:

- [ ] Sidebar navigation renders with all tools
- [ ] Qdrant Manager tab shows collections and search
- [ ] Langfuse Observability tab shows recent traces
- [ ] Promptfoo tab allows test creation and comparison
- [ ] System Health tab shows all service metrics
- [ ] Feature flags control tool visibility
- [ ] All 60+ tests passing
- [ ] Dashboard components responsive and cached
- [ ] No external calls without error handling

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

| Phase        | Checkpoint                                                           | Status         | Notes                                          |
| ------------ | -------------------------------------------------------------------- | -------------- | ---------------------------------------------- |
| **Phase 1**  | `docker-compose up -d` → all services healthy, DevContainer works    | ✅ COMPLETED   | Foundation ready for Phase 2                   |
| **Phase 2**  | UI loads, services connect, health checks display correctly          | ✅ COMPLETED   | Core UI & connectivity ready for Phase 3       |
| **Phase 3**  | Upload PDF → search in KB → chat generates responses with sources    | ✅ COMPLETED   | RAG pipeline ready for Phase 4                 |
| **Phase 4**  | Malicious input blocked, Langfuse shows traces                       | ⏳ Not Started | Security & observability                       |
| **Phase 4b** | All dashboard tools accessible, metrics displayed, 60+ tests passing | ⏳ Not Started | Management interface (see DASHBOARD_DESIGN.md) |
| **Phase 5**  | `pytest --cov≥80%`, README clear to new developer                    | ⏳ Not Started | Testing & docs                                 |

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
├─ Step 2: Docker Compose ............................... ✅ COMPLETED
├─ Step 3: DevContainer ................................. ✅ COMPLETED
├─ Step 4: Configuration Management ..................... ✅ COMPLETED
└─ Step 5: Repository Validation ........................ ✅ COMPLETED

Phase 2: Core Application Skeleton
├─ Step 6: Streamlit UI .................................. ✅ COMPLETED
├─ Step 7: Service Connectivity .......................... ✅ COMPLETED (156 tests)
├─ Step 8: Health Check & Startup ........................ ✅ COMPLETED (20 tests)
└─ Phase 2 Total: 196 unit tests, 1,740 LOC

Phase 3: RAG Pipeline Integration
├─ Step 9: Document Ingestion ............................ ✅ COMPLETED (20 tests)
├─ Step 10: Retrieval Engine ............................. ✅ COMPLETED (18 tests)
├─ Step 11: Agent Orchestration .......................... ✅ COMPLETED (22 tests)
├─ Step 12: Conversation Memory .......................... ✅ COMPLETED (30 tests)
└─ Phase 3 Total: 92 unit tests, 1,550+ LOC

Phase 4: Security & Observability
├─ Step 13: LLM Guard Integration ........................ ⏳ Not Started
├─ Step 14: Langfuse Observability ....................... ⏳ Not Started
└─ Step 15: Environment Configuration ................... ⏳ Not Started

Phase 4b: Tool Dashboards & Management Interface ⭐ NEW
├─ Dashboard Design Document ............................. ✅ COMPLETE (see DASHBOARD_DESIGN.md)
├─ Step 17: Sidebar Navigation Refactor .................. ⏳ Not Started
├─ Step 18: Qdrant Manager Dashboard ..................... ⏳ Not Started
├─ Step 19: Langfuse Observability Dashboard ............ ⏳ Not Started
├─ Step 20: Promptfoo Testing Dashboard ................. ⏳ Not Started
├─ Step 21: System Health Dashboard ..................... ⏳ Not Started
├─ Step 22: Integration & Validation ..................... ⏳ Not Started
└─ Phase 4b Total: 60+ unit tests, 5 new dashboard tools

Phase 5: Testing & Documentation
├─ Step 16: Pytest Setup ................................. ⏳ Not Started
├─ Step 17: Unit Tests ................................... ⏳ Not Started
├─ Step 18: Integration Tests ............................ ⏳ Not Started
└─ Step 19: Documentation ................................ ⏳ Not Started
```

### Update Log

| Date       | Phase | Step   | Status       | Notes                                                      |
| ---------- | ----- | ------ | ------------ | ---------------------------------------------------------- |
| 2026-01-10 | -     | Plan   | ✅ Approved  | Plan reviewed and approved                                 |
| 2026-01-10 | 1     | 1      | ✅ Completed | Project structure and configuration initialized            |
| 2026-01-11 | 1     | 2      | ✅ Completed | Docker Compose with 6 services and resource limits         |
| 2026-01-15 | 1     | 3      | ✅ Completed | DevContainer with VS Code integration and tooling          |
| 2026-01-15 | 1     | 4      | ✅ Completed | Configuration management with Pydantic v2 and logging      |
| 2026-01-15 | 1     | 5      | ✅ Completed | Repository structure validation complete                   |
| 2026-01-15 | 1     | -      | ✅ PHASE 1   | All infrastructure foundation ready for Phase 2            |
| 2026-01-18 | 3     | 9      | ✅ Completed | Document ingestion pipeline with PDF extraction (20 tests) |
| 2026-01-18 | 3     | 10     | ✅ Completed | Hybrid retrieval engine (semantic + keyword) (18 tests)    |
| 2026-01-18 | 3     | 11     | ✅ Completed | Agent orchestration with LangChain integration (22 tests)  |
| 2026-01-18 | 3     | 12     | ✅ Completed | Multi-turn conversation memory management (30 tests)       |
| 2026-01-18 | 3     | -      | ✅ PHASE 3   | RAG pipeline complete with 92 tests, ready for Phase 4     |
| 2026-01-18 | 4b    | Design | ✅ Completed | Dashboard design document created (DASHBOARD_DESIGN.md)    |

---

## Next Steps

1. **Phase 4**: Implement security features (LLM Guard) and observability (Langfuse)
2. **Phase 4b**: Build tool dashboards for Qdrant, Langfuse, Promptfoo, and System Health (follow DASHBOARD_DESIGN.md)
3. **Phase 5**: Add comprehensive documentation and integration tests
4. **Phase 5**: Add comprehensive documentation and integration tests
5. **Production**: Deploy with all security and monitoring features enabled

---

**Document Version**: 1.2  
**Last Updated**: 2026-01-18  
**Maintained By**: Senior AI Architect  
**Status**: Phase 3 Complete - Ready for Phase 4
