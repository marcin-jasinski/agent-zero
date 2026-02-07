"""Unit tests for Promptfoo data models.

Tests cover TestScenario, TestResult, TestRun, and PromptComparison models.
"""

import pytest
from datetime import datetime

from src.models.promptfoo import (
    PromptComparison,
    PromptVersion,
    TestResult,
    TestRun,
    TestScenario,
    TestStatus,
)


class TestTestScenario:
    """Tests for TestScenario model."""
    
    def test_create_scenario_minimal(self):
        """Test creating scenario with minimal fields."""
        scenario = TestScenario(
            id="test-1",
            name="Test Scenario",
            description="Test description",
            input_text="Hello, how are you?",
        )
        
        assert scenario.id == "test-1"
        assert scenario.name == "Test Scenario"
        assert scenario.input_text == "Hello, how are you?"
        assert scenario.expected_output is None
        assert scenario.assertions == []
        assert scenario.tags == []
    
    def test_create_scenario_full(self):
        """Test creating scenario with all fields."""
        scenario = TestScenario(
            id="test-2",
            name="RAG Test",
            description="Test RAG retrieval",
            input_text="What is Agent Zero?",
            expected_output="Agent Zero is a local agent builder",
            assertions=["not_empty", "contains: Agent Zero"],
            tags=["rag", "knowledge_base"],
        )
        
        assert scenario.expected_output == "Agent Zero is a local agent builder"
        assert len(scenario.assertions) == 2
        assert "rag" in scenario.tags
    
    def test_scenario_to_dict(self):
        """Test converting scenario to dictionary."""
        scenario = TestScenario(
            id="test-3",
            name="Test",
            description="Desc",
            input_text="Input",
        )
        
        result = scenario.to_dict()
        
        assert result["id"] == "test-3"
        assert result["name"] == "Test"
        assert "created_at" in result
        assert isinstance(result["created_at"], str)


