"""LLM Guard security middleware for Agent Zero.

This module implements input/output scanning to detect and block:
- Prompt injection attacks
- Toxic/harmful content
- PII leakage
- Malicious instructions

Uses the llm-guard library with pre-configured scanners.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from llm_guard.input_scanners import (
        PromptInjection,
        Toxicity,
        TokenLimit,
        Anonymize,
    )
    from llm_guard.output_scanners import (
        Bias,
        Deanonymize,
        MaliciousURLs,
        NoRefusal,
        Relevance,
        Sensitive,
    )
    from llm_guard.vault import Vault

    LLM_GUARD_AVAILABLE = True
except ImportError:
    LLM_GUARD_AVAILABLE = False

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification for security violations."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScanResult:
    """Result of security scan operation.

    Attributes:
        is_safe: Whether the content passed all security checks
        threat_level: Classification of detected threat
        violations: List of detected security violations
        sanitized_content: Content after sanitization (if applicable)
        scanner_results: Detailed results from each scanner
    """

    is_safe: bool
    threat_level: ThreatLevel
    violations: List[str]
    sanitized_content: Optional[str] = None
    scanner_results: Dict[str, Any] = None


class LLMGuard:
    """Security guard for LLM inputs and outputs.

    This class implements defense-in-depth security scanning using
    multiple layers of protection from the llm-guard library.
    """

    def __init__(
        self,
        enabled: bool = True,
        input_scan_enabled: bool = True,
        output_scan_enabled: bool = True,
        max_input_length: int = 10000,
        max_output_length: int = 5000,
    ) -> None:
        """Initialize LLM Guard with security scanners.

        Args:
            enabled: Master switch for all security scanning
            input_scan_enabled: Enable input scanning
            output_scan_enabled: Enable output scanning
            max_input_length: Maximum allowed input length in characters
            max_output_length: Maximum allowed output length in characters

        Raises:
            ImportError: If llm-guard library is not installed
        """
        self.enabled = enabled
        self.input_scan_enabled = input_scan_enabled
        self.output_scan_enabled = output_scan_enabled
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length

        if not LLM_GUARD_AVAILABLE:
            logger.warning(
                "llm-guard library not available. Security scanning disabled. "
                "Install with: pip install llm-guard"
            )
            self.enabled = False

        # Initialize scanners only if enabled
        self.input_scanners = []
        self.output_scanners = []
        self.vault = None

        if self.enabled and LLM_GUARD_AVAILABLE:
            self._initialize_scanners()
            logger.info(
                f"LLM Guard initialized: input_scan={input_scan_enabled}, "
                f"output_scan={output_scan_enabled}"
            )

    def _initialize_scanners(self) -> None:
        """Initialize input and output security scanners."""
        try:
            # Initialize vault for PII anonymization
            self.vault = Vault()

            # Input scanners
            if self.input_scan_enabled:
                self.input_scanners = [
                    PromptInjection(threshold=0.5),  # Detect prompt injection attacks
                    Toxicity(threshold=0.7),  # Detect toxic/harmful content
                    TokenLimit(
                        limit=self.max_input_length // 4,  # Approximate tokens
                        encoding_name="cl100k_base",
                    ),
                    Anonymize(vault=self.vault),  # Remove PII
                ]

            # Output scanners
            if self.output_scan_enabled:
                self.output_scanners = [
                    Bias(threshold=0.7),  # Detect biased responses
                    MaliciousURLs(),  # Detect malicious URLs
                    Sensitive(
                        entity_types=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
                    ),
                    Deanonymize(vault=self.vault),  # Restore anonymized entities
                ]

            logger.info(
                f"Initialized {len(self.input_scanners)} input scanners, "
                f"{len(self.output_scanners)} output scanners"
            )

        except Exception as e:
            logger.error(f"Failed to initialize LLM Guard scanners: {e}", exc_info=True)
            self.enabled = False

    def scan_user_input(self, user_input: str) -> ScanResult:
        """Scan user input for security threats.

        Args:
            user_input: User-provided input text to scan

        Returns:
            ScanResult with safety status and sanitized content

        Raises:
            ValueError: If input is empty or None
        """
        if not user_input:
            raise ValueError("Input cannot be empty or None")

        # Fast path: scanning disabled
        if not self.enabled or not self.input_scan_enabled:
            return ScanResult(
                is_safe=True,
                threat_level=ThreatLevel.SAFE,
                violations=[],
                sanitized_content=user_input,
            )

        try:
            # Check input length
            if len(user_input) > self.max_input_length:
                logger.warning(
                    f"Input exceeds max length: {len(user_input)} > {self.max_input_length}"
                )
                return ScanResult(
                    is_safe=False,
                    threat_level=ThreatLevel.HIGH,
                    violations=["Input exceeds maximum allowed length"],
                    sanitized_content=user_input[: self.max_input_length],
                )

            # Run all input scanners
            sanitized_input = user_input
            violations = []
            scanner_results = {}

            for scanner in self.input_scanners:
                scanner_name = scanner.__class__.__name__
                try:
                    sanitized_input, is_valid, risk_score = scanner.scan(
                        prompt=sanitized_input
                    )

                    scanner_results[scanner_name] = {
                        "valid": is_valid,
                        "risk_score": risk_score,
                    }

                    if not is_valid:
                        violations.append(f"{scanner_name} detected risk (score: {risk_score})")
                        logger.warning(
                            f"Input failed {scanner_name} scan: risk_score={risk_score}"
                        )

                except Exception as e:
                    logger.error(f"Scanner {scanner_name} failed: {e}")
                    scanner_results[scanner_name] = {"error": str(e)}

            # Determine threat level
            threat_level = self._calculate_threat_level(violations)
            is_safe = threat_level in [ThreatLevel.SAFE, ThreatLevel.LOW]

            result = ScanResult(
                is_safe=is_safe,
                threat_level=threat_level,
                violations=violations,
                sanitized_content=sanitized_input if is_safe else None,
                scanner_results=scanner_results,
            )

            if not is_safe:
                logger.warning(
                    f"Input blocked: threat_level={threat_level.value}, "
                    f"violations={violations}"
                )

            return result

        except Exception as e:
            logger.error(f"Error scanning user input: {e}", exc_info=True)
            # Fail open for non-critical errors
            return ScanResult(
                is_safe=True,
                threat_level=ThreatLevel.SAFE,
                violations=[f"Scanner error: {str(e)}"],
                sanitized_content=user_input,
            )

    def scan_llm_output(
        self, llm_output: str, original_prompt: Optional[str] = None
    ) -> ScanResult:
        """Scan LLM output for security issues.

        Args:
            llm_output: LLM-generated output text to scan
            original_prompt: Original user prompt (for relevance check)

        Returns:
            ScanResult with safety status and sanitized content

        Raises:
            ValueError: If output is empty or None
        """
        if not llm_output:
            raise ValueError("Output cannot be empty or None")

        # Fast path: scanning disabled
        if not self.enabled or not self.output_scan_enabled:
            return ScanResult(
                is_safe=True,
                threat_level=ThreatLevel.SAFE,
                violations=[],
                sanitized_content=llm_output,
            )

        try:
            # Check output length
            if len(llm_output) > self.max_output_length:
                logger.warning(
                    f"Output exceeds max length: {len(llm_output)} > {self.max_output_length}"
                )
                return ScanResult(
                    is_safe=False,
                    threat_level=ThreatLevel.MEDIUM,
                    violations=["Output exceeds maximum allowed length"],
                    sanitized_content=llm_output[: self.max_output_length],
                )

            # Run all output scanners
            sanitized_output = llm_output
            violations = []
            scanner_results = {}

            for scanner in self.output_scanners:
                scanner_name = scanner.__class__.__name__
                try:
                    # Relevance scanner requires prompt
                    if scanner_name == "Relevance" and original_prompt:
                        sanitized_output, is_valid, risk_score = scanner.scan(
                            prompt=original_prompt, output=sanitized_output
                        )
                    else:
                        sanitized_output, is_valid, risk_score = scanner.scan(
                            prompt="", output=sanitized_output
                        )

                    scanner_results[scanner_name] = {
                        "valid": is_valid,
                        "risk_score": risk_score,
                    }

                    if not is_valid:
                        violations.append(f"{scanner_name} detected risk (score: {risk_score})")
                        logger.warning(
                            f"Output failed {scanner_name} scan: risk_score={risk_score}"
                        )

                except Exception as e:
                    logger.error(f"Scanner {scanner_name} failed: {e}")
                    scanner_results[scanner_name] = {"error": str(e)}

            # Determine threat level
            threat_level = self._calculate_threat_level(violations)
            is_safe = threat_level in [ThreatLevel.SAFE, ThreatLevel.LOW]

            result = ScanResult(
                is_safe=is_safe,
                threat_level=threat_level,
                violations=violations,
                sanitized_content=sanitized_output if is_safe else None,
                scanner_results=scanner_results,
            )

            if not is_safe:
                logger.warning(
                    f"Output blocked: threat_level={threat_level.value}, "
                    f"violations={violations}"
                )

            return result

        except Exception as e:
            logger.error(f"Error scanning LLM output: {e}", exc_info=True)
            # Fail open for non-critical errors
            return ScanResult(
                is_safe=True,
                threat_level=ThreatLevel.SAFE,
                violations=[f"Scanner error: {str(e)}"],
                sanitized_content=llm_output,
            )

    def _calculate_threat_level(self, violations: List[str]) -> ThreatLevel:
        """Calculate overall threat level from violations.

        Args:
            violations: List of detected violations

        Returns:
            Aggregate threat level classification
        """
        if not violations:
            return ThreatLevel.SAFE

        # Check for critical violations
        critical_keywords = ["injection", "malicious", "credit_card"]
        high_keywords = ["toxic", "sensitive", "pii"]

        violations_lower = [v.lower() for v in violations]

        if any(kw in v for v in violations_lower for kw in critical_keywords):
            return ThreatLevel.CRITICAL

        if any(kw in v for v in violations_lower for kw in high_keywords):
            return ThreatLevel.HIGH

        if len(violations) >= 3:
            return ThreatLevel.HIGH
        elif len(violations) >= 2:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    def get_status(self) -> Dict[str, Any]:
        """Get current guard status and configuration.

        Returns:
            Dictionary with guard status and configuration
        """
        return {
            "enabled": self.enabled,
            "input_scan_enabled": self.input_scan_enabled,
            "output_scan_enabled": self.output_scan_enabled,
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "llm_guard_available": LLM_GUARD_AVAILABLE,
            "input_scanners": [s.__class__.__name__ for s in self.input_scanners],
            "output_scanners": [s.__class__.__name__ for s in self.output_scanners],
        }
