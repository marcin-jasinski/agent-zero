# Agent Zero (L.A.B.) - Implementation Plan

**Status**: Phases 1-6b Complete ✅ | Phase 6c Active 🔥 | Phase 7+ Planned 🔄  
**Last Updated**: 2026-02-19  
**Test Suite**: 436 tests passing (full regression)

**⚠️ Project Context**: LOCAL DEVELOPMENT PLAYGROUND for AI agent experimentation. Not a production multi-user system.

**🔥 Active Migration**: Replacing Chainlit with FastAPI + Gradio for a unified, tab-based UI (no multi-process workarounds).

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
- **Core Libraries**: LangChain, FastAPI, Gradio, Pydantic, LLM Guard, Pytest
- **Infrastructure**: Ollama (LLM), Qdrant (Vector DB), Meilisearch (Search), Langfuse (Observability), LiteLLM (Gateway), MCP Server
- **Services**:
  - `app-agent`: Python 3.11 + FastAPI + Gradio, single unified app (port 8501)
  - `ollama`: LLM inference (port 11434)
  - `qdrant`: Vector Database (port 6333)
  - `meilisearch`: Full-text Search (port 7700)
  - `postgres`: Langfuse backing DB (port 5432)
  - `langfuse`: Observability UI (port 3000)
  - `litellm`: LLM Gateway (port 4000) - *Planned Phase 7*
  - `mcp-server`: Model Context Protocol (port 3001) - *Planned Phase 8*

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

**Status**: ⚠️ SUPERSEDED by Phase 6b (Chainlit Migration)

---

### PHASE 6b: Chainlit Migration

**Goal**: Migrate from Streamlit to Chainlit for production-grade agent UI with true async support.

**Status**: ⚠️ SUPERSEDED by Phase 6c (FastAPI + Gradio)

**Reason superseded**: Chainlit's single-app-per-process model forced a two-process / two-port architecture for chat vs. admin, requiring process management hacks (`start_services.sh`) and a shared `.chainlit` config workaround. Both apps rendered identically at the UI level. FastAPI + Gradio solves this natively via tabs in one unified app.

**Branch**: `feature/chainlit-migration`

---

#### Step 23: Setup Chainlit Infrastructure

**Status**: ✅ COMPLETE | **Priority**: CRITICAL | **Duration**: 4 hours

**Objective**: Install Chainlit, update Docker configuration, and create basic app structure.

**Implementation**:

- [x] **Install Chainlit** (`pyproject.toml`):
  ```toml
  [tool.poetry.dependencies]
  chainlit = "^1.0.0"
  # Remove: streamlit = "^1.29.0"
  ```

- [x] **Update Docker Configuration** (`docker-compose.yml`):
  ```yaml
  app-agent:
    # Change command
    command: ["poetry", "run", "chainlit", "run", "src/ui/main.py", "--host", "0.0.0.0", "--port", "8501"]
    # Keep same ports for compatibility
  ```

- [x] **Update Dockerfile** (`docker/Dockerfile.app-agent`):
  - [x] Update Python base image to 3.11-slim
  - [x] Update WORKDIR and COPY commands
  - [x] Keep same health check (port 8501)

- [x] **Create Chainlit Config** (`.chainlit`):
  ```toml
  [project]
  enable_telemetry = false
  
  [UI]
  name = "Agent Zero (L.A.B.)"
  default_collapse_content = false
  
  [meta]
  generated_by = "1.0.0"
  ```

- [x] **Update Configuration** (`src/config.py`):
  ```python
  class DashboardConfig(BaseSettings):
      framework: str = Field(default="chainlit")  # was "streamlit"
      # Remove Streamlit-specific configs
  ```

**Deliverable**: Chainlit installed, Docker configured, basic app structure created

**Success Criteria**:
- ✓ `chainlit run src/ui/main.py` starts without errors
- ✓ Docker container starts successfully
- ✓ Port 8501 accessible
- ✓ Health check passes

---

#### Step 24: Migrate Chat Interface (Core Feature)

**Status**: ✅ COMPLETE | **Priority**: CRITICAL | **Duration**: 6 hours

**Objective**: Rewrite chat interface using Chainlit's native APIs for better async handling.

**Implementation**:

