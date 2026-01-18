"""Shared test fixtures and mocks."""

import sys
import pytest
from unittest.mock import Mock, MagicMock


# Install llm-guard mocks BEFORE any test imports
def create_scanner_class(name):
    """Create a mock scanner class."""
    scanner_class = Mock()
    scanner_instance = Mock()
    scanner_instance.scan = Mock(return_value=("sanitized", True, 0.0))
    scanner_instance.__class__.__name__ = name
    scanner_class.return_value = scanner_instance
    return scanner_class


# Mock llm_guard module structure
mock_llm_guard = MagicMock()

# Mock input scanners
mock_input_scanners = MagicMock()
mock_input_scanners.PromptInjection = create_scanner_class("PromptInjection")
mock_input_scanners.Toxicity = create_scanner_class("Toxicity")
mock_input_scanners.TokenLimit = create_scanner_class("TokenLimit")
mock_input_scanners.Anonymize = create_scanner_class("Anonymize")

# Mock output scanners
mock_output_scanners = MagicMock()
mock_output_scanners.Bias = create_scanner_class("Bias")
mock_output_scanners.Deanonymize = create_scanner_class("Deanonymize")
mock_output_scanners.MaliciousURLs = create_scanner_class("MaliciousURLs")
mock_output_scanners.NoRefusal = create_scanner_class("NoRefusal")
mock_output_scanners.Relevance = create_scanner_class("Relevance")
mock_output_scanners.Sensitive = create_scanner_class("Sensitive")

# Mock vault
mock_vault_module = MagicMock()
mock_vault_module.Vault = Mock(return_value=Mock())

# Install mocks in sys.modules BEFORE any imports
sys.modules['llm_guard'] = mock_llm_guard
sys.modules['llm_guard.input_scanners'] = mock_input_scanners
sys.modules['llm_guard.output_scanners'] = mock_output_scanners
sys.modules['llm_guard.vault'] = mock_vault_module
