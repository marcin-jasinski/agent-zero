"""Agent Zero (L.A.B.) - Admin Dashboard Chainlit Application.

A.P.I. Admin Panel — dedicated system management and monitoring interface
for Agent Zero. Runs on port 8502 (separate from the main chat UI on 8501).

Available admin features:
- System health checks across all infrastructure services
- Qdrant vector database management
- Configuration overview
- Langfuse observability summary
- Application log viewer
- Promptfoo test suite management
"""

import asyncio
import shlex
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import chainlit as cl

from src.config import get_config
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

config = get_config()

logger.info("Starting Agent Zero Admin Dashboard (Chainlit Admin)")

# ---------------------------------------------------------------------------
# Log helpers
# ---------------------------------------------------------------------------

SERVICE_LOGGER_PATTERNS = {
    "ALL": [],
    "OLLAMA": ["ollama_client", "ollama", "OllamaClient"],
    "QDRANT": ["qdrant_client", "qdrant", "QdrantVectorClient"],
    "MEILISEARCH": ["meilisearch_client", "meilisearch", "MeilisearchClient"],
    "LANGFUSE": ["langfuse_client", "langfuse", "observability"],
    "AGENT": ["src.core.agent", "src.core.retrieval", "src.core.ingest", "src.core.memory"],
    "UI": ["src.ui", "chainlit", "main", "admin"],
}


def _tail_logs(lines: int = 50, level: str = "ALL", service: str = "ALL") -> str:
    """Read and filter application logs.

    Args:
        lines: Number of lines to return from the end.
        level: Log level filter (ALL/DEBUG/INFO/WARNING/ERROR).
        service: Service filter keyword.

    Returns:
        Filtered log text.
    """
    log_candidates = [
        Path(f"/app/logs/agent-zero-{config.env}.log"),
        Path(f"logs/agent-zero-{config.env}.log"),
    ]
    log_file = next((c for c in log_candidates if c.exists()), None)

    if not log_file:
        return "No log file found yet."

    all_lines = log_file.read_text(encoding="utf-8").splitlines()

    normalized_level = level.upper()
    if normalized_level != "ALL":
        all_lines = [line for line in all_lines if normalized_level in line.upper()]

    normalized_service = service.upper()
    if normalized_service != "ALL":
        patterns = SERVICE_LOGGER_PATTERNS.get(normalized_service, [])
        all_lines = [line for line in all_lines if any(p in line for p in patterns)]

    selected = all_lines[-max(lines, 1):] if all_lines else []
    return "\n".join(selected) if selected else "No logs matching filter."


async def _send_logs_report(lines: int = 50, level: str = "ALL", service: str = "ALL") -> None:
    """Send filtered log report as a Chainlit message."""
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
    """Send Langfuse observability summary."""
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


async def _send_admin_help() -> None:
    """Send admin command reference."""
    help_text = """# 🧭 Admin Commands

## System
- `/health` — Full system health check

## Logs
- `/logs` — Last 50 lines (all levels, all services)
- `/logs <lines> <level> <service>` — e.g. `/logs 100 ERROR AGENT`

## Langfuse
- `/langfuse` — Last 24 h observability summary
- `/langfuse 7d` — Custom time range

## Qdrant
- `/qdrant list` — List all collections
- `/qdrant search <query>` — Semantic search
- `/qdrant create <name> [vector_size] [Cosine|Euclid|Dot]`
- `/qdrant delete <name>`

## Promptfoo
- `/promptfoo summary`
- `/promptfoo scenarios`
- `/promptfoo runs [limit]`
- `/promptfoo create "<name>" "<description>" "<input_text>"`
- `/promptfoo delete <scenario_id>`
- `/promptfoo run <version>`
- `/promptfoo compare <version_a> <version_b>`
"""
    await cl.Message(content=help_text).send()


