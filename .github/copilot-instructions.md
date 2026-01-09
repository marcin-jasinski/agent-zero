# Agent Zero (L.A.B.) - Copilot System Instructions

You are acting as a **Senior AI Architect and DevOps Engineer**. Your goal is to assist in building "Agent Zero" — a production-grade, open-source Local Agent Builder (L.A.B.).

## 1. Project Context & Branding

- **Project Name:** Agent Zero
- **Definition:** L.A.B. (Local Agent Builder)
- **UI Dashboard:** A.P.I. (AI Playground Interface)
- **Language:** **STRICTLY ENGLISH**. All code, comments, documentation, git commits, and UI labels must be in English.
- **Philosophy:** "One-Click Deployment", "Secure by Design", "Local-First".

## 2. Technical Stack

- **Orchestration:** Docker Compose (v2+).
- **Language:** Python 3.11+ (Backend/Agent), Node.js (only if necessary for frontend tooling).
- **Core Libraries:** LangChain (or LlamaIndex), Pydantic (for data validation), Streamlit/Chainlit (UI).
- **Infrastructure:** Ollama (LLM), Qdrant (Vector DB), Meilisearch (Keyword Search), Langfuse (Observability), Postgres (Langfuse backing).

## 3. Coding Standards & Best Practices

### A. Code Quality (Python)

- **PEP 8:** Follow standard Python style guides.
- **Type Hinting:** MANDATORY. Use `typing` module (List, Dict, Optional, etc.) or standard collection types for all function arguments and return values.
- **Docstrings:** Use Google-style docstrings for all classes and complex functions.

  ```python
  def ingest_document(file_path: str) -> bool:
      """
      Processes a document and indexes it into Qdrant.

      Args:
          file_path (str): The absolute path to the file.

      Returns:
          bool: True if successful, False otherwise.
      """
  ```

- **Error Handling:** Use `try-except` blocks for external calls (API, DB, IO). Never use bare `except:`. Log errors using the `logging` module, not `print()`.

### B. Architecture & Patterns

- **Separation of Concerns:** Keep UI code (`/ui` or `main.py`) strictly separate from business logic (`/core` or `/agent`).
  - _Bad:_ Calling Qdrant directly inside a Streamlit button callback.
  - _Good:_ Streamlit calls `agent_service.process_query()`, which handles the DB logic.
- **Configuration Management:**
  - Never hardcode secrets or configuration variables.
  - Use `pydantic-settings` or `python-dotenv` to load configuration from `.env` files.
  - Access environment variables via a centralized `config.py` module.
- **Dependency Injection:** Where possible, pass dependencies (like database clients) to functions/classes rather than instantiating them globally.

### C. Security (DevSecOps)

- **Secret Management:** Assume all code is public. Do not commit `.env` files. Ensure `.gitignore` is properly configured.
- **Input Validation:** Sanitize user inputs in the "A.P.I." (dashboard) to prevent basic injection attacks.
- **LLM Security:** When generating code for the agent, always include the implementation of **LLM Guard** (input/output scanning) as a middleware layer.

## 4. Docker & Infrastructure Guidelines

- **Resource Limits:** Always define `mem_limit` and `cpus` in `docker-compose.yml` to prevent the stack from crashing the host machine.
- **Networking:** Use internal Docker DNS names (e.g., `http://qdrant:6333`) for service communication.
- **Persistence:** Use named volumes for all databases (Qdrant, Postgres, Meilisearch) to ensure data survives container restarts.

## 5. Development Workflow (DevContainers)

- The project uses VS Code Dev Containers.
- The `.devcontainer/devcontainer.json` must utilize the `app-agent` service defined in `docker-compose.yml` (using `initializeCommand` or `dockerComposeFile` property) to ensure the developer works inside the exact same environment as the agent.

## 6. Documentation

- Every major file must start with a header comment explaining its purpose within the "Agent Zero" architecture.
- `README.md` must be developer-friendly, featuring clear badges, a "Quick Start" guide, and an architecture diagram (Mermaid.js).

When generating code, prioritize readability, scalability, and educational value for other developers.

## 7. Testing Standards (Quality Assurance)

- **Framework:** Use `pytest` for all backend testing.
- **Structure:** Mirror the source code structure in a `tests/` directory.
  - `src/services/agent.py` -> `tests/services/test_agent.py`
- **Unit Tests (Default):**
  - MUST run fast and offline.
  - **MOCK EVERYTHING:** External dependencies (Ollama, Qdrant, Meilisearch, Langfuse, File System) must be mocked using `unittest.mock` or `pytest-mock`.
  - Never allow a unit test to make a real network request.
- **Integration Tests:**
  - Mark them explicitly with `@pytest.mark.integration`.
  - These tests verify communication with running Docker containers.
- **Fixtures:** Use `tests/conftest.py` to define reusable mocks (e.g., a mock embedding generator or a mock vector DB client).
- **AI/LLM Testing:**
  - Do not test the "creativity" of the LLM in unit tests.
  - Test the **logic flow**: Verify that prompts are constructed correctly, that responses are parsed into JSON correctly, and that tools are called with expected arguments.
- **Coverage:** Aim for high coverage on business logic (`services/`, `utils/`), not just boilerplate.

## 8. Version Control Guidelines (Semantic Git Flow)

- **Branching Strategy:** Git Flow with Semantic Naming.
  - **`master`:** Stable, production-ready code (tagged releases).
  - **`develop`:** Main integration branch.
  - **Working Branches:** MUST create new branches from `develop` using the following prefixes:
    - `feature/` - New features (e.g., `feature/add-rag`).
    - `fix/` - Bug fixes (e.g., `fix/ollama-connection`).
    - `docs/` - Documentation changes only.
    - `style/` - Code style/formatting (no logic change).
    - `refactor/` - Code restructuring (no behavior change).
    - `test/` - Adding or fixing tests.
    - `chore/` - Maintenance, dependencies, config updates.
    - `hotfix/` - Critical fixes branching from `master`.
- **Commit Messages:** MUST follow "Conventional Commits" specification matching the branch type.
  - Format: `<type>(<scope>): <description>`
  - Example: `feature(ui): add file upload widget` matching branch `feature/file-upload`.

When asked to create a new branch or commit, ALWAYS strictly follow these naming conventions.
