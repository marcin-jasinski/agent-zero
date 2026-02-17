# Observability Stack Testing Guide

## Quick Start (5 Minutes)

### 1. Build and Start Services

```powershell
# Clean previous state
docker-compose down -v

# Rebuild with new dependencies
docker-compose build app-agent

# Start all services (including Prometheus + Grafana)
docker-compose up -d

# Monitor startup logs
docker-compose logs -f app-agent
```

### 2. Verify Metrics Endpoint

**Check metrics are being exported:**

```powershell
curl http://localhost:9091/metrics | Select-String "agent_zero"
```

**Expected output (sample):**
```
# HELP agent_zero_requests_total Total number of requests
# TYPE agent_zero_requests_total counter
agent_zero_requests_total{endpoint="/",status="success"} 42.0

# HELP agent_zero_retrieval_documents_count Documents retrieved per operation
# TYPE agent_zero_retrieval_documents_count histogram
agent_zero_retrieval_documents_count_bucket{retrieval_type="semantic",le="5.0"} 3.0
...
```

### 3. Verify Prometheus Scraping

**Check Prometheus is collecting metrics:**

1. Open: http://localhost:9090/targets
2. Find target: `agent-zero-app (app-agent:9091)`
3. Status should be: **UP** (green)
4. Last scrape: < 15 seconds ago

**Query metrics in Prometheus UI:**
```
# Go to http://localhost:9090/graph
# Run query:
rate(agent_zero_requests_total[5m])
```

### 4. Verify Grafana Dashboard

**Access Grafana:**

1. Open: http://localhost:3001
2. Login: `admin` / `admin` (skip password change)
3. Navigate: **Dashboards** → **Agent Zero - Observability**

**Expected panels:**
- Request Rate (requests/minute)
- Request Latency (p95, p99)
- Document Retrieval Count
- LLM Token Usage (input/output)
- Error Rate (5m window)

### 5. Generate Test Data

**Trigger metrics collection:**

```powershell
# 1. Open Agent Zero UI
Start-Process "http://localhost:8501"

# 2. Upload a test document (Knowledge Base tab)
# Use: data/samples/rag_introduction.md

# 3. Send test queries (Chat tab)
# Example: "What is RAG?"
# Example: "Explain vector databases"

# 4. Wait 30 seconds for metrics aggregation
Start-Sleep -Seconds 30
```

