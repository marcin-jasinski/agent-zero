"""Promptfoo Testing Dashboard component for Agent Zero.

This component provides a UI for managing prompt test scenarios,
running tests, viewing results, and comparing versions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import streamlit as st

from src.config import get_config
from src.models.promptfoo import TestRun, TestScenario, TestStatus
from src.services.promptfoo_client import PromptfooClient


logger = logging.getLogger(__name__)


@st.cache_resource
def get_promptfoo_client() -> PromptfooClient:
    """Get cached Promptfoo client instance.
    
    Returns:
        PromptfooClient instance
    """
    config = get_config()
    return PromptfooClient(data_dir="data/promptfoo")


@st.cache_data(ttl=30)
def get_cached_scenarios() -> List[TestScenario]:
    """Get cached list of test scenarios.
    
    Returns:
        List of TestScenario instances
    """
    client = get_promptfoo_client()
    return client.list_scenarios()


@st.cache_data(ttl=30)
def get_cached_runs(limit: int = 50) -> List[TestRun]:
    """Get cached list of test runs.
    
    Args:
        limit: Maximum number of runs to return
        
    Returns:
        List of TestRun instances
    """
    client = get_promptfoo_client()
    return client.list_runs(limit=limit)


@st.cache_data(ttl=60)
def get_cached_summary() -> dict:
    """Get cached summary metrics.
    
    Returns:
        Dictionary with summary metrics
    """
    client = get_promptfoo_client()
    return client.get_summary_metrics()


def render_promptfoo_dashboard() -> None:
    """Render the main Promptfoo Testing dashboard."""
    st.title("Prompt Testing & Versioning")
    st.markdown("Test and compare different prompt versions to optimize agent performance.")
    
    # Summary metrics
    _render_summary_metrics()
    
    st.divider()
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Test Scenarios",
        "▶️ Run Tests",
        "📊 Test Results",
        "⚖️ Version Comparison"
    ])
    
    with tab1:
        _render_scenarios_tab()
    
    with tab2:
        _render_run_tests_tab()
    
    with tab3:
        _render_results_tab()
    
    with tab4:
        _render_comparison_tab()


def _render_summary_metrics() -> None:
    """Render summary metrics at the top of the dashboard."""
    try:
        summary = get_cached_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Scenarios",
                value=summary["total_scenarios"],
                delta=None,
            )
        
        with col2:
            st.metric(
                label="Total Runs",
                value=summary["total_runs"],
                delta=None,
            )
        
        with col3:
            avg_pass_rate = summary.get("average_pass_rate", 0.0)
            st.metric(
                label="Avg Pass Rate",
                value=f"{avg_pass_rate:.1f}%",
                delta=None,
            )
        
        with col4:
            latest = summary.get("latest_run")
            if latest:
                st.metric(
                    label="Latest Run",
                    value=f"{latest['pass_rate']:.1f}%",
                    delta=f"{latest['version']}",
                )
            else:
                st.metric(label="Latest Run", value="N/A")
        
        # Refresh button
        if st.button("🔄 Refresh Metrics", key="refresh_summary"):
            get_cached_summary.clear()
            st.rerun()
    
    except Exception as e:
        logger.error(f"Error rendering summary metrics: {e}")
        st.error(f"Failed to load summary metrics: {e}")


def _render_scenarios_tab() -> None:
    """Render the test scenarios management tab."""
    st.subheader("Test Scenario Management")
    
    # Create new scenario section
    with st.expander("➕ Create New Test Scenario", expanded=False):
        _render_create_scenario_form()
    
    st.divider()
    
    # List existing scenarios
    st.subheader("Existing Test Scenarios")
    
    try:
        scenarios = get_cached_scenarios()
        
        if not scenarios:
            st.info("No test scenarios yet. Create one above to get started!")
            return
        
        # Filter options
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input(
                "Search scenarios",
                placeholder="Search by name or description...",
                key="scenario_search"
            )
        with col2:
            if st.button("🔄 Refresh List", key="refresh_scenarios"):
                get_cached_scenarios.clear()
                st.rerun()
        
        # Filter scenarios
        filtered = scenarios
        if search_term:
            filtered = [
                s for s in scenarios
                if search_term.lower() in s.name.lower()
                or search_term.lower() in s.description.lower()
            ]
        
        # Display scenarios
        for scenario in filtered:
            _render_scenario_card(scenario)
    
    except Exception as e:
        logger.error(f"Error loading scenarios: {e}")
        st.error(f"Failed to load scenarios: {e}")


def _render_create_scenario_form() -> None:
    """Render form for creating a new test scenario."""
    with st.form("create_scenario_form"):
        name = st.text_input("Scenario Name*", placeholder="e.g., RAG Query Test")
        description = st.text_area(
            "Description*",
            placeholder="Describe what this test validates...",
            height=80
        )
        input_text = st.text_area(
            "Input Text*",
            placeholder="User query to test...",
            height=100
        )
        expected_output = st.text_area(
            "Expected Output (Optional)",
            placeholder="Expected response or key phrases...",
            height=100
        )
        
        # Assertions
        st.markdown("**Assertions (Optional)**")
        assertion_options = [
            "not_empty",
            "no_toxic",
            "matches_expected",
            "contains: [keyword]",
            "max_length: 500",
        ]
        selected_assertions = st.multiselect(
            "Select assertion types",
            options=assertion_options,
            help="Assertions to validate the response"
        )
        
        custom_assertion = st.text_input(
            "Custom Assertion",
            placeholder="e.g., contains: specific phrase"
        )
        
        # Tags
        tags_input = st.text_input(
            "Tags (comma-separated)",
            placeholder="e.g., rag, safety, performance"
        )
        
        submitted = st.form_submit_button("Create Scenario")
        
        if submitted:
            if not name or not description or not input_text:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            try:
                # Prepare assertions
                assertions = list(selected_assertions)
                if custom_assertion:
                    assertions.append(custom_assertion)
                
                # Prepare tags
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                
                # Create scenario
                client = get_promptfoo_client()
                scenario = client.create_scenario(
                    name=name,
                    description=description,
                    input_text=input_text,
                    expected_output=expected_output if expected_output else None,
                    assertions=assertions,
                    tags=tags,
                )
                
                # Clear cache and show success
                get_cached_scenarios.clear()
                st.success(f"✅ Created scenario: {scenario.name}")
                st.rerun()
            
            except Exception as e:
                logger.error(f"Error creating scenario: {e}")
                st.error(f"Failed to create scenario: {e}")


def _render_scenario_card(scenario: TestScenario) -> None:
    """Render a single scenario card with details and actions.
    
    Args:
        scenario: TestScenario to display
    """
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### {scenario.name}")
            st.markdown(f"*{scenario.description}*")
            st.code(scenario.input_text, language=None)
            
            if scenario.expected_output:
                with st.expander("Expected Output"):
                    st.write(scenario.expected_output)
            
            if scenario.assertions:
                st.caption(f"**Assertions:** {', '.join(scenario.assertions)}")
            
            if scenario.tags:
                st.caption(f"**Tags:** {', '.join([f'`{t}`' for t in scenario.tags])}")
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{scenario.id}"):
                client = get_promptfoo_client()
                if client.delete_scenario(scenario.id):
                    get_cached_scenarios.clear()
                    st.success("Deleted!")
                    st.rerun()
        
        st.divider()


def _render_run_tests_tab() -> None:
    """Render the test execution tab."""
    st.subheader("Run Test Suite")
    
    try:
        scenarios = get_cached_scenarios()
        
        if not scenarios:
            st.warning("No test scenarios available. Create scenarios first in the 'Test Scenarios' tab.")
            return
        
        # Test run configuration
        col1, col2 = st.columns(2)
        
        with col1:
            prompt_version = st.selectbox(
                "Prompt Version",
                options=["v1.0", "v2.0", "v3.0", "latest", "custom"],
                help="Select the prompt version to test"
            )
            
            if prompt_version == "custom":
                prompt_version = st.text_input("Custom Version Name", placeholder="e.g., v1.5-experimental")
        
        with col2:
            run_mode = st.radio(
                "Run Mode",
                options=["All Scenarios", "Selected Scenarios"],
                help="Choose which scenarios to run"
            )
        
        # Scenario selection
        selected_ids = []
        if run_mode == "Selected Scenarios":
            scenario_names = {f"{s.name} ({s.id[:8]})": s.id for s in scenarios}
            selected_names = st.multiselect(
                "Select Scenarios",
                options=list(scenario_names.keys()),
            )
            selected_ids = [scenario_names[name] for name in selected_names]
        
        # Run button
        if st.button("▶️ Run Tests", type="primary"):
            if run_mode == "Selected Scenarios" and not selected_ids:
                st.error("Please select at least one scenario")
                return
            
            _execute_test_run(
                prompt_version=prompt_version,
                scenario_ids=selected_ids if run_mode == "Selected Scenarios" else None
            )
    
    except Exception as e:
        logger.error(f"Error in run tests tab: {e}")
        st.error(f"Failed to load test configuration: {e}")


def _execute_test_run(prompt_version: str, scenario_ids: Optional[List[str]] = None) -> None:
    """Execute a test run and display results.
    
    Args:
        prompt_version: Version identifier
        scenario_ids: Specific scenarios to run (None = all)
    """
    try:
        with st.spinner("Running tests..."):
            client = get_promptfoo_client()
            
            # Execute test run (without agent callback for now - mock mode)
            test_run = client.run_tests(
                prompt_version=prompt_version,
                scenario_ids=scenario_ids,
                agent_callback=None,  # Would integrate with agent in production
            )
            
            # Clear cache
            get_cached_runs.clear()
            get_cached_summary.clear()
            
            # Display results
            st.success(f"✅ Test run completed!")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Tests", test_run.total_tests)
            with col2:
                st.metric("Passed", test_run.passed_tests, delta=None)
            with col3:
                st.metric("Failed", test_run.failed_tests, delta=None)
            with col4:
                st.metric("Pass Rate", f"{test_run.pass_rate:.1f}%")
            
            st.info(f"Run ID: `{test_run.id}` | Version: `{test_run.prompt_version}`")
    
    except Exception as e:
        logger.error(f"Error executing test run: {e}")
        st.error(f"Test execution failed: {e}")


def _render_results_tab() -> None:
    """Render the test results history tab."""
    st.subheader("Test Run History")
    
    try:
        runs = get_cached_runs(limit=50)
        
        if not runs:
            st.info("No test runs yet. Run tests from the 'Run Tests' tab.")
            return
        
        # Refresh button
        if st.button("🔄 Refresh Results", key="refresh_results"):
            get_cached_runs.clear()
            st.rerun()
        
        # Display runs
        for run in runs:
            _render_test_run_card(run)
    
    except Exception as e:
        logger.error(f"Error loading test results: {e}")
        st.error(f"Failed to load test results: {e}")


def _render_test_run_card(run: TestRun) -> None:
    """Render a single test run card with results.
    
    Args:
        run: TestRun to display
    """
    # Determine status emoji
    if run.pass_rate == 100.0:
        status_emoji = "✅"
    elif run.pass_rate >= 80.0:
        status_emoji = "🟡"
    else:
        status_emoji = "🔴"
    
    with st.expander(
        f"{status_emoji} {run.prompt_version} - {run.pass_rate:.1f}% passed - {run.started_at.strftime('%Y-%m-%d %H:%M')}",
        expanded=False
    ):
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total", run.total_tests)
        with col2:
            st.metric("✅ Passed", run.passed_tests)
        with col3:
            st.metric("❌ Failed", run.failed_tests)
        with col4:
            st.metric("⚠️ Errors", run.error_tests)
        with col5:
            st.metric("Avg Latency", f"{run.average_latency_ms:.0f}ms")
        
        # Show individual results
        if run.results:
            st.markdown("**Individual Test Results:**")
            for result in run.results:
                status_icon = {
                    TestStatus.PASSED: "✅",
                    TestStatus.FAILED: "❌",
                    TestStatus.ERROR: "⚠️",
                }.get(result.status, "❓")
                
                st.markdown(
                    f"{status_icon} Scenario `{result.scenario_id[:8]}` - "
                    f"{result.latency_ms:.0f}ms - {result.status.value}"
                )
                
                if result.status == TestStatus.FAILED and result.assertion_results:
                    failed_assertions = [
                        assertion for assertion, passed in result.assertion_results.items()
                        if not passed
                    ]
                    if failed_assertions:
                        st.caption(f"Failed assertions: {', '.join(failed_assertions)}")


def _render_comparison_tab() -> None:
    """Render the version comparison tab."""
    st.subheader("Version Comparison")
    
    try:
        runs = get_cached_runs(limit=100)
        
        if len(runs) < 2:
            st.warning("Need at least 2 test runs to compare versions.")
            return
        
        # Get unique versions
        versions = sorted(set(run.prompt_version for run in runs))
        
        col1, col2 = st.columns(2)
        
        with col1:
            version_a = st.selectbox("Version A", options=versions, index=0)
        
        with col2:
            version_b = st.selectbox(
                "Version B",
                options=versions,
                index=min(1, len(versions) - 1)
            )
        
        if st.button("⚖️ Compare Versions", type="primary"):
            _display_version_comparison(version_a, version_b)
    
    except Exception as e:
        logger.error(f"Error in comparison tab: {e}")
        st.error(f"Failed to load comparison: {e}")


def _display_version_comparison(version_a: str, version_b: str) -> None:
    """Display comparison between two versions.
    
    Args:
        version_a: First version
        version_b: Second version
    """
    try:
        client = get_promptfoo_client()
        comparison = client.compare_versions(version_a, version_b)
        
        if not comparison:
            st.error("Could not find test runs for both versions")
            return
        
        st.success(f"Comparing {version_a} vs {version_b}")
        
        # Summary metrics comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"### {version_a}")
            st.metric("Pass Rate", f"{comparison.run_a.pass_rate:.1f}%")
            st.metric("Avg Latency", f"{comparison.run_a.average_latency_ms:.0f}ms")
            st.metric("Total Tests", comparison.run_a.total_tests)
        
        with col2:
            st.markdown(f"### {version_b}")
            st.metric("Pass Rate", f"{comparison.run_b.pass_rate:.1f}%")
            st.metric("Avg Latency", f"{comparison.run_b.average_latency_ms:.0f}ms")
            st.metric("Total Tests", comparison.run_b.total_tests)
        
        st.divider()
        
        # Improvements and regressions
        if comparison.improvements:
            st.markdown("### ✅ Improvements")
            for improvement in comparison.improvements:
                st.success(improvement)
        
        if comparison.regressions:
            st.markdown("### ⚠️ Regressions")
            for regression in comparison.regressions:
                st.warning(regression)
        
        # Recommendation
        st.markdown("### Recommendation")
        st.info(comparison.recommendation)
    
    except Exception as e:
        logger.error(f"Error displaying comparison: {e}")
        st.error(f"Comparison failed: {e}")


# Export main function
__all__ = ["render_promptfoo_dashboard"]
