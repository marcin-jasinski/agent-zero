# Code Review - Critical Issues Found

## Summary

Comprehensive code review identified **multiple critical issues** with method calls that don't exist in the actual service clients. The root cause is that the core modules (agent.py, retrieval.py, ingest.py) call non-existent methods on the service clients.

## Issues Found

### 1. **CRITICAL: agent.py - Line 296 - Non-existent `chat()` method**

- **File:** `src/core/agent.py`
- **Method:** `_invoke_llm()`
- **Issue:** Calls `self.ollama_client.chat()` which doesn't exist
- **Actual method:** `OllamaClient.generate()`
- **Fix:** Replace chat() call with generate() call

### 2. **CRITICAL: agent.py - Uses non-existent chat interface**

- **File:** `src/core/agent.py`
- **Lines:** 296-317
- **Issue:** Uses message list and chat model interface that OllamaClient doesn't support
- **Context:** OllamaClient only supports:
  - `generate(model, prompt, system, temperature, top_p, max_tokens)` -> str
  - NOT: `chat(messages=[{role, content}], model, stream)` -> dict/str
- **Fix:** Refactor to use generate() API

### 3. **CRITICAL: retrieval.py - Line 94 - Non-existent `generate_embedding()` method**

- **File:** `src/core/retrieval.py`
- **Method:** `_semantic_search()`
- **Issue:** Calls `self.ollama_client.generate_embedding()`
- **Actual method:** `OllamaClient.embed()`
- **Fix:** Replace generate_embedding() with embed()

### 4. **CRITICAL: retrieval.py - Line 97 - Non-existent `search_vectors()` method**

- **File:** `src/core/retrieval.py`
- **Method:** `_semantic_search()`
- **Issue:** Calls `self.qdrant_client.search_vectors()`
- **Actual method:** `QdrantVectorClient.search()`
- **Fix:** Replace search_vectors() with search()
- **Note:** Also requires using QdrantVectorClient not QdrantClient

### 5. **CRITICAL: retrieval.py - Line 137 - Method signature mismatch**

- **File:** `src/core/retrieval.py`
- **Method:** `_keyword_search()`
- **Issue:** Calls `self.meilisearch_client.search(query=query, limit=top_k)`
- **Problem:** Missing required `index_uid` parameter
- **Actual signature:** `search(index_uid: str, query: str, limit: int)`
- **Fix:** Add index_uid parameter from config

### 6. **CRITICAL: retrieval.py - Line 294 - Same search_vectors() issue**

- **File:** `src/core/retrieval.py`
- **Method:** `search_with_context()`
- **Issue:** Calls `self.qdrant_client.search_vectors()` which doesn't exist
- **Fix:** Replace with search() method

### 7. **CRITICAL: ingest.py - Line 366 - Non-existent `generate_embedding()` method**

- **File:** `src/core/ingest.py`
- **Method:** `_process_chunks()`
- **Issue:** Calls `self.ollama_client.generate_embedding()`
- **Actual method:** `OllamaClient.embed()`
- **Fix:** Replace generate_embedding() with embed()

### 8. **CRITICAL: ingest.py - Import error**

- **File:** `src/core/ingest.py`
- **Line:** 21
- **Issue:** Imports `QdrantClient` but actual class is `QdrantVectorClient`
- **Fix:** Change import to `from src.services.qdrant_client import QdrantVectorClient`

### 9. **CRITICAL: ingest.py - Parameter type mismatch**

- **File:** `src/core/ingest.py`
- **Line:** 37
- **Issue:** Type hint says `qdrant_client: QdrantClient` but should be `QdrantVectorClient`
- **Fix:** Update type hint

## Service Client API Reference

### OllamaClient Available Methods:

- `__init__(base_url, timeout)`
- `is_healthy() -> bool`
- `list_models() -> list[str]`
- `generate(model, prompt, system, temperature, top_p, max_tokens) -> str` ✅ USE THIS
- `embed(text, model) -> list[float]` ✅ USE THIS
- `pull_model(model) -> bool`
- `_make_request()` (private)

### QdrantVectorClient Available Methods:

- `__init__(host, port)`
- `is_healthy() -> bool`
- `create_collection(collection_name, vector_size, force_recreate) -> bool`
- `upsert_vectors(collection_name, points) -> bool`
- `search(collection_name, query_vector, limit, score_threshold) -> list[dict]` ✅ USE THIS (NOT search_vectors)
- `delete_collection(collection_name) -> bool`
- `get_collection_info(collection_name) -> dict`

### MeilisearchClient Available Methods:

- `__init__(host, port, api_key)`
- `is_healthy() -> bool`
- `create_index(index_uid, primary_key) -> bool`
- `add_documents(index_uid, documents, primary_key) -> bool`
- `search(index_uid, query, limit) -> list[dict]` ✅ REQUIRES index_uid parameter
- `delete_index(index_uid) -> bool`
- `get_index_stats(index_uid) -> dict`
- `list_indexes() -> list[str]`

## Test Impact

Tests are also mocking non-existent methods:

- `test_agent.py`: Mocks `ollama_client.chat` (doesn't exist)
- `test_retrieval.py`: Mocks `ollama_client.generate_embedding` and `qdrant_client.search_vectors`
- `test_ingest.py`: Mocks `ollama_client.generate_embedding`
- These tests will need to be updated to mock the actual methods

## Files Affected

1. `src/core/agent.py` - \_invoke_llm() method
2. `src/core/retrieval.py` - \_semantic_search(), \_keyword_search(), search_with_context()
3. `src/core/ingest.py` - imports and \_process_chunks()
4. `tests/core/test_agent.py` - Mock calls
5. `tests/core/test_retrieval.py` - Mock calls
6. `tests/core/test_ingest.py` - Mock calls

## Priority Order for Fixes

1. Fix OllamaClient method calls (agent.py, retrieval.py, ingest.py)
2. Fix QdrantVectorClient method calls and imports
3. Fix MeilisearchClient method calls (add index_uid)
4. Update all test mocks
5. Run full test suite to validate
