"""Test script to verify configuration loading."""

if __name__ == "__main__":
    import json
    from src.config import get_config
    from src.logging_config import setup_logging, get_logger

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    # Load configuration
    logger.info("Loading configuration...")
    config = get_config()

    logger.info("Configuration loaded successfully!")
    logger.info(f"Environment: {config.env}")
    logger.info(f"Debug: {config.debug}")
    logger.info(f"Log Level: {config.log_level}")
    logger.info(f"Ollama Model: {config.ollama.model}")
    logger.info(f"Qdrant Collection: {config.qdrant.collection_name}")
    logger.info(f"Meilisearch Index: {config.meilisearch.index_name}")

    # Print service URLs
    logger.info(f"Ollama URL: {config.ollama.host}")
    logger.info(f"Qdrant URL: {config.qdrant.url}")
    logger.info(f"Meilisearch URL: {config.meilisearch.host}")
    logger.info(f"Langfuse URL: {config.langfuse.host}")

    # Display config as JSON for debugging
    logger.debug(
        "Full configuration: " + json.dumps(config.model_dump(), indent=2, default=str)
    )
