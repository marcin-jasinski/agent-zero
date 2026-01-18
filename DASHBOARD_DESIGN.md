# Agent Zero Dashboard Design - Tool Dashboards & Management Interface

**Version**: 1.0  
**Date**: 2026-01-18  
**Phase**: 4b (Post-Phase 4 Security & Observability)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [UI Layout & Navigation](#ui-layout--navigation)
4. [Component Specifications](#component-specifications)
5. [Implementation Guidelines](#implementation-guidelines)
6. [Data Flow](#data-flow)
7. [Future Enhancements](#future-enhancements)

---

## Overview

### Vision

Transform Agent Zero UI from a single chat interface to a comprehensive management platform where users can:

- Monitor and manage vector database (Qdrant)
- View real-time observability traces (Langfuse)
- Test and version prompts (Promptfoo integration)
- Monitor system health and performance
- Configure all services without leaving the dashboard

### Problem Statement

Currently, users must:

- Switch between Streamlit UI (chat) and external services (Qdrant UI, Langfuse UI)
- Manually manage documents and vectors
- Limited visibility into agent decision-making
- No integrated system monitoring

### Solution

**Unified Dashboard** with tool-specific tabs accessible from a dynamic left sidebar.

---

## Architecture

### Current Structure (Phase 2-3)

```
Streamlit App (port 8501)
├─ Sidebar: Service Health Status
└─ Main Area:
   ├─ Chat Tab
   ├─ Knowledge Base Tab
   ├─ Settings Tab
   └─ Logs Tab
```

### Proposed Structure (Phase 4b)

```
Streamlit App (port 8501)
├─ Sidebar: Dynamic Tool Navigation
│  ├─ Core Tools (always visible)
│  │  ├─ 💬 Chat
│  │  ├─ 📚 Knowledge Base
│  │  ├─ ⚙️ Settings
│  │  └─ 📋 Logs
│  │
│  └─ Management Tools (conditional)
│     ├─ 🔍 Qdrant Manager
│     ├─ 📊 Langfuse Observability
│     ├─ 🎯 Promptfoo Testing
│     └─ 🎛️ System Health
│
└─ Main Area: Dynamic Content Area
   └─ Tool-specific components
```

### Technical Stack

- **UI Framework**: Streamlit (existing)
- **Sidebar Navigation**: Custom Streamlit sidebar with icons + labels
- **Tool Components**: Modular Streamlit components in `/src/ui/tools/`
- **Data Fetching**: Service client wrappers (existing)
- **Caching**: Streamlit `@st.cache_data` for performance

---

## UI Layout & Navigation

### Sidebar Navigation Structure

#### Core Tools Section

**Always visible, unchanged from Phase 2:**

```
┌─────────────────────┐
│  Agent Zero (L.A.B) │
├─────────────────────┤
│ 💬 Chat             │ ← Current: main communication
├─────────────────────┤
│ 📚 Knowledge Base    │ ← Current: document management
├─────────────────────┤
│ ⚙️ Settings         │ ← Current: configuration
├─────────────────────┤
│ 📋 Logs            │ ← Current: activity logs
├─────────────────────┤
│ Service Health      │
│ 🟢 Ollama           │
│ 🟢 Qdrant           │
│ 🟢 Meilisearch      │
└─────────────────────┘
```

#### Management Tools Section (NEW)

**Conditional visibility based on Phase 4 completion:**

```
├─────────────────────┤
│ MANAGEMENT TOOLS    │
├─────────────────────┤
│ 🔍 Qdrant Manager   │ ← NEW: Vector DB management
│ 📊 Langfuse Traces  │ ← NEW: Observability dashboard
│ 🎯 Promptfoo        │ ← NEW: Prompt testing
│ 🎛️ System Health    │ ← NEW: Detailed metrics
└─────────────────────┘
```

### Main Content Area - Tab Layouts

#### 1. Chat Tab (Existing - No Changes)

```
┌─────────────────────────────────────────────┐
│ 💬 Chat                                      │
├─────────────────────────────────────────────┤
│                                              │
│  Message History                             │
│  ┌──────────────────────────────────────┐   │
│  │ [Assistant]: Here's the answer with  │   │
│  │              sources: [PDF1, PDF2]   │   │
│  │                                      │   │
│  │ [User]: What about X?                │   │
│  │                                      │   │
│  │ [Assistant]: Based on context...     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Input: [_________________] [Send] [Clear]  │
└─────────────────────────────────────────────┘
```

#### 2. Knowledge Base Tab (Existing - Minor Enhancement)

```
┌─────────────────────────────────────────────┐
│ 📚 Knowledge Base                            │
├─────────────────────────────────────────────┤
│                                              │
│  Upload: [Choose File] [Upload]              │
│  Filter: [All Docs] [Search: ____] [Clear]  │
│                                              │
│  Documents:                                  │
│  ┌──────────────────────────────────────┐   │
│  │ ✓ report_2024.pdf        │ 5.2 MB    │   │
│  │   Chunks: 12   │ Uploaded: 2h ago    │   │
│  │   [View] [Delete] [Details]          │   │
│  ├──────────────────────────────────────┤   │
│  │ ✓ manual_v3.pdf          │ 8.1 MB    │   │
│  │   Chunks: 18   │ Uploaded: 5h ago    │   │
│  │   [View] [Delete] [Details]          │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### 3. Qdrant Manager Tab (NEW - Phase 4b)

```
┌─────────────────────────────────────────────┐
│ 🔍 Qdrant Manager                            │
├─────────────────────────────────────────────┤
│                                              │
│  Collections Overview:                       │
│  ┌──────────────────────────────────────┐   │
│  │ Collection: documents                 │   │
│  │ ├─ Vectors: 8,432                    │   │
│  │ ├─ Vector Size: 768 dims             │   │
│  │ ├─ Distance Metric: Cosine           │   │
│  │ ├─ Storage: 12.5 MB                  │   │
│  │ └─ [Details] [Search] [Delete]       │   │
│  ├──────────────────────────────────────┤   │
│  │ Collection: [New Collection]          │   │
│  │   [Create] [Cancel]                  │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Search Interface:                           │
│  ┌──────────────────────────────────────┐   │
│  │ Query by embedding:                   │   │
│  │ [____________________________] [Search]   │
│  │ Top K: [5 ▼]                         │   │
│  │                                      │   │
│  │ Results:                              │   │
│  │ 1. Score: 0.92 | "text snippet..."  │   │
│  │ 2. Score: 0.87 | "text snippet..."  │   │
│  │ 3. Score: 0.81 | "text snippet..."  │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### 4. Langfuse Observability Tab (NEW - Phase 4b)

```
┌─────────────────────────────────────────────┐
│ 📊 Langfuse Observability                    │
├─────────────────────────────────────────────┤
│                                              │
│  Trace Summary:                              │
│  ┌──────────────────────────────────────┐   │
│  │ Total Traces: 1,247                  │   │
│  │ Last 24h: 342                        │   │
│  │ Avg Latency: 2.3s                    │   │
│  │ Error Rate: 0.2%                     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Recent Traces:                              │
│  ┌──────────────────────────────────────┐   │
│  │ 📍 [2026-01-18 14:32:45] Chat Query  │   │
│  │    Duration: 2.1s   Status: ✓        │   │
│  │    Tokens: 245 in, 89 out            │   │
│  │    [View Trace] [View Details]       │   │
│  ├──────────────────────────────────────┤   │
│  │ 📍 [2026-01-18 14:31:12] Retrieval   │   │
│  │    Duration: 0.8s   Status: ✓        │   │
│  │    Retrieved: 5 docs                 │   │
│  │    [View Trace] [View Details]       │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Filters: [Last 24h ▼] [All Users ▼]        │
│  [Full Langfuse Dashboard] (opens port 3000)│
└─────────────────────────────────────────────┘
```

#### 5. Promptfoo Testing Tab (NEW - Phase 4b)

```
┌─────────────────────────────────────────────┐
│ 🎯 Promptfoo Testing                         │
├─────────────────────────────────────────────┤
│                                              │
│  Create Test:                                │
│  ┌──────────────────────────────────────┐   │
│  │ Test Name: [_________________]       │   │
│  │ Prompt Template:                     │   │
│  │ ┌──────────────────────────────────┐ │   │
│  │ │ You are a helpful assistant...   │ │   │
│  │ │ {user_query}                     │ │   │
│  │ └──────────────────────────────────┘ │   │
│  │ Variables: [Add Variable]            │   │
│  │ [Save as Draft] [Run Test]           │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  Test Runs:                                  │
│  ┌──────────────────────────────────────┐   │
│  │ v1.0 (Latest)                        │   │
│  │ Model: ministral-3:3b                │   │
│  │ Test Cases: 15                       │   │
│  │ Pass Rate: 93%                       │   │
│  │ [View Results] [Compare] [Deploy]    │   │
│  ├──────────────────────────────────────┤   │
│  │ v0.9                                 │   │
│  │ Model: ministral-3:3b                │   │
│  │ Test Cases: 15                       │   │
│  │ Pass Rate: 87%                       │   │
│  │ [View Results] [Compare] [Revert]    │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

#### 6. System Health Tab (NEW - Phase 4b)

```
┌─────────────────────────────────────────────┐
│ 🎛️ System Health                             │
├─────────────────────────────────────────────┤
│                                              │
│  Overall System Status: 🟢 HEALTHY           │
│                                              │
│  Service Metrics:                            │
│  ┌──────────────────────────────────────┐   │
│  │ Ollama                               │   │
│  │ Status: 🟢 Running                   │   │
│  │ CPU: 45% │ Memory: 2.1 GB / 8 GB    │   │
│  │ Models: 2 loaded                     │   │
│  │ Requests: 342 (last 24h)             │   │
│  ├──────────────────────────────────────┤   │
│  │ Qdrant                               │   │
│  │ Status: 🟢 Running                   │   │
│  │ Memory: 1.2 GB / 2 GB                │   │
│  │ Collections: 1                       │   │
│  │ Vectors: 8,432                       │   │
│  ├──────────────────────────────────────┤   │
│  │ Meilisearch                          │   │
│  │ Status: 🟢 Running                   │   │
│  │ Memory: 0.8 GB / 2 GB                │   │
│  │ Documents Indexed: 45                │   │
│  │ Searches: 1,203 (last 24h)           │   │
│  ├──────────────────────────────────────┤   │
│  │ Langfuse                             │   │
│  │ Status: 🟢 Running                   │   │
│  │ Database: 👍 Connected               │   │
│  │ Traces Stored: 1,247                 │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  System Resources (Host Docker):             │
│  ┌──────────────────────────────────────┐   │
│  │ Total CPU: 2.3 / 8 cores             │   │
│  │ Total Memory: 4.1 GB / 16 GB         │   │
│  │ Disk Used: 8.5 GB / 100 GB           │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Sidebar Navigation Component

**File**: `src/ui/components/navigation.py`

```python
class SidebarNavigation:
    """Dynamic sidebar navigation with tool management."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.tools = self._load_available_tools()

    def _load_available_tools(self) -> List[ToolDefinition]:
        """Load available tools based on Phase 4 completion status."""
        tools = [
            ToolDefinition("chat", "💬 Chat", "chat_component"),
            ToolDefinition("knowledge_base", "📚 Knowledge Base", "kb_component"),
            ToolDefinition("settings", "⚙️ Settings", "settings_component"),
            ToolDefinition("logs", "📋 Logs", "logs_component"),
        ]

        # Add Phase 4b tools if enabled
        if config.phase_4b_enabled:
            tools.extend([
                ToolDefinition("qdrant", "🔍 Qdrant Manager", "qdrant_component"),
                ToolDefinition("langfuse", "📊 Langfuse Traces", "langfuse_component"),
                ToolDefinition("promptfoo", "🎯 Promptfoo", "promptfoo_component"),
                ToolDefinition("health", "🎛️ System Health", "health_component"),
            ])

        return tools

    def render(self) -> str:
        """Render sidebar with tool buttons and health status."""
        pass
```

### 2. Qdrant Manager Component

**File**: `src/ui/tools/qdrant_dashboard.py`

**Features**:

- List all collections with stats
- View collection details (vectors, dimensions, distance metric)
- Search interface (semantic + hybrid)
- Delete collection
- Create new collection
- Vector statistics

**Data Source**: `src/services/qdrant_client.py` (existing)

### 3. Langfuse Observability Component

**File**: `src/ui/tools/langfuse_dashboard.py`

**Features**:

- Summary metrics (total traces, latency, error rate)
- Recent traces list with filtering
- Trace details viewer
- Token usage statistics
- Link to full Langfuse UI (port 3000)
- Configurable time range filters

**Data Source**: New `src/services/langfuse_client.py` (read-only wrapper)

### 4. Promptfoo Testing Component

**File**: `src/ui/tools/promptfoo_dashboard.py`

**Features**:

- Create test scenarios
- Version management
- Test run results
- Pass/fail rate tracking
- Comparison between versions
- Deploy selected prompt version

**Data Source**: New `src/services/promptfoo_client.py` (if available) or local config

### 5. System Health Component

**File**: `src/ui/tools/system_health_dashboard.py`

**Features**:

- Overall system status indicator
- Per-service metrics (CPU, memory, requests)
- Host Docker stats (total resources)
- Health trend visualization
- Alert configuration

**Data Source**: Enhanced `src/services/health_check.py` with metrics

---

## Implementation Guidelines

### Step 1: Refactor Sidebar Navigation

**Priority**: P0 (blocking)

```python
# In src/ui/main.py

with st.sidebar:
    st.title("Agent Zero (L.A.B.)")

    # Use new sidebar navigation component
    from src.ui.components.navigation import SidebarNavigation
    nav = SidebarNavigation(config)
    selected_tool = nav.render()

    # Display service health (existing)
    st.divider()
    display_service_health()
```

**Steps**:

1. Create `src/ui/components/navigation.py` with `SidebarNavigation` class
2. Extract current tab logic to `selected_tool` state
3. Conditionally render tool components based on selection
4. Test with existing 4 tools first (Chat, KB, Settings, Logs)

### Step 2: Implement Management Tool Components

**Create in parallel**:

1. `src/ui/tools/qdrant_dashboard.py`
2. `src/ui/tools/langfuse_dashboard.py`
3. `src/ui/tools/promptfoo_dashboard.py`
4. `src/ui/tools/system_health_dashboard.py`

**Each component should**:

- Have `render()` method matching interface
- Use Streamlit columns for layout
- Cache data with `@st.cache_data` (5-minute TTL)
- Handle errors gracefully
- Include refresh buttons

### Step 3: Enhance Service Clients

**Qdrant Client** (existing - add methods):

```python
def get_collections_stats() -> List[CollectionStats]:
    """Get all collections with storage and vector counts."""

def semantic_search(query: str, collection: str, top_k: int) -> List[SearchResult]:
    """Search by embedding similarity."""
```

**Langfuse Client** (NEW):

```python
def get_trace_summary() -> TraceSummary:
    """Get recent trace statistics."""

def get_recent_traces(limit: int = 20) -> List[Trace]:
    """Get recent traces with filtering."""

def get_trace_details(trace_id: str) -> TraceDetail:
    """Get full trace execution details."""
```

**Health Check Client** (existing - enhance):

```python
def get_service_metrics(service: str) -> ServiceMetrics:
    """Get detailed metrics for a service."""

def get_docker_stats() -> DockerStats:
    """Get host Docker resource usage."""
```

### Step 4: Update Configuration

**In `src/config.py`**:

```python
class FeatureFlags(BaseModel):
    """Feature flags for conditional UI rendering."""

    # Phase 4b dashboard features
    qdrant_manager_enabled: bool = False  # Enable when Phase 4b starts
    langfuse_dashboard_enabled: bool = False
    promptfoo_enabled: bool = False
    system_health_dashboard_enabled: bool = False
```

### Step 5: Testing & Validation

**Unit Tests**:

```
tests/ui/components/test_navigation.py
tests/ui/tools/test_qdrant_dashboard.py
tests/ui/tools/test_langfuse_dashboard.py
tests/ui/tools/test_promptfoo_dashboard.py
tests/ui/tools/test_system_health_dashboard.py
```

**Integration Tests**:

- Test sidebar navigation with all tools
- Test switching between tabs
- Test data loading and caching

---

## Data Flow

### User Interaction Flow

```
User selects tool in sidebar
    ↓
st.session_state["selected_tool"] = tool_name
    ↓
Main content area re-renders
    ↓
Tool component's render() method called
    ↓
Component fetches data (with caching)
    ↓
Component displays UI
    ↓
User interacts (search, filter, delete, etc.)
    ↓
Component calls service client method
    ↓
Service client calls backend service (Qdrant, Langfuse, etc.)
    ↓
Response displayed in UI
    ↓
Data cache invalidated if needed
```

### Architecture Diagram

```
Streamlit UI (port 8501)
├─ Sidebar Navigation
│  └─ SidebarNavigation component (new)
│
├─ Chat Tool
│  └─ chat_component (existing)
│
├─ Knowledge Base Tool
│  └─ knowledge_base_component (existing + enhanced)
│
├─ Qdrant Manager Tool (NEW)
│  ├─ Collections list
│  ├─ Search interface
│  └─ Service: QdrantClient (existing, enhanced)
│
├─ Langfuse Dashboard Tool (NEW)
│  ├─ Trace summary
│  ├─ Recent traces
│  └─ Service: LangfuseClient (new)
│
├─ Promptfoo Tool (NEW)
│  ├─ Test creation
│  ├─ Test runs
│  └─ Service: PromptfooClient (new, optional)
│
└─ System Health Tool (NEW)
   ├─ Service status
   ├─ Resource metrics
   └─ Service: HealthCheckClient (existing, enhanced)
```

---

## Future Enhancements

### Phase 4c: Advanced Features

- **Real-time metrics**: WebSocket updates instead of refresh buttons
- **Custom dashboards**: User-defined tool layouts
- **Alerting**: Notifications for service outages
- **Export data**: CSV/JSON export of metrics and traces

### Phase 5: Production Features

- **Multi-user support**: Separate dashboards per user
- **Audit logging**: Track all actions in system health
- **Rate limiting**: Prevent excessive tool queries
- **Authentication**: Access control for sensitive tools

### Phase 6: AI Enhancements

- **Auto-diagnostics**: AI suggests optimizations based on metrics
- **Anomaly detection**: ML-based system health alerts
- **Performance optimization**: Auto-tune Qdrant query parameters

---

## Summary

This dashboard design transforms Agent Zero from a chat-focused tool into a comprehensive management platform. By implementing Phase 4b:

✅ **Users gain complete visibility** into vector database, observability, and system health  
✅ **Single interface** replaces multiple external dashboards  
✅ **Production-ready monitoring** without leaving Streamlit  
✅ **Extensible architecture** for future tool additions

**Implementation Timeline**: ~3-4 weeks for core Phase 4b components

---

**Document Version**: 1.0  
**Created**: 2026-01-18  
**Status**: Ready for Phase 4b implementation  
**Approval**: Pending
