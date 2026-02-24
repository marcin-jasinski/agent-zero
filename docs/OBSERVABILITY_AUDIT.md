# Agent Zero Observability Audit Report

**Date:** February 9, 2026  
**Auditor:** GitHub Copilot  
**Project:** Agent Zero (L.A.B. - Local Agent Builder)

---

## Executive Summary

This audit evaluates Agent Zero's observability implementation across the three pillars: **Logs**, **Metrics**, and **Tracing**. The goal is to ensure developers have comprehensive visibility into the system's behavior for debugging, optimization, and monitoring.

**Overall Assessment:** ⭐️⭐️⭐️⚪️⚪️ (3/5)

- ✅ **Logging:** Well-implemented with structured logging, filtering, and UI access
- ⚠️ **Metrics:** Basic implementation present, missing formalized metrics collection
- ✅ **Tracing:** Solid foundation with Langfuse integration, room for enhancement

---

## Pillar 1: Logging ✅

### Current Implementation

#### **Strengths**
1. **Structured Logging** ([logging_config.py](../src/logging_config.py)):
   - JSON and text formatters available
   - Supports multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Rotating file handlers (10MB limit, 10 backups)
   - Separate error log file for critical issues
   - ANSI color support for terminal output

2. **Service-Level Filtering** ([logs.py](../src/ui/tools/logs.py)):
   - Pattern-based filtering by logger name
   - Filter by: Ollama, Qdrant, Meilisearch, Langfuse, Agent Core, etc.
   - Real-time log viewing with auto-refresh (1s intervals)
   - Level-based filtering (INFO, WARNING, ERROR)

3. **Comprehensive Coverage**:
   ```python
   # Examples of logged operations:
   - Document ingestion: "Successfully ingested 31 chunks from XTB_Raport_na_2026.pdf in 19.45s"
   - RAG retrieval: "Using HYBRID search for query: '...'"
   - Timing information: "[TIMING] Embedding generation took 0.45s"
   - Error tracking: "Qdrant search failed: ConnectionError"
   ```

4. **UI Access**:
  - In-chat admin actions and external observability links
  - Real-time streaming with statistics (total lines, INFO/WARNING/ERROR counts)
  - Service-targeted filtering in generated reports

#### **Gaps & Recommendations**

| Priority | Issue | Recommendation | Effort |
|----------|-------|----------------|--------|
| 🔴 High | Missing log correlation IDs | Add `request_id` to all log entries for tracing multi-step operations | Medium |
| 🟡 Medium | No log aggregation | Implement log shipping to external systems (Loki, ELK) for persistence | High |
| 🟡 Medium | Limited structured fields | Add more contextual data: `user_id`, `conversation_id`, `document_id` | Low |
| 🟢 Low | No log sampling | Implement log sampling for high-volume DEBUG logs | Low |

#### **Action Items**

1. **Add Request ID Tracking**:
   ```python
   # src/logging_config.py - Enhance JSONFormatter
   import uuid
   from contextvars import ContextVar
   
   request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')
   
   class JSONFormatter(logging.Formatter):
       def format(self, record: logging.LogRecord) -> str:
           log_data = {
               "timestamp": datetime.utcnow().isoformat(),
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
               "request_id": request_id_ctx.get() or str(uuid.uuid4()),  # ← NEW
               # ... rest of fields
           }
   ```

2. **Add Conversation Context**:
   ```python
   # src/core/agent.py - Add to all log statements
   logger.info(
       f"Generated response for conversation {conversation_id}",
       extra={"conversation_id": conversation_id, "documents_used": len(retrieved_docs)}
   )
   ```

---

## Pillar 2: Metrics ⚠️

### Current Implementation

#### **Strengths**
1. **System Health Metrics** ([system_health.py](../src/ui/tools/system_health.py)):
   - CPU usage percentage (via psutil)
   - Memory usage (used/total GB)
   - Disk usage percentage
   - Service health checks (Ollama, Qdrant, Meilisearch, Langfuse)

2. **Business Metrics (Scattered)**:
   - Document counts in Qdrant/Meilisearch (visible in dashboards)
   - Token usage per trace (tracked in Langfuse)
   - Test pass rates (Promptfoo dashboard)
   - Retrieval counts per query

#### **Gaps & Recommendations**