async def _try_handle_admin_command(user_message: str) -> bool:
    """Handle slash commands for the admin dashboard.

    Args:
        user_message: Raw message text from the user.

    Returns:
        True when the message was handled as an admin command.
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

    if cmd in ("/help", "/admin"):
        await _send_admin_help()
        return True

    if cmd == "/health":
        await _run_health_check()
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

    if cmd == "/qdrant":
        await _handle_qdrant_command(parts)
        return True

    if cmd == "/promptfoo":
        await _handle_promptfoo_command(parts)
        return True

    await cl.Message(
        content=(
            f"❌ Unknown command: `{cmd}`\n\n"
            "Type `/help` for a list of available commands."
        )
    ).send()
    return True


async def _run_health_check() -> None:
    """Execute a full system health check and send results."""
    async with cl.Step(name="🏥 Checking System Health", type="tool") as step:
        step.output = "Checking all services..."
        await step.update()

        try:
            from src.services.health_check import HealthChecker

            checker = HealthChecker()
            statuses = await asyncio.to_thread(checker.check_all)

            all_healthy = all(s.is_healthy for s in statuses.values())
            report = "# 🏥 System Health Report\n\n"
            report += "✅ **All services operational**\n\n" if all_healthy else "⚠️ **Some services have issues**\n\n"
            report += "## Service Status\n\n"

            for _name, status in statuses.items():
                icon = "✅" if status.is_healthy else "❌"
                report += f"### {icon} {status.name}\n"
                report += f"- **Status**: {'Healthy' if status.is_healthy else 'Unhealthy'}\n"
                report += f"- **Message**: {status.message}\n"
                if getattr(status, "details", None):
                    report += (
                        f"- **Details**: {', '.join(f'{k}={v}' for k, v in status.details.items())}\n"
                    )
                report += "\n"

            report += "\n---\n\n**📊 View Detailed Metrics:**\n\n"
            report += "- [Grafana Dashboard →](http://localhost:3000) (admin/admin)\n"
            report += "- [Prometheus →](http://localhost:9090)\n"
            report += "- [Langfuse Traces →](http://localhost:3001)\n"

            step.output = "✅ Health check complete"
            await step.update()
            await cl.Message(content=report).send()

        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            step.output = f"❌ Health check failed: {str(e)}"
            step.is_error = True
            await step.update()
            await cl.Message(content=f"❌ **Health check failed**: {str(e)}").send()


async def _handle_qdrant_command(parts: list[str]) -> None:
    """Handle /qdrant sub-commands.

    Args:
        parts: Tokenised command parts, e.g. ['/qdrant', 'list'].
    """
    from src.services.qdrant_client import QdrantVectorClient

    qdrant = QdrantVectorClient()
    sub = parts[1].lower() if len(parts) > 1 else "list"

    if sub == "list":
        collections = await asyncio.to_thread(qdrant.list_collections)
        content = "# 📊 Qdrant Collections\n\n"
        if collections:
            for c in collections:
                content += (
                    f"- **{c['name']}** | vectors: {c['vectors_count']:,} "
                    f"| points: {c['points_count']:,}\n"
                )
        else:
            content += "No collections found.\n"
        await cl.Message(content=content).send()
        return

    if sub == "search" and len(parts) > 2:
        from src.services.ollama_client import OllamaClient

        query = " ".join(parts[2:])
        ollama = OllamaClient()
        results = await asyncio.to_thread(
            qdrant.search_by_text, query, config.qdrant.collection_name, 5, ollama
        )
        content = f"# 🔎 Qdrant Search (`{config.qdrant.collection_name}`)\n\n"
        if results:
            for r in results:
                snippet = r["content"][:240].replace("\n", " ")
                content += f"- **Score {r['score']:.3f}** | {r['source']} | {snippet}\n"
        else:
            content += "No results found.\n"
        await cl.Message(content=content).send()
        return

    if sub == "create" and len(parts) > 2:
        name = parts[2]
        vector_size = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 768
        distance = parts[4] if len(parts) > 4 else "Cosine"
        success, message = await asyncio.to_thread(
            qdrant.create_collection_ui, name, vector_size, distance
        )
        await cl.Message(content=f"{'✅' if success else '❌'} {message}").send()
        return

    if sub == "delete" and len(parts) > 2:
        success, message = await asyncio.to_thread(qdrant.delete_collection_ui, parts[2])
        await cl.Message(content=f"{'✅' if success else '❌'} {message}").send()
        return

    await cl.Message(content="❌ Unknown /qdrant sub-command. Use `/help`.").send()


async def _handle_promptfoo_command(parts: list[str]) -> None:
    """Handle /promptfoo sub-commands.

    Args:
        parts: Tokenised command parts.
    """
    from src.services.promptfoo_client import PromptfooClient

    client = PromptfooClient()
    sub = parts[1].lower() if len(parts) > 1 else "summary"

    if sub == "summary":
        summary = await asyncio.to_thread(client.get_summary_metrics)
        scenarios = await asyncio.to_thread(client.list_scenarios)
        runs = await asyncio.to_thread(client.list_runs, None, 5)

        content = "# 🧪 Promptfoo Summary\n\n"
        content += f"- **Total Scenarios**: {summary.get('total_scenarios', 0)}\n"
        content += f"- **Total Runs**: {summary.get('total_runs', 0)}\n"
        content += f"- **Average Pass Rate**: {summary.get('average_pass_rate', 0.0):.1f}%\n\n"

        content += "## Scenarios\n\n"
        if scenarios:
            for s in scenarios[:10]:
                content += f"- **{s.name}** (`{s.id[:8]}`)\n"
        else:
            content += "No scenarios configured.\n"

        content += "\n## Recent Runs\n\n"
        if runs:
            for r in runs:
                content += f"- **{r.prompt_version}** | {r.pass_rate:.1f}% ({r.passed_tests}/{r.total_tests})\n"
        else:
            content += "No test runs yet.\n"

        await cl.Message(content=content).send()
        return

    if sub == "scenarios":
        scenarios = await asyncio.to_thread(client.list_scenarios)
        content = "# 🧪 Promptfoo Scenarios\n\n"
        if scenarios:
            for s in scenarios:
                content += f"- **{s.name}** (`{s.id}`)\n"
        else:
            content += "No scenarios configured.\n"
        await cl.Message(content=content).send()
        return

    if sub == "runs":
        limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
        runs = await asyncio.to_thread(client.list_runs, None, limit)
        content = "# 🧪 Promptfoo Runs\n\n"
        if runs:
            for r in runs:
                content += f"- **{r.prompt_version}** | {r.pass_rate:.1f}% | `{r.id}`\n"
        else:
            content += "No runs available.\n"
        await cl.Message(content=content).send()
        return

    if sub == "create" and len(parts) > 4:
        scenario = await asyncio.to_thread(client.create_scenario, parts[2], parts[3], parts[4])
        await cl.Message(
            content=f"✅ Scenario created: **{scenario.name}** (`{scenario.id}`)"
        ).send()
        return

    if sub == "delete" and len(parts) > 2:
        deleted = await asyncio.to_thread(client.delete_scenario, parts[2])
        if deleted:
            await cl.Message(content=f"✅ Scenario deleted: `{parts[2]}`").send()
        else:
            await cl.Message(content=f"❌ Scenario not found: `{parts[2]}`").send()
        return

    if sub == "run" and len(parts) > 2:
        run = await asyncio.to_thread(client.run_tests, parts[2], None, None)
        content = (
            "# ✅ Promptfoo Run Complete\n\n"
            f"- **Version**: {run.prompt_version}\n"
            f"- **Pass Rate**: {run.pass_rate:.1f}%\n"
            f"- **Passed/Total**: {run.passed_tests}/{run.total_tests}\n"
        )
        await cl.Message(content=content).send()
        return

    if sub == "compare" and len(parts) > 3:
        comparison = await asyncio.to_thread(client.compare_versions, parts[2], parts[3])
        if not comparison:
            await cl.Message(content="❌ Could not compare versions (missing runs).").send()
            return

        content = "# ⚖️ Prompt Version Comparison\n\n"
        content += f"- **A**: {comparison.version_a}\n"
        content += f"- **B**: {comparison.version_b}\n"
        content += f"- **Recommendation**: {comparison.recommendation}\n\n"
        if comparison.improvements:
            content += "## Improvements\n" + "\n".join(f"- {i}" for i in comparison.improvements) + "\n\n"
        if comparison.regressions:
            content += "## Regressions\n" + "\n".join(f"- {r}" for r in comparison.regressions)
        await cl.Message(content=content).send()
        return

    await cl.Message(content="❌ Unknown /promptfoo command. Use `/help`.").send()


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------


@cl.on_chat_start
async def start() -> None:
    """Render admin dashboard landing page on session start."""
    logger.info("Admin dashboard session started")

    # ------------------------------------------------------------------
    # 1. Welcome message with quick-action buttons
    # ------------------------------------------------------------------
    await cl.Message(
        content=(
            "# 🛡️ Agent Zero — Admin Dashboard\n\n"
            "**A.P.I. Admin Panel** — system management and monitoring interface.\n\n"
            "The main **chat interface** is available at "
            "[localhost:8501](http://localhost:8501).\n\n"
            "---\n\n"
            "Click a button below for a quick status snapshot, or use a slash command:"
        ),
        actions=[
            cl.Action(name="system_health", payload={"action": "health"}, label="🏥 System Health"),
            cl.Action(name="qdrant_info", payload={"action": "qdrant"}, label="📊 Qdrant Info"),
            cl.Action(name="settings_info", payload={"action": "settings"}, label="⚙️ Settings"),
            cl.Action(name="langfuse_info", payload={"action": "langfuse"}, label="🔬 Langfuse"),
            cl.Action(name="logs_info", payload={"action": "logs"}, label="📋 Logs"),
            cl.Action(name="promptfoo_info", payload={"action": "promptfoo"}, label="🧪 Promptfoo"),
            cl.Action(name="admin_help", payload={"action": "help"}, label="🧭 Help"),
        ],
    ).send()

    # ------------------------------------------------------------------
    # 2. External dashboard links
    # ------------------------------------------------------------------
    await cl.Message(
        content=(
            "### 🔗 External Dashboards\n\n"
            "| Service | URL | Notes |\n"
            "|---------|-----|-------|\n"
            "| Qdrant | [localhost:6333/dashboard](http://localhost:6333/dashboard) | Vector DB admin |\n"
            "| Grafana | [localhost:3000](http://localhost:3000) | Metrics (admin/admin) |\n"
            "| Langfuse | [localhost:3001](http://localhost:3001) | LLM traces |\n"
            "| Prometheus | [localhost:9090](http://localhost:9090) | Raw metrics |\n"
            "| Meilisearch | [localhost:7700](http://localhost:7700) | Search admin |\n\n"
            "*Type `/help` for all available slash commands.*"
        )
    ).send()

    logger.info("Admin dashboard session ready")


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle slash commands in the admin dashboard."""
    user_message = message.content.strip() if message.content else ""

    if not user_message:
        return

    if not await _try_handle_admin_command(user_message):
        await cl.Message(
            content=(
                "ℹ️ This is the **Admin Dashboard** — it only accepts slash commands.\n\n"
                "Type `/help` for a list of available commands, or use the Quick-Action "
                "buttons above.\n\n"
                "For the AI chat interface, visit [localhost:8501](http://localhost:8501)."
            )
        ).send()


