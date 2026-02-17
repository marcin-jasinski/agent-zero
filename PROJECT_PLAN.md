# Agent Zero (L.A.B.) - Implementation Plan

**Status**: Phases 1-5 Complete ✅ | Phases 6-8 In Progress  
**Last Updated**: 2026-02-17  
**Test Suite**: 404 tests passing, 0 skipped

**⚠️ Project Context**: LOCAL DEVELOPMENT PLAYGROUND for AI agent experimentation. Not a production multi-user system.

---

## Table of Contents

1. [Project Definition](#project-definition)
2. [Completed Phases Summary](#completed-phases-summary)
3. [Active Implementation Phases](#active-implementation-phases)
4. [Critical Design Decisions](#critical-design-decisions)
5. [Validation Checkpoints](#validation-checkpoints)

---

## Project Definition

### Branding & Concept

- **Name**: Agent Zero
- **Concept**: L.A.B. (Local Agent Builder)
- **UI Dashboard**: A.P.I. (AI Playground Interface)
- **Philosophy**: "One-Click Deployment", "Secure by Design", "Local-First"

### Technical Stack

- **Orchestration**: Docker Compose v2+
- **Language**: Python 3.11+
- **Core Libraries**: LangChain, Streamlit, Pydantic, LLM Guard, Pytest
- **Infrastructure**: Ollama (LLM), Qdrant (Vector DB), Meilisearch (Search), Langfuse (Observability), LiteLLM (Gateway), MCP Server
- **Services**:
  - `app-agent`: Python 3.11 + Streamlit (port 8501)
  - `ollama`: LLM inference (port 11434)
  - `qdrant`: Vector Database (port 6333)
  - `meilisearch`: Full-text Search (port 7700)
  - `postgres`: Langfuse backing DB (port 5432)
  - `langfuse`: Observability UI (port 3000)
  - `litellm`: LLM Gateway (port 4000) - *Planned*
  - `mcp-server`: Model Context Protocol (port 3001) - *Planned*

---

## Completed Phases Summary

### ✅ PHASE 1: Foundation & Infrastructure (Steps 1-5)

**Completed**: 2026-01-15

- Docker Compose with 6 services, resource limits, health checks
- DevContainer configuration for VS Code
- Configuration management with Pydantic
- Complete project structure and git setup

**Key Deliverables**: Production-ready Docker environment, developer-friendly workspace

---

### ✅ PHASE 2: Core Application Skeleton (Steps 6-8)

**Completed**: 2026-01-16 | **Tests**: 196 unit tests

- Streamlit UI with 4 tabs (Chat, Knowledge Base, Settings, Logs)
- Service client layer (Ollama, Qdrant, Meilisearch, Langfuse)
- Health check system and startup sequence
- Comprehensive error handling and logging

**Key Deliverables**: Working UI, all services connected and monitored

---

### ✅ PHASE 3: RAG Pipeline Integration (Steps 9-12)

**Completed**: 2026-01-18 | **Tests**: 92 unit tests

- Document ingestion pipeline (PDF → chunks → embeddings → storage)
- Hybrid retrieval engine (semantic + keyword search)
- LangChain agent orchestration with tool calling
- Multi-turn conversation memory management

**Key Deliverables**: End-to-end RAG workflow from upload to chat response

---

### ✅ PHASE 4: Security & Observability (Steps 13-15)

**Completed**: 2026-01-18 | **Tests**: 84 unit tests

- LLM Guard integration (input/output scanning)
- Langfuse observability (tracing, metrics)
- Environment-specific configuration (dev/staging/prod modes)

**Key Deliverables**: Security guardrails, comprehensive observability

---

### ✅ PHASE 4b: Tool Dashboards & Management Interface (Steps 17-22)

**Completed**: 2026-02-02 | **Tests**: 149 unit tests

- Dynamic sidebar navigation with feature flags
- Qdrant Manager (collections, search, CRUD)
- Langfuse Dashboard (traces, metrics)
- Promptfoo Testing Dashboard (scenarios, test runs, version comparison)
- System Health Dashboard (service monitoring, auto-refresh)
- Integration tests for all dashboard tools

**Key Deliverables**: Complete management interface with 5 dashboard tools

---

### ✅ PHASE 5: Testing & UX Polish (Steps 16-18, 19.5-19.8)

**Completed**: 2026-01-30 | **Tests**: 404 total (0 skipped)

- Comprehensive test suite with 404 passing tests
- Progress indicators for all long-running operations
- Error visibility improvements with troubleshooting hints
- Sample documents and example queries for onboarding
- Security warnings and documentation polish

**Key Deliverables**: Production-ready codebase with excellent test coverage and UX

---

## Active Implementation Phases

### PHASE 6: UI Simplification

**Goal**: Clean up sidebar navigation by removing redundant service status display.

---

#### Step 23: Simplify Sidebar Navigation (Remove Redundant Service Status)

**Status**: 🔄 TODO | **Priority**: HIGH

**Objective**: Remove redundant "Service Status" section from sidebar since System Health tab provides the same information.

**Current Problem**:
- Sidebar shows: Core Tools, Management Tools, **Service Status section**, then System Health tab
- Service Status section duplicates information from System Health tab
- Takes up valuable sidebar space
- Confusing for users (two places to check service health)

**Implementation**:

- [ ] **Remove Service Status Section** (`src/ui/components/navigation.py`):
  - [ ] Delete `_render_service_status()` method or move its content to System Health tab only
  - [ ] Remove service status rendering from sidebar navigation
  - [ ] Keep only: Core Tools separator → Management Tools separator → Tool list

- [ ] **Update System Health Tab** (`src/ui/tools/system_health.py`):
  - [ ] Ensure it remains the single source of truth for service status
  - [ ] Keep all existing functionality (service metrics, auto-refresh, etc.)
  - [ ] Verify it's easily accessible from sidebar

- [ ] **Update Tests** (`tests/ui/test_navigation.py`):
  - [ ] Remove tests for service status in sidebar
  - [ ] Verify System Health tab still renders correctly
  - [ ] Update integration tests if needed
  - [ ] **Target**: Maintain 13 tests passing

**Deliverable**: Cleaner, simpler sidebar with no redundant information

**Success Criteria**:
- ✓ Sidebar shows only tool categories (Core, Management)
- ✓ Service status visible only in System Health tab
- ✓ No visual regression in UI
- ✓ All existing tests pass
- ✓ User can still easily check service health via System Health tab

---

### PHASE 7: LiteLLM Gateway Integration

**Goal**: Centralize LLM infrastructure using LiteLLM proxy for provider flexibility and unified guardrails.

**Benefits**:
- ✅ Support 100+ LLM providers (Ollama, OpenAI, Anthropic, Azure, etc.)
- ✅ Built-in fallbacks, retries, and caching
- ✅ Cost tracking and token counting
- ✅ Drop-in replacement architecture
- ✅ Centralized LLM Guard integration

---

#### Step 24: Add LiteLLM Proxy Service

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Add LiteLLM Service to Docker** (`docker-compose.yml`):
  ```yaml
  litellm:
    image: ghcr.io/berriai/litellm:latest
    container_name: litellm
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:-sk-1234}
      - DATABASE_URL=postgresql://langfuse:changeme123@postgres:5432/langfuse
    volumes:
      - ./config/litellm_config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
    mem_limit: 512m
    cpus: 1.0
  ```

- [ ] **Create LiteLLM Configuration** (`config/litellm_config.yaml`):
  ```yaml
  model_list:
    - model_name: ollama-default
      litellm_params:
        model: ollama/llama2
        api_base: http://ollama:11434
        
    - model_name: gpt-4o-mini
      litellm_params:
        model: gpt-4o-mini
        api_key: os.environ/OPENAI_API_KEY  # Optional
        
    - model_name: claude-3-5-sonnet
      litellm_params:
        model: claude-3-5-sonnet-20241022
        api_key: os.environ/ANTHROPIC_API_KEY  # Optional
  ```

- [ ] **Update Environment Configuration** (`.env.example`):
  - [ ] Add `LITELLM_MASTER_KEY=sk-1234`
  - [ ] Add `OPENAI_API_KEY=` (optional)
  - [ ] Add `ANTHROPIC_API_KEY=` (optional)
  - [ ] Add `LLM_PROVIDER=ollama-default` (default)

**Deliverable**: LiteLLM proxy running and accessible at port 4000

**Success Criteria**: ✓ LiteLLM service starts successfully, ✓ Health check passes

---

#### Step 25: Update Agent to Use LiteLLM

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Update Agent Configuration** (`src/config.py`):
  ```python
  class LLMConfig(BaseSettings):
      provider: str = Field(default="ollama-default")
      base_url: str = Field(default="http://litellm:4000/v1")
      api_key: str = Field(default="sk-1234")
      temperature: float = Field(default=0.7, ge=0.0, le=2.0)
      max_tokens: int = Field(default=2000)
  ```

- [ ] **Refactor Agent LLM Client** (`src/core/agent.py`):
  - [ ] Replace direct `ChatOllama` with OpenAI-compatible client pointing to LiteLLM
  - [ ] Use `openai` Python SDK with custom base_url
  - [ ] Support provider switching via config

- [ ] **Create LiteLLM Client Service** (`src/services/litellm_client.py`):
  - [ ] Wrapper for LiteLLM API calls
  - [ ] Methods: `chat()`, `embed()`, `list_models()`
  - [ ] Error handling for provider-specific errors
  - [ ] Logging integration with Langfuse

**Deliverable**: Agent uses LiteLLM for all LLM calls

**Success Criteria**: ✓ Chat works with Ollama through LiteLLM, ✓ Can switch providers via config

**Tests**: 15-20 unit tests

---

#### Step 26: Centralize LLM Guard in LiteLLM

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Integrate LLM Guard as Callback** (`src/observability/litellm_guard_callback.py`):
  - [ ] Create LiteLLM callback for request/response scanning
  - [ ] Scan inputs before sending to LLM
  - [ ] Scan outputs before returning to agent
  - [ ] Log all blocked content to Langfuse

- [ ] **Update LiteLLM Configuration** (`config/litellm_config.yaml`):
  - [ ] Enable callbacks in general_settings
  - [ ] Configure LLM Guard scanners

**Deliverable**: All LLM calls automatically scanned by LLM Guard

**Success Criteria**: ✓ Malicious inputs blocked centrally, ✓ All providers protected

**Tests**: 10 unit tests

---

### PHASE 7 Validation Checkpoint

**Complete When**:
- [ ] LiteLLM proxy service running and healthy
- [ ] Agent successfully uses LiteLLM for chat
- [ ] Provider switching works (Ollama ↔ OpenAI)
- [ ] LLM Guard integrated as LiteLLM callback
- [ ] All security scans centralized
- [ ] 25-30 new tests passing

---

### PHASE 8: MCP Server Integration (Default-Enabled)

**Goal**: Add Model Context Protocol server to demonstrate modern tool architecture alongside traditional Python tools.

---

#### Step 27: Add MCP Server to Docker

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Create MCP Server Package** (`mcp-server/package.json`)
- [ ] **Implement MCP Server** (`mcp-server/index.js`):
  - [ ] Tool 1: `list_documents` - List files in knowledge base folder
  - [ ] Tool 2: `read_document` - Read specific document content
  - [ ] Tool 3: `fetch_url` - Fetch and convert web page to markdown

- [ ] **Add MCP Service to Docker** (`docker-compose.yml`):
  ```yaml
  mcp-server:
    image: node:20-alpine
    container_name: mcp-server
    working_dir: /app
    ports:
      - "3001:3001"
    volumes:
      - ./mcp-server:/app
      - ./data:/data:ro
    command: ["npm", "start"]
    mem_limit: 256m
    cpus: 0.5
  ```

**Deliverable**: MCP server running with 3 tools available

---

#### Step 28: Create MCP Client Service

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Create MCP Client** (`src/services/mcp_client.py`):
  - [ ] Method: `list_tools()` - Discover available MCP tools
  - [ ] Method: `call_tool(name, arguments)` - Execute MCP tool
  - [ ] Async HTTP client with timeout handling

- [ ] **Update Configuration** (`src/config.py`):
  ```python
  class MCPConfig(BaseSettings):
      enabled: bool = Field(default=True)
      base_url: str = Field(default="http://mcp-server:3001")
  ```

**Tests**: 15 unit tests

---

#### Step 29: Integrate MCP Tools into Agent

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Update Agent Tool Initialization** (`src/core/agent.py`):
  - [ ] Discover MCP tools on agent startup
  - [ ] Convert MCP tools to LangChain tool format
  - [ ] Add to agent's tool list
  - [ ] Mark tools with source type (Python vs MCP)

- [ ] **UI Enhancement** (`src/ui/tools/chat.py`):
  - [ ] Show tool type: 🔧 Python Tool vs 🔌 MCP Tool
  - [ ] Display MCP tool execution time

**Tests**: 10 unit tests

---

### PHASE 8 Validation Checkpoint

**Complete When**:
- [ ] MCP server running with 3 tools
- [ ] Agent can call MCP tools
- [ ] UI shows distinction between Python and MCP tools
- [ ] 25 new tests passing

---

### PHASE 9: Intelligent Retrieval & Performance Optimization

**Goal**: Optimize agent performance with smart retrieval routing and improve ingestion speed.

---

#### Step 30: Intelligent Retrieval Optimization

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Stage 1: Empty Knowledge Base Check** (0ms overhead)
- [ ] **Stage 2: Intent Classification** (1-2s, skips unnecessary retrieval)
- [ ] **Stage 3: Semantic Similarity Threshold** (filters low-relevance results)
- [ ] **Stage 4: Hybrid Search Score Normalization** (RRF algorithm)

**Performance Impact**:
- General queries: 7-8s → 2-3s (60% faster)
- Empty KB queries: 7-8s → 2-3s (70% faster)
- KB-relevant queries: No regression

**Tests**: 21 unit tests

---

#### Step 31: Performance & DevOps Improvements

**Status**: 🔄 TODO

**Implementation**:

- [ ] **Batch Embedding Generation**: 500 chunks in <10s (was 25-100s)
- [ ] **Automatic Ollama Model Pull**: Zero-config first-time setup

**Tests**: 8 unit tests

---

### PHASE 9 Validation Checkpoint

**Complete When**:
- [ ] General queries complete in 2-3s
- [ ] Intent classification accurately routes queries
- [ ] 29+ new tests passing
- [ ] Performance improvement visible in Langfuse

---

### PHASE 10: Comprehensive Documentation

**Goal**: Create professional documentation for public release.

---

#### Step 32: Create README.md

**Status**: 🔄 TODO

**Implementation**:

- [ ] Badges, project overview, key features
- [ ] Quick Start guide (<5 minutes)
- [ ] Architecture diagram (Mermaid)
- [ ] Screenshots of UI
- [ ] Configuration guide
- [ ] ⚠️ FOR LOCAL DEVELOPMENT ONLY section
- [ ] Troubleshooting guide

---

#### Step 33: Create ARCHITECTURE.md

**Status**: 🔄 TODO

**Implementation**:

- [ ] System overview and design philosophy
- [ ] Layer diagrams with data flow
- [ ] Service interaction diagrams
- [ ] RAG pipeline deep dive
- [ ] LiteLLM Gateway architecture
- [ ] MCP integration architecture

---

#### Step 34: Create CONTRIBUTING.md

**Status**: 🔄 TODO

**Implementation**:

- [ ] Development setup instructions
- [ ] Commit conventions (Conventional Commits)
- [ ] Pull request process
- [ ] Testing requirements
- [ ] Code review checklist

---

### PHASE 10 Validation Checkpoint

**Complete When**:
- [ ] README is comprehensive and public-ready
- [ ] ARCHITECTURE.md provides technical depth
- [ ] CONTRIBUTING.md sets clear expectations
- [ ] Quick Start tested by new developer

---

## Critical Design Decisions

### 1. Single Service Architecture
- **Decision**: All logic in `app-agent` container
- **Rationale**: Simplifies deployment for single-user local development

### 2. Synchronous Execution
- **Decision**: No message queues initially
- **Rationale**: MVP simplicity; suitable for single-user

### 3. Session-Based Memory
- **Decision**: In-memory conversation store per session
- **Rationale**: Fast, no schema needed; appropriate for local use

### 4. Dual Indexing (Meilisearch + Qdrant)
- **Decision**: Index in both semantic and keyword stores
- **Rationale**: Ensures comprehensive search coverage

### 5. Default-Enabled MCP
- **Decision**: MCP tools enabled by default
- **Rationale**: Educational value; demonstrates modern architecture

### 6. LiteLLM Gateway
- **Decision**: Centralize all LLM calls through LiteLLM
- **Rationale**: Provider flexibility, unified security, cost tracking

---

## Validation Checkpoints

### Summary Table

| Phase        | Checkpoint                                                           | Status         |
| ------------ | -------------------------------------------------------------------- | -------------- |
| **Phase 1**  | Docker environment ready                                             | ✅ COMPLETED   |
| **Phase 2**  | UI loads, services connected                                         | ✅ COMPLETED   |
| **Phase 3**  | RAG pipeline end-to-end                                              | ✅ COMPLETED   |
| **Phase 4**  | Security & observability                                             | ✅ COMPLETED   |
| **Phase 4b** | Dashboard tools (149 tests)                                          | ✅ COMPLETED   |
| **Phase 5**  | Testing & UX (404 tests)                                             | ✅ COMPLETED   |
| **Phase 6**  | UI simplified (sidebar cleanup)                                      | 🔄 TODO        |
| **Phase 7**  | LiteLLM Gateway integration                                          | 🔄 TODO        |
| **Phase 8**  | MCP Server integration                                               | 🔄 TODO        |
| **Phase 9**  | Performance optimizations                                            | 🔄 TODO        |
| **Phase 10** | Comprehensive documentation                                          | 🔄 TODO        |

---

## Progress Summary

**Current Status**: Phase 5 Complete ✅

**Completed**:
- ✅ 404 tests passing (0 skipped)
- ✅ Full RAG pipeline with observability
- ✅ 5 dashboard management tools
- ✅ Comprehensive security (LLM Guard)
- ✅ UX polish and example content

**Next Steps**:
1. **Phase 6**: Simplify sidebar navigation (Step 23)
2. **Phase 7**: Integrate LiteLLM Gateway (Steps 24-26)
3. **Phase 8**: Add MCP Server (Steps 27-29)
4. **Phase 9**: Optimize performance (Steps 30-31)
5. **Phase 10**: Complete documentation (Steps 32-34)

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-17  
**Test Suite**: 404 tests passing → Target: 480+ after Phases 6-9  
**New Features Planned**: UI cleanup, LiteLLM Gateway (multi-provider), MCP Server (modern tools), Smart Retrieval
