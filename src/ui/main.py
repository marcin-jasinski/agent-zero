"""Agent Zero (L.A.B.) - Main Chainlit Application Entry Point.

This is the A.P.I. (AI Playground Interface) - the web-based dashboard
for Agent Zero, the Local Agent Builder.

Phase 6b: Migrated from Streamlit to Chainlit for production-grade async architecture.
Step 24: Full agent integration with async message processing.
"""

import asyncio
import inspect
import shlex
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to Python path for module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import chainlit as cl

from src.config import get_config
from src.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

logger.info("Starting Agent Zero UI (Chainlit)")


SERVICE_LOGGER_PATTERNS = {
    "ALL": [],
    "OLLAMA": ["ollama_client", "ollama", "OllamaClient"],
    "QDRANT": ["qdrant_client", "qdrant", "QdrantVectorClient"],
    "MEILISEARCH": ["meilisearch_client", "meilisearch", "MeilisearchClient"],
    "LANGFUSE": ["langfuse_client", "langfuse", "observability"],
    "AGENT": ["src.core.agent", "src.core.retrieval", "src.core.ingest", "src.core.memory"],
    "UI": ["src.ui", "chainlit", "main"],
}


def _tail_logs(lines: int = 50, level: str = "ALL", service: str = "ALL") -> str:
    """Read and filter application logs similarly to the legacy dashboard.

    Args:
        lines: Number of lines to return from the end.
        level: Log level filter (ALL/DEBUG/INFO/WARNING/ERROR).
        service: Service filter (ALL/OLLAMA/QDRANT/MEILISEARCH/LANGFUSE/AGENT/UI).

    Returns:
        Filtered log text.
    """
    log_candidates = [
        Path(f"/app/logs/agent-zero-{config.env}.log"),
        Path(f"logs/agent-zero-{config.env}.log"),
    ]
    log_file = next((candidate for candidate in log_candidates if candidate.exists()), None)

    if not log_file:
        return "No log file found yet."

    all_lines = log_file.read_text(encoding="utf-8").splitlines()

    normalized_level = level.upper()
    if normalized_level != "ALL":
        all_lines = [line for line in all_lines if normalized_level in line.upper()]

    normalized_service = service.upper()
    if normalized_service != "ALL":
        patterns = SERVICE_LOGGER_PATTERNS.get(normalized_service, [])
        all_lines = [line for line in all_lines if any(pattern in line for pattern in patterns)]

    selected = all_lines[-max(lines, 1):] if all_lines else []
    return "\n".join(selected) if selected else "No logs matching filter."


async def _send_logs_report(lines: int = 50, level: str = "ALL", service: str = "ALL") -> None:
    """Send filtered logs report to user."""
    logs_text = await asyncio.to_thread(_tail_logs, lines, level, service)

    report = "# 📋 Application Logs\n\n"
    report += f"- **Lines**: {lines}\n"
    report += f"- **Level**: {level.upper()}\n"
    report += f"- **Service**: {service.upper()}\n"
    report += f"- **Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += "```text\n"
    report += logs_text[-12000:] if len(logs_text) > 12000 else logs_text
    report += "\n```\n\n"
    report += "Use `/logs <lines> <level> <service>` for custom filters."

    await cl.Message(content=report).send()


async def _send_langfuse_report(time_range: str = "24h") -> None:
    """Send Langfuse observability summary and recent traces."""
    from src.services.langfuse_client import LangfuseClient

    client = LangfuseClient()
    if not client.enabled:
        await cl.Message(content="⚠️ **Langfuse is disabled** in configuration.").send()
        return

    summary = await asyncio.to_thread(client.get_trace_summary, time_range)
    traces = await asyncio.to_thread(client.get_recent_traces, 10, None)

    report = "# 🔬 Langfuse Observability\n\n"
    report += f"- **Range**: {time_range}\n"
    report += f"- **Total Traces**: {summary.total_traces}\n"
    report += f"- **Last 24h**: {summary.traces_24h}\n"
    report += f"- **Avg Latency**: {summary.avg_latency_ms:.0f} ms\n"
    report += f"- **Error Rate**: {summary.error_rate:.1f}%\n\n"

    report += "## Recent Traces\n\n"
    if traces:
        for trace in traces:
            report += (
                f"- **{trace.name}** | {trace.status} | {trace.duration_ms:.0f} ms "
                f"| in/out tokens: {trace.input_tokens}/{trace.output_tokens}\n"
            )
    else:
        report += "No traces available.\n"

    report += "\n---\n[Open Langfuse Dashboard →](http://localhost:3001)"
    await cl.Message(content=report).send()


