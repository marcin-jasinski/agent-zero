"""Agent Zero (L.A.B.) — Gradio Admin Dashboard Tab.

This module builds the "🛡️ Admin" tab of the unified Gradio UI.
It is called by src.ui.app and registers all components inside the
active gr.Blocks context.

All handler functions are plain Python callables with no Gradio or
Chainlit imports, making them trivially testable with unittest.mock.

Sub-tabs:
  🏥 System Health  — service health check (auto-refresh on tab switch)
  📊 Qdrant         — collection stats + semantic search
  🔬 Langfuse       — trace summary and recent traces
  🧪 Promptfoo      — test scenarios and run history
  ⚙️  Settings       — current AppConfig values
  📋 Logs           — tail application log with level/service filters
"""

import logging
from datetime import datetime

import gradio as gr

from src.config import get_config
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
config = get_config()


# ---------------------------------------------------------------------------
# Handler: System Health
# ---------------------------------------------------------------------------


def get_health_report() -> str:
    """Run a full health check on all services and return a markdown report.

    Returns:
        Markdown string with per-service status.
    """
    try:
        from src.services.health_check import HealthChecker

        checker = HealthChecker()
        statuses = checker.check_all()
        all_healthy = all(s.is_healthy for s in statuses.values())

        lines = [
            "# 🏥 System Health Report\n",
            f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
            "✅ **All services operational.**\n" if all_healthy else "⚠️ **Some services have issues.**\n",
            "| Service | Status | Message |",
            "|---------|--------|---------|",
        ]
        for _key, status in statuses.items():
            icon = "✅" if status.is_healthy else "❌"
            lines.append(f"| **{status.name}** | {icon} | {status.message} |")

        lines += [
            "\n---",
            "**External Dashboards:**  "
            "[Grafana](http://localhost:3001) · "
            "[Prometheus](http://localhost:9090) · "
            "[Langfuse](http://localhost:3000)",
        ]
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"Health report failed: {exc}", exc_info=True)
        return f"❌ **Health check failed:**\n\n```\n{exc}\n```"


# ---------------------------------------------------------------------------
# Handler: Qdrant
# ---------------------------------------------------------------------------


def get_qdrant_collections() -> tuple[str, list[str]]:
    """Fetch Qdrant collections for the stats panel and dropdown.

    Returns:
        Tuple of (markdown stats string, list of collection names).
    """
    try:
        from src.services.qdrant_client import QdrantVectorClient

        qdrant = QdrantVectorClient()
        if not qdrant.is_healthy():
            return "❌ **Qdrant is not reachable.**", []

        collections = qdrant.list_collections()
        if not collections:
            return "ℹ️ **No collections found.** Upload a document to create the first one.", []

        names = [c["name"] for c in collections]
        lines = [
            f"# 📊 Qdrant Collections ({len(collections)})\n",
            "| Collection | Vectors | Points |",
            "|------------|---------|--------|",
        ]
        for c in collections:
            lines.append(
                f"| **{c['name']}** | {c.get('vectors_count', 0):,} | {c.get('points_count', 0):,} |"
            )
        return "\n".join(lines), names

    except Exception as exc:
        logger.error(f"Qdrant collections failed: {exc}", exc_info=True)
        return f"❌ **Error:** {exc}", []


def search_qdrant(query: str, collection: str) -> str:
    """Run a semantic search in a Qdrant collection.

    Args:
        query: Natural-language search query.
        collection: Collection name to search.

    Returns:
        Markdown string with search results.
    """
    if not query or not query.strip():
        return "⚠️ Enter a search query."
    if not collection:
        return "⚠️ Select a collection first."

    try:
        from src.services.ollama_client import OllamaClient
        from src.services.qdrant_client import QdrantVectorClient

        qdrant = QdrantVectorClient()
        ollama = OllamaClient()
        results = qdrant.search_by_text(query, collection, 5, ollama)

        if not results:
            return f"ℹ️ No results for **{query}** in `{collection}`."

        lines = [f"# 🔎 Results for \"{query}\" in `{collection}`\n"]
        for i, r in enumerate(results, 1):
            snippet = str(r.get("content", ""))[:240].replace("\n", " ")
            source = r.get("source", "unknown")
            score = r.get("score", 0.0)
            lines.append(f"### {i}. Score: {score:.3f} — `{source}`\n> {snippet}\n")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"Qdrant search failed: {exc}", exc_info=True)
        return f"❌ **Search error:** {exc}"


