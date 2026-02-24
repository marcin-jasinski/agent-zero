# Agent Zero Architecture

## Overview

Agent Zero follows a local-first, single-user architecture centered on a FastAPI + Gradio A.P.I. interface and Python service orchestration.

## Runtime Components

- A.P.I. UI: FastAPI + Gradio app in `src/ui/app.py` (port 8501 — Chat tab + Admin tab)
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

1. User sends a message in the Gradio Chat tab.
2. `src/ui/chat.py:respond()` resolves session state and conversation context.
3. Agent processes input, applies guardrails, and retrieves supporting chunks.
4. Ollama generates a response through orchestrator logic.
5. Response is streamed back to the Gradio Chatbot component.
6. Metrics/traces are emitted to observability backends.

## Document Ingestion Flow

1. User uploads `pdf`, `txt`, or `md` file in the Gradio Chat tab.
2. UI triggers async ingestion path.
3. Ingestor extracts/chunks content and generates embeddings.
4. Chunks are indexed in Qdrant and Meilisearch.
5. Indexed content becomes available for subsequent retrieval.

## Session Management

Gradio `gr.State` stores per-browser-tab runtime objects:

- `agent`: `AgentOrchestrator` instance
- `conversation_id`: active conversation key
- `ollama`, `qdrant`, `meilisearch`: service client references

The state is populated by `initialize_agent()` which is wired to the Gradio `blocks.load` event.

## Deployment Topology

Docker Compose is the canonical runtime topology for local development. The `app-agent` service runs `uvicorn src.ui.app:api --port 8501` which serves both the Gradio UI and the FastAPI REST layer, while data and model services run as sibling containers on the same internal network.

## Security Notes

- LLM Guard remains enabled/disabled by configuration in `src/config.py`
- Input/output length and scanning controls are centrally configured
- Design assumes local trusted execution only (not public internet exposure)