async def _send_promptfoo_report() -> None:
    """Send Promptfoo summary, scenarios, and recent runs."""
    from src.services.promptfoo_client import PromptfooClient

    client = PromptfooClient()
    summary = await asyncio.to_thread(client.get_summary_metrics)
    scenarios = await asyncio.to_thread(client.list_scenarios)
    runs = await asyncio.to_thread(client.list_runs, None, 5)

    report = "# 🧪 Promptfoo Testing Summary\n\n"
    report += f"- **Total Scenarios**: {summary.get('total_scenarios', 0)}\n"
    report += f"- **Total Runs**: {summary.get('total_runs', 0)}\n"
    report += f"- **Average Pass Rate**: {summary.get('average_pass_rate', 0.0):.1f}%\n\n"

    report += "## Scenarios\n\n"
    if scenarios:
        for scenario in scenarios[:10]:
            report += f"- **{scenario.name}** (`{scenario.id[:8]}`)\n"
    else:
        report += "No scenarios configured.\n"

    report += "\n## Recent Runs\n\n"
    if runs:
        for run in runs:
            report += (
                f"- **{run.prompt_version}** | {run.pass_rate:.1f}% pass "
                f"({run.passed_tests}/{run.total_tests})\n"
            )
    else:
        report += "No test runs yet.\n"

    report += "\nUse `/promptfoo run <version>` and `/promptfoo compare <v1> <v2>` for operations."
    await cl.Message(content=report).send()


async def _send_admin_help() -> None:
    """Send admin command help to cover legacy dashboard operations."""
    help_text = """# 🧭 Admin Commands (Legacy Dashboard Parity)

## Logs
- `/logs`
- `/logs 100 ERROR AGENT`

## Langfuse
- `/langfuse`
- `/langfuse 7d`

## Qdrant Manager
- `/qdrant list`
- `/qdrant search <query>`
- `/qdrant create <name> [vector_size] [Cosine|Euclid|Dot]`
- `/qdrant delete <name>`

## Promptfoo
- `/promptfoo summary`
- `/promptfoo scenarios`
- `/promptfoo create "<name>" "<description>" "<input_text>"`
- `/promptfoo delete <scenario_id>`
- `/promptfoo runs [limit]`
- `/promptfoo run <version>`
- `/promptfoo compare <version_a> <version_b>`
"""
    await cl.Message(content=help_text).send()


async def _try_handle_admin_command(user_message: str) -> bool:
    """Handle admin slash commands for parity with legacy Streamlit dashboards.

    Returns:
        True when message was handled as admin command.
    """
    if not user_message.startswith("/"):
        return False

    try:
        parts = shlex.split(user_message)
    except ValueError:
        await cl.Message(content="❌ Invalid command syntax.").send()
        return True

    if not parts:
        return False

    cmd = parts[0].lower()

    if cmd == "/help":
        await _send_admin_help()
        return True

    if cmd == "/logs":
        lines = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
        level = parts[2] if len(parts) > 2 else "ALL"
        service = parts[3] if len(parts) > 3 else "ALL"
        await _send_logs_report(lines, level, service)
        return True

    if cmd == "/langfuse":
        time_range = parts[1] if len(parts) > 1 else "24h"
        await _send_langfuse_report(time_range)
        return True

    if cmd == "/promptfoo":
        from src.services.promptfoo_client import PromptfooClient

        client = PromptfooClient()
        sub = parts[1].lower() if len(parts) > 1 else "summary"

        if sub == "summary":
            await _send_promptfoo_report()
            return True

        if sub == "scenarios":
            scenarios = await asyncio.to_thread(client.list_scenarios)
            content = "# 🧪 Promptfoo Scenarios\n\n"
            if scenarios:
                for scenario in scenarios:
                    content += f"- **{scenario.name}** (`{scenario.id}`)\n"
            else:
                content += "No scenarios configured.\n"
            await cl.Message(content=content).send()
            return True

        if sub == "create" and len(parts) > 4:
            scenario = await asyncio.to_thread(
                client.create_scenario,
                parts[2],
                parts[3],
                parts[4],
            )
            await cl.Message(
                content=f"✅ Scenario created: **{scenario.name}** (`{scenario.id}`)"
            ).send()
            return True

        if sub == "delete" and len(parts) > 2:
            deleted = await asyncio.to_thread(client.delete_scenario, parts[2])
            if deleted:
                await cl.Message(content=f"✅ Scenario deleted: `{parts[2]}`").send()
            else:
                await cl.Message(content=f"❌ Scenario not found: `{parts[2]}`").send()
            return True

        if sub == "runs":
            limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
            runs = await asyncio.to_thread(client.list_runs, None, limit)
            content = "# 🧪 Promptfoo Runs\n\n"
            if runs:
                for run in runs:
                    content += f"- **{run.prompt_version}** | {run.pass_rate:.1f}% | `{run.id}`\n"
            else:
                content += "No runs available.\n"
            await cl.Message(content=content).send()
            return True

        if sub == "run" and len(parts) > 2:
            version = parts[2]
            run = await asyncio.to_thread(client.run_tests, version, None, None)
            content = (
                "# ✅ Promptfoo Run Complete\n\n"
                f"- **Version**: {run.prompt_version}\n"
                f"- **Pass Rate**: {run.pass_rate:.1f}%\n"
                f"- **Passed/Total**: {run.passed_tests}/{run.total_tests}\n"
            )
            await cl.Message(content=content).send()
            return True

        if sub == "compare" and len(parts) > 3:
            comparison = await asyncio.to_thread(client.compare_versions, parts[2], parts[3])
            if not comparison:
                await cl.Message(content="❌ Could not compare versions (missing runs)." ).send()
                return True

            content = "# ⚖️ Prompt Version Comparison\n\n"
            content += f"- **A**: {comparison.version_a}\n"
            content += f"- **B**: {comparison.version_b}\n"
            content += f"- **Recommendation**: {comparison.recommendation}\n\n"
            if comparison.improvements:
                content += "## Improvements\n" + "\n".join(f"- {item}" for item in comparison.improvements) + "\n\n"
            if comparison.regressions:
                content += "## Regressions\n" + "\n".join(f"- {item}" for item in comparison.regressions)
            await cl.Message(content=content).send()
            return True

        await cl.Message(content="❌ Unknown /promptfoo command. Use `/help`.").send()
        return True

    if cmd == "/qdrant":
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient

        qdrant = QdrantVectorClient()
        sub = parts[1].lower() if len(parts) > 1 else "list"

        if sub == "list":
            collections = await asyncio.to_thread(qdrant.list_collections)
            content = "# 📊 Qdrant Collections\n\n"
            if collections:
                for collection in collections:
                    content += (
                        f"- **{collection['name']}** | vectors: {collection['vectors_count']:,} "
                        f"| points: {collection['points_count']:,}\n"
                    )
            else:
                content += "No collections found.\n"
            await cl.Message(content=content).send()
            return True

        if sub == "search" and len(parts) > 2:
            query = " ".join(parts[2:])
            ollama = OllamaClient()
            collection_name = config.qdrant.collection_name
            results = await asyncio.to_thread(
                qdrant.search_by_text,
                query,
                collection_name,
                5,
                ollama,
            )
            content = f"# 🔎 Qdrant Search Results (`{collection_name}`)\n\n"
            if results:
                for result in results:
                    snippet = result["content"][:240].replace("\n", " ")
                    content += f"- **Score {result['score']:.3f}** | {result['source']} | {snippet}\n"
            else:
                content += "No results found.\n"
            await cl.Message(content=content).send()
            return True

        if sub == "create" and len(parts) > 2:
            name = parts[2]
            vector_size = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 768
            distance = parts[4] if len(parts) > 4 else "Cosine"
            success, message = await asyncio.to_thread(qdrant.create_collection_ui, name, vector_size, distance)
            prefix = "✅" if success else "❌"
            await cl.Message(content=f"{prefix} {message}").send()
            return True

        if sub == "delete" and len(parts) > 2:
            success, message = await asyncio.to_thread(qdrant.delete_collection_ui, parts[2])
            prefix = "✅" if success else "❌"
            await cl.Message(content=f"{prefix} {message}").send()
            return True

        await cl.Message(content="❌ Unknown /qdrant command. Use `/help`.").send()
        return True

    return False


