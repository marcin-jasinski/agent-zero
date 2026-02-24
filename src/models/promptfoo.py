"""Data models for Promptfoo prompt testing and versioning.

This module defines the data structures for managing prompt test scenarios,
test runs, and version comparison in the Agent Zero system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class TestStatus(str, Enum):
    """Test execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

    __test__ = False


class PromptVersion(str, Enum):
    """Prompt version tracking."""
    
    V1 = "v1.0"
    V2 = "v2.0"
    V3 = "v3.0"
    LATEST = "latest"


@dataclass
class TestScenario:
    """A single test scenario for prompt evaluation.
    
    Attributes:
        id: Unique identifier for the test scenario
        name: Human-readable test name
        description: Detailed description of what is being tested
        input_text: The user input/query to test
        expected_output: Expected response or behavior
        assertions: List of assertions to validate (e.g., "contains X", "no_toxic")
        tags: Categorization tags (e.g., ["rag", "safety", "factual"])
        created_at: Timestamp of creation
        updated_at: Timestamp of last modification
    """
    
    id: str
    name: str
    description: str
    input_text: str
    expected_output: Optional[str] = None
    assertions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    __test__ = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_text": self.input_text,
            "expected_output": self.expected_output,
            "assertions": self.assertions,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TestResult:
    """Result of a single test execution.
    
    Attributes:
        scenario_id: ID of the test scenario that was executed
        status: Test execution status (passed/failed/error)
        actual_output: The actual response from the agent
        latency_ms: Response time in milliseconds
        token_count: Number of tokens used (if available)
        assertion_results: Dict mapping assertion to pass/fail status
        error_message: Error details if status is ERROR
        executed_at: Timestamp of execution
    """
    
    scenario_id: str
    status: TestStatus
    actual_output: str
    latency_ms: float
    token_count: Optional[int] = None
    assertion_results: Dict[str, bool] = field(default_factory=dict)
    error_message: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)
    __test__ = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "status": self.status.value,
            "actual_output": self.actual_output,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "assertion_results": self.assertion_results,
            "error_message": self.error_message,
            "executed_at": self.executed_at.isoformat(),
        }


@dataclass
class TestRun:
    """A complete test run across multiple scenarios.
    
    Attributes:
        id: Unique identifier for this test run
        prompt_version: The prompt version being tested
        results: List of test results for each scenario
        started_at: Timestamp when run started
        completed_at: Timestamp when run completed
        total_tests: Total number of tests executed
        passed_tests: Number of tests that passed
        failed_tests: Number of tests that failed
        error_tests: Number of tests that errored
        average_latency_ms: Average response time across all tests
        total_tokens: Total tokens used in the run
    """
    
    id: str
    prompt_version: str
    results: List[TestResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    average_latency_ms: float = 0.0
    total_tokens: int = 0
    __test__ = False
    
    def calculate_metrics(self) -> None:
        """Calculate summary metrics from results."""
        self.total_tests = len(self.results)
        self.passed_tests = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        self.failed_tests = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        self.error_tests = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        
        if self.results:
            self.average_latency_ms = sum(r.latency_ms for r in self.results) / len(self.results)
            self.total_tokens = sum(r.token_count or 0 for r in self.results)
    
    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "prompt_version": self.prompt_version,
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "average_latency_ms": self.average_latency_ms,
            "total_tokens": self.total_tokens,
        }


@dataclass
class PromptComparison:
    """Comparison between two prompt versions.
    
    Attributes:
        version_a: First version identifier
        version_b: Second version identifier
        run_a: Test run for version A
        run_b: Test run for version B
        improvements: List of metrics that improved in version B
        regressions: List of metrics that regressed in version B
        recommendation: Which version is recommended and why
    """
    
    version_a: str
    version_b: str
    run_a: TestRun
    run_b: TestRun
    improvements: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)
    recommendation: str = ""
    
    def analyze(self) -> None:
        """Analyze differences and generate recommendation."""
        self.improvements = []
        self.regressions = []
        
        # Compare pass rates
        if self.run_b.pass_rate > self.run_a.pass_rate:
            self.improvements.append(
                f"Pass rate improved: {self.run_a.pass_rate:.1f}% → {self.run_b.pass_rate:.1f}%"
            )
        elif self.run_b.pass_rate < self.run_a.pass_rate:
            self.regressions.append(
                f"Pass rate regressed: {self.run_a.pass_rate:.1f}% → {self.run_b.pass_rate:.1f}%"
            )
        
        # Compare latency
        if self.run_b.average_latency_ms < self.run_a.average_latency_ms:
            improvement_pct = (
                (self.run_a.average_latency_ms - self.run_b.average_latency_ms)
                / self.run_a.average_latency_ms
                * 100
            )
            self.improvements.append(
                f"Latency improved: {improvement_pct:.1f}% faster"
            )
        elif self.run_b.average_latency_ms > self.run_a.average_latency_ms:
            regression_pct = (
                (self.run_b.average_latency_ms - self.run_a.average_latency_ms)
                / self.run_a.average_latency_ms
                * 100
            )
            self.regressions.append(
                f"Latency regressed: {regression_pct:.1f}% slower"
            )
        
        # Generate recommendation
        if len(self.improvements) > len(self.regressions):
            self.recommendation = f"✅ {self.version_b} recommended (more improvements)"
        elif len(self.regressions) > len(self.improvements):
            self.recommendation = f"⚠️ {self.version_a} recommended (avoid regressions)"
        else:
            self.recommendation = f"🤝 Both versions similar, choose based on specific needs"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version_a": self.version_a,
            "version_b": self.version_b,
            "run_a": self.run_a.to_dict(),
            "run_b": self.run_b.to_dict(),
            "improvements": self.improvements,
            "regressions": self.regressions,
            "recommendation": self.recommendation,
        }
