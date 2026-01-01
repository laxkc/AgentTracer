"""
Unit Tests for Agent SDK

Tests the core SDK functionality:
- Run context creation
- Step tracking with automatic timing
- Metadata validation (privacy enforcement)
- Failure recording
"""

import time
from datetime import datetime
from uuid import UUID

import pytest

from sdk.agenttrace import AgentTracer, RunContext, StepContext


class TestStepContext:
    """Test StepContext for automatic timing and metadata validation"""

    def test_step_timing(self):
        """Test that step context correctly tracks timing"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")
        run = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "test_step") as step:
            time.sleep(0.1)  # Simulate work

        # Check that step was recorded
        assert len(run._steps) == 1
        recorded_step = run._steps[0]

        assert recorded_step["step_type"] == "tool"
        assert recorded_step["name"] == "test_step"
        assert recorded_step["seq"] == 0
        assert recorded_step["latency_ms"] >= 100  # At least 100ms

    def test_step_metadata_safe(self):
        """Test that safe metadata is accepted"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")
        run = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "api_call") as step:
            # Safe metadata should be accepted
            step.add_metadata(
                {
                    "http_status": 200,
                    "retry_attempt": 1,
                    "tool_name": "search_api",
                    "result_count": 10,
                }
            )

        recorded_step = run._steps[0]
        assert recorded_step["metadata"]["http_status"] == 200
        assert recorded_step["metadata"]["retry_attempt"] == 1
        assert recorded_step["metadata"]["tool_name"] == "search_api"

    def test_step_metadata_forbidden(self):
        """Test that forbidden metadata is rejected"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")
        run = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "api_call") as step:
            # Forbidden keys should be filtered out
            step.add_metadata(
                {
                    "prompt": "This should be filtered",  # Forbidden
                    "response": "This should be filtered",  # Forbidden
                    "http_status": 200,  # Safe
                }
            )

        recorded_step = run._steps[0]
        # Forbidden keys should not be in metadata
        assert "prompt" not in recorded_step["metadata"]
        assert "response" not in recorded_step["metadata"]
        # Safe keys should be present
        assert recorded_step["metadata"]["http_status"] == 200


class TestRunContext:
    """Test RunContext for run tracking and failure recording"""

    def test_run_basic(self):
        """Test basic run creation and tracking"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        with tracer.start_run() as run:
            with run.step("plan", "analyze_query"):
                pass

            with run.step("retrieve", "search_kb"):
                pass

        assert len(run._steps) == 2
        assert run._steps[0]["seq"] == 0
        assert run._steps[1]["seq"] == 1
        assert run.status == "success"

    def test_run_with_failure(self):
        """Test failure recording"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        with tracer.start_run() as run:
            with run.step("tool", "api_call"):
                pass

            run.record_failure(
                failure_type="tool",
                failure_code="timeout",
                message="API call timed out after 30s",
            )

        assert run.status == "failure"
        assert run._failure is not None
        assert run._failure["failure_type"] == "tool"
        assert run._failure["failure_code"] == "timeout"

    def test_run_uncaught_exception(self):
        """Test that uncaught exceptions are recorded as failures"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        with tracer.start_run() as run:
            with run.step("tool", "api_call"):
                pass

            # Simulate an exception (but catch it to prevent test failure)
            try:
                raise ValueError("Simulated error")
            except ValueError:
                # Manually trigger __exit__ with exception
                import sys

                exc_info = sys.exc_info()
                run.__exit__(*exc_info)

        assert run.status == "failure"
        assert run._failure is not None
        assert run._failure["failure_type"] == "orchestration"
        assert run._failure["failure_code"] == "uncaught_exception"

    def test_retry_modeling(self):
        """Test that retries are captured as separate steps"""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        with tracer.start_run() as run:
            # Simulate 3 retry attempts (each is a separate step)
            for attempt in range(3):
                with run.step("tool", "api_call") as step:
                    step.add_metadata({"attempt": attempt + 1})

        # Should have 3 separate step spans
        assert len(run._steps) == 3
        assert run._steps[0]["metadata"]["attempt"] == 1
        assert run._steps[1]["metadata"]["attempt"] == 2
        assert run._steps[2]["metadata"]["attempt"] == 3


class TestAgentTracer:
    """Test AgentTracer initialization and configuration"""

    def test_tracer_init(self):
        """Test tracer initialization"""
        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
            api_url="http://localhost:8000",
            environment="test",
        )

        assert tracer.agent_id == "test_agent"
        assert tracer.agent_version == "1.0.0"
        assert tracer.api_url == "http://localhost:8000"
        assert tracer.environment == "test"

    def test_tracer_context_manager(self):
        """Test tracer as context manager"""
        with AgentTracer(
            agent_id="test_agent", agent_version="1.0.0"
        ) as tracer:
            assert tracer.agent_id == "test_agent"

        # Client should be closed after exit
        assert tracer._client.is_closed


# ============================================================================
# Integration Tests (require running ingest API)
# ============================================================================


@pytest.mark.integration
def test_end_to_end_telemetry():
    """
    End-to-end test of telemetry capture and sending.

    This test requires the ingest API to be running.
    """
    tracer = AgentTracer(
        agent_id="test_agent",
        agent_version="1.0.0",
        api_url="http://localhost:8000",
        environment="test",
    )

    with tracer.start_run() as run:
        with run.step("plan", "analyze_query") as step:
            step.add_metadata({"query_type": "semantic"})

        with run.step("retrieve", "search_kb") as step:
            step.add_metadata({"result_count": 10})

        with run.step("respond", "generate_response") as step:
            step.add_metadata({"response_length": 250})

    # If we get here without exception, telemetry was sent successfully
    assert run.status == "success"