**Check dashboard updates:**
- Refresh Grafana dashboard (http://localhost:3001)
- Verify metrics appear in panels
- Check retrieval count increased
- Check LLM token usage recorded

## Detailed Validation

### Metrics Coverage Check

**Verify all metric types are exported:**

```powershell
# Counter metrics (totals)
curl http://localhost:9091/metrics | Select-String "agent_zero_requests_total"
curl http://localhost:9091/metrics | Select-String "agent_zero_documents_ingested_total"
curl http://localhost:9091/metrics | Select-String "agent_zero_llm_tokens_total"

# Histogram metrics (distributions)
curl http://localhost:9091/metrics | Select-String "agent_zero_request_duration_seconds"
curl http://localhost:9091/metrics | Select-String "agent_zero_retrieval_documents_count"
curl http://localhost:9091/metrics | Select-String "agent_zero_embedding_duration_seconds"

# Gauge metrics (current state)
curl http://localhost:9091/metrics | Select-String "agent_zero_active_requests"
curl http://localhost:9091/metrics | Select-String "agent_zero_collection_size"
```

### Service Health Check

**Test health check endpoints:**

```powershell
# Agent Zero health (includes all services)
curl http://localhost:8501/health | ConvertFrom-Json

# Prometheus health
curl http://localhost:9090/-/healthy

# Grafana health
curl http://localhost:3001/api/health | ConvertFrom-Json
```

**Expected response (app health):**
```json
{
  "status": "healthy",
  "services": {
    "ollama": {"is_healthy": true, "message": "LLM inference service is operational"},
    "qdrant": {"is_healthy": true, "message": "Vector database is operational"},
    "meilisearch": {"is_healthy": true, "message": "Full-text search engine is operational"},
    "langfuse": {"is_healthy": true, "message": "Observability service is operational"},
    "prometheus": {"is_healthy": true, "message": "Metrics service is operational"},
    "grafana": {"is_healthy": true, "message": "Visualization service is operational"}
  }
}
```

### Dashboard Feature Flags

**Verify dashboards are visible by default:**

1. Open Agent Zero UI: http://localhost:8501
2. Check sidebar navigation includes:
   - ✅ **Chat** (core)
   - ✅ **Knowledge Base** (core)
   - ✅ **Langfuse Dashboard** (enabled by default)
   - ✅ **System Health** (enabled by default, shows Prometheus + Grafana)
   - ✅ **Promptfoo** (enabled by default)
   - ✅ **Settings** (core)
   - ✅ **Logs** (core)

### Prometheus Configuration

**Verify scrape targets:**

```powershell
# Check Prometheus config is loaded correctly
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml
```

**Expected scrape jobs:**
```yaml
scrape_configs:
  - job_name: 'agent-zero-app'
    static_configs:
      - targets: ['app-agent:9091']
    scrape_interval: 10s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Provisioning

**Verify datasource auto-provisioned:**

```powershell
# Check Grafana recognizes Prometheus
docker-compose exec grafana curl -u admin:admin http://localhost:3000/api/datasources | ConvertFrom-Json
```

**Expected datasource:**
```json
[
  {
    "id": 1,
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "isDefault": true
  }
]
```

**Verify dashboard auto-loaded:**

```powershell
# List dashboards
docker-compose exec grafana curl -u admin:admin http://localhost:3000/api/search?type=dash-db | ConvertFrom-Json
```

**Expected dashboard:**
```json
[
  {
    "id": 1,
    "uid": "agent-zero-observability",
    "title": "Agent Zero - Observability",
    "uri": "db/agent-zero-observability",
    "type": "dash-db"
  }
]
```

## Troubleshooting

### Issue: Metrics endpoint not responding (port 9091)

**Diagnosis:**
```powershell
# Check if metrics server started
docker-compose logs app-agent | Select-String "metrics server"

# Check port binding
docker-compose ps app-agent
```

**Expected log:**
```
INFO - Prometheus metrics server started on port 9091
```

**Solution:**
- Ensure `prometheus-client>=0.19.0` is installed
- Rebuild container: `docker-compose build app-agent`
- Check for port conflicts: `netstat -an | Select-String "9091"`

### Issue: Prometheus shows target DOWN

**Diagnosis:**
```powershell
# Check Prometheus logs
docker-compose logs prometheus | Select-String "error"

# Check network connectivity
docker-compose exec prometheus wget -O- http://app-agent:9091/metrics
```

**Solution:**
- Verify app-agent service started: `docker-compose ps app-agent`
- Check depends_on in docker-compose.yml includes prometheus
- Restart services: `docker-compose restart prometheus app-agent`

### Issue: Grafana dashboard shows "No Data"

**Diagnosis:**
```powershell
# Check datasource connection
docker-compose exec grafana curl -u admin:admin http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up
```

**Expected response:**
```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [...]
  }
}
```

**Solution:**
- Wait 2-3 minutes for initial data collection
- Generate test data (upload document, send queries)
- Check Prometheus is scraping: http://localhost:9090/targets
- Verify metrics exist: http://localhost:9091/metrics

### Issue: Missing prometheus-client dependency

**Diagnosis:**
```powershell
# Check if library installed
docker-compose exec app-agent python -c "import prometheus_client; print('OK')"
```

**Solution:**
```powershell
# Install dependency
docker-compose exec app-agent pip install prometheus-client>=0.19.0

# Or rebuild container (permanent fix)
docker-compose build app-agent
docker-compose up -d
```

### Issue: Services not starting in correct order

**Diagnosis:**
```powershell
# Check startup sequence
docker-compose logs --tail=50 | Select-String "started|ready"
```

**Expected order:**
1. postgres (Langfuse DB)
2. qdrant, meilisearch, ollama (core services)
3. langfuse (depends on postgres)
4. prometheus (independent)
5. grafana (depends on prometheus)
6. app-agent (depends on all)

**Solution:**
- Check `depends_on` clauses in docker-compose.yml
- Use `docker-compose down -v && docker-compose up -d` for clean start

## Performance Validation

### Metrics Collection Overhead

**Test impact on application performance:**

```powershell
# 1. Measure latency WITH metrics enabled
# Send 10 queries, note average response time