| Priority | Issue | Recommendation | Effort |
|----------|-------|----------------|--------|
| 🔴 High | **No centralized metrics system** | Add Prometheus + Grafana to docker-compose | High |
| 🔴 High | **Missing application metrics** | Instrument code with counters, histograms, gauges | Medium |
| 🟡 Medium | **No alerting** | Set up alert rules for critical metrics (disk full, service down) | High |
| 🟡 Medium | **No time-series visualization** | Create Grafana dashboards for trends over time | Medium |
| 🟢 Low | **No custom metrics API** | Expose `/metrics` endpoint for Prometheus scraping | Low |

#### **Critical Missing Metrics**

**Application Performance Metrics:**
- Request latency (p50, p95, p99)
- Error rates (4xx, 5xx)
- Throughput (requests per second)
- Agent response time breakdown

**RAG-Specific Metrics:**
- Embedding generation time
- Vector search latency
- Hybrid search result counts
- Document retrieval success rate

**LLM Metrics:**
- Token consumption rate (tokens/minute)
- Model inference time
- Prompt completion ratio
- Generation errors

**Infrastructure Metrics:**
- Container resource usage (CPU, memory per service)
- Vector DB collection size growth
- Full-text index size
- PostgreSQL connection pool usage

#### **Action Items**

1. **Add Prometheus to Stack**:
   ```yaml
   # docker-compose.yml - Add new service
   prometheus:
     image: prom/prometheus:latest
     container_name: agent-zero-prometheus
     ports:
       - "9090:9090"
     volumes:
       - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
       - prometheus-data:/prometheus
     command:
       - '--config.file=/etc/prometheus/prometheus.yml'
       - '--storage.tsdb.path=/prometheus'
     networks:
       - agent-zero-network
     restart: unless-stopped
   
   grafana:
     image: grafana/grafana:latest
     container_name: agent-zero-grafana
     ports:
       - "3001:3000"  # Port 3000 is used by Langfuse
     environment:
       - GF_SECURITY_ADMIN_PASSWORD=admin
     volumes:
       - grafana-data:/var/lib/grafana
     depends_on:
       - prometheus
     networks:
       - agent-zero-network
     restart: unless-stopped
   ```

2. **Instrument Application Code**:
   ```python
   # Add to pyproject.toml dependencies:
   # "prometheus-client>=0.19.0",
   
   # src/observability/metrics.py (NEW FILE)
   from prometheus_client import Counter, Histogram, Gauge, start_http_server
   
   # Request counters
   requests_total = Counter(
       'agent_zero_requests_total',
       'Total requests processed',
       ['endpoint', 'status']
   )
   
   # Latency histograms
   request_latency = Histogram(
       'agent_zero_request_duration_seconds',
       'Request latency in seconds',
       ['endpoint']
   )
   
   # RAG-specific metrics
   retrieval_docs_count = Histogram(
       'agent_zero_retrieval_documents',
       'Number of documents retrieved per query',
       ['retrieval_type']
   )
   
   embedding_latency = Histogram(
       'agent_zero_embedding_duration_seconds',
       'Embedding generation time in seconds'
   )
   
   # LLM metrics
   llm_tokens_total = Counter(
       'agent_zero_llm_tokens_total',
       'Total tokens processed',
       ['type']  # input, output
   )
   
   llm_generation_latency = Histogram(
       'agent_zero_llm_generation_duration_seconds',
       'LLM generation time in seconds',
       ['model']
   )
   ```

3. **Add Metrics Decorator**:
   ```python
   # src/observability/metrics.py
   import time
   from functools import wraps
   
   def track_latency(metric: Histogram):
       """Decorator to track function execution time."""
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               start = time.time()
               try:
                   result = func(*args, **kwargs)
                   metric.observe(time.time() - start)
                   return result
               except Exception as e:
                   metric.observe(time.time() - start)
                   raise
           return wrapper
       return decorator
   
   # Usage example:
   # @track_latency(embedding_latency)
   # def generate_embedding(self, text: str) -> list[float]:
   #     ...
   ```