- [x] **Create Chainlit Main App** (`src/ui/main.py`):
  ```python
  import chainlit as cl
  from src.core.agent import AgentOrchestrator
  from src.core.retrieval import RetrievalEngine
  
  @cl.on_chat_start
  async def start():
      """Initialize agent when chat session starts."""
      # Service health checks
      await check_services()
      
      # Initialize agent
      agent = AgentOrchestrator(
          model_name=config.llm.model_name,
          enable_guardrails=config.security.enable_llm_guard,
          enable_observability=config.observability.enable_langfuse
      )
      
      # Create conversation
      conversation_id = agent.memory.create_conversation()
      
      # Store in session
      cl.user_session.set("agent", agent)
      cl.user_session.set("conversation_id", conversation_id)
      
      # Welcome message
      await cl.Message(
          content="👋 Welcome to Agent Zero! Ask me anything or upload documents to build your knowledge base.",
          author="Agent Zero"
      ).send()
  
  @cl.on_message
  async def main(message: cl.Message):
      """Process user messages with streaming response."""
      agent = cl.user_session.get("agent")
      conversation_id = cl.user_session.get("conversation_id")
      
      # Show thinking indicator
      async with cl.Step(name="Thinking", type="llm") as step:
          # Process message (with retrieval)
          response = await agent.process_message_async(
              conversation_id=conversation_id,
              message=message.content,
              use_retrieval=True
          )
          
          step.output = response
      
      # Send response
      await cl.Message(content=response).send()
  
  @cl.on_chat_end
  async def end():
      """Cleanup when chat ends."""
      await cl.Message(content="Goodbye! 👋").send()
  ```

- [x] **Add Async Support to Agent** (`src/core/agent.py`):
  ```python
  async def process_message_async(
      self,
      conversation_id: str,
      message: str,
      use_retrieval: bool = True
  ) -> str:
      """Async version of process_message for Chainlit."""
      # Same logic but with async/await
      return await asyncio.to_thread(
          self.process_message,
          conversation_id,
          message,
          use_retrieval
      )
  ```

- [x] **Remove Streamlit Components**:
  - [x] Delete `src/ui/tools/chat.py` (Streamlit version)
  - [x] Delete `src/ui/components/navigation.py`
  - [x] Delete session state management code

**Tests**: 15 unit tests + 3 integration tests

**Deliverable**: Fully functional chat interface with async message processing

**Success Criteria**:
- ✓ Chat loads without errors
- ✓ User can send messages and receive responses
- ✓ No background thread workarounds needed
- ✓ Streaming responses work smoothly
- ✓ Conversation history persists

---

#### Step 25: Migrate Knowledge Base (Document Upload)

**Status**: ✅ COMPLETE | **Priority**: HIGH | **Duration**: 4 hours

**Objective**: Implement document upload and ingestion using Chainlit's file upload API.

**Implementation**:

- [x] **Add File Upload Handler** (`src/ui/main.py`):
  ```python
  @cl.on_file_upload(accept=["application/pdf", "text/plain"])
  async def handle_file(file: cl.File):
      """Handle document uploads for knowledge base."""
      agent = cl.user_session.get("agent")
      
      # Show progress
      async with cl.Step(name=f"Processing {file.name}", type="tool") as step:
          try:
              # Ingest document
              result = await ingest_document_async(
                  file_path=file.path,
                  file_name=file.name
              )
              
              step.output = f"✅ Ingested {result['chunks']} chunks"
              
              await cl.Message(
                  content=f"Document '{file.name}' processed successfully! "
                          f"{result['chunks']} chunks indexed."
              ).send()
          except Exception as e:
              step.output = f"❌ Error: {str(e)}"
              await cl.Message(
                  content=f"Failed to process '{file.name}': {str(e)}"
              ).send()
  ```

- [x] **Add Async Ingestion** (`src/core/ingest.py`):
  ```python
  async def ingest_document_async(
      file_path: str,
      file_name: str
  ) -> dict:
      """Async wrapper for document ingestion."""
      return await asyncio.to_thread(
          ingest_document,
          file_path,
          file_name
      )
  ```

- [x] **Remove Streamlit Components**:
  - [x] Delete `src/ui/tools/knowledge_base.py`

**Tests**: 10 unit tests + 2 integration tests

**Deliverable**: Document upload with progress indicators

**Success Criteria**:
- ✓ Users can upload PDF and text files
- ✓ Progress indicators show ingestion status
- ✓ Error messages display clearly
- ✓ Documents searchable after upload

