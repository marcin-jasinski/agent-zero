"""Promptfoo client for prompt testing and version management.

This service manages prompt test scenarios, executes test runs,
and provides version comparison functionality for Agent Zero.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.models.promptfoo import (
    PromptComparison,
    TestResult,
    TestRun,
    TestScenario,
    TestStatus,
)


logger = logging.getLogger(__name__)


class PromptfooClient:
    """Client for managing prompt tests and versions.
    
    This is a local implementation that stores test scenarios and results
    in JSON files. In a production environment, this could be replaced with
    API calls to an external Promptfoo service.
    
    Attributes:
        data_dir: Directory where test scenarios and results are stored
        scenarios_file: Path to scenarios JSON file
        runs_file: Path to test runs JSON file
    """

    def __init__(self, data_dir: str = "data/promptfoo"):
        """Initialize Promptfoo client.
        
        Args:
            data_dir: Directory path for storing test data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.scenarios_file = self.data_dir / "scenarios.json"
        self.runs_file = self.data_dir / "test_runs.json"

        # Initialize files if they don't exist
        if not self.scenarios_file.exists():
            self._save_scenarios([])
        if not self.runs_file.exists():
            self._save_runs([])

        logger.info("PromptfooClient initialized with data_dir=%s", data_dir)

    # ========== Test Scenario Management ==========

    def create_scenario(  # pylint: disable=too-many-positional-arguments
        self,
        name: str,
        description: str,
        input_text: str,
        expected_output: Optional[str] = None,
        assertions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> TestScenario:
        """Create a new test scenario.
        
        Args:
            name: Test scenario name
            description: Detailed description
            input_text: User input to test
            expected_output: Expected response (optional)
            assertions: List of assertions to validate
            tags: Categorization tags
            
        Returns:
            Created TestScenario instance
        """
        scenario = TestScenario(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            input_text=input_text,
            expected_output=expected_output,
            assertions=assertions or [],
            tags=tags or [],
        )

        scenarios = self.list_scenarios()
        scenarios.append(scenario)
        self._save_scenarios(scenarios)

        logger.info("Created test scenario: %s - %s", scenario.id, name)
        return scenario

    def list_scenarios(self, tags: Optional[List[str]] = None) -> List[TestScenario]:
        """List all test scenarios, optionally filtered by tags.
        
        Args:
            tags: Filter scenarios by these tags (OR logic)
            
        Returns:
            List of TestScenario instances
        """
        scenarios = self._load_scenarios()

        if tags:
            scenarios = [
                s for s in scenarios
                if any(tag in s.tags for tag in tags)
            ]

        return scenarios

    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Get a specific test scenario by ID.
        
        Args:
            scenario_id: Unique scenario identifier
            
        Returns:
            TestScenario if found, None otherwise
        """
        scenarios = self.list_scenarios()
        for scenario in scenarios:
            if scenario.id == scenario_id:
                return scenario
        return None

    def update_scenario(self, scenario_id: str, **updates) -> Optional[TestScenario]:
        """Update an existing test scenario.
        
        Args:
            scenario_id: ID of scenario to update
            **updates: Fields to update (name, description, etc.)
            
        Returns:
            Updated TestScenario if found, None otherwise
        """
        scenarios = self.list_scenarios()
        for _, scenario in enumerate(scenarios):
            if scenario.id == scenario_id:
                # Update fields
                for key, value in updates.items():
                    if hasattr(scenario, key):
                        setattr(scenario, key, value)
                scenario.updated_at = datetime.now()

                self._save_scenarios(scenarios)
                logger.info("Updated scenario: %s", scenario_id)
                return scenario

        logger.warning("Scenario not found: %s", scenario_id)
        return None

    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete a test scenario.
        
        Args:
            scenario_id: ID of scenario to delete
            
        Returns:
            True if deleted, False if not found
        """
        scenarios = self.list_scenarios()
        original_count = len(scenarios)
        scenarios = [s for s in scenarios if s.id != scenario_id]

        if len(scenarios) < original_count:
            self._save_scenarios(scenarios)
            logger.info("Deleted scenario: %s", scenario_id)
            return True

        logger.warning("Scenario not found: %s", scenario_id)
        return False

    # ========== Test Execution ==========

    def run_tests(
        self,
        prompt_version: str,
        scenario_ids: Optional[List[str]] = None,
        agent_callback=None,
    ) -> TestRun:
        """Execute test scenarios and record results.
        
        Args:
            prompt_version: Version identifier for the prompt being tested
            scenario_ids: Specific scenarios to run (None = all)
            agent_callback: Callable that takes input_text and returns response
            
        Returns:
            TestRun instance with results
        """
        # Get scenarios to test
        all_scenarios = self.list_scenarios()
        if scenario_ids:
            scenarios = [s for s in all_scenarios if s.id in scenario_ids]
        else:
            scenarios = all_scenarios

        if not scenarios:
            logger.warning("No scenarios to test")
            return TestRun(
                id=str(uuid.uuid4()),
                prompt_version=prompt_version,
            )

        # Create test run
        test_run = TestRun(
            id=str(uuid.uuid4()),
            prompt_version=prompt_version,
            started_at=datetime.now(),
        )

        logger.info(
            "Starting test run %s for %s with %s scenarios",
            test_run.id, prompt_version, len(scenarios),
        )

        # Execute each scenario
        for scenario in scenarios:
            result = self._execute_scenario(scenario, agent_callback)
            test_run.results.append(result)

        # Finalize metrics
        test_run.completed_at = datetime.now()
        test_run.calculate_metrics()

        # Save test run
        runs = self._load_runs()
        runs.append(test_run)
        self._save_runs(runs)

        logger.info(
            "Test run completed: %d/%d passed (%.1f%%)",
            test_run.passed_tests, test_run.total_tests, test_run.pass_rate,
        )

        return test_run

    def _execute_scenario(
        self,
        scenario: TestScenario,
        agent_callback=None,
    ) -> TestResult:
        """Execute a single test scenario.
        
        Args:
            scenario: Test scenario to execute
            agent_callback: Function to call agent (or mock for testing)
            
        Returns:
            TestResult instance
        """
        start_time = datetime.now()

        try:
            # Call agent (or use mock response)
            if agent_callback:
                actual_output = agent_callback(scenario.input_text)
                token_count = len(actual_output.split())  # Rough estimate
            else:
                # Mock response for testing
                actual_output = f"Mock response for: {scenario.input_text}"
                token_count = 10

            # Calculate latency
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            # Run assertions
            assertion_results = {}
            all_passed = True

            for assertion in scenario.assertions:
                passed = self._check_assertion(assertion, actual_output, scenario.expected_output)
                assertion_results[assertion] = passed
                if not passed:
                    all_passed = False

            # Determine status
            if not scenario.assertions:
                # No assertions = consider passed if we got a response
                status = TestStatus.PASSED
            else:
                status = TestStatus.PASSED if all_passed else TestStatus.FAILED

            return TestResult(
                scenario_id=scenario.id,
                status=status,
                actual_output=actual_output,
                latency_ms=latency_ms,
                token_count=token_count,
                assertion_results=assertion_results,
            )

        except Exception as e:
            logger.error("Error executing scenario %s: %s", scenario.id, e)
            return TestResult(
                scenario_id=scenario.id,
                status=TestStatus.ERROR,
                actual_output="",
                latency_ms=0.0,
                error_message=str(e),
            )

    def _check_assertion(
        self,
        assertion: str,
        actual_output: str,
        expected_output: Optional[str],
    ) -> bool:
        """Check if an assertion passes.
        
        Args:
            assertion: Assertion type (e.g., "contains X", "no_toxic")
            actual_output: Actual response from agent
            expected_output: Expected response (if provided)
            
        Returns:
            True if assertion passes, False otherwise
        """
        assertion_lower = assertion.lower()

        # Simple assertion types
        if assertion_lower.startswith("contains:"):
            keyword = assertion.split(":", 1)[1].strip()
            return keyword.lower() in actual_output.lower()
        if assertion_lower == "not_empty":
            return len(actual_output.strip()) > 0
        if assertion_lower == "no_toxic":
            # Simple toxicity check (would use LLM Guard in real impl)
            toxic_words = ["hate", "violence", "offensive"]
            return not any(word in actual_output.lower() for word in toxic_words)
        if assertion_lower == "matches_expected":
            if expected_output:
                return actual_output.strip() == expected_output.strip()
            return False
        if assertion_lower.startswith("max_length:"):
            max_len = int(assertion.split(":", 1)[1].strip())
            return len(actual_output) <= max_len
        logger.warning("Unknown assertion type: %s", assertion)
        return True  # Default to pass for unknown assertions

    # ========== Test Run History ==========

    def list_runs(
        self,
        prompt_version: Optional[str] = None,
        limit: int = 50,
    ) -> List[TestRun]:
        """List test run history.
        
        Args:
            prompt_version: Filter by specific version
            limit: Maximum number of runs to return
            
        Returns:
            List of TestRun instances, newest first
        """
        runs = self._load_runs()

        # Filter by version if specified
        if prompt_version:
            runs = [r for r in runs if r.prompt_version == prompt_version]

        # Sort by started_at descending (newest first)
        runs.sort(key=lambda r: r.started_at, reverse=True)

        return runs[:limit]

    def get_run(self, run_id: str) -> Optional[TestRun]:
        """Get a specific test run by ID.
        
        Args:
            run_id: Test run identifier
            
        Returns:
            TestRun if found, None otherwise
        """
        runs = self._load_runs()
        for run in runs:
            if run.id == run_id:
                return run
        return None

    # ========== Version Comparison ==========

    def compare_versions(
        self,
        version_a: str,
        version_b: str,
    ) -> Optional[PromptComparison]:
        """Compare two prompt versions using their latest test runs.
        
        Args:
            version_a: First version identifier
            version_b: Second version identifier
            
        Returns:
            PromptComparison instance if both versions found, None otherwise
        """
        # Get latest run for each version
        runs_a = self.list_runs(prompt_version=version_a, limit=1)
        runs_b = self.list_runs(prompt_version=version_b, limit=1)

        if not runs_a or not runs_b:
            logger.warning(
                "Missing test runs for comparison: %s or %s", version_a, version_b
            )
            return None

        comparison = PromptComparison(
            version_a=version_a,
            version_b=version_b,
            run_a=runs_a[0],
            run_b=runs_b[0],
        )

        comparison.analyze()
        return comparison

    def get_summary_metrics(self) -> Dict:
        """Get summary metrics across all test runs.
        
        Returns:
            Dictionary with aggregate metrics
        """
        runs = self._load_runs()
        scenarios = self.list_scenarios()

        if not runs:
            return {
                "total_scenarios": len(scenarios),
                "total_runs": 0,
                "average_pass_rate": 0.0,
                "latest_run": None,
            }

        # Calculate aggregate metrics
        total_runs = len(runs)
        average_pass_rate = sum(r.pass_rate for r in runs) / total_runs
        latest_run = max(runs, key=lambda r: r.started_at)

        return {
            "total_scenarios": len(scenarios),
            "total_runs": total_runs,
            "average_pass_rate": average_pass_rate,
            "latest_run": {
                "id": latest_run.id,
                "version": latest_run.prompt_version,
                "pass_rate": latest_run.pass_rate,
                "started_at": latest_run.started_at.isoformat(),
            },
        }

    # ========== Persistence Helpers ==========

    def _load_scenarios(self) -> List[TestScenario]:
        """Load scenarios from JSON file."""
        try:
            with open(self.scenarios_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenarios = []
            for item in data:
                # Parse datetime fields
                item["created_at"] = datetime.fromisoformat(item["created_at"])
                item["updated_at"] = datetime.fromisoformat(item["updated_at"])
                scenarios.append(TestScenario(**item))

            return scenarios
        except Exception as e:
            logger.error("Error loading scenarios: %s", e)
            return []

    def _save_scenarios(self, scenarios: List[TestScenario]) -> None:
        """Save scenarios to JSON file."""
        try:
            data = [s.to_dict() for s in scenarios]
            with open(self.scenarios_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Error saving scenarios: %s", e)

    def _load_runs(self) -> List[TestRun]:
        """Load test runs from JSON file."""
        try:
            with open(self.runs_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            runs = []
            for run_data in data:
                # Parse datetime fields
                run_data["started_at"] = datetime.fromisoformat(run_data["started_at"])
                if run_data.get("completed_at"):
                    run_data["completed_at"] = datetime.fromisoformat(run_data["completed_at"])

                # Parse results
                results = []
                for result_data in run_data.get("results", []):
                    result_data["executed_at"] = datetime.fromisoformat(result_data["executed_at"])
                    result_data["status"] = TestStatus(result_data["status"])
                    results.append(TestResult(**result_data))
                run_data["results"] = results

                runs.append(TestRun(**run_data))

            return runs
        except Exception as e:
            logger.error("Error loading runs: %s", e)
            return []

    def _save_runs(self, runs: List[TestRun]) -> None:
        """Save test runs to JSON file."""
        try:
            data = [r.to_dict() for r in runs]
            with open(self.runs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Error saving runs: %s", e)