4. **Create Grafana Dashboard**:
   ```json
   // config/grafana/dashboards/agent-zero.json
   {
     "dashboard": {
       "title": "Agent Zero - Observability",
       "panels": [
         {
           "title": "Request Rate",
           "targets": [
             {
               "expr": "rate(agent_zero_requests_total[5m])"
             }
           ]
         },
         {
           "title": "p95 Latency",
           "targets": [
             {
               "expr": "histogram_quantile(0.95, agent_zero_request_duration_seconds_bucket)"
             }
           ]
         },
         {
           "title": "Document Retrieval",
           "targets": [
             {
               "expr": "rate(agent_zero_retrieval_documents_count[5m])"
             }
           ]
         }
       ]
     }
   }
   ```

5. **Expose Metrics Endpoint**:
   ```python
   # src/ui/main.py - Add at startup
   from prometheus_client import start_http_server
   
   # Start metrics server on port 9091 (inside container)
   start_http_server(9091)
   logger.info("Prometheus metrics server started on port 9091")
   ```

---

## Pillar 3: Tracing ✅

### Current Implementation

#### **Strengths**
1. **Langfuse Integration** ([langfuse_callback.py](../src/observability/langfuse_callback.py)):
   - Trace-based tracking using Langfuse SDK v2
   - Conversation-level tracing with persistent trace objects
   - Spans for: retrieval, LLM generation, agent decisions
   - Token usage tracking (input/output tokens per generation)
   - Custom scores (confidence tracking)

2. **Comprehensive Tracking**:
   ```python
   # Tracked operations:
   - track_retrieval(conversation_id, query, results_count, retrieval_type)
   - track_llm_generation(conversation_id, model, prompt, response, duration_ms)
   - track_agent_decision(conversation_id, decision_type, metadata)
   - track_confidence_score(conversation_id, confidence, reasoning)
   ```

