"""Unit tests for PromptfooClient service.

Tests cover scenario management, test execution, and version comparison.
All tests use mock data and do not depend on external services.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.models.promptfoo import TestScenario, TestStatus
from src.services.promptfoo_client import PromptfooClient


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def client(temp_data_dir):
    """Create PromptfooClient with temporary data directory."""
    return PromptfooClient(data_dir=temp_data_dir)


class TestPromptfooClientInitialization:
    """Tests for client initialization."""
    
    def test_client_creates_data_directory(self, temp_data_dir):
        """Test that client creates data directory if it doesn't exist."""
        data_path = Path(temp_data_dir) / "new_dir"
        assert not data_path.exists()
        
        client = PromptfooClient(data_dir=str(data_path))
        
        assert data_path.exists()
        assert (data_path / "scenarios.json").exists()
        assert (data_path / "test_runs.json").exists()
    
    def test_client_initializes_empty_files(self, client):
        """Test that client initializes empty JSON files."""
        scenarios = client.list_scenarios()
        runs = client.list_runs()
        
        assert scenarios == []
        assert runs == []


class TestScenarioManagement:
    """Tests for test scenario CRUD operations."""
    
    def test_create_scenario(self, client):
        """Test creating a new test scenario."""
        scenario = client.create_scenario(
            name="Test RAG",
            description="Test RAG retrieval functionality",
            input_text="What is Agent Zero?",
            expected_output="Agent Zero is a local agent builder",
            assertions=["not_empty", "contains: Agent"],
            tags=["rag", "test"],
        )
        
        assert scenario.id is not None
        assert scenario.name == "Test RAG"
        assert len(scenario.assertions) == 2
        assert "rag" in scenario.tags
    
    def test_list_scenarios(self, client):
        """Test listing all scenarios."""
        client.create_scenario("Test 1", "Desc 1", "Input 1")
        client.create_scenario("Test 2", "Desc 2", "Input 2")
        
        scenarios = client.list_scenarios()
        
        assert len(scenarios) == 2
        assert scenarios[0].name == "Test 1"
        assert scenarios[1].name == "Test 2"
    
    def test_list_scenarios_filtered_by_tags(self, client):
        """Test filtering scenarios by tags."""
        client.create_scenario("Test 1", "Desc", "Input", tags=["rag"])
        client.create_scenario("Test 2", "Desc", "Input", tags=["safety"])
        client.create_scenario("Test 3", "Desc", "Input", tags=["rag", "safety"])
        
        rag_scenarios = client.list_scenarios(tags=["rag"])
        
        assert len(rag_scenarios) == 2
        assert all("rag" in s.tags for s in rag_scenarios)
    
    def test_get_scenario_by_id(self, client):
        """Test retrieving a specific scenario."""
        created = client.create_scenario("Test", "Desc", "Input")
        
        retrieved = client.get_scenario(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test"
    
    def test_get_nonexistent_scenario(self, client):
        """Test retrieving a scenario that doesn't exist."""
        result = client.get_scenario("nonexistent-id")
        
        assert result is None
    
    def test_update_scenario(self, client):
        """Test updating an existing scenario."""
        scenario = client.create_scenario("Original", "Desc", "Input")
        
        updated = client.update_scenario(
            scenario.id,
            name="Updated Name",
            description="Updated description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.input_text == "Input"  # Unchanged
    
    def test_update_nonexistent_scenario(self, client):
        """Test updating a scenario that doesn't exist."""
        result = client.update_scenario("nonexistent-id", name="New Name")
        
        assert result is None
    
    def test_delete_scenario(self, client):
        """Test deleting a scenario."""
        scenario = client.create_scenario("To Delete", "Desc", "Input")
        
        deleted = client.delete_scenario(scenario.id)
        
        assert deleted is True
        assert client.get_scenario(scenario.id) is None
    
    def test_delete_nonexistent_scenario(self, client):
        """Test deleting a scenario that doesn't exist."""
        result = client.delete_scenario("nonexistent-id")
        
        assert result is False


class TestTestExecution:
    """Tests for test execution functionality."""
    
    def test_run_tests_without_scenarios(self, client):
        """Test running tests when no scenarios exist."""
        run = client.run_tests(prompt_version="v1.0")
        
        assert run.total_tests == 0
        assert run.results == []
    
    def test_run_all_tests(self, client):
        """Test running all available scenarios."""
        client.create_scenario("Test 1", "Desc", "Input 1")
        client.create_scenario("Test 2", "Desc", "Input 2")
        
        run = client.run_tests(prompt_version="v1.0")
        
        assert run.total_tests == 2
        assert run.passed_tests == 2  # Mock always passes
        assert run.pass_rate == 100.0
    
    def test_run_selected_tests(self, client):
        """Test running specific scenarios."""
        s1 = client.create_scenario("Test 1", "Desc", "Input 1")
        s2 = client.create_scenario("Test 2", "Desc", "Input 2")
        client.create_scenario("Test 3", "Desc", "Input 3")
        
        run = client.run_tests(
            prompt_version="v1.0",
            scenario_ids=[s1.id, s2.id],
        )
        
        assert run.total_tests == 2
    
    def test_run_tests_with_custom_callback(self, client):
        """Test running tests with custom agent callback."""
        client.create_scenario("Test", "Desc", "Input")
        
        def custom_agent(input_text):
            return f"Response to: {input_text}"
        
        run = client.run_tests(
            prompt_version="v1.0",
            agent_callback=custom_agent,
        )
        
        assert run.total_tests == 1
        assert "Response to: Input" in run.results[0].actual_output
    
    def test_assertion_not_empty(self, client):
        """Test 'not_empty' assertion."""
        client.create_scenario(
            "Test",
            "Desc",
            "Input",
            assertions=["not_empty"],
        )
        
        # Mock returns non-empty response
        run = client.run_tests(prompt_version="v1.0")
        
        assert run.results[0].status == TestStatus.PASSED
        assert run.results[0].assertion_results["not_empty"] is True
    
    def test_assertion_contains(self, client):
        """Test 'contains:' assertion."""
        client.create_scenario(
            "Test",
            "Desc",
            "Input",
            assertions=["contains: Mock"],
        )
        
        run = client.run_tests(prompt_version="v1.0")
        
        # Mock response contains "Mock"
        assert run.results[0].status == TestStatus.PASSED
        assert run.results[0].assertion_results["contains: Mock"] is True
    
    def test_assertion_no_toxic(self, client):
        """Test 'no_toxic' assertion."""
        client.create_scenario(
            "Test",
            "Desc",
            "Input",
            assertions=["no_toxic"],
        )
        
        run = client.run_tests(prompt_version="v1.0")
        
        assert run.results[0].status == TestStatus.PASSED
    
    def test_test_execution_error_handling(self, client):
        """Test error handling during test execution."""
        client.create_scenario("Test", "Desc", "Input")
        
        def failing_agent(input_text):
            raise Exception("Agent error")
        
        run = client.run_tests(
            prompt_version="v1.0",
            agent_callback=failing_agent,
        )
        
        assert run.results[0].status == TestStatus.ERROR
        assert "Agent error" in run.results[0].error_message


class TestRunHistory:
    """Tests for test run history management."""
    
    def test_list_runs(self, client):
        """Test listing test runs."""
        client.create_scenario("Test", "Desc", "Input")
        
        client.run_tests(prompt_version="v1.0")
        client.run_tests(prompt_version="v2.0")
        
        runs = client.list_runs()
        
        assert len(runs) == 2
        # Newest first
        assert runs[0].prompt_version == "v2.0"
        assert runs[1].prompt_version == "v1.0"
    
    def test_list_runs_filtered_by_version(self, client):
        """Test filtering runs by version."""
        client.create_scenario("Test", "Desc", "Input")
        
        client.run_tests(prompt_version="v1.0")
        client.run_tests(prompt_version="v1.0")
        client.run_tests(prompt_version="v2.0")
        
        v1_runs = client.list_runs(prompt_version="v1.0")
        
        assert len(v1_runs) == 2
        assert all(r.prompt_version == "v1.0" for r in v1_runs)
    
    def test_list_runs_with_limit(self, client):
        """Test limiting number of returned runs."""
        client.create_scenario("Test", "Desc", "Input")
        
        for i in range(10):
            client.run_tests(prompt_version=f"v{i}")
        
        runs = client.list_runs(limit=5)
        
        assert len(runs) == 5
    
    def test_get_run_by_id(self, client):
        """Test retrieving a specific run."""
        client.create_scenario("Test", "Desc", "Input")
        
        run = client.run_tests(prompt_version="v1.0")
        retrieved = client.get_run(run.id)
        
        assert retrieved is not None
        assert retrieved.id == run.id
        assert retrieved.prompt_version == "v1.0"
    
    def test_get_nonexistent_run(self, client):
        """Test retrieving a run that doesn't exist."""
        result = client.get_run("nonexistent-id")
        
        assert result is None


class TestVersionComparison:
    """Tests for version comparison functionality."""
    
    def test_compare_versions(self, client):
        """Test comparing two versions."""
        s1 = client.create_scenario("Test 1", "Desc", "Input 1")
        s2 = client.create_scenario("Test 2", "Desc", "Input 2")
        
        # Run v1.0 - will have 100% pass rate
        client.run_tests(prompt_version="v1.0")
        
        # Run v2.0 - will also have 100% pass rate
        client.run_tests(prompt_version="v2.0")
        
        comparison = client.compare_versions("v1.0", "v2.0")
        
        assert comparison is not None
        assert comparison.version_a == "v1.0"
        assert comparison.version_b == "v2.0"
        assert comparison.recommendation is not None
    
    def test_compare_versions_missing_run(self, client):
        """Test comparison when one version has no runs."""
        client.create_scenario("Test", "Desc", "Input")
        client.run_tests(prompt_version="v1.0")
        
        comparison = client.compare_versions("v1.0", "v2.0")
        
        assert comparison is None
    
    def test_get_summary_metrics_empty(self, client):
        """Test summary metrics with no data."""
        metrics = client.get_summary_metrics()
        
        assert metrics["total_scenarios"] == 0
        assert metrics["total_runs"] == 0
        assert metrics["average_pass_rate"] == 0.0
        assert metrics["latest_run"] is None
    
    def test_get_summary_metrics_with_data(self, client):
        """Test summary metrics with data."""
        client.create_scenario("Test 1", "Desc", "Input 1")
        client.create_scenario("Test 2", "Desc", "Input 2")
        
        client.run_tests(prompt_version="v1.0")
        client.run_tests(prompt_version="v2.0")
        
        metrics = client.get_summary_metrics()
        
        assert metrics["total_scenarios"] == 2
        assert metrics["total_runs"] == 2
        assert metrics["average_pass_rate"] == 100.0
        assert metrics["latest_run"] is not None
        assert metrics["latest_run"]["version"] == "v2.0"


class TestPersistence:
    """Tests for data persistence."""
    
    def test_scenarios_persist_across_instances(self, temp_data_dir):
        """Test that scenarios persist between client instances."""
        # Create scenario with first client instance
        client1 = PromptfooClient(data_dir=temp_data_dir)
        scenario = client1.create_scenario("Test", "Desc", "Input")
        
        # Load with second client instance
        client2 = PromptfooClient(data_dir=temp_data_dir)
        scenarios = client2.list_scenarios()
        
        assert len(scenarios) == 1
        assert scenarios[0].id == scenario.id
    
    def test_runs_persist_across_instances(self, temp_data_dir):
        """Test that runs persist between client instances."""
        # Create and run test with first client
        client1 = PromptfooClient(data_dir=temp_data_dir)
        client1.create_scenario("Test", "Desc", "Input")
        run = client1.run_tests(prompt_version="v1.0")
        
        # Load with second client
        client2 = PromptfooClient(data_dir=temp_data_dir)
        runs = client2.list_runs()
        
        assert len(runs) == 1
        assert runs[0].id == run.id
    
    def test_data_survives_corrupted_json(self, temp_data_dir, client):
        """Test graceful handling of corrupted JSON files."""
        # Corrupt the scenarios file
        scenarios_file = Path(temp_data_dir) / "scenarios.json"
        with open(scenarios_file, "w") as f:
            f.write("{invalid json")
        
        # Should return empty list, not crash
        scenarios = client.list_scenarios()
        
        assert scenarios == []