# ---------------------------------------------------------------------------
# Handler: Langfuse
# ---------------------------------------------------------------------------


def get_langfuse_report(time_range: str = "24h") -> str:
    """Fetch Langfuse observability summary for a given time range.

    Args:
        time_range: One of "1h", "24h", "7d".

    Returns:
        Markdown string with trace summary and recent traces.
    """
    try:
        from src.services.langfuse_client import LangfuseClient

        client = LangfuseClient()
        if not client.enabled:
            return (
                "⚠️ **Langfuse is disabled.**\n\n"
                "Set `LANGFUSE_ENABLED=true` in your environment to enable observability."
            )

        summary = client.get_trace_summary(time_range)
        traces = client.get_recent_traces(10, None)

        lines = [
            f"# 🔬 Langfuse Observability — last {time_range}\n",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Traces | {summary.total_traces} |",
            f"| Last 24 h | {summary.traces_24h} |",
            f"| Avg Latency | {summary.avg_latency_ms:.0f} ms |",
            f"| Error Rate | {summary.error_rate:.1f}% |",
            "\n## Recent Traces\n",
        ]
        if traces:
            lines += [
                "| Name | Status | Duration | Tokens (in/out) |",
                "|------|--------|----------|-----------------|",
            ]
            for t in traces:
                lines.append(
                    f"| {t.name} | {t.status} | {t.duration_ms:.0f} ms "
                    f"| {t.input_tokens}/{t.output_tokens} |"
                )
        else:
            lines.append("*No traces yet.*")

        lines.append(
            "\n---\n[Open Langfuse Dashboard →](http://localhost:3000)"
        )
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"Langfuse report failed: {exc}", exc_info=True)
        return f"❌ **Langfuse error:** {exc}"


# ---------------------------------------------------------------------------
# Handler: Promptfoo
# ---------------------------------------------------------------------------


def get_promptfoo_report() -> str:
    """Fetch Promptfoo test suite summary.

    Returns:
        Markdown string with scenario list and recent runs.
    """
    try:
        from src.services.promptfoo_client import PromptfooClient

        client = PromptfooClient()
        summary = client.get_summary_metrics()
        scenarios = client.list_scenarios()
        runs = client.list_runs(None, 5)

        lines = [
            "# 🧪 Promptfoo Test Suite\n",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Scenarios | {summary.get('total_scenarios', 0)} |",
            f"| Total Runs | {summary.get('total_runs', 0)} |",
            f"| Avg Pass Rate | {summary.get('average_pass_rate', 0.0):.1f}% |",
            "\n## Scenarios\n",
        ]
        if scenarios:
            lines += ["| Name | ID |", "|-----|----|"]
            for s in scenarios[:10]:
                lines.append(f"| {s.name} | `{s.id[:8]}…` |")
        else:
            lines.append("*No scenarios configured.*")

        lines.append("\n## Recent Runs\n")
        if runs:
            lines += [
                "| Version | Pass Rate | Passed/Total |",
                "|---------|-----------|--------------|",
            ]
            for r in runs:
                lines.append(
                    f"| {r.prompt_version} | {r.pass_rate:.1f}% | {r.passed_tests}/{r.total_tests} |"
                )
        else:
            lines.append("*No test runs yet.*")

        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"Promptfoo report failed: {exc}", exc_info=True)
        return f"❌ **Promptfoo error:** {exc}"


# ---------------------------------------------------------------------------
# Handler: Settings
# ---------------------------------------------------------------------------