---

#### Step 26: Create Admin Dashboard (Settings & Monitoring)

**Status**: ✅ COMPLETE | **Priority**: MEDIUM | **Duration**: 5 hours

**Objective**: Build admin interface for system monitoring and configuration using Chainlit's data layer.

**Implementation**:

- [x] **Create Dashboard Page** (`src/ui/admin.py`):
  ```python
  import chainlit as cl
  from chainlit.data import ChainlitDataLayer
  
  @cl.oauth_callback
  async def oauth_callback(
      provider_id: str,
      token: str,
      raw_user_data: dict,
      default_user: cl.User
  ) -> Optional[cl.User]:
      """Admin authentication (optional)."""
      # Simple password check for local use
      return default_user
  
  @cl.action_callback("view_system_health")
  async def on_action(action: cl.Action):
      """Show system health when action clicked."""
      health_status = await check_all_services()
      
      elements = []
      for service, status in health_status.items():
          icon = "✅" if status.is_healthy else "❌"
          elements.append(
              cl.Text(
                  name=service,
                  content=f"{icon} {service}: {status.message}",
                  display="inline"
              )
          )
      
      await cl.Message(
          content="System Health Status:",
          elements=elements
      ).send()
  
  @cl.action_callback("view_qdrant_collections")
  async def on_qdrant_action(action: cl.Action):
      """Show Qdrant collections."""
      qdrant = QdrantClient()
      collections = qdrant.list_collections()
      
      content = "## Qdrant Collections\n\n"
      for coll in collections:
          content += f"- **{coll.name}**: {coll.vectors_count} vectors\n"
      
      await cl.Message(content=content).send()
  ```

- [x] **Add Action Buttons** (in welcome message):
  ```python
  actions = [
      cl.Action(
          name="view_system_health",
          value="health",
          label="📊 System Health"
      ),
      cl.Action(
          name="view_qdrant_collections",
          value="qdrant",
          label="🗄️ Qdrant Status"
      ),
      cl.Action(
          name="view_settings",
          value="settings",
          label="⚙️ Settings"
      )
  ]
  
  await cl.Message(
      content="Welcome!",
      actions=actions
  ).send()
  ```

- [x] **Remove Streamlit Dashboards**:
  - [x] Delete `src/ui/tools/system_health.py`
  - [x] Delete `src/ui/tools/qdrant_dashboard.py`
  - [x] Delete `src/ui/tools/langfuse_dashboard.py`
  - [x] Delete `src/ui/tools/promptfoo_dashboard.py`
  - [x] Delete `src/ui/tools/settings.py`
  - [x] Delete `src/ui/tools/logs.py`

**Tests**: 12 unit tests

**Deliverable**: Admin actions accessible via buttons in chat interface

**Success Criteria**:
- ✓ Action buttons appear in chat
- ✓ System health displays correctly
- ✓ Qdrant collections visible
- ✓ Settings accessible

---

#### Step 27: Update Test Suite for Chainlit

**Status**: ✅ COMPLETE | **Priority**: HIGH | **Duration**: 4 hours

**Objective**: Migrate test suite from Streamlit-based tests to Chainlit-compatible tests.

**Implementation**:

- [x] **Update Test Structure** (`tests/ui/`):
  - [x] Delete Streamlit-specific test files:
    - `test_navigation.py`
    - `test_system_health.py`
    - All `tools/test_*.py` files
  
  - [x] Create new Chainlit tests:
    - `test_chat_handlers.py` (on_chat_start, on_message, on_chat_end)
    - `test_file_upload.py` (document ingestion)
    - `test_actions.py` (admin dashboard actions)