async def _initialize_agent() -> tuple[Optional[object], Optional[str], Optional[str]]:
    """Initialize the agent with proper error handling.
    
    Returns:
        Tuple of (agent, conversation_id, error_message)
        If successful: (agent, conversation_id, None)
        If failed: (None, None, error_message)
    """
    try:
        from src.core.agent import AgentOrchestrator
        from src.core.retrieval import RetrievalEngine
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient
        from src.services.meilisearch_client import MeilisearchClient
        
        # Initialize services with health checks
        ollama = OllamaClient()
        if not ollama.is_healthy():
            return None, None, "❌ **Ollama service is not responding**\n\nPlease ensure Ollama is running:\n```bash\ndocker-compose up -d ollama\n```"
        
        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            return None, None, "❌ **Qdrant service is not responding**\n\nPlease ensure Qdrant is running:\n```bash\ndocker-compose up -d qdrant\n```"
        
        meilisearch = MeilisearchClient()
        if not meilisearch.is_healthy():
            return None, None, "❌ **Meilisearch service is not responding**\n\nPlease ensure Meilisearch is running:\n```bash\ndocker-compose up -d meilisearch\n```"
        
        retrieval = RetrievalEngine(ollama, qdrant, meilisearch)
        agent = AgentOrchestrator(ollama, retrieval)
        conversation_id = agent.start_conversation()
        
        logger.info(f"Agent initialized successfully: conversation_id={conversation_id}")
        return agent, conversation_id, None
        
    except ImportError as e:
        logger.error(f"Import error during agent initialization: {e}", exc_info=True)
        return None, None, f"❌ **Missing dependency**: {str(e)}\n\nPlease check your installation."
    except ConnectionError as e:
        logger.error(f"Connection error during agent initialization: {e}", exc_info=True)
        return None, None, f"❌ **Connection failed**: {str(e)}\n\nPlease check if all services are running."
    except Exception as e:
        logger.error(f"Agent initialization error: {e}", exc_info=True)
        return None, None, f"❌ **Failed to initialize agent**: {str(e)}"


