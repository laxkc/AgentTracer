"""
Unit Tests: Pydantic Models

Tests request/response schema validation and field constraints.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from server.models.database import (
    AgentDecisionCreate,
    AgentFailureCreate,
    AgentQualitySignalCreate,
    AgentRunCreate,
    AgentStepCreate,
)


class TestAgentRunValidation:
    """Test AgentRunCreate model validation."""

    def test_valid_run_creation(self):
        """Test creating valid run."""
        run = AgentRunCreate(
            run_id=str(uuid4()),
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            status="success",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            metadata={},
            steps=[],
            failures=[],
            decisions=[],
            quality_signals=[],
        )

        assert run.agent_id == "test_agent"
        assert run.status == "success"

    def test_run_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentRunCreate(
                # Missing run_id
                agent_id="test_agent",
                agent_version="1.0.0",
            )

    def test_run_invalid_status(self):
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError):
            AgentRunCreate(
                run_id=str(uuid4()),
                agent_id="test_agent",
                agent_version="1.0.0",
                environment="production",
                status="invalid_status",  # Invalid
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            )

    def test_run_with_nested_objects(self):
        """Test run with nested steps and failures."""
        run = AgentRunCreate(
            run_id=str(uuid4()),
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            status="failure",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            metadata={},
            steps=[
                AgentStepCreate(
                    step_type="tool",
                    name="api_call",
                    seq=0,
                    latency_ms=100,
                    metadata={},
                )
            ],
            failures=[
                AgentFailureCreate(
                    failure_type="tool_error",
                    failure_code="timeout",
                    message="API timeout",
                    step_seq=0,
                )
            ],
            decisions=[],
            quality_signals=[],
        )

        assert len(run.steps) == 1
        assert len(run.failures) == 1
        assert run.status == "failure"


class TestAgentStepValidation:
    """Test AgentStepCreate model validation."""

    def test_valid_step_creation(self):
        """Test creating valid step."""
        step = AgentStepCreate(
            step_type="tool",
            name="api_call",
            seq=0,
            latency_ms=150,
            metadata={},
        )

        assert step.step_type == "tool"
        assert step.latency_ms == 150

    def test_step_invalid_type(self):
        """Test that invalid step types are rejected."""
        with pytest.raises(ValidationError):
            AgentStepCreate(
                step_type="invalid_type",
                name="test",
                seq=0,
                latency_ms=100,
            )

    @pytest.mark.parametrize(
        "step_type",
        ["plan", "retrieve", "tool", "respond", "orchestrate"],
    )
    def test_step_valid_types(self, step_type):
        """Test all valid step types are accepted."""
        step = AgentStepCreate(
            step_type=step_type,
            name="test_step",
            seq=0,
            latency_ms=100,
            metadata={},
        )

        assert step.step_type == step_type

    def test_step_negative_latency(self):
        """Test that negative latency is rejected."""
        with pytest.raises(ValidationError):
            AgentStepCreate(
                step_type="tool",
                name="test",
                seq=0,
                latency_ms=-100,  # Negative latency invalid
            )

    def test_step_negative_sequence(self):
        """Test that negative sequence numbers are rejected."""
        with pytest.raises(ValidationError):
            AgentStepCreate(
                step_type="tool",
                name="test",
                seq=-1,  # Negative seq invalid
                latency_ms=100,
            )


class TestAgentFailureValidation:
    """Test AgentFailureCreate model validation."""

    def test_valid_failure_creation(self):
        """Test creating valid failure."""
        failure = AgentFailureCreate(
            failure_type="tool_error",
            failure_code="timeout",
            message="Request timed out",
            step_seq=0,
        )

        assert failure.failure_type == "tool_error"
        assert failure.failure_code == "timeout"

    def test_failure_missing_message(self):
        """Test that missing message raises ValidationError."""
        with pytest.raises(ValidationError):
            AgentFailureCreate(
                failure_type="tool_error",
                failure_code="timeout",
                # Missing message
                step_seq=0,
            )

    @pytest.mark.parametrize(
        "failure_type",
        ["tool_error", "model_error", "retrieval_error", "orchestration_error"],
    )
    def test_failure_valid_types(self, failure_type):
        """Test all valid failure types are accepted."""
        failure = AgentFailureCreate(
            failure_type=failure_type,
            failure_code="test_code",
            message="Test failure",
            step_seq=0,
        )

        assert failure.failure_type == failure_type


class TestAgentDecisionValidation:
    """Test AgentDecisionCreate model validation."""

    def test_valid_decision_creation(self):
        """Test creating valid decision."""
        decision = AgentDecisionCreate(
            decision_type="tool_selection",
            selected="api",
            alternatives=["api", "cache", "database"],
            metadata={},
        )

        assert decision.decision_type == "tool_selection"
        assert decision.selected == "api"
        assert len(decision.alternatives) == 3

    def test_decision_with_no_alternatives(self):
        """Test decision with empty alternatives list."""
        decision = AgentDecisionCreate(
            decision_type="binary_choice",
            selected="yes",
            alternatives=[],
            metadata={},
        )

        assert len(decision.alternatives) == 0

    def test_decision_selected_not_in_alternatives(self):
        """Test that selected value can be outside alternatives (edge case)."""
        # This is allowed - selected might be computed differently
        decision = AgentDecisionCreate(
            decision_type="tool_selection",
            selected="other",
            alternatives=["api", "cache"],
            metadata={},
        )

        assert decision.selected not in decision.alternatives


class TestAgentQualitySignalValidation:
    """Test AgentQualitySignalCreate model validation."""

    def test_valid_quality_signal_creation(self):
        """Test creating valid quality signal."""
        signal = AgentQualitySignalCreate(
            signal_type="schema_valid",
            signal_code="full_match",
            metadata={},
        )

        assert signal.signal_type == "schema_valid"
        assert signal.signal_code == "full_match"

    def test_quality_signal_missing_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentQualitySignalCreate(
                signal_type="schema_valid",
                # Missing signal_code
            )

    def test_quality_signal_with_metadata(self):
        """Test quality signal with metadata."""
        signal = AgentQualitySignalCreate(
            signal_type="tool_success",
            signal_code="first_attempt",
            metadata={"retry_count": 0},
        )

        assert signal.metadata["retry_count"] == 0


class TestMetadataValidation:
    """Test metadata field validation across models."""

    def test_metadata_must_be_dict(self):
        """Test that metadata must be a dictionary."""
        with pytest.raises(ValidationError):
            AgentStepCreate(
                step_type="tool",
                name="test",
                seq=0,
                latency_ms=100,
                metadata="not_a_dict",  # Invalid
            )

    def test_empty_metadata_allowed(self):
        """Test that empty metadata is allowed."""
        step = AgentStepCreate(
            step_type="tool",
            name="test",
            seq=0,
            latency_ms=100,
            metadata={},
        )

        assert step.metadata == {}

    def test_metadata_with_nested_objects(self):
        """Test metadata with nested objects."""
        step = AgentStepCreate(
            step_type="tool",
            name="test",
            seq=0,
            latency_ms=100,
            metadata={"config": {"timeout": 30, "retry": True}},
        )

        assert step.metadata["config"]["timeout"] == 30