class TestTestResult:
    """Tests for TestResult model."""
    
    def test_create_passed_result(self):
        """Test creating a passed test result."""
        result = TestResult(
            scenario_id="test-1",
            status=TestStatus.PASSED,
            actual_output="This is the response",
            latency_ms=1234.5,
            token_count=25,
        )
        
        assert result.status == TestStatus.PASSED
        assert result.latency_ms == 1234.5
        assert result.token_count == 25
        assert result.error_message is None
    
    def test_create_failed_result_with_assertions(self):
        """Test creating failed result with assertion details."""
        result = TestResult(
            scenario_id="test-2",
            status=TestStatus.FAILED,
            actual_output="Wrong response",
            latency_ms=500.0,
            assertion_results={
                "not_empty": True,
                "contains: keyword": False,
            },
        )
        
        assert result.status == TestStatus.FAILED
        assert result.assertion_results["not_empty"] is True
        assert result.assertion_results["contains: keyword"] is False
    
    def test_create_error_result(self):
        """Test creating error result."""
        result = TestResult(
            scenario_id="test-3",
            status=TestStatus.ERROR,
            actual_output="",
            latency_ms=0.0,
            error_message="Connection timeout",
        )
        
        assert result.status == TestStatus.ERROR
        assert result.error_message == "Connection timeout"
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = TestResult(
            scenario_id="test-4",
            status=TestStatus.PASSED,
            actual_output="Output",
            latency_ms=100.0,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["scenario_id"] == "test-4"
        assert result_dict["status"] == "passed"
        assert result_dict["latency_ms"] == 100.0


class TestTestRun:
    """Tests for TestRun model."""
    
    def test_create_empty_run(self):
        """Test creating empty test run."""
        run = TestRun(
            id="run-1",
            prompt_version="v1.0",
        )
        
        assert run.id == "run-1"
        assert run.prompt_version == "v1.0"
        assert run.total_tests == 0
        assert run.pass_rate == 0.0
    
    def test_calculate_metrics_all_passed(self):
        """Test metrics calculation when all tests pass."""
        run = TestRun(
            id="run-2",
            prompt_version="v1.0",
            results=[
                TestResult("s1", TestStatus.PASSED, "out1", 100.0, token_count=10),
                TestResult("s2", TestStatus.PASSED, "out2", 200.0, token_count=20),
                TestResult("s3", TestStatus.PASSED, "out3", 300.0, token_count=30),
            ],
        )
        
        run.calculate_metrics()
        
        assert run.total_tests == 3
        assert run.passed_tests == 3
        assert run.failed_tests == 0
        assert run.error_tests == 0
        assert run.pass_rate == 100.0
        assert run.average_latency_ms == 200.0
        assert run.total_tokens == 60
    
    def test_calculate_metrics_mixed_results(self):
        """Test metrics calculation with mixed results."""
        run = TestRun(
            id="run-3",
            prompt_version="v2.0",
            results=[
                TestResult("s1", TestStatus.PASSED, "out1", 100.0),
                TestResult("s2", TestStatus.FAILED, "out2", 200.0),
                TestResult("s3", TestStatus.ERROR, "", 0.0),
                TestResult("s4", TestStatus.PASSED, "out4", 300.0),
            ],
        )
        
        run.calculate_metrics()
        
        assert run.total_tests == 4
        assert run.passed_tests == 2
        assert run.failed_tests == 1
        assert run.error_tests == 1
        assert run.pass_rate == 50.0
    
    def test_run_to_dict(self):
        """Test converting run to dictionary."""
        run = TestRun(
            id="run-4",
            prompt_version="v1.0",
        )
        run.calculate_metrics()
        
        run_dict = run.to_dict()
        
        assert run_dict["id"] == "run-4"
        assert run_dict["prompt_version"] == "v1.0"
        assert "total_tests" in run_dict
        assert "passed_tests" in run_dict


class TestPromptComparison:
    """Tests for PromptComparison model."""
    
    def test_analyze_improvement(self):
        """Test analysis when version B improves on version A."""
        run_a = TestRun(id="run-a", prompt_version="v1.0")
        run_a.total_tests = 10
        run_a.passed_tests = 7
        run_a.average_latency_ms = 1000.0
        
        run_b = TestRun(id="run-b", prompt_version="v2.0")
        run_b.total_tests = 10
        run_b.passed_tests = 9
        run_b.average_latency_ms = 800.0
        
        comparison = PromptComparison(
            version_a="v1.0",
            version_b="v2.0",
            run_a=run_a,
            run_b=run_b,
        )
        
        comparison.analyze()
        
        assert len(comparison.improvements) == 2  # Pass rate + latency
        assert len(comparison.regressions) == 0
        assert "v2.0 recommended" in comparison.recommendation
    
    def test_analyze_regression(self):
        """Test analysis when version B regresses."""
        run_a = TestRun(id="run-a", prompt_version="v1.0")
        run_a.total_tests = 10
        run_a.passed_tests = 9
        run_a.average_latency_ms = 500.0
        
        run_b = TestRun(id="run-b", prompt_version="v2.0")
        run_b.total_tests = 10
        run_b.passed_tests = 7
        run_b.average_latency_ms = 1200.0
        
        comparison = PromptComparison(
            version_a="v1.0",
            version_b="v2.0",
            run_a=run_a,
            run_b=run_b,
        )
        
        comparison.analyze()
        
        assert len(comparison.improvements) == 0
        assert len(comparison.regressions) == 2  # Pass rate + latency
        assert "v1.0 recommended" in comparison.recommendation
    
    def test_analyze_similar_versions(self):
        """Test analysis when versions are similar."""
        run_a = TestRun(id="run-a", prompt_version="v1.0")
        run_a.total_tests = 10
        run_a.passed_tests = 8
        run_a.average_latency_ms = 1000.0
        
        run_b = TestRun(id="run-b", prompt_version="v2.0")
        run_b.total_tests = 10
        run_b.passed_tests = 8
        run_b.average_latency_ms = 1000.0
        
        comparison = PromptComparison(
            version_a="v1.0",
            version_b="v2.0",
            run_a=run_a,
            run_b=run_b,
        )
        
        comparison.analyze()
        
        assert len(comparison.improvements) == 0
        assert len(comparison.regressions) == 0
        assert "similar" in comparison.recommendation.lower()
    
    def test_comparison_to_dict(self):
        """Test converting comparison to dictionary."""
        run_a = TestRun(id="run-a", prompt_version="v1.0")
        run_b = TestRun(id="run-b", prompt_version="v2.0")
        
        comparison = PromptComparison(
            version_a="v1.0",
            version_b="v2.0",
            run_a=run_a,
            run_b=run_b,
        )
        comparison.analyze()
        
        comp_dict = comparison.to_dict()
        
        assert comp_dict["version_a"] == "v1.0"
        assert comp_dict["version_b"] == "v2.0"
        assert "run_a" in comp_dict
        assert "recommendation" in comp_dict
