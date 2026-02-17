# Observability Implementation Guide

This guide provides step-by-step instructions to implement the recommendations from the [Observability Audit Report](./OBSERVABILITY_AUDIT.md).

---

## Quick Start: Add Prometheus + Grafana (30 minutes)

### Step 1: Install Dependencies

```bash
# Install prometheus-client in your Python environment
pip install prometheus-client>=0.19.0

# Or update from pyproject.toml (already updated)
pip install -e .
```

### Step 2: Start Observability Stack

```bash
# Start Prometheus and Grafana alongside existing services
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Verify services are running
docker-compose ps
```

### Step 3: Enable Metrics in Application

Add to `src/ui/main.py` at the top of the `main()` function:

```python
def main() -> None:
    """Main application entry point."""
    # Load configuration
    config = get_config()

    logger.info("Starting Agent Zero UI")
    
    # ↓ ADD THIS BLOCK
    # Start Prometheus metrics server
    from src.observability import start_metrics_server, METRICS_AVAILABLE
    
    if METRICS_AVAILABLE:
        try:
            start_metrics_server(port=9091)
            logger.info("Metrics server initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")
    else:
        logger.warning("Prometheus metrics not available - install prometheus-client")
    # ↑ END ADD
    
    # ... rest of main() function
```

### Step 4: Access Dashboards

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3001 (login: admin/admin)
- **Metrics Endpoint:** http://localhost:9091/metrics

---

## Step-by-Step: Instrument Your Code

### 1. Track Request Latency (Decorator Pattern)

```python
# Example: src/ui/tools/chat.py
from src.observability import track_request_latency

@track_request_latency('chat')
def process_chat_request(message: str) -> str:
    """Process chat request with automatic metrics tracking."""
    # Your existing code
    return response
```

### 2. Track RAG Retrieval Metrics

```python
# Example: src/core/retrieval.py
from src.observability import track_retrieval
import time

def retrieve_relevant_docs(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
    start = time.time()
    
    # Your existing retrieval logic
    results = self._hybrid_search(query, top_k)
    
    # Track metrics
    duration = time.time() - start
    track_retrieval(
        retrieval_type='hybrid',
        document_count=len(results),
        duration_seconds=duration
    )
    
    return results
```

### 3. Track LLM Generation

```python
# Example: src/core/agent.py
from src.observability import track_llm_generation
import time

def _invoke_llm(self, prompt: str) -> str:
    start = time.time()
    
    # Your existing LLM call
    response = self.ollama_client.generate(...)
    
    # Track metrics
    duration = time.time() - start
    track_llm_generation(
        model=self.config.model_name,
        input_tokens=len(prompt.split()),  # Approximate, use actual token count if available
        output_tokens=len(response.split()),
        duration_seconds=duration
    )
    
    return response
```

### 4. Track Document Ingestion

```python
# Example: src/core/ingest.py
from src.observability import track_document_ingestion
import time

def ingest_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> IngestionResult:
    start = time.time()
    
    # Your existing ingestion logic
    result = self._process_document(pdf_bytes, filename)
    
    # Track metrics
    duration = time.time() - start
    status = 'success' if result.success_count > 0 else 'failed'
    track_document_ingestion(
        status=status,
        chunk_count=result.success_count,
        duration_seconds=duration
    )
    
    return result
```

### 5. Track Database Collection Sizes

```python
# Example: Add to src/services/health_check.py or a periodic task

from src.observability import update_collection_sizes

def update_metrics():
    """Update database size metrics periodically."""
    # Get collection sizes from your database clients
    qdrant_size = qdrant_client.get_collection_info("documents").points_count
    meilisearch_size = meilisearch_client.get_index("documents").get_stats()["numberOfDocuments"]
    
    # Update metrics
    update_collection_sizes(
        qdrant_collection="documents",
        qdrant_size=qdrant_size,
        meilisearch_index="documents",
        meilisearch_size=meilisearch_size
    )
```

---

## Advanced: Create Custom Metrics

### Define New Metric

```python
# src/observability/metrics.py

from prometheus_client import Counter

# Add your custom metric
custom_operation_total = Counter(
    'agent_zero_custom_operation_total',
    'Description of your custom metric',
    ['label1', 'label2']
)

# Export in helper function
def track_custom_operation(label1_value: str, label2_value: str) -> None:
    """Track custom operation."""
    custom_operation_total.labels(label1=label1_value, label2=label2_value).inc()
```

### Use in Code

```python
from src.observability.metrics import track_custom_operation

def my_function():
    # Your logic
    track_custom_operation('value1', 'value2')
```

---

## Grafana Dashboard Setup

### 1. Import Dashboard