- [x] **Example Test** (`tests/ui/test_chat_handlers.py`):
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  import chainlit as cl
  from src.ui.main import start, main
  
  @pytest.mark.asyncio
  async def test_chat_start_initializes_agent():
      """Test that agent is initialized on chat start."""
      with patch("src.ui.main.AgentOrchestrator") as mock_agent:
          mock_agent.return_value = MagicMock()
          
          # Mock user session
          cl.user_session.set = MagicMock()
          
          await start()
          
          # Verify agent initialized
          assert cl.user_session.set.called
          assert mock_agent.called
  
  @pytest.mark.asyncio
  async def test_message_processing():
      """Test message processing with agent."""
      with patch("src.ui.main.cl.user_session.get") as mock_get:
          mock_agent = MagicMock()
          mock_agent.process_message_async = AsyncMock(return_value="Test response")
          mock_get.side_effect = lambda key: {
              "agent": mock_agent,
              "conversation_id": "test-123"
          }.get(key)
          
          message = MagicMock(content="Test message")
          await main(message)
          
          mock_agent.process_message_async.assert_called_once()
  ```

- [x] **Update Integration Tests** (`tests/integration/`):
  - [x] Replace Streamlit app tests with Chainlit tests
  - [x] Test full chat workflow (start → upload → chat → end)

- [x] **Update conftest.py** (`tests/conftest.py`):
  - [x] Remove Streamlit fixtures
  - [x] Add Chainlit fixtures (mock session, mock message, etc.)

**Tests**: Full regression suite (target: 350+ tests passing)

**Deliverable**: Comprehensive test coverage for Chainlit UI

**Success Criteria**:
- ✓ All UI tests passing with Chainlit
- ✓ Integration tests cover chat workflow
- ✓ Test coverage ≥80%
- ✓ No Streamlit dependencies in test suite

---

#### Step 28: Update Documentation & Configuration

**Status**: ✅ COMPLETE | **Priority**: MEDIUM | **Duration**: 2 hours

**Objective**: Update all documentation and configuration files to reflect Chainlit migration.

**Implementation**:

- [x] **Update README.md**:
  - [x] Replace Streamlit references with Chainlit
  - [x] Update Quick Start commands:
    ```bash
    # Old: streamlit run src/ui/main.py
    # New: chainlit run src/ui/main.py
    ```
  - [ ] Update screenshots (if any)

- [x] **Update ARCHITECTURE.md**:
  - [x] Update UI layer diagram
  - [x] Explain Chainlit async architecture
  - [x] Document session management changes

- [x] **Update PROJECT_PLAN.md**:
  - [x] Mark Phase 6b complete
  - [x] Update test count targets

- [x] **Update pyproject.toml**:
  - [x] Remove streamlit dependency
  - [x] Verify chainlit in dependencies

- [x] **Update .devcontainer**:
  - [x] Update VS Code labels/messages (if any Streamlit-specific)

- [x] **Update Docker Documentation** (`docs/`):
  - [x] Update service descriptions
  - [x] Update troubleshooting guides

**Deliverable**: All documentation current and accurate

**Success Criteria**:
- ✓ No mentions of Streamlit in user-facing docs
- ✓ Quick Start guide works for new users
- ✓ Architecture docs reflect new structure

---

### PHASE 6b Validation Checkpoint

**Complete When**:
- [x] Chainlit running in Docker on port 8501
- [x] Chat interface fully functional with async processing
- [x] Document upload and ingestion working
- [x] Admin dashboard actions accessible
- [x] 350+ tests passing (adjusted for new architecture)
- [x] All documentation updated
- [x] No Streamlit dependencies remaining
- [x] Performance improved (no background thread overhead)

**Performance Evidence (2026-02-18)**:
- ✅ Removed explicit `run_in_executor` usage from `src/ui/main.py`
- ✅ Removed per-ingestor `ThreadPoolExecutor` allocation from `src/core/ingest.py`
- ✅ Checkpoint benchmark: `tests/ui/test_phase6b_performance_checkpoint.py::test_process_message_async_dispatch_overhead_is_low`
  - Result: `0.05s` for `300` async dispatch calls (`~0.17 ms/call` average)

**Expected Benefits**:
- ✅ **Stability**: No more race conditions from Streamlit reruns
- ✅ **Performance**: True async, no ThreadPoolExecutor hacks
- ✅ **UX**: Native streaming responses, better progress indicators
- ✅ **Maintainability**: Purpose-built framework, less defensive code
- ✅ **Production-Ready**: Industry-standard agent UI

**Migration Risk Assessment**: **LOW**
- Core logic (agent, retrieval, services) unchanged
- Only UI layer replaced
- Tests ensure functionality preserved
- Can rollback to Streamlit branch if needed

---

### PHASE 6c: FastAPI + Gradio Migration 🔥

**Goal**: Replace Chainlit with a unified FastAPI + Gradio application. Single process, single port, proper tab-based navigation between chat and admin — no multi-process workarounds required.

**Rationale**:
- ❌ **Chainlit Issues**: Single-app-per-process forces two ports, two processes, shared `.chainlit` config, no native tabs
- ✅ **Gradio Benefits**: `gr.Blocks()` with `gr.Tab()` provides native multi-section UI; `gr.Progress()` is a real progress bar; streaming via Python generators (no `asyncio.to_thread` wrappers)
- ✅ **FastAPI Benefits**: Clean REST layer for `/health`, future LiteLLM and MCP API endpoints (Phase 7, 8) sit alongside the UI naturally
- ✅ **Audience Fit**: Gradio is the standard AI community framework — immediately familiar to the contributors this project targets
- ✅ **Testability**: Gradio handlers are plain Python functions, no framework-specific mocking needed
- ✅ **Migration Scope**: Only `src/ui/` changes; all `src/core/`, `src/services/`, `src/security/`, `src/observability/` untouched

**Branch**: `feature/gradio-migration`

---

#### Step 29: Setup FastAPI + Gradio Infrastructure

**Status**: 🔄 TODO | **Priority**: CRITICAL | **Duration**: 2 hours

**Objective**: Swap Chainlit for FastAPI + Gradio, simplify Docker to a single process.

**Implementation**:

- [ ] **Update `pyproject.toml`**:
  ```toml
  # Remove:
  # chainlit>=1.0.0
  # Add:
  "gradio>=4.0.0",
  "fastapi>=0.110.0",
  "uvicorn[standard]>=0.29.0",
  ```

- [ ] **Update `docker-compose.yml`**:
  ```yaml
  app-agent:
    command: ["uvicorn", "src.ui.app:api", "--host", "0.0.0.0", "--port", "8501"]
    ports:
      - "8501:8501"   # Unified app (chat + admin tabs)
      - "9091:9091"   # Prometheus metrics
    # Remove port 8502 entirely
  ```

- [ ] **Update `docker/Dockerfile.app-agent`**:
  - [ ] Replace `CMD ["/app/start_services.sh"]` with `CMD ["uvicorn", "src.ui.app:api", "--host", "0.0.0.0", "--port", "8501"]`
  - [ ] Remove `COPY docker/start_services.sh` line
  - [ ] Remove `EXPOSE 8502`

- [ ] **Delete obsolete files**:
  - [ ] `docker/start_services.sh`
  - [ ] `.chainlit` (root config file)
  - [ ] `src/ui/main.py` (Chainlit entry point)
  - [ ] `src/ui/admin_app.py` (Chainlit admin entry point)
  - [ ] `src/ui/admin.py` (Chainlit admin report helpers)

- [ ] **Create `src/ui/app.py`** (FastAPI entry point):
  ```python
  from fastapi import FastAPI
  import gradio as gr
  from src.ui.chat import build_chat_ui
  from src.ui.dashboard import build_admin_ui

  api = FastAPI(title="Agent Zero API")

  @api.get("/health")
  async def health():
      return {"status": "ok"}

  with gr.Blocks(title="Agent Zero (L.A.B.)") as gradio_app:
      with gr.Tab("💬 Chat"):
          build_chat_ui()
      with gr.Tab("🛡️ Admin"):
          build_admin_ui()

  api = gr.mount_gradio_app(api, gradio_app, path="/")
  ```

**Success Criteria**:
- ✓ `uvicorn src.ui.app:api --port 8501` starts without errors
- ✓ `http://localhost:8501` shows tabbed UI
- ✓ `http://localhost:8501/health` returns `{"status": "ok"}`
- ✓ Docker container starts with single process

