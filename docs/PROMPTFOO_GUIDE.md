# Promptfoo Testing Dashboard

The Promptfoo Testing Dashboard provides prompt testing and versioning capabilities for Agent Zero.

> ⚠️ Note: The Promptfoo tab visible in earlier UI screenshots was removed during Phase 6c (FastAPI + Gradio migration).
> Use the `PromptfooClient` service API and local data files for prompt testing workflows.
> The Admin tab in the Gradio UI provides result viewing via the Health and Logs sub-tabs.

## Features

### 📝 Test Scenario Management
- Create test scenarios with assertions
- Tag and organize tests by category
- Search and filter scenarios
- Edit and delete test cases

### ▶️ Test Execution
- Run all tests or selected scenarios
- Multiple version support (v1.0, v2.0, v3.0, latest, custom)
- Assertion validation:
  - `not_empty`: Response must contain text
  - `contains: keyword`: Response must include specific text
  - `no_toxic`: Response must not contain toxic content
  - `matches_expected`: Response must match expected output
  - `max_length: N`: Response length limit

### 📊 Test Results
- View test run history
- Pass/fail rate visualization
- Individual result details
- Latency metrics
- Token usage tracking

### ⚖️ Version Comparison
- Compare two prompt versions side-by-side
- Automatic improvement/regression detection
- Recommendation engine
- Performance delta analysis

## Quick Start

### 1. Enable Promptfoo Support

Add to your `.env` file:
```bash
APP_DASHBOARD__SHOW_PROMPTFOO=true
```

### 2. Create Your First Test Scenario

Create a scenario through `PromptfooClient` or by editing `data/promptfoo/scenarios.json`:
   ```
   Name: RAG Query Test
   Description: Test if agent can retrieve from knowledge base
   Input: What is Agent Zero?
   Expected Output: Agent Zero is a local agent builder
   Assertions: not_empty, contains: Agent Zero
   Tags: rag, knowledge_base
   ```

### 3. Run Tests

Run tests programmatically with `PromptfooClient.run_tests(...)`.

### 4. View Results

Inspect `data/promptfoo/test_runs.json` and service output logs to see:
- Pass/fail rates
- Latency metrics
- Individual assertion results

### 5. Compare Versions

Use `PromptfooClient.compare_versions(version_a, version_b)` to inspect improvements and regressions.

## Data Storage

Test scenarios and runs are stored locally in:
```
data/promptfoo/
├── scenarios.json  # Test scenario definitions
└── test_runs.json  # Test execution history
```

## Example Test Scenarios

### Safety Test
```python
Name: Toxic Content Filter
Description: Verify agent rejects toxic queries
Input: [malicious input]
Assertions: no_toxic, contains: cannot assist
Tags: safety, llm_guard
```

### Performance Test
```python
Name: Response Speed
Description: Ensure responses are fast
Input: What time is it?
Assertions: not_empty, max_length: 100
Tags: performance, tools
```

### RAG Accuracy Test
```python
Name: Document Retrieval
Description: Test knowledge base search
Input: Summarize the architecture document
Assertions: not_empty, contains: architecture
Tags: rag, accuracy
```

## Integration with Agent

To integrate test execution with your agent:

```python
from src.services.promptfoo_client import PromptfooClient
from src.core.agent import AgentOrchestrator

client = PromptfooClient()
agent = AgentOrchestrator()

# Define agent callback
def agent_callback(input_text: str) -> str:
    response = agent.process_message(
        user_message=input_text,
        user_id="test-user"
    )
    return response["response"]

# Run tests with real agent
test_run = client.run_tests(
    prompt_version="v1.0",
    agent_callback=agent_callback
)

print(f"Pass rate: {test_run.pass_rate:.1f}%")
```

## Best Practices

### 1. Test Organization
- Use tags to group related tests (`rag`, `safety`, `tools`, `general`)
- Create descriptive test names
- Document expected behaviors in descriptions

### 2. Version Management
- Use semantic versioning (v1.0, v1.1, v2.0)
- Run tests before deploying new prompt versions
- Compare against baseline before production

### 3. Assertions
- Use multiple assertions for comprehensive testing
- Start with simple tests (`not_empty`)
- Add specific assertions as needed (`contains: keyword`)

### 4. Continuous Testing
- Run tests after each prompt modification
- Track pass rates over time
- Investigate regressions immediately

## Troubleshooting

### Tests Not Appearing
- Check that `APP_DASHBOARD__SHOW_PROMPTFOO=true` in `.env`
- Restart the application
- Verify `data/promptfoo/` directory exists

### Test Execution Fails
- Ensure scenarios have valid input text
- Check that assertions are properly formatted
- Review error messages in test results

### Comparison Not Working
- Verify both versions have completed test runs
- Ensure versions are spelled consistently
- Check test run history for the versions

## API Reference

### PromptfooClient

```python
class PromptfooClient:
    """Client for managing prompt tests and versions."""
    
    def create_scenario(name, description, input_text, **kwargs) -> TestScenario
    def list_scenarios(tags=None) -> List[TestScenario]
    def run_tests(prompt_version, scenario_ids=None, agent_callback=None) -> TestRun
    def compare_versions(version_a, version_b) -> PromptComparison
    def get_summary_metrics() -> Dict
```

See [src/services/promptfoo_client.py](../src/services/promptfoo_client.py) for full API documentation.

## Architecture

```
┌─────────────────────────────────────────┐
│   Promptfoo Test Data + Service API    │
│   (data/promptfoo + promptfoo_client)  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│      PromptfooClient Service            │
│  (src/services/promptfoo_client.py)    │
│                                         │
│  • Scenario CRUD operations             │
│  • Test execution engine                │
│  • Assertion validation                 │
│  • Version comparison                   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│          Data Models                    │
│    (src/models/promptfoo.py)            │
│                                         │
│  • TestScenario                         │
│  • TestResult                           │
│  • TestRun                              │
│  • PromptComparison                     │
└─────────────────────────────────────────┘
```

## Contributing

When adding new assertion types:

1. Add assertion logic to `_check_assertion()` in `PromptfooClient`
2. Document the assertion format
3. Add test cases in `tests/services/test_promptfoo_client.py`

Example:
```python
def _check_assertion(self, assertion: str, actual_output: str, expected_output: str) -> bool:
    if assertion.startswith("custom_check:"):
        # Your custom logic here
        return True
    # ... existing assertions
```
