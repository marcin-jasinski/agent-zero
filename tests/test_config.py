"""Tests for configuration management and environment-specific validation."""

import pytest
from unittest.mock import patch, Mock
from pydantic import ValidationError

from src.config import (
    AppConfig,
    OllamaConfig,
    QdrantConfig,
    MeilisearchConfig,
    PostgresConfig,
    LangfuseConfig,
    SecurityConfig,
    get_config,
)


class TestOllamaConfig:
    """Test Ollama configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.host == "http://localhost:11434"
        assert config.model == "qwen3:4b"
        assert config.embed_model == "nomic-embed-text:latest"
        assert config.timeout == 300
        assert config.max_retries == 3

    def test_base_url_property(self):
        """Test base_url property alias."""
        config = OllamaConfig()
        assert config.base_url == config.host

    def test_custom_values(self):
        """Test custom configuration values."""
        config = OllamaConfig(
            host="http://custom:11434",
            model="llama2",
            timeout=600
        )
        assert config.host == "http://custom:11434"
        assert config.model == "llama2"
        assert config.timeout == 600


class TestQdrantConfig:
    """Test Qdrant configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = QdrantConfig()
        assert config.host == "localhost"
        assert config.port == 6333
        assert config.collection_name == "documents"
        assert config.vector_size == 768

    def test_url_property(self):
        """Test URL construction."""
        config = QdrantConfig(host="qdrant-server", port=6333)
        assert config.url == "http://qdrant-server:6333"

    def test_custom_vector_size(self):
        """Test custom vector size."""
        config = QdrantConfig(vector_size=1024)
        assert config.vector_size == 1024


class TestMeilisearchConfig:
    """Test Meilisearch configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MeilisearchConfig()
        assert config.host == "http://localhost:7700"
        assert config.index_name == "documents"
        assert config.timeout == 30

    def test_port_extraction(self):
        """Test port extraction from host URL."""
        config = MeilisearchConfig(host="http://localhost:7700")
        assert config.port == 7700

    def test_port_extraction_no_port(self):
        """Test port extraction when no port in URL."""
        config = MeilisearchConfig(host="http://localhost")
        assert config.port == 7700  # Default


class TestPostgresConfig:
    """Test PostgreSQL configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PostgresConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.db == "langfuse"
        assert config.user == "langfuse"

    def test_url_property(self):
        """Test database URL construction."""
        config = PostgresConfig(
            host="pg-server",
            port=5432,
            db="testdb",
            user="testuser",
            password="testpass"
        )
        expected = "postgresql://testuser:testpass@pg-server:5432/testdb"
        assert config.url == expected


