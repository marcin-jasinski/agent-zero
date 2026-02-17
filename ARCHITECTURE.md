# Agent Zero Architecture

## Overview

Agent Zero follows a local-first, single-user architecture centered on a Chainlit-based A.P.I. interface and Python service orchestration.

## Runtime Components

- A.P.I. UI: Chainlit app in `src/ui/main.py` (port 8501)
- Agent orchestration: `src/core/agent.py`
- Retrieval engine: `src/core/retrieval.py`
- Ingestion pipeline: `src/core/ingest.py`
- Vector storage: Qdrant (port 6333)
- Keyword search: Meilisearch (port 7700)
- LLM inference: Ollama (port 11434)
- Observability: Langfuse + Prometheus + Grafana

## Layered Design

- UI layer (`src/ui`): chat handlers, upload handling, admin actions
- Core layer (`src/core`): conversation flow, ingestion, retrieval, memory
- Services layer (`src/services`): external clients (Ollama, Qdrant, Meilisearch, health)
- Security layer (`src/security`): LLM Guard input/output scanning
- Observability layer (`src/observability`): tracing and metrics instrumentation

## Request Flow

1. User sends a message in Chainlit.
2. `src/ui/main.py` resolves session agent and conversation context.
3. Agent processes input, applies guardrails, and retrieves supporting chunks.
4. Ollama generates a response through orchestrator logic.
5. Response is formatted with source context and returned to Chainlit.
6. Metrics/traces are emitted to observability backends.

## Document Ingestion Flow

1. User uploads `pdf`, `txt`, or `md` file in Chainlit.
2. UI triggers async ingestion path.
3. Ingestor extracts/chunks content and generates embeddings.
4. Chunks are indexed in Qdrant and Meilisearch.
5. Indexed content becomes available for subsequent retrieval.

## Session Management

Chainlit `user_session` stores per-conversation runtime objects:

- `agent`: `AgentOrchestrator` instance
- `conversation_id`: active conversation key
- `ingestor`: lazily initialized `DocumentIngestor`
- `agent_initialized`: readiness flag

## Deployment Topology

Docker Compose is the canonical runtime topology for local development. The `app-agent` service hosts the Chainlit UI and internal Python orchestration code, while data and model services run as sibling containers on the same internal network.

## Security Notes

- LLM Guard remains enabled/disabled by configuration in `src/config.py`
- Input/output length and scanning controls are centrally configured
- Design assumes local trusted execution only (not public internet exposure)