# ---------------------------------------------------------------------------
# Action callbacks (Quick-Action button handlers)
# ---------------------------------------------------------------------------


@cl.action_callback("system_health")
async def on_system_health_action(action: cl.Action) -> None:
    """Handle System Health button click."""
    logger.info("Admin: system health check requested")
    await _run_health_check()


@cl.action_callback("qdrant_info")
async def on_qdrant_info_action(action: cl.Action) -> None:
    """Handle Qdrant Info button click."""
    logger.info("Admin: Qdrant info requested")

    async with cl.Step(name="📊 Fetching Qdrant Info", type="tool") as step:
        step.output = "Querying Qdrant..."
        await step.update()

        try:
            from src.services.qdrant_client import QdrantVectorClient

            qdrant = QdrantVectorClient()

            if not qdrant.is_healthy():
                step.output = "❌ Qdrant is not responding"
                step.is_error = True
                await step.update()
                await cl.Message(content="❌ **Qdrant service is not responding.**").send()
                return

            collections = await asyncio.to_thread(qdrant.list_collections)
            report = "# 📊 Qdrant Vector Database\n\n"
            report += f"**Target Collection**: `{config.qdrant.collection_name}`\n\n"

            collection_exists = any(c["name"] == config.qdrant.collection_name for c in collections)
            if collection_exists:
                stats = await asyncio.to_thread(
                    qdrant.get_collection_stats, config.qdrant.collection_name
                )
                if stats:
                    report += "## Collection Details\n\n"
                    report += "- **Status**: ✅ Active\n"
                    report += f"- **Vector Count**: {stats['vectors_count']:,}\n"
                    report += f"- **Points Count**: {stats['points_count']:,}\n"
                    report += f"- **Vector Size**: {stats['vector_size']}\n"
                    report += f"- **Distance Metric**: {stats['distance_metric']}\n"
                else:
                    report += "- **Status**: ✅ Exists (details unavailable)\n"
            else:
                report += "- **Status**: ⚠️ Collection not found\n"
                report += "\nThe collection is created automatically on first document upload.\n"

            if collections:
                report += f"\n## All Collections ({len(collections)})\n\n"
                for c in collections:
                    report += f"- **{c['name']}**: {c['vectors_count']:,} vectors\n"

            report += "\n---\n"
            report += f"- [Qdrant Dashboard →](http://localhost:6333/dashboard)\n"
            report += f"- [API Docs →](http://localhost:6333/docs)\n"

            step.output = "✅ Qdrant info retrieved"
            await step.update()
            await cl.Message(content=report).send()

        except Exception as e:
            logger.error(f"Qdrant info failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()
            await cl.Message(content=f"❌ **Failed to get Qdrant info**: {str(e)}").send()


@cl.action_callback("settings_info")
async def on_settings_info_action(action: cl.Action) -> None:
    """Handle Settings button click."""
    logger.info("Admin: settings info requested")

    try:
        report = "# ⚙️ Agent Zero Configuration\n\n"

        report += "## Application\n\n"
        report += f"- **Version**: {config.app_version}\n"
        report += f"- **Environment**: {config.env}\n"
        report += f"- **Debug Mode**: {'✅ Enabled' if config.debug else '❌ Disabled'}\n"
        report += f"- **Log Level**: {config.log_level}\n\n"

        report += "## LLM (Ollama)\n\n"
        report += f"- **Model**: {config.ollama.model}\n"
        report += f"- **Embedding Model**: {config.ollama.embed_model}\n"
        report += f"- **Host**: {config.ollama.host}\n"
        report += f"- **Timeout**: {config.ollama.timeout}s\n\n"

        report += "## Vector Database (Qdrant)\n\n"
        report += f"- **Collection**: {config.qdrant.collection_name}\n"
        report += f"- **Host**: {config.qdrant.host}:{config.qdrant.port}\n"
        report += f"- **Vector Size**: {config.qdrant.vector_size}\n\n"

        report += "## Search (Meilisearch)\n\n"
        report += f"- **Index**: {config.meilisearch.index_name}\n"
        report += f"- **Host**: {config.meilisearch.host}\n\n"

        report += "## Security\n\n"
        report += f"- **LLM Guard**: {'✅ Enabled' if config.security.llm_guard_enabled else '❌ Disabled'}\n"
        report += f"- **Max Input Length**: {config.security.max_input_length:,} chars\n"
        report += f"- **Max Output Length**: {config.security.max_output_length:,} chars\n\n"

        report += "## Observability\n\n"
        report += f"- **Langfuse**: {'✅ Enabled' if config.langfuse.enabled else '❌ Disabled'}\n"
        if config.langfuse.enabled:
            report += f"- **Host**: {config.langfuse.host}\n\n"

        report += "---\n\n*Loaded from environment variables / `.env` file.*\n"

        await cl.Message(content=report).send()

    except Exception as e:
        logger.error(f"Settings info failed: {e}", exc_info=True)
        await cl.Message(content=f"❌ **Failed to get settings**: {str(e)}").send()


@cl.action_callback("langfuse_info")
async def on_langfuse_info_action(action: cl.Action) -> None:
    """Handle Langfuse button click."""
    logger.info("Admin: Langfuse info requested")
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
async def on_logs_info_action(action: cl.Action) -> None:
    """Handle Logs button click."""
    logger.info("Admin: logs info requested")
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
async def on_promptfoo_info_action(action: cl.Action) -> None:
    """Handle Promptfoo button click."""
    logger.info("Admin: Promptfoo info requested")
    async with cl.Step(name="🧪 Fetching Promptfoo Summary", type="tool") as step:
        step.output = "Loading prompt test data..."
        await step.update()
        try:
            await _handle_promptfoo_command(["promptfoo", "summary"])
            step.output = "✅ Promptfoo summary ready"
            await step.update()
        except Exception as e:
            logger.error(f"Promptfoo summary failed: {e}", exc_info=True)
            step.output = f"❌ Failed: {str(e)}"
            step.is_error = True
            await step.update()


@cl.action_callback("admin_help")
async def on_admin_help_action(action: cl.Action) -> None:
    """Handle Help button click."""
    logger.info("Admin: help requested")
    await _send_admin_help()


if __name__ == "__main__":
    logger.info(f"Agent Zero Admin Dashboard {config.app_version} — {config.env}")
