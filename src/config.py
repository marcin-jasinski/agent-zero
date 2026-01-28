"""Configuration management for Agent Zero using Pydantic v2.

This module provides centralized configuration management with validation,
type safety, and environment variable loading.

Environment Modes:
- development: Local experimentation, optional guards, detailed logging
- staging: Pre-production testing, guards enabled, moderate logging  
- production: Full security enforcement, observability required, minimal logging

Security Requirements by Environment:
- development: LLM Guard optional, Langfuse optional, debug allowed
- staging: LLM Guard required, Langfuse required, no debug mode
- production: LLM Guard required, Langfuse required, no debug mode, strict validation

Environment Variable Naming:
For nested configurations in AppConfig, use the nested delimiter format:
- Top-level: APP_<FIELD>=value (e.g., APP_ENV=production)
- Nested fields: APP_<PARENT>__<FIELD>=value (e.g., APP_SECURITY__LLM_GUARD_ENABLED=true)
- Note: Double underscore (__) separates parent from child field name
"""

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, field_validator, ConfigDict
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class OllamaConfig(BaseSettings):
    """Configuration for Ollama LLM service."""

    host: str = Field(default="http://localhost:11434", description="Ollama API host")
    model: str = Field(default="ministral-3:3b", description="Default LLM model name")
    embed_model: str = Field(default="nomic-embed-text-v2-moe", description="Embedding model name")
    timeout: int = Field(default=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    @property
    def base_url(self) -> str:
        """Alias for host for backwards compatibility."""
        return self.host

    class Config:
        env_prefix = "OLLAMA_"


class QdrantConfig(BaseSettings):
    """Configuration for Qdrant vector database."""

    host: str = Field(default="localhost", description="Qdrant server host")
    port: int = Field(default=6333, description="Qdrant server port")
    api_key: str = Field(default="", description="Optional API key")
    collection_name: str = Field(default="documents", description="Default collection name")
    vector_size: int = Field(default=768, description="Embedding vector size (must match embedding model output)")
    similarity_metric: str = Field(default="cosine", description="Vector similarity metric")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @property
    def url(self) -> str:
        """Construct Qdrant API URL."""
        return f"http://{self.host}:{self.port}"

    class Config:
        env_prefix = "QDRANT_"


class MeilisearchConfig(BaseSettings):
    """Configuration for Meilisearch full-text search."""

    host: str = Field(default="http://localhost:7700", description="Meilisearch API host")
    api_key: str = Field(default="", description="Optional API key")
    index_name: str = Field(default="documents", description="Default index name")
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @property
    def port(self) -> int:
        """Extract port from host URL, default to 7700."""
        # Handles both full URLs like "http://localhost:7700" and just host/port combinations
        if ":" in self.host.split("//")[-1]:  # Check if port is in the URL
            return int(self.host.split(":")[-1])
        return 7700

    class Config:
        env_prefix = "MEILISEARCH_"


class PostgresConfig(BaseSettings):
    """Configuration for PostgreSQL database."""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    db: str = Field(default="langfuse", description="Database name")
    user: str = Field(default="langfuse", description="Database user")
    password: str = Field(default="changeme123", description="Database password")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")

    @property
    def url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        )

    class Config:
        env_prefix = "POSTGRES_"


class LangfuseConfig(BaseSettings):
    """Configuration for Langfuse observability platform."""

    host: str = Field(default="http://localhost:3000", description="Langfuse API host")
    public_key: str = Field(default="", description="Langfuse public key")
    secret_key: str = Field(default="", description="Langfuse secret key")
    enabled: bool = Field(default=True, description="Enable Langfuse integration")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    batch_size: int = Field(default=100, description="Trace batch size")

    class Config:
        env_prefix = "LANGFUSE_"


class SecurityConfig(BaseSettings):
    """Configuration for security features."""

    llm_guard_enabled: bool = Field(
        default=False, description="Enable LLM Guard input/output scanning"
    )
    llm_guard_input_scan: bool = Field(default=True, description="Scan user inputs")
    llm_guard_output_scan: bool = Field(default=True, description="Scan LLM outputs")
    max_input_length: int = Field(default=10000, description="Max input length in chars")
    max_output_length: int = Field(default=5000, description="Max output length in chars")
    allowed_origins: list[str] = Field(
        default=["http://localhost:8501"], description="CORS allowed origins"
    )

    class Config:
        env_prefix = "LLM_GUARD_"


