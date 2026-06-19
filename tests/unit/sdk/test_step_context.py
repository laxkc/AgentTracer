"""
Unit Tests: StepContext

Tests automatic timing and metadata validation for steps.
"""

import time

import pytest

from sdk.agenttrace import AgentTracer, RunContext


class TestStepTiming:
    """Test that StepContext correctly tracks timing."""

    def test_step_measures_duration(self):
        """Test that step context measures duration accurately."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "timed_step"):
            time.sleep(0.1)  # Sleep for 100ms

        assert len(run._steps) == 1
        # Should be at least 100ms, allow some margin
        assert run._steps[0]["latency_ms"] >= 100
        assert run._steps[0]["latency_ms"] < 200  # Reasonable upper bound

    def test_step_timing_multiple_steps(self):
        """Test timing for multiple steps."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("plan", "step1"):
            time.sleep(0.05)

        with run.step("tool", "step2"):
            time.sleep(0.1)

        assert len(run._steps) == 2
        assert run._steps[0]["latency_ms"] >= 50
        assert run._steps[1]["latency_ms"] >= 100

    def test_zero_duration_step(self):
        """Test step with minimal duration."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "fast_step"):
            pass  # No work

        assert len(run._steps) == 1
        # Should be very small but non-negative
        assert run._steps[0]["latency_ms"] >= 0
        assert run._steps[0]["latency_ms"] < 10  # Should be < 10ms


class TestStepMetadata:
    """Test step metadata handling."""

    def test_step_with_metadata(self):
        """Test step with custom metadata."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        metadata = {"endpoint": "/api/users", "method": "GET"}

        with run.step("tool", "api_call") as step:
            step.add_metadata(metadata)

        assert len(run._steps) == 1
        assert run._steps[0]["metadata"]["endpoint"] == "/api/users"

    def test_step_without_metadata(self):
        """Test step without metadata."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "simple_step"):
            pass

        assert len(run._steps) == 1
        assert run._steps[0]["metadata"] == {}


class TestStepExceptionHandling:
    """Test step behavior when exceptions occur."""

    def test_step_records_on_exception(self):
        """Test that step is recorded even if exception occurs."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with pytest.raises(ValueError):
            with run.step("tool", "failing_step"):
                raise ValueError("Test error")

        # Step should still be recorded
        assert len(run._steps) == 1
        assert run._steps[0]["name"] == "failing_step"

    def test_step_timing_on_exception(self):
        """Test that timing is still captured when exception occurs."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with pytest.raises(ValueError):
            with run.step("tool", "timed_failure"):
                time.sleep(0.05)
                raise ValueError("Test error")

        assert len(run._steps) == 1
        assert run._steps[0]["latency_ms"] >= 50


class TestStepValidation:
    """Test step type and name validation."""

    def test_valid_step_types_accepted(self):
        """Test that valid step types are accepted."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        # All valid types should work
        valid_types = ["plan", "retrieve", "tool", "respond", "other"]
        for step_type in valid_types:
            with run.step(step_type, "test_step"):
                pass

        assert len(run._steps) == 5

    def test_empty_step_name_accepted(self):
        """Test that empty step names are accepted by SDK (validation at API layer)."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        # SDK doesn't validate empty names - that happens at API layer
        with run.step("tool", ""):
            pass

        assert len(run._steps) == 1