# 2. Disable metrics (set METRICS_AVAILABLE=False)
docker-compose exec app-agent sh -c 'echo "METRICS_AVAILABLE=False" >> .env'
docker-compose restart app-agent

# 3. Measure latency WITHOUT metrics
# Send 10 queries, note average response time

# Expected overhead: < 5ms per request
```

### Resource Usage

**Monitor container resource consumption:**

```powershell
# Check CPU and memory usage
docker stats --no-stream prometheus grafana app-agent
```

**Expected resource usage (idle):**
- Prometheus: ~50MB RAM, <1% CPU
- Grafana: ~80MB RAM, <1% CPU  
- app-agent: +10MB RAM (metrics overhead)

**Expected resource usage (under load):**
- Prometheus: ~100MB RAM, 5-10% CPU
- Grafana: ~120MB RAM, 2-5% CPU

## Integration Testing

### End-to-End Workflow Test

**Complete user journey with metrics tracking:**

```powershell
# 1. Start fresh stack
docker-compose down -v
docker-compose up -d
Start-Sleep -Seconds 60  # Wait for startup

# 2. Upload document
# UI: http://localhost:8501 → Knowledge Base → Upload data/samples/rag_introduction.md

# 3. Verify ingestion metrics
curl http://localhost:9091/metrics | Select-String "documents_ingested_total"

# Expected: agent_zero_documents_ingested_total{status="success"} 1.0

# 4. Send query
# UI: Chat → "What is RAG?"

# 5. Verify retrieval metrics
curl http://localhost:9091/metrics | Select-String "retrieval_documents_count"

# Expected: agent_zero_retrieval_documents_count_bucket{retrieval_type="hybrid",...} > 0

# 6. Verify LLM metrics
curl http://localhost:9091/metrics | Select-String "llm_tokens_total"

# Expected: agent_zero_llm_tokens_total{model="ministral-3:3b",token_type="input"} > 0

# 7. Check Grafana dashboard
# UI: http://localhost:3001 → Agent Zero dashboard
# Verify all panels show data
```

## Success Criteria

✅ **Deployment:**
- All 8 services start successfully (ollama, qdrant, meilisearch, postgres, langfuse, prometheus, grafana, app-agent)
- No error logs during startup
- Health checks pass for all services

✅ **Metrics:**
- Endpoint http://localhost:9091/metrics responds
- Prometheus scrapes successfully (target UP)
- All metric types present (counter, histogram, gauge)

✅ **Visualization:**
- Grafana accessible at http://localhost:3001
- Agent Zero dashboard loaded automatically
- Panels display data after test queries

✅ **Integration:**
- Dashboard links visible in UI sidebar (Langfuse, System Health)
- Service health page shows Prometheus + Grafana status
- Metrics update in real-time during usage

✅ **Performance:**
- Metrics overhead < 5ms per request
- Prometheus memory < 150MB
- Grafana memory < 150MB

## Next Steps

After successful validation:

1. **Customize Grafana Dashboard:**
   - Edit `config/grafana/dashboards/agent-zero.json`
   - Add custom panels for your use case
   - Reload: `docker-compose restart grafana`

2. **Add Custom Metrics:**
   - Edit `src/observability/metrics.py`
   - Define new metrics (counters, gauges, histograms)
   - Use in your code: `track_my_custom_metric()`

3. **Configure Alerts:**
   - Add alert rules to `config/prometheus/alert_rules.yml`
   - Configure notification channels in Grafana
   - Test alert firing conditions

4. **Production Hardening:**
   - Change Grafana default password
   - Enable Prometheus authentication
   - Configure data retention policies
   - Set up backup for metrics data

5. **Extend Observability:**
   - Add cAdvisor for container metrics
   - Enable Ollama Prometheus exporter
   - Collect Qdrant internal metrics
   - Integrate with external APM tools