async def _get_or_create_ingestor() -> tuple[Optional[object], Optional[str]]:
    """Get or create DocumentIngestor instance.
    
    Returns:
        Tuple of (ingestor, error_message)
        If successful: (ingestor, None)
        If failed: (None, error_message)
    """
    # Check if already in session
    ingestor = cl.user_session.get("ingestor")
    if ingestor:
        return ingestor, None
    
    try:
        from src.core.ingest import DocumentIngestor
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient
        from src.services.meilisearch_client import MeilisearchClient
        
        # Initialize services
        ollama = OllamaClient()
        if not ollama.is_healthy():
            return None, "❌ **Ollama service is not responding**\n\nDocument ingestion requires Ollama for embeddings."
        
        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            return None, "❌ **Qdrant service is not responding**\n\nDocument ingestion requires Qdrant for vector storage."
        
        meilisearch = MeilisearchClient()
        if not meilisearch.is_healthy():
            return None, "❌ **Meilisearch service is not responding**\n\nDocument ingestion requires Meilisearch for keyword search."
        
        ingestor = DocumentIngestor(
            ollama_client=ollama,
            qdrant_client=qdrant,
            meilisearch_client=meilisearch,
            chunk_size=500,
            chunk_overlap=50,
        )
        
        # Cache in session
        cl.user_session.set("ingestor", ingestor)
        
        logger.info("DocumentIngestor initialized successfully")
        return ingestor, None
        
    except Exception as e:
        logger.error(f"Failed to initialize DocumentIngestor: {e}", exc_info=True)
        return None, f"❌ **Failed to initialize document ingestor**: {str(e)}"


async def _ingest_document_async(
    ingestor,
    file_bytes: bytes,
    filename: str,
    file_type: str
) -> tuple[Optional[object], Optional[str]]:
    """Ingest a document asynchronously.
    
    Args:
        ingestor: DocumentIngestor instance
        file_bytes: Raw file bytes
        filename: Original filename
        file_type: File extension (pdf, txt, md)
        
    Returns:
        Tuple of (IngestionResult, error_message)
    """
    try:
        if file_type == "pdf":
            result = await asyncio.to_thread(
                ingestor.ingest_pdf_bytes,
                file_bytes,
                filename,
                chunk_size=500,
                chunk_overlap=50,
                skip_duplicates=True,
            )
        else:
            # Text or Markdown
            text_content = file_bytes.decode("utf-8")
            result = await asyncio.to_thread(
                ingestor.ingest_text,
                text_content,
                filename,
                chunk_size=500,
                chunk_overlap=50,
                skip_duplicates=True,
            )
        
        return result, None
        
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error: {e}", exc_info=True)
        return None, "❌ **Failed to read file**\n\nInvalid text encoding. Please ensure the file is UTF-8 encoded."
    except Exception as e:
        logger.error(f"Document ingestion error: {e}", exc_info=True)
        return None, f"❌ **Error during ingestion**: {str(e)}"


async def _process_message_async(agent, conversation_id: str, user_message: str) -> tuple[str, Optional[str]]:
    """Process a message with the agent asynchronously.
    
    Args:
        agent: The AgentOrchestrator instance
        conversation_id: The conversation ID
        user_message: The user's message
        
    Returns:
        Tuple of (response: str, error_message: Optional[str])
    """
    try:
        process_message_async = getattr(agent, "process_message_async", None)
        if process_message_async and inspect.iscoroutinefunction(process_message_async):
            response = await agent.process_message_async(
                conversation_id,
                user_message,
                use_retrieval=True,
            )
        else:
            response = await asyncio.to_thread(
                agent.process_message,
                conversation_id,
                user_message,
                use_retrieval=True,
            )
        
        return response, None
        
    except TimeoutError as e:
        logger.error(f"Timeout during message processing: {e}", exc_info=True)
        return "", "⏱️ **Request timed out**\n\nThe LLM may be busy or the model is too large. Try again or use a smaller model."
    except ConnectionError as e:
        logger.error(f"Connection error during message processing: {e}", exc_info=True)
        return "", "🔌 **Lost connection to a service**\n\nPlease check if Ollama, Qdrant, and Meilisearch are running."
    except Exception as e:
        logger.error(f"Error during message processing: {e}", exc_info=True)
        return "", f"❌ **Error processing message**: {str(e)}"


