# Phase 2 Step 8: Health Check & Startup Sequence - Design Plan

## Overview

Step 8 implements the initialization and startup sequence for Agent Zero. This ensures all services are properly configured before the UI becomes operational.

## Architecture

### Startup Sequence Flow

```
1. App Start (src/ui/main.py)
   ↓
2. Load Config (src/config.py)
   ↓
3. Initialize Logger (src/logging_config.py)
   ↓
4. Create Service Clients (src/services/*.py)
   ↓
5. Run Startup Tasks (src/startup.py)
   ├─ Initialize Ollama
   ├─ Create Qdrant Collections
   └─ Create Meilisearch Indexes
   ↓
6. Health Check (src/services/health_check.py)
   ↓
7. Display UI with Status (src/ui/main.py)
```

## Detailed Implementation Plan

### 1. Create `src/startup.py`

**Purpose:** Initialize services with required resources on application start

**Components:**

```python
async def initialize_ollama() -> bool
    """
    - Check if default model exists (e.g., "mistral")
    - If missing, pull the model
    - Validate model is usable
    - Return True if successful
    """
    
async def initialize_qdrant() -> bool
    """
    - Create "documents" collection for embeddings
    - Vector size: 768 (standard for most models)
    - Distance metric: COSINE
    - Return True if successful
    """
    
async def initialize_meilisearch() -> bool
    """
    - Create "documents" index
    - Primary key: "id"
    - Searchable attributes: ["content", "source", "metadata"]
    - Return True if successful
    """
    
async def startup() -> dict
    """
    - Run all initialization tasks
    - Return status dict: {
        "ollama": bool,
        "qdrant": bool,
        "meilisearch": bool,
        "errors": list[str]
      }
    """
```

### 2. Update `src/ui/main.py`

**Purpose:** Integrate startup sequence into Streamlit app

**Changes:**

```python
@st.cache_resource
def run_startup():
    """Run startup sequence once per session"""
    return asyncio.run(startup())

def main():
    # Run startup (cached)
    startup_status = run_startup()
    
    # Display startup errors if any
    if startup_status["errors"]:
        st.error("⚠️ Startup Warnings")
        for error in startup_status["errors"]:
            st.warning(error)
    
    # Show health status
    render_sidebar_status()
    
    # If all healthy, show normal UI
    if startup_status["all_healthy"]:
        render_tabs()
    else:
        st.info("Waiting for services to become healthy...")
        st.write(startup_status)
```

### 3. Update Health Check

**Purpose:** Validate startup results

**Changes to `src/services/health_check.py`:**

```python
def check_ollama() -> ServiceStatus:
    """
    - Check if model count > 0
    - Verify default model exists
    - Return status
    """
    
def check_qdrant() -> ServiceStatus:
    """
    - List collections
    - Verify "documents" collection exists
    - Return status
    """
    
def check_meilisearch() -> ServiceStatus:
    """
    - List indexes
    - Verify "documents" index exists
    - Return status
    """
```

## Edge Cases & Error Handling

### Ollama Initialization

| Scenario | Handling |
|----------|----------|
| Model pull timeout | Retry 3x with backoff, log warning, continue |
| Model already exists | Skip pull, verify usability |
| Network error | Log error, continue (will retry on health check) |

### Qdrant Initialization

| Scenario | Handling |
|----------|----------|
| Collection already exists | Skip creation (idempotent) |
| Invalid vector size | Use default (768), log warning |
| Connection timeout | Fail startup, show error in UI |

### Meilisearch Initialization

| Scenario | Handling |
|----------|----------|
| Index already exists | Skip creation (idempotent) |
| Invalid index name | Use sanitized name |
| Connection timeout | Fail startup, show error in UI |

## Logging Strategy

All startup operations logged to `logs/app.log` with format:

```
[TIMESTAMP] [LEVEL] [COMPONENT] Message

Example:
[2024-01-15 10:30:45] [INFO] [STARTUP] Initializing Ollama service
[2024-01-15 10:30:46] [INFO] [OLLAMA] Pulling model: mistral
[2024-01-15 10:30:52] [INFO] [OLLAMA] Model mistral ready
[2024-01-15 10:30:53] [INFO] [STARTUP] All services initialized successfully
```

## Testing Strategy

### Startup Tests (`tests/test_startup.py`)

**Mock Strategy:**
- Mock all service clients
- Test happy path (all services initialize)
- Test partial failure (one service fails)
- Test retry behavior
- Test idempotency (running twice should be safe)

**Test Cases (estimated 20-25 tests):**

1. `test_initialize_ollama_success` - Model pulled successfully
2. `test_initialize_ollama_model_exists` - Skip pull if exists
3. `test_initialize_ollama_pull_timeout` - Retry on timeout
4. `test_initialize_ollama_connection_error` - Network failure handling
5. `test_initialize_qdrant_success` - Collection created
6. `test_initialize_qdrant_already_exists` - Idempotent behavior
7. `test_initialize_qdrant_connection_error` - Network failure
8. `test_initialize_meilisearch_success` - Index created
9. `test_initialize_meilisearch_already_exists` - Idempotent behavior
10. `test_initialize_meilisearch_invalid_name` - Name sanitization
11. `test_startup_all_healthy` - All services initialize
12. `test_startup_partial_failure` - One service fails
13. `test_startup_all_failed` - All services fail
14. `test_startup_error_messages` - Errors properly logged
15. `test_startup_idempotency` - Safe to run multiple times

### Integration Tests (`tests/integration/test_startup.py`)

**Note:** Mark with `@pytest.mark.integration`

- Start real Docker containers
- Run full startup sequence
- Verify actual resources created
- Verify health checks pass

## File Structure

```
src/
├─ startup.py                    # NEW: Initialization sequence
├─ ui/
│  └─ main.py                   # MODIFIED: Add startup integration
├─ services/
│  ├─ health_check.py           # MODIFIED: Enhance validation
│  └─ ...
└─ ...

tests/
├─ test_startup.py              # NEW: Startup unit tests
└─ integration/
   └─ test_startup.py           # NEW: Startup integration tests
```

## Success Criteria

- [x] Startup runs once per session
- [x] All services initialize in correct order
- [x] Errors logged with context
- [x] UI displays startup status
- [x] Health checks validate startup results
- [x] Idempotent behavior (safe to run multiple times)
- [x] 20+ startup tests created
- [x] Edge cases handled gracefully
- [x] All errors visible in UI logs tab

## Estimated Implementation Time

- `src/startup.py` development: 1-2 hours
- `src/ui/main.py` integration: 0.5-1 hour
- Service client updates: 0.5 hour
- Test development: 1-2 hours
- Code review & fixes: 0.5-1 hour

**Total: 4-7 hours**

## Phase 2 Step 8 Acceptance Criteria

When complete:
- [ ] `docker-compose up` → All services healthy
- [ ] Navigate to `http://localhost:8501` → UI loads
- [ ] Sidebar shows 🟢 healthy status for all services
- [ ] UI logs show successful initialization
- [ ] Health checks pass for all services
- [ ] 20+ tests all passing
- [ ] Code review passed
- [ ] No Python errors in terminal

---

## Next: Phase 3 Planning

Once Step 8 complete:
- Document Ingestion Pipeline (Step 9)
- Retrieval Engine (Step 10)
- Agent Orchestration (Step 11)
- Conversation Memory (Step 12)