---

#### Step 30: Implement Unified Chat Interface

**Status**: 🔄 TODO | **Priority**: CRITICAL | **Duration**: 4 hours

**Objective**: Build the chat tab with streaming LLM responses, file upload, and initialization progress.

**Implementation**:

- [ ] **Create `src/ui/chat.py`**:
  ```python
  import gradio as gr
  from src.core.agent import AgentOrchestrator

  def build_chat_ui():
      """Build the chat tab UI components."""
      state = gr.State({})  # holds agent + conversation_id per session

      status_bar = gr.Markdown("⏳ Initializing agent...")
      chatbot = gr.Chatbot(type="messages", height=520, label="Agent Zero")

      with gr.Row():
          msg_box = gr.Textbox(
              placeholder="Ask me anything or type /help...",
              scale=5, show_label=False
          )
          send_btn = gr.Button("Send", variant="primary", scale=1)

      upload = gr.File(
          file_types=[".pdf", ".txt", ".md"],
          label="📎 Upload document to Knowledge Base"
      )

      # Initialization on page load
      gradio_app.load(fn=initialize_agent, outputs=[state, status_bar])

      # Message submission (streaming generator)
      send_btn.click(
          fn=respond,
          inputs=[msg_box, chatbot, state],
          outputs=[msg_box, chatbot]
      )

      # File upload with gr.Progress()
      upload.upload(
          fn=ingest_document,
          inputs=[upload, state],
          outputs=[status_bar]
      )
  ```