@cl.on_chat_start
async def start():
    """Initialize agent when chat session starts.

    Sends a persistent loading message first so the user always sees
    initialization progress, then sends the welcome/ready message as a
    separate second message once initialization completes.  This avoids
    the "no loading screen" issue caused by in-place message updates
    happening too fast for the browser to render the interim state.
    """
    logger.info("New chat session started")
    cl.user_session.set("initializing", True)
    cl.user_session.set("agent_initialized", False)

    # ------------------------------------------------------------------
    # 1. Send loading screen immediately – always visible to the user.
    #    This message is NOT updated later; a separate success message
    #    is sent when initialization completes.
    # ------------------------------------------------------------------
    await cl.Message(
        content=(
            "# 🧠 Initializing Agent Zero (L.A.B.)\n\n"
            "Please wait while I connect to all required services...\n\n"
            "### Startup checklist\n"
            "- 🤖 Ollama (LLM)\n"
            "- 📊 Qdrant (Vector Database)\n"
            "- 🔍 Meilisearch (Keyword Search)\n\n"
            "You will see the full chat interface as soon as initialization is complete."
        )
    ).send()

    # ------------------------------------------------------------------
    # 2. Initialize agent with a visible progress step.
    # ------------------------------------------------------------------
    async with cl.Step(name="Initializing Agent", type="tool") as step:
        step.output = "Connecting to Ollama, Qdrant, and Meilisearch..."
        await step.update()

        agent, conversation_id, error = await _initialize_agent()

        if error:
            step.output = error
            step.is_error = True
            await step.update()
            cl.user_session.set("agent_initialized", False)
            cl.user_session.set("initializing", False)
            # Send a separate error message so the user knows what to do next.
            await cl.Message(
                content=(
                    f"## ❌ Initialization Failed\n\n{error}\n\n"
                    "---\n\n"
                    "Please check that all Docker services are running:\n"
                    "```bash\n"
                    "docker-compose ps\n"
                    "```\n"
                    "Then **refresh this page** to retry."
                )
            ).send()
            return

        # Store initialized agent in session.
        cl.user_session.set("agent", agent)
        cl.user_session.set("conversation_id", conversation_id)
        cl.user_session.set("agent_initialized", True)
        cl.user_session.set("initializing", False)

        step.output = "✅ All services connected"
        await step.update()

    # ------------------------------------------------------------------
    # 3. Send new success message with action buttons.
    #    This is a *separate* message from the loading one – both remain
    #    visible in the chat history.
    # ------------------------------------------------------------------
    await cl.Message(
        content=(
            "# 👋 Welcome to Agent Zero (L.A.B.)\n\n"
            "**Local Agent Builder** — Production-grade AI agent development platform.\n\n"
            "✅ **All services connected successfully!**\n\n"
            "## What can I help you with?\n\n"
            "- 💬 **Ask Questions** — I'll search the knowledge base for accurate answers\n"
            "- 📄 **RAG-Powered** — Responses are grounded in your uploaded documents\n"
            "- 🔍 **Source Attribution** — I cite my sources for transparency\n"
            "- 📎 **Upload Documents** — Attach PDF / TXT / MD files to add them to the KB\n\n"
            "---\n\n"
            "**Try asking me a question to get started!**\n\n"
            "*Example: \"What is RAG and how does it work?\"*"
        ),
        actions=[
            cl.Action(name="system_health", payload={"action": "health"}, label="🏥 System Health"),
            cl.Action(name="qdrant_info", payload={"action": "qdrant"}, label="📊 Qdrant Info"),
            cl.Action(name="settings_info", payload={"action": "settings"}, label="⚙️ Settings"),
            cl.Action(name="langfuse_info", payload={"action": "langfuse"}, label="🔬 Langfuse"),
            cl.Action(name="logs_info", payload={"action": "logs"}, label="📋 Logs"),
            cl.Action(name="promptfoo_info", payload={"action": "promptfoo"}, label="🧪 Promptfoo"),
            cl.Action(name="admin_help", payload={"action": "help"}, label="🧭 Admin Help"),
        ],
    ).send()

    # ------------------------------------------------------------------
    # 4. Send external dashboard links as a separate informational message.
    # ------------------------------------------------------------------
    await cl.Message(
        content=(
            "### 🔗 External Dashboards\n\n"
            "| Service | URL |\n"
            "|---------|-----|\n"
            "| Qdrant | [Dashboard](http://localhost:6333/dashboard) · [API Docs](http://localhost:6333/docs) |\n"
            "| Grafana | [localhost:3000](http://localhost:3000) (admin/admin) |\n"
            "| Langfuse | [localhost:3001](http://localhost:3001) |\n"
            "| Prometheus | [localhost:9090](http://localhost:9090) |\n"
            "| Meilisearch | [localhost:7700](http://localhost:7700) |\n\n"
            "*For the full Admin Dashboard, open [localhost:8502](http://localhost:8502).*\n\n"
            "💡 Use `/help` to see all available admin slash commands."
        )
    ).send()

    logger.info("Chat session initialized successfully")


@cl.on_message
async def main(message: cl.Message):
    """Process user messages and file uploads."""
    logger.info(f"Received message: {message.content if message.content else '[File upload]'}")
    
    # Check for file attachments first
    if message.elements:
        for element in message.elements:
            if isinstance(element, cl.File):
                await process_file_upload(element)
        
        # If only files (no text), return after processing
        if not message.content or not message.content.strip():
            return
    
    # Process text message
    user_message = message.content

    if cl.user_session.get("initializing", False):
        await cl.Message(
            content="⏳ **Agent Zero is still initializing**\n\nPlease wait a few seconds and try again when startup completes."
        ).send()
        return

    if user_message and await _try_handle_admin_command(user_message.strip()):
        return
    
    # Check if agent is initialized
    if not cl.user_session.get("agent_initialized", False):
        await cl.Message(
            content="⚠️ **Agent not initialized**\n\nPlease refresh the page to restart the session."
        ).send()
        return
    
    # Get agent and conversation from session
    agent = cl.user_session.get("agent")
    conversation_id = cl.user_session.get("conversation_id")
    
    if not agent or not conversation_id:
        await cl.Message(
            content="⚠️ **Session error**\n\nAgent or conversation ID not found. Please refresh the page."
        ).send()
        return
    
    # Create a response message that we'll stream to
    response_msg = cl.Message(content="")
    await response_msg.send()
    
    # Process message with progress indicator
    async with cl.Step(name="🤔 Thinking", type="llm") as thinking_step:
        thinking_step.output = "Retrieving relevant documents and generating response..."
        await thinking_step.update()
        
        # Process the message asynchronously
        response, error = await _process_message_async(agent, conversation_id, user_message)
        
        if error:
            thinking_step.output = error
            thinking_step.is_error = True
            await thinking_step.update()
            
            response_msg.content = error
            await response_msg.update()
            return
        
        thinking_step.output = "✅ Response generated"
        await thinking_step.update()
    
    # Update the response message with the final response
    response_msg.content = response
    await response_msg.update()
    
    logger.info(f"Response sent successfully (length: {len(response)} chars)")


