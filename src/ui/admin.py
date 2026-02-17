"""Agent Zero (L.A.B.) - Chainlit Admin Report Helpers.

This module contains report builders used by the Chainlit A.P.I. admin actions.
It keeps admin formatting logic separated from message-handler orchestration.
"""

from typing import Any, Mapping


def build_system_health_report(statuses: Mapping[str, Any]) -> str:
    """Build a markdown system health report from service statuses.

    Args:
        statuses: Mapping of service name to health status objects.

    Returns:
        Markdown report string suitable for Chainlit messages.
    """
    report = "# 🏥 System Health Report\n\n"
    all_healthy = all(status.is_healthy for status in statuses.values()) if statuses else False

    if all_healthy:
        report += "✅ **All services operational**\n\n"
    else:
        report += "⚠️ **Some services have issues**\n\n"

    report += "## Service Status\n\n"

    for _name, status in statuses.items():
        icon = "✅" if status.is_healthy else "❌"
        report += f"### {icon} {status.name}\n"
        report += f"- **Status**: {'Healthy' if status.is_healthy else 'Unhealthy'}\n"
        report += f"- **Message**: {status.message}\n"

        if getattr(status, "details", None):
            report += f"- **Details**: {', '.join(f'{k}={v}' for k, v in status.details.items())}\n"

        report += "\n"

    return report


def build_qdrant_report(collection_name: str, collections: list[dict[str, Any]], collection_stats: dict[str, Any] | None) -> str:
    """Build a markdown report for Qdrant collection status.

    Args:
        collection_name: Target collection configured for Agent Zero.
        collections: All available collections from Qdrant.
        collection_stats: Stats for the target collection if available.

    Returns:
        Markdown report string.
    """
    report = "# 📊 Qdrant Vector Database Info\n\n"
    report += f"**Target Collection**: `{collection_name}`\n\n"

    if collection_stats:
        report += "## Collection Details\n\n"
        report += "- **Status**: ✅ Active\n"
        report += f"- **Vector Count**: {collection_stats['vectors_count']:,}\n"
        report += f"- **Points Count**: {collection_stats['points_count']:,}\n"
        report += f"- **Vector Size**: {collection_stats['vector_size']}\n"
        report += f"- **Distance Metric**: {collection_stats['distance_metric']}\n"
    else:
        report += "- **Status**: ⚠️ Collection not found\n"
        report += "\nThe collection will be created automatically when you upload your first document.\n"

    if collections:
        report += f"\n## All Collections ({len(collections)})\n\n"
        for collection in collections:
            report += f"- **{collection['name']}**: {collection['vectors_count']:,} vectors\n"

    return report


def build_settings_report(config: Any) -> str:
    """Build a markdown settings overview from application config.

    Args:
        config: App configuration object.

    Returns:
        Markdown report string.
    """
    report = "# ⚙️ Agent Zero Configuration\n\n"
    report += "## Application\n\n"
    report += f"- **Version**: {config.app_version}\n"
    report += f"- **Environment**: {config.env}\n"
    report += f"- **Debug Mode**: {'✅ Enabled' if config.debug else '❌ Disabled'}\n"
    report += f"- **Log Level**: {config.log_level}\n\n"

    report += "## LLM Configuration\n\n"
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
    report += f"- **Input Scanning**: {'✅ Enabled' if config.security.llm_guard_input_scan else '❌ Disabled'}\n"
    report += f"- **Output Scanning**: {'✅ Enabled' if config.security.llm_guard_output_scan else '❌ Disabled'}\n"
    report += f"- **Max Input Length**: {config.security.max_input_length:,} chars\n"
    report += f"- **Max Output Length**: {config.security.max_output_length:,} chars\n\n"

    report += "## Observability\n\n"
    report += f"- **Langfuse**: {'✅ Enabled' if config.langfuse.enabled else '❌ Disabled'}\n"
    if config.langfuse.enabled:
        report += f"- **Host**: {config.langfuse.host}\n\n"

    return report