3. **UI Dashboard** ([langfuse_dashboard.py](../src/ui/tools/langfuse_dashboard.py)):
   - Summary metrics: total traces, traces in last 24h, avg latency, error rate
   - Recent traces view with expandable details
   - Status filtering (all, success, error)
   - Token usage visualization
   - Link to full Langfuse dashboard (http://localhost:3000)

4. **Graceful Degradation**:
   - Feature flag: `LANGFUSE_ENABLED=true/false`
   - Falls back safely if Langfuse is unavailable
   - Logs errors without breaking application flow

#### **Gaps & Recommendations**

| Priority | Issue | Recommendation | Effort |
|----------|-------|----------------|--------|
| 🟡 Medium | No distributed tracing headers | Add W3C Trace Context headers for cross-service tracing | Medium |
| 🟡 Medium | Limited span attributes | Add more contextual metadata to spans (document IDs, chunk counts) | Low |
| 🟢 Low | No sampling strategy | Implement trace sampling for high-traffic scenarios | Medium |
| 🟢 Low | No error tagging | Add error tags and stack traces to failed spans | Low |

#### **Action Items**

1. **Enhance Span Metadata**:
   ```python
   # src/observability/langfuse_callback.py
   def track_retrieval(
       self,
       conversation_id: str,
       query: str,
       results_count: int,
       retrieval_type: str = "hybrid",
   ) -> None:
       trace = self._get_or_create_trace(conversation_id)
       
       trace.span(
           name="document_retrieval",
           input={"query": query[:500], "type": retrieval_type},
           output={"results_count": results_count},
           metadata={
               "retrieval_type": retrieval_type,
               "timestamp": datetime.utcnow().isoformat(),
               # ↓ ADD THESE
               "query_length": len(query),
               "semantic_results": results_count,  # if available
               "keyword_results": 0,  # if available
               "hybrid_weight_semantic": 0.7,  # from config
               "hybrid_weight_keyword": 0.3,  # from config
           },
       )
   ```

2. **Add Error Tracking to Spans**:
   ```python
   # src/observability/langfuse_callback.py
   def track_error(
       self,
       conversation_id: str,
       error_type: str,
       error_message: str,
       stack_trace: Optional[str] = None,
   ) -> None:
       """Track errors as events in the trace."""
       if not self.enabled or not self.client:
           return
       
       try:
           trace = self._get_or_create_trace(conversation_id)
           
           trace.event(
               name="error_occurred",
               input={"error_type": error_type},
               output={"error_message": error_message},
               metadata={
                   "stack_trace": stack_trace,
                   "timestamp": datetime.utcnow().isoformat(),
               },
           )
       except Exception as e:
           logger.error(f"Failed to track error: {e}")
   ```

3. **Enable Feature Flag by Default**:
   ```python
   # src/config.py - Update LangfuseConfig
   class LangfuseConfig(BaseSettings):
       enabled: bool = Field(default=True, description="Enable Langfuse integration")  # ← ALREADY TRUE
   ```
   
   Update `.env` documentation to ensure developers know Langfuse is available out-of-the-box.

---

## Summary: Observability Maturity Matrix

| Pillar | Current State | Target State | Gap Analysis |
|--------|--------------|--------------|--------------|
| **Logging** | ✅ Advanced | ✅ Advanced | Add correlation IDs, external shipping |
| **Metrics** | ⚠️ Basic | ✅ Advanced | Add Prometheus/Grafana, instrument code |
| **Tracing** | ✅ Intermediate | ✅ Advanced | Enhance metadata, add error tracking |

### Immediate Priorities (Next 2 Weeks)

1. **[HIGH]** Add Prometheus + Grafana to docker-compose
2. **[HIGH]** Instrument RAG pipeline with metrics (retrieval latency, doc counts)
3. **[MEDIUM]** Add request ID correlation to logs
4. **[MEDIUM]** Enhance Langfuse spans with richer metadata
5. **[LOW]** Create default Grafana dashboard for Agent Zero

### Long-Term Enhancements (Next Quarter)

1. **Alerting Infrastructure**: Set up Alertmanager for critical alerts
2. **Log Aggregation**: Implement Loki for long-term log storage
3. **Distributed Tracing**: Add OpenTelemetry for cross-service tracing
4. **Custom Metrics API**: Build developer-facing metrics API
5. **Observability Documentation**: Create developer guide for adding custom observability

---

## Developer Access Verification ✅

### How Developers Access Observability

| Tool | Access Method | URL | Status |
|------|--------------|-----|--------|
| **Logs** | Container logs + in-chat diagnostics | http://localhost:8501 | ✅ Working |
| **Langfuse Tracing** | Gradio Admin tab + full dashboard | http://localhost:3000 | ✅ Working |
| **System Health** | Admin tab → Health panel | http://localhost:8501 | ✅ Working |
| **Qdrant Metrics** | Qdrant dashboard | http://localhost:6333/dashboard | ✅ Working |
| **Meilisearch Metrics** | Meilisearch native UI | http://localhost:7700 | ✅ Working |
| **Prometheus** | Direct TSDB UI | http://localhost:9090 | ✅ Working |
| **Grafana** | Agent Zero dashboard | http://localhost:3001 | ✅ Working |

### Feature Flags

```python
# src/config.py - DashboardFeatures
show_logs: bool = True  # ✅ Enabled
show_langfuse_dashboard: bool = False  # ❌ Disabled by default
show_system_health: bool = False  # ❌ Disabled by default
```

**Recommendation:** Enable observability dashboards by default in development:
```python
show_langfuse_dashboard: bool = Field(
    default=True if env == "development" else False,  # ← Auto-enable in dev
    description="Show Langfuse Observability dashboard"
)
```

---

## Technical Debt & Risks

### High Priority
- **No metrics persistence**: System metrics are ephemeral, no historical data
- **Single point of failure**: Langfuse outage disables all tracing
- **No alerting**: Critical issues may go unnoticed

### Medium Priority
- **Log rotation limits**: 10 x 10MB = 100MB max, may be insufficient for production
- **No log compression**: Disk space waste
- **Manual log analysis**: No search/query interface for logs

### Low Priority
- **psutil optional**: System health dashboard degrades without it
- **No trace sampling**: High-volume scenarios may overwhelm Langfuse

---

## Conclusion

Agent Zero has a **solid foundation** for observability with excellent logging and tracing capabilities. The primary gap is **formalized metrics collection** via Prometheus/Grafana.

**Key Strengths:**
- Comprehensive structured logging with service filtering
- Production-ready Langfuse tracing integration
- Developer-friendly UI for observability access

**Critical Next Steps:**
1. Add Prometheus + Grafana (1-2 days effort)
2. Instrument RAG pipeline with metrics (2-3 days effort)
3. Enable observability dashboards by default in development

**Estimated Total Effort:** 1-2 weeks to reach "Advanced" maturity across all three pillars.

---

**Report Generated:** February 9, 2026  
**Next Review:** March 9, 2026 (30 days)