async def process_file_upload(file: cl.File):
    """Handle uploaded files and ingest into knowledge base.
    
    Args:
        file: Uploaded file from user
    """
    logger.info(f"File upload started: {file.name} ({file.size} bytes)")
    
    # Determine file type
    file_ext = file.name.lower().split(".")[-1]
    if file_ext not in ["pdf", "txt", "md"]:
        await cl.Message(
            content=f"❌ **Unsupported file type**: {file_ext}\n\nPlease upload PDF, TXT, or MD files."
        ).send()
        return
    
    # Get or create ingestor
    async with cl.Step(name="Initializing Document Ingestor", type="tool") as init_step:
        ingestor, error = await _get_or_create_ingestor()
        
        if error:
            init_step.output = error
            init_step.is_error = True
            await init_step.update()
            
            await cl.Message(content=error).send()
            return
        
        init_step.output = "✅ Ingestor ready"
        await init_step.update()
    
    # Read file bytes
    file_bytes = file.content
    
    # Ingest document with progress tracking
    async with cl.Step(name=f"📄 Ingesting {file.name}", type="tool") as ingest_step:
        ingest_step.output = f"Processing {file_ext.upper()} document...\n"
        ingest_step.output += f"- Chunking text (500 chars/chunk, 50 char overlap)\n"
        ingest_step.output += f"- Generating embeddings\n"
        ingest_step.output += f"- Indexing in Qdrant and Meilisearch"
        await ingest_step.update()
        
        result, error = await _ingest_document_async(
            ingestor,
            file_bytes,
            file.name,
            file_ext
        )
        
        if error:
            ingest_step.output = error
            ingest_step.is_error = True
            await ingest_step.update()
            
            await cl.Message(content=error).send()
            return
        
        if not result.success:
            ingest_step.output = f"❌ Ingestion failed: {result.error}"
            ingest_step.is_error = True
            await ingest_step.update()
            
            await cl.Message(
                content=f"❌ **Ingestion failed**: {result.error}"
            ).send()
            return
        
        # Check if duplicate
        if result.skipped_duplicate:
            ingest_step.output = f"⚠️ Duplicate detected (Document ID: {result.existing_document_id})"
            await ingest_step.update()
            
            await cl.Message(
                content=f"""⚠️ **Document already exists in knowledge base**

**File**: {file.name}
**Document ID**: {result.existing_document_id}
**Chunks**: {result.chunks_count}

The document hash matches an existing document. Skipped duplicate ingestion.

If you need to re-ingest, please delete the old version first."""
            ).send()
            return
        
        # Success!
        ingest_step.output = f"✅ Ingested successfully\n"
        ingest_step.output += f"- Document ID: {result.document_id}\n"
        ingest_step.output += f"- Chunks created: {result.chunks_count}\n"
        ingest_step.output += f"- Duration: {result.duration_seconds:.1f}s"
        await ingest_step.update()
    
    # Send success message
    await cl.Message(
        content=f"""✅ **Document indexed successfully!**

**Filename**: {file.name}
**Document ID**: {result.document_id}
**Chunks**: {result.chunks_count}
**Processing time**: {result.duration_seconds:.1f}s

The document is now available in the knowledge base. You can ask questions about it!

Try asking: *"What is this document about?"* or *"Summarize the key points."*"""
    ).send()
    
    logger.info(f"Document ingested successfully: {file.name} -> {result.document_id} ({result.chunks_count} chunks)")


@cl.on_chat_end
async def end():
    """Cleanup when chat ends."""
    logger.info("Chat session ended")
    
    # Get conversation ID for logging
    conversation_id = cl.user_session.get("conversation_id")
    if conversation_id:
        logger.info(f"Ending conversation: {conversation_id}")