def get_settings_report() -> str:
    """Render current AppConfig as a markdown report.

    Returns:
        Markdown string showing all configuration sections.
    """
    try:
        lines = [
            "# ⚙️ Agent Zero Configuration\n",
            f"*Environment: **{config.env}** | Version: **{config.app_version}***\n",
            "## Application",
            f"- **Debug**: {'✅' if config.debug else '❌'}",
            f"- **Log Level**: {config.log_level}",
            "\n## LLM (Ollama)",
            f"- **Model**: `{config.ollama.model}`",
            f"- **Embed Model**: `{config.ollama.embed_model}`",
            f"- **Host**: `{config.ollama.host}`",
            f"- **Timeout**: {config.ollama.timeout}s",
            "\n## Vector DB (Qdrant)",
            f"- **Collection**: `{config.qdrant.collection_name}`",
            f"- **Host**: `{config.qdrant.host}:{config.qdrant.port}`",
            f"- **Vector Size**: {config.qdrant.vector_size}",
            "\n## Search (Meilisearch)",
            f"- **Index**: `{config.meilisearch.index_name}`",
            f"- **Host**: `{config.meilisearch.host}`",
            "\n## Security",
            f"- **LLM Guard**: {'✅ Enabled' if config.security.llm_guard_enabled else '❌ Disabled'}",
            f"- **Max Input**: {config.security.max_input_length:,} chars",
            f"- **Max Output**: {config.security.max_output_length:,} chars",
            "\n## Observability (Langfuse)",
            f"- **Enabled**: {'✅' if config.langfuse.enabled else '❌'}",
        ]
        if config.langfuse.enabled:
            lines.append(f"- **Host**: `{config.langfuse.host}`")

        lines.append("\n---\n*Values loaded from environment / `.env` file.*")
        return "\n".join(lines)

    except Exception as exc:
        logger.error(f"Settings report failed: {exc}", exc_info=True)
        return f"❌ **Error reading settings:** {exc}"


# ---------------------------------------------------------------------------
# Handler: Logs
# ---------------------------------------------------------------------------


_SERVICE_PATTERNS: dict[str, list[str]] = {
    "ALL": [],
    "OLLAMA": ["ollama_client", "OllamaClient", "ollama"],
    "QDRANT": ["qdrant_client", "QdrantVectorClient", "qdrant"],
    "MEILISEARCH": ["meilisearch_client", "MeilisearchClient", "meilisearch"],
    "LANGFUSE": ["langfuse_client", "langfuse", "observability"],
    "AGENT": ["src.core.agent", "src.core.retrieval", "src.core.ingest", "src.core.memory"],
}


def get_logs(lines: int = 50, level: str = "ALL", service: str = "ALL") -> str:
    """Read and filter the application log file.

    Args:
        lines: Number of lines to return from the tail.
        level: Log level filter (ALL / DEBUG / INFO / WARNING / ERROR).
        service: Service filter keyword.

    Returns:
        Filtered log text (plain text, not markdown — shown in a Textbox).
    """
    from pathlib import Path

    candidates = [
        Path(f"/app/logs/agent-zero-{config.env}.log"),
        Path(f"logs/agent-zero-{config.env}.log"),
    ]
    log_file = next((p for p in candidates if p.exists()), None)
    if not log_file:
        return "No log file found yet."

    try:
        all_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"Error reading log file: {exc}"

    level_upper = level.upper()
    if level_upper != "ALL":
        all_lines = [ln for ln in all_lines if level_upper in ln.upper()]

    service_upper = service.upper()
    if service_upper != "ALL":
        patterns = _SERVICE_PATTERNS.get(service_upper, [])
        if patterns:
            all_lines = [ln for ln in all_lines if any(p in ln for p in patterns)]

    selected = all_lines[-max(int(lines), 1):]
    return "\n".join(selected) if selected else "(no log entries matching filter)"


# ---------------------------------------------------------------------------
# UI builder
# ---------------------------------------------------------------------------


