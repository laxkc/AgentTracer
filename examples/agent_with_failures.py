"""
Example Agent with Failure Scenarios

This example demonstrates how to capture and classify different types of agent failures:
1. Tool failures (timeout, API error, invalid response)
2. Model failures (rate limit, context length, invalid output)
3. Retrieval failures (no results, connection error)
4. Orchestration failures (invalid state, constraint violation)

Run this to populate the observability platform with failure data.
"""

import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sdk.agenttrace import AgentTracer

# Initialize tracer
tracer = AgentTracer(
    agent_id="test_agent_failures",
    agent_version="1.0.0",
    api_url="http://localhost:8000",
    environment="staging",
)


def simulate_tool_timeout_failure():
    """Simulate a tool call that times out"""
    print("\n" + "=" * 60)
    print("Scenario 1: Tool Timeout Failure")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "analyze_request"):
            time.sleep(0.05)

        # Retrieval step
        with run.step("retrieve", "fetch_context"):
            time.sleep(0.08)

        # Tool call that times out
        try:
            with run.step("tool", "call_external_api") as step:
                time.sleep(0.1)
                # Simulate timeout
                raise TimeoutError("API call exceeded 30s timeout")
        except TimeoutError as e:
            run.record_failure(
                failure_type="tool",
                failure_code="timeout",
                message=f"External API call timed out after 30 seconds: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_model_rate_limit_failure():
    """Simulate a model rate limit error"""
    print("\n" + "=" * 60)
    print("Scenario 2: Model Rate Limit Failure")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "prepare_prompt"):
            time.sleep(0.04)

        # Model call that hits rate limit
        try:
            with run.step("respond", "generate_response") as step:
                time.sleep(0.12)
                # Simulate rate limit
                raise Exception("Rate limit exceeded: 429 Too Many Requests")
        except Exception as e:
            run.record_failure(
                failure_type="model",
                failure_code="rate_limit",
                message=f"LLM provider rate limit exceeded (429): {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_retrieval_no_results_failure():
    """Simulate a retrieval that returns no results"""
    print("\n" + "=" * 60)
    print("Scenario 3: Retrieval No Results Failure")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "parse_query"):
            time.sleep(0.06)

        # Retrieval that finds nothing
        try:
            with run.step("retrieve", "search_knowledge_base") as step:
                time.sleep(0.15)
                # Simulate no results
                results = []
                if not results:
                    raise ValueError("No relevant documents found for query")
        except ValueError as e:
            run.record_failure(
                failure_type="retrieval",
                failure_code="no_results",
                message=f"Knowledge base search returned 0 results for user query: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_orchestration_constraint_violation():
    """Simulate an orchestration constraint violation"""
    print("\n" + "=" * 60)
    print("Scenario 4: Orchestration Constraint Violation")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "validate_request"):
            time.sleep(0.05)

        # Multiple tool calls
        with run.step("tool", "fetch_user_data"):
            time.sleep(0.08)

        with run.step("tool", "check_permissions"):
            time.sleep(0.07)

        # Orchestration fails due to constraint
        try:
            with run.step("plan", "validate_workflow") as step:
                time.sleep(0.04)
                # Simulate constraint violation
                raise RuntimeError("Maximum retry attempts (3) exceeded for workflow")
        except RuntimeError as e:
            run.record_failure(
                failure_type="orchestration",
                failure_code="max_retries_exceeded",
                message=f"Workflow exceeded maximum retry limit: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_tool_invalid_response_failure():
    """Simulate a tool returning invalid data"""
    print("\n" + "=" * 60)
    print("Scenario 5: Tool Invalid Response Failure")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "prepare_tool_call"):
            time.sleep(0.05)

        # Tool call that returns invalid data
        try:
            with run.step("tool", "call_weather_api") as step:
                time.sleep(0.11)
                # Simulate invalid response
                response = {"error": "malformed JSON"}
                if "error" in response:
                    raise ValueError("API returned malformed response")
        except ValueError as e:
            run.record_failure(
                failure_type="tool",
                failure_code="invalid_response",
                message=f"Weather API returned invalid JSON structure: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_model_context_length_failure():
    """Simulate a model context length error"""
    print("\n" + "=" * 60)
    print("Scenario 6: Model Context Length Exceeded")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "build_context"):
            time.sleep(0.06)

        # Retrieval that gets too many docs
        with run.step("retrieve", "fetch_documents"):
            time.sleep(0.13)

        # Model call that exceeds context
        try:
            with run.step("respond", "generate_with_context") as step:
                time.sleep(0.09)
                # Simulate context length error
                raise Exception("Context length of 150000 tokens exceeds model limit of 128000")
        except Exception as e:
            run.record_failure(
                failure_type="model",
                failure_code="context_length_exceeded",
                message=f"Prompt exceeded model context window: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_retrieval_connection_failure():
    """Simulate a retrieval database connection error"""
    print("\n" + "=" * 60)
    print("Scenario 7: Retrieval Connection Failure")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "prepare_search"):
            time.sleep(0.04)

        # Retrieval connection failure
        try:
            with run.step("retrieve", "query_vector_db") as step:
                time.sleep(0.08)
                # Simulate connection error
                raise ConnectionError("Failed to connect to vector database: Connection refused")
        except ConnectionError as e:
            run.record_failure(
                failure_type="retrieval",
                failure_code="connection_error",
                message=f"Vector database connection failed: {str(e)}",
            )
            print(f"✗ Failed: {e}")
            return