- [ ] **Implement `initialize_agent(progress=gr.Progress())`**:
  - [ ] `progress(0.0, desc="Connecting to Ollama...")` → check Ollama health
  - [ ] `progress(0.33, desc="Connecting to Qdrant...")` → check Qdrant health
  - [ ] `progress(0.66, desc="Connecting to Meilisearch...")` → check Meilisearch
  - [ ] `progress(1.0, desc="Agent ready")` → initialize `AgentOrchestrator`
  - [ ] Returns `(session_state_dict, status_markdown)`

- [ ] **Implement `respond(message, history, state)` as a generator**:
  ```python
  def respond(message, history, state):
      agent = state["agent"]
      history.append({"role": "user", "content": message})
      history.append({"role": "assistant", "content": ""})
      for chunk in agent.stream_message(state["conversation_id"], message):
          history[-1]["content"] += chunk
          yield "", history
  ```

- [ ] **Implement `ingest_document(file, state, progress=gr.Progress())`**:
  - [ ] `progress(0, desc="Reading file...")` → load bytes
  - [ ] `progress(0.3, desc="Chunking...")` → split text
  - [ ] `progress(0.6, desc="Embedding...")` → generate vectors
  - [ ] `progress(1.0, desc="Done")` → store in Qdrant + Meilisearch
  - [ ] Returns status markdown with chunk count

**Tests**: 15 unit tests

**Success Criteria**:
- ✓ Chat loads with progress bar during initialization
- ✓ LLM responses stream token-by-token
- ✓ File upload shows real progress bar
- ✓ Conversation history persists within session

---

#### Step 31: Implement Admin Dashboard

**Status**: 🔄 TODO | **Priority**: HIGH | **Duration**: 3 hours

**Objective**: Build the admin tab with sub-tabs for all management functions.

**Implementation**:

- [ ] **Create `src/ui/dashboard.py`**:
  ```python
  import gradio as gr

  def build_admin_ui():
      """Build the admin dashboard tab with nested sub-tabs."""
      with gr.Tab("🏥 System Health"):
          refresh_btn = gr.Button("Refresh", variant="secondary")
          health_output = gr.Markdown()
          refresh_btn.click(fn=get_health_report, outputs=[health_output])
          # Auto-refresh on tab load

      with gr.Tab("📊 Qdrant"):
          with gr.Row():
              collection_selector = gr.Dropdown(label="Collection")
              refresh_qdrant = gr.Button("Refresh")
          qdrant_stats = gr.Markdown()
          search_input = gr.Textbox(label="Search query")
          search_results = gr.Markdown()

      with gr.Tab("🔬 Langfuse"):
          time_range = gr.Radio(["1h", "24h", "7d"], value="24h", label="Range")
          langfuse_output = gr.Markdown()

      with gr.Tab("🧪 Promptfoo"):
          promptfoo_output = gr.Markdown()

      with gr.Tab("⚙️ Settings"):
          settings_output = gr.Markdown()

      with gr.Tab("📋 Logs"):
          with gr.Row():
              log_lines = gr.Slider(10, 500, value=50, step=10, label="Lines")
              log_level = gr.Dropdown(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"], value="ALL")
              log_service = gr.Dropdown(["ALL", "OLLAMA", "QDRANT", "AGENT"], value="ALL")
          log_output = gr.Textbox(lines=20, label="Log output", interactive=False)
          gr.Button("Refresh Logs").click(
              fn=get_logs, inputs=[log_lines, log_level, log_service], outputs=[log_output]
          )
  ```