def build_admin_ui() -> None:
    """Register all Admin tab components inside the active gr.Blocks context.

    Must be called inside an open ``with gr.Blocks() as \u2026`` / ``with gr.Tab():``
    context.
    """
    # ---- System Health --------------------------------------------------
    with gr.Tab("🏥 System Health") as tab_health:
        health_btn = gr.Button("🔄 Refresh", variant="secondary")
        health_out = gr.Markdown("*Loading…*")
        health_btn.click(fn=get_health_report, outputs=[health_out])

    # ---- Qdrant ---------------------------------------------------------
    with gr.Tab("📊 Qdrant") as tab_qdrant:
        with gr.Row():
            collection_dd = gr.Dropdown(
                choices=[], label="Collection", interactive=True, scale=4
            )
            refresh_qdrant_btn = gr.Button("🔄 Refresh", scale=1)

        qdrant_stats = gr.Markdown("*Loading…*")

        gr.Markdown("### 🔎 Semantic Search")
        with gr.Row():
            search_input = gr.Textbox(
                placeholder="Enter search query…", scale=5, show_label=False, container=False
            )
            search_btn = gr.Button("Search", variant="primary", scale=1)
        search_results = gr.Markdown("")

        def _refresh_qdrant() -> tuple[str, gr.Dropdown]:
            stats_md, names = get_qdrant_collections()
            return stats_md, gr.Dropdown(choices=names, value=names[0] if names else None)

        refresh_qdrant_btn.click(
            fn=_refresh_qdrant,
            outputs=[qdrant_stats, collection_dd],
        )
        search_btn.click(
            fn=search_qdrant,
            inputs=[search_input, collection_dd],
            outputs=[search_results],
        )

    # ---- Langfuse -------------------------------------------------------
    with gr.Tab("🔬 Langfuse") as tab_langfuse:
        time_range = gr.Radio(
            choices=["1h", "24h", "7d"], value="24h", label="Time range"
        )
        langfuse_btn = gr.Button("🔄 Refresh", variant="secondary")
        langfuse_out = gr.Markdown("*Loading…*")
        langfuse_btn.click(
            fn=get_langfuse_report,
            inputs=[time_range],
            outputs=[langfuse_out],
        )

    # ---- Promptfoo ------------------------------------------------------
    with gr.Tab("🧪 Promptfoo") as tab_promptfoo:
        promptfoo_btn = gr.Button("🔄 Refresh", variant="secondary")
        promptfoo_out = gr.Markdown("*Loading…*")
        promptfoo_btn.click(fn=get_promptfoo_report, outputs=[promptfoo_out])

    # ---- Settings -------------------------------------------------------
    with gr.Tab("⚙️ Settings") as tab_settings:
        settings_btn = gr.Button("🔄 Refresh", variant="secondary")
        settings_out = gr.Markdown("*Loading…*")
        settings_btn.click(fn=get_settings_report, outputs=[settings_out])

    # ---- Logs -----------------------------------------------------------
    with gr.Tab("📋 Logs") as tab_logs:
        with gr.Row():
            log_lines_sl = gr.Slider(
                minimum=10, maximum=500, value=50, step=10, label="Lines", scale=2
            )
            log_level_dd = gr.Dropdown(
                choices=["ALL", "DEBUG", "INFO", "WARNING", "ERROR"],
                value="ALL",
                label="Level",
                scale=1,
            )
            log_service_dd = gr.Dropdown(
                choices=["ALL", "OLLAMA", "QDRANT", "MEILISEARCH", "LANGFUSE", "AGENT"],
                value="ALL",
                label="Service",
                scale=1,
            )
            logs_btn = gr.Button("🔄 Refresh", variant="secondary", scale=1)
        log_output = gr.Textbox(
            lines=24,
            label="Log output",
            interactive=False,
        )

        def _refresh_logs(lines: int, level: str, service: str) -> str:
            return get_logs(lines, level, service)

        logs_btn.click(
            fn=_refresh_logs,
            inputs=[log_lines_sl, log_level_dd, log_service_dd],
            outputs=[log_output],
        )

    # -----------------------------------------------------------------------
    # Auto-load on tab select
    # -----------------------------------------------------------------------
    tab_health.select(fn=get_health_report, outputs=[health_out])
    tab_qdrant.select(fn=_refresh_qdrant, outputs=[qdrant_stats, collection_dd])
    tab_langfuse.select(
        fn=get_langfuse_report, inputs=[time_range], outputs=[langfuse_out]
    )
    tab_promptfoo.select(fn=get_promptfoo_report, outputs=[promptfoo_out])
    tab_settings.select(fn=get_settings_report, outputs=[settings_out])
    tab_logs.select(
        fn=_refresh_logs,
        inputs=[log_lines_sl, log_level_dd, log_service_dd],
        outputs=[log_output],
    )