def simulate_partial_success_with_retry():
    """Simulate a partial success where retry eventually succeeds"""
    print("\n" + "=" * 60)
    print("Scenario 8: Partial Success (Retry Eventually Succeeds)")
    print("=" * 60)

    with tracer.start_run() as run:
        # Planning step
        with run.step("plan", "analyze_task"):
            time.sleep(0.05)

        # First attempt fails
        with run.step("tool", "api_call_attempt_1"):
            time.sleep(0.10)

        # Second attempt fails
        with run.step("tool", "api_call_attempt_2"):
            time.sleep(0.11)

        # Third attempt succeeds
        with run.step("tool", "api_call_attempt_3"):
            time.sleep(0.09)

        # Generate response
        with run.step("respond", "generate_final_response"):
            time.sleep(0.15)

        # Mark as partial since we had failures but eventually succeeded
        run.status = "partial"
        print("✓ Partial success: Completed after 3 retry attempts")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Agent Failure Scenarios")
    print("=" * 60)
    print("\nThis will create runs with various failure types:")
    print("  - Tool failures (timeout, invalid response)")
    print("  - Model failures (rate limit, context length)")
    print("  - Retrieval failures (no results, connection error)")
    print("  - Orchestration failures (constraint violations)")
    print("\n")

    # Run all failure scenarios
    simulate_tool_timeout_failure()
    time.sleep(0.5)

    simulate_model_rate_limit_failure()
    time.sleep(0.5)

    simulate_retrieval_no_results_failure()
    time.sleep(0.5)

    simulate_orchestration_constraint_violation()
    time.sleep(0.5)

    simulate_tool_invalid_response_failure()
    time.sleep(0.5)

    simulate_model_context_length_failure()
    time.sleep(0.5)

    simulate_retrieval_connection_failure()
    time.sleep(0.5)

    simulate_partial_success_with_retry()

    print("\n" + "=" * 60)
    print("Failure scenarios completed!")
    print("=" * 60)
    print("\nCheck the observability platform:")
    print("  - Dashboard: http://localhost:3000")
    print("  - Stats API: http://localhost:8001/v1/stats")
    print("  - Runs API: http://localhost:8001/v1/runs")
    print("\nYou should now see:")
    print("  ✗ 7 failed runs")
    print("  ⚠ 1 partial run")
    print("  📊 Failure breakdown by type/code")
    print("=" * 60)