- [ ] **Implement handler functions** (thin wrappers over existing service clients):
  - [ ] `get_health_report()` → calls `HealthChecker.check_all()`, returns markdown
  - [ ] `get_qdrant_stats(collection)` → calls `QdrantVectorClient`
  - [ ] `search_qdrant(query, collection)` → semantic search
  - [ ] `get_langfuse_report(time_range)` → calls `LangfuseClient`
  - [ ] `get_promptfoo_report()` → calls `PromptfooClient`
  - [ ] `get_settings_report()` → reads `config`
  - [ ] `get_logs(lines, level, service)` → reads log file

**Tests**: 12 unit tests

**Success Criteria**:
- ✓ All admin sub-tabs load without errors
- ✓ System health shows real service statuses
- ✓ Qdrant search returns results
- ✓ Log viewer filters by level and service

---

#### Step 32: Update Docker & Simplify Startup

**Status**: 🔄 TODO | **Priority**: HIGH | **Duration**: 1 hour

**Objective**: Single-process Docker container, remove all multi-process complexity.

**Implementation**:

- [ ] **Remove from `docker-compose.yml`**: port `8502:8502`
- [ ] **Update `docker-compose.yml` command**:
  ```yaml
  command: ["uvicorn", "src.ui.app:api", "--host", "0.0.0.0", "--port", "8501", "--reload"]
  environment:
    - APP_PORT=8501
    # Remove APP_ADMIN_PORT=8502
  ```
- [ ] **Update `docker/Dockerfile.app-agent`**: replace `CMD` and remove `start_services.sh` copy
- [ ] **Delete `docker/start_services.sh`**
- [ ] **Update healthcheck**: `curl -f http://localhost:8501/health` (FastAPI route, not Chainlit)
- [ ] **Update `.devcontainer`**: remove port 8502 forward if present

**Success Criteria**:
- ✓ `docker compose up app-agent` starts a single process
- ✓ Container health check passes via `/health` endpoint
- ✓ No orphan admin process on container restart

---

#### Step 33: Migrate Test Suite for Gradio

**Status**: 🔄 TODO | **Priority**: HIGH | **Duration**: 3 hours

**Objective**: Rewrite UI tests. Gradio handlers are plain Python functions — no framework mocking required.

**Implementation**:

- [ ] **Delete Chainlit-specific test files** (`tests/ui/`):
  - [ ] `test_chat_handlers.py`
  - [ ] `test_file_upload.py`
  - [ ] `test_actions.py`
  - [ ] `test_admin_app.py`
  - [ ] Any file importing `chainlit`

- [ ] **Create new Gradio tests** (`tests/ui/`):
  - [ ] `test_chat.py` — test `initialize_agent`, `respond`, `ingest_document` directly
  - [ ] `test_dashboard.py` — test all admin handler functions
  - [ ] `test_app.py` — test FastAPI `/health` endpoint with `TestClient`

- [ ] **Example test** (no mocking magic needed):
  ```python
  from unittest.mock import MagicMock, patch
  from src.ui.chat import initialize_agent, respond

  def test_initialize_agent_returns_state_on_success():
      with patch("src.ui.chat.OllamaClient") as mock_ollama:
          mock_ollama.return_value.is_healthy.return_value = True
          # ... mock qdrant, meilisearch similarly
          state, status = initialize_agent()
          assert "agent" in state
          assert "✅" in status

  def test_respond_yields_chunks():
      mock_agent = MagicMock()
      mock_agent.stream_message.return_value = iter(["Hello", " world"])
      state = {"agent": mock_agent, "conversation_id": "test-123"}
      chunks = list(respond("Hi", [], state))
      assert chunks[-1][1][-1]["content"] == "Hello world"
  ```

- [ ] **Update `tests/conftest.py`**: remove Chainlit fixtures, add Gradio/FastAPI fixtures

**Tests**: 350+ passing (target)

**Success Criteria**:
- ✓ Zero Chainlit imports in test suite
- ✓ All UI handler functions testable without framework setup
- ✓ FastAPI `/health` covered by integration test

---

#### Step 34: Update Documentation

**Status**: 🔄 TODO | **Priority**: MEDIUM | **Duration**: 1 hour

**Implementation**:

