"""
Unit Tests: RunContext

Tests RunContext initialization, state management, and telemetry capture.
"""

from datetime import datetime
from uuid import UUID

from sdk.agenttrace import AgentTracer, RunContext


class TestRunContextInitialization:
    """Test RunContext initialization and state."""

    def test_create_run_context(self):
        """Test basic RunContext creation."""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")
        run = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        assert run.agent_id == "test_agent"
        assert run.agent_version == "1.0.0"
        assert run.environment == "test"
        assert isinstance(run.run_id, UUID)
        assert run.status == "success"
        # started_at is None until __enter__ is called
        assert run.started_at is None

    def test_run_id_is_unique(self):
        """Test that each run gets a unique ID."""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        run1 = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )
        run2 = RunContext(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        assert run1.run_id != run2.run_id

    def test_run_context_manager_sets_timestamps(self):
        """Test that context manager sets started_at."""
        tracer = AgentTracer(agent_id="test_agent", agent_version="1.0.0")

        with tracer.start_run() as run:
            assert run.started_at is not None
            assert isinstance(run.started_at, datetime)


class TestRunContextStepTracking:
    """Test step tracking within RunContext."""

    def test_record_single_step(self):
        """Test recording a single step."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "api_call"):
            pass

        assert len(run._steps) == 1
        assert run._steps[0]["step_type"] == "tool"
        assert run._steps[0]["name"] == "api_call"
        assert run._steps[0]["seq"] == 0

    def test_step_sequence_numbering(self):
        """Test that steps are numbered sequentially."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("plan", "step1"):
            pass
        with run.step("tool", "step2"):
            pass
        with run.step("respond", "step3"):
            pass

        assert len(run._steps) == 3
        assert run._steps[0]["seq"] == 0
        assert run._steps[1]["seq"] == 1
        assert run._steps[2]["seq"] == 2

    def test_valid_step_types(self):
        """Test all valid step types are accepted."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        valid_types = ["plan", "retrieve", "tool", "respond", "other"]

        for step_type in valid_types:
            with run.step(step_type, f"{step_type}_step"):
                pass

        assert len(run._steps) == len(valid_types)


class TestRunContextFailureTracking:
    """Test failure tracking within RunContext."""

    def test_record_failure(self):
        """Test recording a failure."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        run.record_failure(
            failure_type="tool",
            failure_code="timeout",
            message="API call timed out",
        )

        assert run._failure is not None
        assert run._failure["failure_type"] == "tool"
        assert run._failure["failure_code"] == "timeout"
        assert run.status == "failure"

    def test_record_failure_with_step_id(self):
        """Test recording failure with step_id."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        with run.step("tool", "api_call") as step:
            run.record_failure(
                failure_type="tool",
                failure_code="timeout",
                message="Timeout 1",
                step_id=step.step_id,
            )

        assert run._failure is not None
        assert run.status == "failure"


class TestRunContextDecisionTracking:
    """Test decision tracking within RunContext."""

    def test_record_decision(self):
        """Test recording an agent decision."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        run.record_decision(
            decision_type="tool_selection",
            selected="api",
            reason_code="fresh_data_required",
            candidates=["api", "cache", "database"],
        )

        assert len(run._decisions) == 1
        assert run._decisions[0]["decision_type"] == "tool_selection"
        assert run._decisions[0]["selected"] == "api"
        assert run._decisions[0]["reason_code"] == "fresh_data_required"
        assert "api" in run._decisions[0]["candidates"]


class TestRunContextQualitySignals:
    """Test quality signal tracking within RunContext."""

    def test_record_quality_signal(self):
        """Test recording a quality signal."""
        tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
        run = RunContext(
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            tracer=tracer,
        )

        run.record_quality_signal(
            signal_type="schema_valid",
            signal_code="full_match",
            value=True,
        )

        assert len(run._quality_signals) == 1
        assert run._quality_signals[0]["signal_type"] == "schema_valid"
        assert run._quality_signals[0]["signal_code"] == "full_match"
        assert run._quality_signals[0]["value"] is True