class AppConfig(BaseSettings):
    """Main application configuration."""

    app_name: str = Field(default="Agent Zero", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    env: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment mode"
    )
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="App host")
    port: int = Field(default=8501, description="Streamlit port")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(default="json", description="Log format")

    # Service configurations (nested)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig, description="Ollama config")
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig, description="Qdrant config")
    meilisearch: MeilisearchConfig = Field(
        default_factory=MeilisearchConfig, description="Meilisearch config"
    )
    postgres: PostgresConfig = Field(
        default_factory=PostgresConfig, description="PostgreSQL config"
    )
    langfuse: LangfuseConfig = Field(
        default_factory=LangfuseConfig, description="Langfuse config"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig, description="Security config"
    )

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment value."""
        valid_envs = {"development", "staging", "production"}
        if v not in valid_envs:
            raise ValueError(f"env must be one of {valid_envs}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v

    def model_post_init(self, __context):
        """Post-initialization validation and environment-specific enforcement.
        
        Raises:
            ValueError: If configuration violates environment-specific requirements
        """
        self._validate_environment_requirements()
        self._log_environment_configuration()

    def _validate_environment_requirements(self) -> None:
        """Validate configuration meets requirements for current environment.
        
        Development: Permissive settings for local experimentation
        Staging: Security guards enabled, observability required
        Production: Strict security and observability enforcement
        
        Raises:
            ValueError: If configuration violates environment requirements
        """
        if self.env == "production":
            # Production: Strict security and observability
            if self.debug:
                raise ValueError(
                    "Production environment error: debug mode must be disabled"
                )
            if not self.langfuse.enabled:
                raise ValueError(
                    "Production environment error: Langfuse observability is required. "
                    "Set LANGFUSE_ENABLED=true"
                )
            if not self.security.llm_guard_enabled:
                raise ValueError(
                    "Production environment error: LLM Guard security scanning is required. "
                    "Set LLM_GUARD_ENABLED=true"
                )
            if self.log_level == "DEBUG":
                raise ValueError(
                    "Production environment error: log_level must not be DEBUG. "
                    "Use INFO or higher"
                )
        
        elif self.env == "staging":
            # Staging: Security guards required, debug discouraged
            if self.debug:
                logger.warning(
                    "⚠️ Staging environment: debug mode enabled. "
                    "Consider disabling for production-like testing"
                )
            if not self.langfuse.enabled:
                raise ValueError(
                    "Staging environment error: Langfuse observability is required. "
                    "Set LANGFUSE_ENABLED=true"
                )
            if not self.security.llm_guard_enabled:
                raise ValueError(
                    "Staging environment error: LLM Guard security scanning is required. "
                    "Set LLM_GUARD_ENABLED=true"
                )
        
        elif self.env == "development":
            # Development: Flexible settings with warnings
            if not self.security.llm_guard_enabled:
                logger.info(
                    "ℹ️ Development mode: LLM Guard disabled. "
                    "Enable with LLM_GUARD_ENABLED=true to test security features"
                )
            if not self.langfuse.enabled:
                logger.info(
                    "ℹ️ Development mode: Langfuse disabled. "
                    "Enable with LANGFUSE_ENABLED=true to test observability"
                )

    def _log_environment_configuration(self) -> None:
        """Log current environment configuration for visibility."""
        logger.info("=" * 70)
        logger.info(f"🚀 Agent Zero Configuration Loaded")
        logger.info("=" * 70)
        logger.info(f"Environment: {self.env.upper()}")
        logger.info(f"Debug Mode: {self.debug}")
        logger.info(f"Log Level: {self.log_level}")
        logger.info(f"LLM Guard: {'✓ Enabled' if self.security.llm_guard_enabled else '✗ Disabled'}")
        logger.info(f"Langfuse: {'✓ Enabled' if self.langfuse.enabled else '✗ Disabled'}")
        logger.info("=" * 70)

    model_config = ConfigDict(
        extra="ignore",  # Ignore extra fields from env variables
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        env_nested_delimiter="__",
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """
    Get or create the application configuration.

    This function is cached to ensure only one instance of configuration
    is loaded throughout the application lifecycle.

    Returns:
        AppConfig: The validated application configuration instance.

    Raises:
        ValidationError: If configuration values are invalid.
    """
    config = AppConfig()

    logger = logging.getLogger(__name__)
    logger.info(
        f"Configuration loaded: env={config.env}, "
        f"debug={config.debug}, log_level={config.log_level}"
    )

    return config


# Convenience function for quick access
def config() -> AppConfig:
    """Get the current configuration instance."""
    return get_config()