@cl.action_callback("system_health")
async def on_system_health_action(action: cl.Action):
    """Handle system health check action."""
    logger.info("System health check requested")
    
    async with cl.Step(name="🏥 Checking System Health", type="tool") as step:
        step.output = "Checking all services..."
        await step.update()
        
        try:
            from src.services.health_check import HealthChecker
            
            checker = HealthChecker()
            statuses = await asyncio.to_thread(checker.check_all)
            
            # Format results
            health_report = "# 🏥 System Health Report\n\n"
            
            all_healthy = all(status.is_healthy for status in statuses.values())
            if all_healthy:
                health_report += "✅ **All services operational**\n\n"
            else:
                health_report += "⚠️ **Some services have issues**\n\n"
            
            health_report += "## Service Status\n\n"
            
            for name, status in statuses.items():
                emoji = "✅" if status.is_healthy else "❌"
                health_report += f"### {emoji} {status.name}\n"
                health_report += f"- **Status**: {'Healthy' if status.is_healthy else 'Unhealthy'}\n"
                health_report += f"- **Message**: {status.message}\n"
                
                if status.details:
                    health_report += f"- **Details**: {', '.join(f'{k}={v}' for k, v in status.details.items())}\n"
                
                health_report += "\n"
            
            step.output = "✅ Health check complete"
            await step.update()
            
            # Add external monitoring links
            health_report += "\n---\n\n"
            health_report += "**📊 View Detailed Metrics:**\n\n"
            health_report += "- [Grafana Dashboard →](http://localhost:3000) - Visual metrics (admin/admin)\n"
            health_report += "- [Prometheus Metrics →](http://localhost:9090) - Raw data and queries\n"
            health_report += "- [Langfuse Traces →](http://localhost:3001) - LLM observability\n"
            
            await cl.Message(content=health_report).send()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            step.output = f"❌ Health check failed: {str(e)}"
            step.is_error = True
            await step.update()
            
            await cl.Message(
                content=f"❌ **Health check failed**: {str(e)}"
            ).send()