1. Open Grafana: http://localhost:3001
2. Login: admin/admin
3. Navigate to **Dashboards** → **Browse**
4. The "Agent Zero - Observability Dashboard" should be auto-provisioned
5. If not, manually import: **Dashboards** → **Import** → Upload `/config/grafana/dashboards/agent-zero.json`

### 2. Customize Panels

- Click **Edit** on any panel
- Modify queries, visualization type, thresholds
- Click **Apply** and **Save dashboard**

### 3. Create Alerts

```yaml
# Example: High error rate alert
groups:
  - name: agent_zero_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(agent_zero_requests_total{status="error"}[5m]))
            /
            sum(rate(agent_zero_requests_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 10%)"
```

Save to `config/prometheus/rules/alerts.yml` and update `prometheus.yml`:

```yaml
rule_files:
  - 'rules/*.yml'
```

---

## Testing Your Metrics

### 1. Generate Load

```bash
# Use the application normally, or use a load testing tool
# Example: Send multiple chat requests

for i in {1..10}; do
    curl -X POST http://localhost:8501/api/chat \
         -H "Content-Type: application/json" \
         -d '{"message": "What is RAG?"}'
done
```

### 2. Query Prometheus

```promql
# Request rate
rate(agent_zero_requests_total[5m])

# p95 latency
histogram_quantile(0.95, rate(agent_zero_request_duration_seconds_bucket[5m]))

# Error rate percentage
(sum(rate(agent_zero_requests_total{status="error"}[5m])) / sum(rate(agent_zero_requests_total[5m]))) * 100
```

### 3. View in Grafana

- Navigate to the Agent Zero dashboard
- Charts should populate with data
- Use time range selector to adjust view

---

## Troubleshooting

### Metrics Server Won't Start

**Error:** `OSError: [Errno 98] Address already in use`

**Solution:** Port 9091 is in use. Either:
1. Stop the conflicting service: `lsof -ti:9091 | xargs kill -9`
2. Change the port in `main.py`: `start_metrics_server(port=9092)`

### Grafana Shows "No Data"

**Check:**
1. Is Prometheus running? `curl http://localhost:9090/-/healthy`
2. Is Prometheus scraping the app? Check **Status** → **Targets** in Prometheus UI
3. Are metrics being generated? `curl http://localhost:9091/metrics`

**Fix:**
- Ensure app-agent service exposes port 9091 in `docker-compose.yml`:
  ```yaml
  ports:
    - "8501:8501"
    - "9091:9091"  # ← Add this
  ```

### Metrics Not Appearing in Prometheus

**Check:**
1. Verify metrics endpoint: `curl http://localhost:9091/metrics | grep agent_zero`
2. Check Prometheus targets: http://localhost:9090/targets
   - Should show `app-agent:9091` with state **UP**

**Fix:**
- Restart Prometheus: `docker-compose restart prometheus`
- Check `config/prometheus.yml` syntax
- Verify network connectivity: `docker exec agent-zero-app curl http://prometheus:9090/-/healthy`

---

## Production Considerations

### 1. Expose Metrics Securely

**Do NOT expose metrics port to public internet!**

Use one of these approaches:

**Option A: Internal network only**
```yaml
# docker-compose.yml
services:
  app-agent:
    expose:
      - "9091"  # Internal only, not published to host
```

**Option B: Authentication**
```python
# Add basic auth to metrics server
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Wrap with authentication middleware
```

### 2. Metrics Retention

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s

# Adjust retention in docker-compose.observability.yml
command:
  - '--storage.tsdb.retention.time=90d'  # Keep 90 days of data
```

### 3. High Cardinality Warning

**Avoid high-cardinality labels!**

❌ Bad (unbounded values):
```python
requests_total.labels(user_id=user_id, query=query).inc()
```

✅ Good (bounded values):
```python
requests_total.labels(endpoint='chat', status='success').inc()
```

---

## Next Steps

1. **Enable Feature Flags** (in `src/config.py`):
   ```python
   show_langfuse_dashboard: bool = True  # Enable by default in development
   show_system_health: bool = True
   ```

2. **Add Request ID Tracking** (see Audit Report, Section: Logging → Action Items)

3. **Set Up Alerting** (Prometheus Alertmanager + PagerDuty/Slack)

4. **Create Team Dashboard** (Share Grafana dashboard URL with team)

5. **Document Metrics** (Add descriptions to all custom metrics)

---

## Resources

- **Prometheus Documentation:** https://prometheus.io/docs/
- **Grafana Documentation:** https://grafana.com/docs/
- **Prometheus Client (Python):** https://github.com/prometheus/client_python
- **PromQL Tutorial:** https://prometheus.io/docs/prometheus/latest/querying/basics/

---

**Questions?** Check the [Observability Audit Report](./OBSERVABILITY_AUDIT.md) for detailed analysis and recommendations.