- [ ] **Update `README.md`**: replace Chainlit references with Gradio/FastAPI, update Quick Start
- [ ] **Update `ARCHITECTURE.md`**: update UI layer diagram, explain single-process model
- [ ] **Update `pyproject.toml`**: confirm chainlit removed, gradio + fastapi + uvicorn present
- [ ] **Update this `PROJECT_PLAN.md`**: mark Phase 6c complete

**Success Criteria**:
- ✓ No Chainlit references in user-facing docs
- ✓ Architecture diagram reflects single FastAPI + Gradio process

---

### PHASE 6c Validation Checkpoint

**Complete When**:
- [ ] FastAPI + Gradio running in Docker on port 8501 (single process)
- [ ] Chat tab: streaming LLM responses working
- [ ] Chat tab: file upload with `gr.Progress()` progress bar working
- [ ] Chat tab: agent initialization shows step-by-step progress bar
- [ ] Admin tab: all sub-tabs (Health, Qdrant, Langfuse, Promptfoo, Settings, Logs) functional
- [ ] Port 8502 removed from Docker entirely
- [ ] `start_services.sh` deleted
- [ ] `.chainlit` config deleted
- [ ] 350+ tests passing, zero Chainlit imports
- [ ] All documentation updated

**Expected Benefits**:
- ✅ **No multi-process hacks**: single `uvicorn` process manages everything
- ✅ **Native tabs**: chat and admin in one app, no port confusion
- ✅ **Real progress bar**: `gr.Progress()` works out of the box, no JS needed
- ✅ **Streaming**: Python generator pattern, no `asyncio.to_thread` overhead
- ✅ **Future-proof**: FastAPI REST layer ready for Phase 7 (LiteLLM) and Phase 8 (MCP)
- ✅ **Testability**: plain function tests, no Chainlit session mocking
- ✅ **Audience fit**: Gradio is the standard AI community demo framework

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

| Phase         | Checkpoint                                                          | Status       |
| ------------- | ------------------------------------------------------------------- | ------------ |
| **Phase 1**   | Docker environment ready                                            | ✅ COMPLETED |
| **Phase 2**   | UI loads, services connected                                        | ✅ COMPLETED |
| **Phase 3**   | RAG pipeline end-to-end                                             | ✅ COMPLETED |
| **Phase 4**   | Security & observability                                            | ✅ COMPLETED |
| **Phase 4b**  | Dashboard tools (149 tests)                                         | ✅ COMPLETED |
| **Phase 5**   | Testing & UX (404 tests)                                            | ✅ COMPLETED |
| **Phase 6**   | UI simplified (sidebar cleanup)                                     | ⚠️ SUPERSEDED |
| **Phase 6b**  | Chainlit migration (async, production-ready)                        | ⚠️ SUPERSEDED |
| **Phase 6c**  | FastAPI + Gradio migration (unified app, single process)            | 🔥 ACTIVE    |
| **Phase 7**   | LiteLLM Gateway integration                                         | 🔄 TODO      |
| **Phase 8**   | MCP Server integration                                              | 🔄 TODO      |
| **Phase 9**   | Performance optimizations                                           | 🔄 TODO      |
| **Phase 10**  | Comprehensive documentation                                         | 🔄 TODO      |

---

## Progress Summary

**Current Status**: Phase 6c Active 🔥 | Next: Phase 7 (LiteLLM Gateway) after 6c completes

**Completed**:
- ✅ 436 tests passing (0 skipped)
- ✅ Full RAG pipeline with observability
- ✅ 5 dashboard management tools
- ✅ Comprehensive security (LLM Guard)
- ✅ UX polish and example content

**Active**:
- 🔥 **Phase 6c**: FastAPI + Gradio migration (Steps 29-34) — replacing Chainlit

**Next Steps** (Priority Order):
1. **Phase 6c**: Complete FastAPI + Gradio migration (Steps 29-34)
2. **Phase 7**: Integrate LiteLLM Gateway (Steps 24-26)
3. **Phase 8**: Add MCP Server (Steps 27-29)
4. **Phase 9**: Optimize performance (Steps 30-31)
5. **Phase 10**: Complete documentation (Steps 32-34)

**Total Remaining Effort**: ~5-6 days

---

**Document Version**: 3.1  
**Last Updated**: 2026-02-18  
**Test Suite**: 436 tests passing → Target: 350+ after Chainlit migration → 480+ after all phases  
**Critical Change**: Migrating from Streamlit to Chainlit for production stability