@cl.action_callback("qdrant_info")
async def on_qdrant_info_action(action: cl.Action):
    """Handle Qdrant information display action."""
    logger.info("Qdrant info requested")
    
    async with cl.Step(name="📊 Fetching Qdrant Collections", type="tool") as step:
        step.output = "Querying Qdrant..."
        await step.update()
        
        try:
            from src.services.qdrant_client import QdrantVectorClient
            from src.config import get_config
            
            qdrant = QdrantVectorClient()
            config = get_config()
            
            if not qdrant.is_healthy():
                step.output = "❌ Qdrant is not responding"
                step.is_error = True
                await step.update()
                
                await cl.Message(
                    content="❌ **Qdrant service is not responding**\n\nPlease check if Qdrant is running."
                ).send()
                return
            
            # Get all collections
            collections = await asyncio.to_thread(qdrant.list_collections)
            
            info_report = "# 📊 Qdrant Vector Database Info\n\n"
            info_report += f"**Target Collection**: `{config.qdrant.collection_name}`\n\n"
            
            # Check if our collection exists
            collection_exists = any(c["name"] == config.qdrant.collection_name for c in collections)
            
            if collection_exists:
                # Get collection stats
                collection_stats = await asyncio.to_thread(
                    qdrant.get_collection_stats,
                    config.qdrant.collection_name,
                )
                
                if collection_stats:
                    info_report += "## Collection Details\n\n"
                    info_report += f"- **Status**: ✅ Active\n"
                    info_report += f"- **Vector Count**: {collection_stats['vectors_count']:,}\n"
                    info_report += f"- **Points Count**: {collection_stats['points_count']:,}\n"
                    info_report += f"- **Vector Size**: {collection_stats['vector_size']}\n"
                    info_report += f"- **Distance Metric**: {collection_stats['distance_metric']}\n"
                    
                    if collection_stats['vectors_count'] > 0:
                        info_report += f"\n**📚 Knowledge Base**: Contains {collection_stats['vectors_count']:,} document chunks\n"
                    else:
                        info_report += f"\n**📚 Knowledge Base**: Empty - upload documents to get started\n"
                else:
                    info_report += "- **Status**: ✅ Exists but details unavailable\n"
            else:
                info_report += "- **Status**: ⚠️ Collection not found\n"
                info_report += "\nThe collection will be created automatically when you upload your first document.\n"
            
            # Show all collections
            if collections:
                info_report += f"\n## All Collections ({len(collections)})\n\n"
                for col in collections:
                    info_report += f"- **{col['name']}**: {col['vectors_count']:,} vectors\n"
            
            step.output = "✅ Qdrant info retrieved"
            await step.update()
            
            # Add external Qdrant dashboard links
            info_report += "\n---\n\n"
            info_report += "**🔗 Explore in Qdrant Dashboard:**\n\n"
            info_report += f"- [View Collections →](http://localhost:6333/dashboard#/collections)\n"
            info_report += f"- [Browse '{config.qdrant.collection_name}' →](http://localhost:6333/dashboard#/collections/{config.qdrant.collection_name})\n"
            info_report += f"- [API Documentation →](http://localhost:6333/docs)\n"
            
            await cl.Message(content=info_report).send()
            
        except Exception as e:
            logger.error(f"Qdrant info failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()
            
            await cl.Message(
                content=f"❌ **Failed to get Qdrant info**: {str(e)}"
            ).send()


@cl.action_callback("settings_info")
async def on_settings_info_action(action: cl.Action):
    """Handle settings information display action."""
    logger.info("Settings info requested")
    
    try:
        from src.config import get_config
        
        config = get_config()
        
        settings_report = "# ⚙️ Agent Zero Configuration\n\n"
        
        settings_report += "## Application\n\n"
        settings_report += f"- **Version**: {config.app_version}\n"
        settings_report += f"- **Environment**: {config.env}\n"
        settings_report += f"- **Debug Mode**: {'✅ Enabled' if config.debug else '❌ Disabled'}\n"
        settings_report += f"- **Log Level**: {config.log_level}\n\n"
        
        settings_report += "## LLM Configuration\n\n"
        settings_report += f"- **Model**: {config.ollama.model}\n"
        settings_report += f"- **Embedding Model**: {config.ollama.embed_model}\n"
        settings_report += f"- **Host**: {config.ollama.host}\n"
        settings_report += f"- **Timeout**: {config.ollama.timeout}s\n\n"
        
        settings_report += "## Vector Database (Qdrant)\n\n"
        settings_report += f"- **Collection**: {config.qdrant.collection_name}\n"
        settings_report += f"- **Host**: {config.qdrant.host}:{config.qdrant.port}\n"
        settings_report += f"- **Vector Size**: {config.qdrant.vector_size}\n\n"
        
        settings_report += "## Search (Meilisearch)\n\n"
        settings_report += f"- **Index**: {config.meilisearch.index_name}\n"
        settings_report += f"- **Host**: {config.meilisearch.host}\n\n"
        
        settings_report += "## Security\n\n"
        settings_report += f"- **LLM Guard**: {'✅ Enabled' if config.security.llm_guard_enabled else '❌ Disabled'}\n"
        settings_report += f"- **Input Scanning**: {'✅ Enabled' if config.security.llm_guard_input_scan else '❌ Disabled'}\n"
        settings_report += f"- **Output Scanning**: {'✅ Enabled' if config.security.llm_guard_output_scan else '❌ Disabled'}\n"
        settings_report += f"- **Max Input Length**: {config.security.max_input_length:,} chars\n"
        settings_report += f"- **Max Output Length**: {config.security.max_output_length:,} chars\n\n"
        
        settings_report += "## Observability\n\n"
        settings_report += f"- **Langfuse**: {'✅ Enabled' if config.langfuse.enabled else '❌ Disabled'}\n"
        if config.langfuse.enabled:
            settings_report += f"- **Host**: {config.langfuse.host}\n\n"
        
        settings_report += "---\n\n"
        settings_report += "*Configuration loaded from environment variables and `.env` file*\n\n"
        
        # Add management links
        settings_report += "**🔧 Service Management:**\n\n"
        settings_report += "- [Qdrant Dashboard →](http://localhost:6333/dashboard) - Vector database admin\n"
        settings_report += "- [Meilisearch →](http://localhost:7700) - Search index admin\n"
        settings_report += "- [Grafana →](http://localhost:3000) - Monitoring dashboard\n"
        settings_report += "- [Langfuse →](http://localhost:3001) - LLM observability\n"
        
        await cl.Message(content=settings_report).send()
        
    except Exception as e:
        logger.error(f"Settings info failed: {e}", exc_info=True)
        await cl.Message(
            content=f"❌ **Failed to get settings**: {str(e)}"
        ).send()


@cl.action_callback("langfuse_info")
async def on_langfuse_info_action(action: cl.Action):
    """Handle Langfuse observability summary action."""
    logger.info("Langfuse info requested")
    async with cl.Step(name="🔬 Fetching Langfuse Summary", type="tool") as step:
        step.output = "Collecting observability data..."
        await step.update()
        try:
            await _send_langfuse_report("24h")
            step.output = "✅ Langfuse summary ready"
            await step.update()
        except Exception as e:
            logger.error(f"Langfuse summary failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()


@cl.action_callback("logs_info")
async def on_logs_info_action(action: cl.Action):
    """Handle quick logs action."""
    logger.info("Logs info requested")
    async with cl.Step(name="📋 Reading Logs", type="tool") as step:
        step.output = "Loading latest application logs..."
        await step.update()
        try:
            await _send_logs_report(50, "ALL", "ALL")
            step.output = "✅ Logs loaded"
            await step.update()
        except Exception as e:
            logger.error(f"Logs report failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()


@cl.action_callback("promptfoo_info")
async def on_promptfoo_info_action(action: cl.Action):
    """Handle quick promptfoo status action."""
    logger.info("Promptfoo info requested")
    async with cl.Step(name="🧪 Fetching Promptfoo Summary", type="tool") as step:
        step.output = "Loading prompt test data..."
        await step.update()
        try:
            await _send_promptfoo_report()
            step.output = "✅ Promptfoo summary ready"
            await step.update()
        except Exception as e:
            logger.error(f"Promptfoo summary failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()


@cl.action_callback("admin_help")
async def on_admin_help_action(action: cl.Action):
    """Handle admin help action."""
    logger.info("Admin help requested")
    await _send_admin_help()


if __name__ == "__main__":
    logger.info(f"Agent Zero {config.app_version} - {config.env} environment")