class TestLangfuseConfig:
    """Test Langfuse configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LangfuseConfig()
        assert config.host == "http://localhost:3000"
        assert config.enabled is True
        assert config.batch_size == 100

    def test_disabled_by_config(self):
        """Test Langfuse can be disabled."""
        config = LangfuseConfig(enabled=False)
        assert config.enabled is False


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SecurityConfig()
        assert config.llm_guard_enabled is False
        assert config.llm_guard_input_scan is True
        assert config.llm_guard_output_scan is True
        assert config.max_input_length == 10000

    def test_custom_limits(self):
        """Test custom security limits."""
        config = SecurityConfig(
            llm_guard_enabled=True,
            max_input_length=5000,
            max_output_length=2000
        )
        assert config.llm_guard_enabled is True
        assert config.max_input_length == 5000
        assert config.max_output_length == 2000


class TestAppConfigDevelopmentEnvironment:
    """Test application configuration in development environment."""

    def test_development_defaults(self):
        """Test development environment defaults."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "APP_DEBUG": "false"
        }, clear=True):
            config = AppConfig()
            assert config.env == "development"
            assert config.debug is False
            assert config.log_level == "INFO"

    def test_development_allows_debug(self):
        """Test development allows debug mode."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "APP_DEBUG": "true"
        }, clear=True):
            config = AppConfig()
            assert config.env == "development"
            assert config.debug is True
            # Should not raise error

    def test_development_allows_disabled_guards(self):
        """Test development allows disabled security guards."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "LLM_GUARD_ENABLED": "false",
            "LANGFUSE_ENABLED": "false"
        }, clear=True):
            config = AppConfig()
            assert config.security.llm_guard_enabled is False
            assert config.langfuse.enabled is False
            # Should not raise error

    def test_development_allows_debug_logging(self):
        """Test development allows DEBUG log level."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "APP_LOG_LEVEL": "DEBUG"
        }, clear=True):
            config = AppConfig()
            assert config.log_level == "DEBUG"
            # Should not raise error


class TestAppConfigStagingEnvironment:
    """Test application configuration in staging environment."""

    def test_staging_requires_guards(self):
        """Test staging requires security guards."""
        with patch.dict("os.environ", {
            "APP_ENV": "staging",
            "LLM_GUARD_ENABLED": "false"
        }, clear=True):
            with pytest.raises(ValueError, match="Staging environment error.*LLM Guard"):
                AppConfig()

    def test_staging_requires_langfuse(self):
        """Test staging requires Langfuse."""
        with patch.dict("os.environ", {
            "APP_ENV": "staging",
            "LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "false"
        }, clear=True):
            with pytest.raises(ValueError, match="Staging environment error.*Langfuse"):
                AppConfig()

    def test_staging_warns_about_debug(self):
        """Test staging warns about debug mode."""
        with patch.dict("os.environ", {
            "APP_ENV": "staging",
            "APP_DEBUG": "true",
            "APP_SECURITY__LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "true",
            "APP_LOG_LEVEL": "INFO"
        }, clear=True):
            with patch("src.config.logger") as mock_logger:
                config = AppConfig()
                # Should not raise error but should warn
                assert any("debug mode enabled" in str(call).lower() 
                          for call in mock_logger.warning.call_args_list)

    def test_staging_valid_configuration(self):
        """Test staging with valid configuration."""
        with patch.dict("os.environ", {
            "APP_ENV": "staging",
            "APP_SECURITY__LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "true",
            "APP_DEBUG": "false",
            "APP_LOG_LEVEL": "INFO"
        }, clear=True):
            config = AppConfig()
            assert config.env == "staging"
            assert config.security.llm_guard_enabled is True
            assert config.langfuse.enabled is True


class TestAppConfigProductionEnvironment:
    """Test application configuration in production environment."""

    def test_production_requires_guards(self):
        """Test production requires LLM Guard."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "APP_DEBUG": "false",
            "LLM_GUARD_ENABLED": "false",
            "LANGFUSE_ENABLED": "true",
            "APP_LOG_LEVEL": "INFO"
        }, clear=True):
            with pytest.raises(ValueError, match="Production environment error.*LLM Guard"):
                AppConfig()

    def test_production_requires_langfuse(self):
        """Test production requires Langfuse."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "APP_DEBUG": "false",
            "LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "false",
            "APP_LOG_LEVEL": "INFO"
        }, clear=True):
            with pytest.raises(ValueError, match="Production environment error.*Langfuse"):
                AppConfig()

    def test_production_rejects_debug_mode(self):
        """Test production rejects debug mode."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "APP_DEBUG": "true",
            "LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "true"
        }, clear=True):
            with pytest.raises(ValueError, match="Production environment error.*debug"):
                AppConfig()

    def test_production_rejects_debug_logging(self):
        """Test production rejects DEBUG log level."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "APP_LOG_LEVEL": "DEBUG",
            "LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "true"
        }, clear=True):
            with pytest.raises(ValueError, match="Production environment error.*log_level"):
                AppConfig()

    def test_production_valid_configuration(self):
        """Test production with valid configuration."""
        with patch.dict("os.environ", {
            "APP_ENV": "production",
            "APP_DEBUG": "false",
            "APP_LOG_LEVEL": "INFO",
            "APP_SECURITY__LLM_GUARD_ENABLED": "true",
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_HOST": "http://localhost:3000",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": ""
        }, clear=True):
            config = AppConfig()
            assert config.env == "production"
            assert config.debug is False
            assert config.security.llm_guard_enabled is True
            assert config.langfuse.enabled is True
            assert config.log_level == "INFO"


class TestAppConfigValidation:
    """Test application configuration validation."""

    def test_invalid_environment(self):
        """Test invalid environment value."""
        with patch.dict("os.environ", {"APP_ENV": "invalid"}, clear=True):
            with pytest.raises(ValidationError):
                AppConfig()

    def test_invalid_log_level(self):
        """Test invalid log level value."""
        with patch.dict("os.environ", {"APP_LOG_LEVEL": "INVALID"}, clear=True):
            with pytest.raises(ValidationError):
                AppConfig()

    def test_env_validation(self):
        """Test environment validation method."""
        # Test only development since staging/production need guards
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "APP_DEBUG": "false"
        }, clear=True):
            config = AppConfig()
            assert config.env == "development"


class TestAppConfigLogging:
    """Test application configuration logging."""

    def test_configuration_logs_environment(self):
        """Test that configuration logs environment details."""
        with patch.dict("os.environ", {
            "APP_ENV": "development"
        }, clear=True):
            with patch("src.config.logger") as mock_logger:
                config = AppConfig()
                # Should log configuration details
                mock_logger.info.assert_called()
                # Check for environment logging
                log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("Environment: DEVELOPMENT" in call for call in log_calls)


class TestGetConfig:
    """Test get_config singleton function."""

    def test_get_config_returns_instance(self):
        """Test get_config returns AppConfig instance."""
        with patch.dict("os.environ", {"APP_ENV": "development"}, clear=True):
            # Clear the cache first
            get_config.cache_clear()
            config = get_config()
            assert isinstance(config, AppConfig)

    def test_get_config_caches_instance(self):
        """Test get_config caches the instance."""
        with patch.dict("os.environ", {"APP_ENV": "development"}, clear=True):
            # Clear the cache first
            get_config.cache_clear()
            config1 = get_config()
            config2 = get_config()
            # Should return same instance
            assert config1 is config2

    def test_get_config_logs_configuration(self):
        """Test get_config logs configuration details."""
        with patch.dict("os.environ", {"APP_ENV": "development"}, clear=True):
            with patch("src.config.logger") as mock_logger:
                get_config.cache_clear()
                config = get_config()
                # Should log configuration
                mock_logger.info.assert_called()


class TestNestedConfigurationAccess:
    """Test nested configuration access."""

    def test_access_nested_ollama_config(self):
        """Test accessing nested Ollama configuration."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "OLLAMA_HOST": "http://custom:11434"
        }, clear=True):
            config = AppConfig()
            assert config.ollama.host == "http://custom:11434"

    def test_access_nested_qdrant_config(self):
        """Test accessing nested Qdrant configuration."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "QDRANT_PORT": "6334"
        }, clear=True):
            config = AppConfig()
            assert config.qdrant.port == 6334

    def test_access_nested_security_config(self):
        """Test accessing nested security configuration."""
        with patch.dict("os.environ", {
            "APP_ENV": "development",
            "LLM_GUARD_MAX_INPUT_LENGTH": "5000"
        }, clear=True):
            config = AppConfig()
            assert config.security.max_input_length == 5000
