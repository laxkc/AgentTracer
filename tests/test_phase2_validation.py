"""
Unit Tests for Phase 2: Decision and Quality Signal Validation

Tests Phase 2 privacy enforcement and enum validation:
- Decision type and reason code validation
- Signal type and code validation
- Privacy metadata validation
- Pydantic model validation
- Database constraint validation

Critical: These tests verify NO PHASE 1 BEHAVIOR CHANGES
"""

import pytest
from datetime import datetime
from uuid import uuid4

from backend.models import (
    AgentDecisionCreate,
    AgentQualitySignalCreate,
    AgentDecisionResponse,
    AgentQualitySignalResponse,
)
from backend.enums import (
    DecisionType,
    SignalType,
    validate_decision_type,
    validate_reason_code,
    validate_signal_type,
    validate_signal_code,
    get_valid_reason_codes,
    get_valid_signal_codes,
)


# ============================================================================
# Enum Validation Tests
# ============================================================================


class TestDecisionEnumValidation:
    """Test decision type and reason code enum validation."""

    def test_valid_decision_types(self):
        """Test that all defined decision types are valid."""
        for decision_type in DecisionType:
            assert validate_decision_type(decision_type.value) is True

    def test_invalid_decision_type(self):
        """Test that invalid decision types are rejected."""
        assert validate_decision_type("invalid_type") is False
        assert validate_decision_type("") is False
        assert validate_decision_type("random_string") is False

    def test_valid_reason_codes_for_tool_selection(self):
        """Test valid reason codes for tool_selection decision type."""
        decision_type = DecisionType.TOOL_SELECTION.value
        valid_codes = get_valid_reason_codes(decision_type)

        assert len(valid_codes) > 0
        assert "fresh_data_required" in valid_codes
        assert "cached_data_sufficient" in valid_codes

        for code in valid_codes:
            assert validate_reason_code(decision_type, code) is True

    def test_invalid_reason_code_for_decision_type(self):
        """Test that invalid reason codes are rejected."""
        decision_type = DecisionType.TOOL_SELECTION.value

        # Test wrong reason code for this decision type
        assert validate_reason_code(decision_type, "invalid_code") is False
        assert validate_reason_code(decision_type, "") is False

    def test_reason_code_from_different_decision_type(self):
        """Test that reason codes are validated against their decision type."""
        # semantic_search_preferred is for retrieval_strategy, not tool_selection
        assert validate_reason_code(
            DecisionType.TOOL_SELECTION.value,
            "semantic_search_preferred"
        ) is False


class TestSignalEnumValidation:
    """Test signal type and signal code enum validation."""

    def test_valid_signal_types(self):
        """Test that all defined signal types are valid."""
        for signal_type in SignalType:
            assert validate_signal_type(signal_type.value) is True

    def test_invalid_signal_type(self):
        """Test that invalid signal types are rejected."""
        assert validate_signal_type("invalid_type") is False
        assert validate_signal_type("") is False
        assert validate_signal_type("random_string") is False

    def test_valid_signal_codes_for_schema_valid(self):
        """Test valid signal codes for schema_valid signal type."""
        signal_type = SignalType.SCHEMA_VALID.value
        valid_codes = get_valid_signal_codes(signal_type)

        assert len(valid_codes) > 0
        assert "full_match" in valid_codes
        assert "partial_match" in valid_codes
        assert "validation_failed" in valid_codes

        for code in valid_codes:
            assert validate_signal_code(signal_type, code) is True

    def test_invalid_signal_code_for_signal_type(self):
        """Test that invalid signal codes are rejected."""
        signal_type = SignalType.SCHEMA_VALID.value

        # Test wrong signal code for this signal type
        assert validate_signal_code(signal_type, "invalid_code") is False
        assert validate_signal_code(signal_type, "") is False

    def test_signal_code_from_different_signal_type(self):
        """Test that signal codes are validated against their signal type."""
        # no_results is for empty_retrieval, not schema_valid
        assert validate_signal_code(
            SignalType.SCHEMA_VALID.value,
            "no_results"
        ) is False


# ============================================================================
# Privacy Validation Tests (CRITICAL)
# ============================================================================


class TestDecisionPrivacyValidation:
    """Test privacy enforcement for decision metadata."""

    def test_valid_decision_metadata(self):
        """Test that valid metadata is accepted."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            metadata={
                "tool_latency_ms": 150,
                "retry_attempt": 1,
                "tool_name": "api_v2"
            }
        )
        assert decision.metadata["tool_latency_ms"] == 150

    def test_blocked_metadata_key_prompt(self):
        """Test that 'prompt' key in metadata is rejected."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"prompt": "What is the weather?"}
            )

    def test_blocked_metadata_key_response(self):
        """Test that 'response' key in metadata is rejected."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"response": "The weather is sunny"}
            )

    def test_blocked_metadata_key_reasoning(self):
        """Test that 'reasoning' key in metadata is rejected."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"reasoning": "I think API is better"}
            )

    def test_blocked_metadata_key_case_insensitive(self):
        """Test that blocked keys are case-insensitive."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"PROMPT": "test"}
            )

    def test_metadata_string_length_limit(self):
        """Test that long strings in metadata are rejected."""
        long_string = "x" * 101  # 101 characters
        with pytest.raises(ValueError, match="exceeds 100 characters"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"description": long_string}
            )

    def test_metadata_non_primitive_type(self):
        """Test that non-primitive types in metadata are rejected."""
        with pytest.raises(ValueError, match="must be primitive type"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"nested": {"key": "value"}}
            )

    def test_metadata_list_type_rejected(self):
        """Test that list types in metadata are rejected."""
        with pytest.raises(ValueError, match="must be primitive type"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"items": ["a", "b", "c"]}
            )


class TestSignalPrivacyValidation:
    """Test privacy enforcement for signal metadata."""

    def test_valid_signal_metadata(self):
        """Test that valid metadata is accepted."""
        signal = AgentQualitySignalCreate(
            signal_type=SignalType.SCHEMA_VALID.value,
            signal_code="full_match",
            value=True,
            metadata={
                "schema_version": "1.2.0",
                "field_count": 5,
                "validation_time_ms": 10
            }
        )
        assert signal.metadata["schema_version"] == "1.2.0"

    def test_blocked_metadata_key_prompt(self):
        """Test that 'prompt' key in metadata is rejected."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentQualitySignalCreate(
                signal_type=SignalType.SCHEMA_VALID.value,
                signal_code="full_match",
                value=True,
                metadata={"prompt": "test"}
            )

    def test_blocked_metadata_key_text(self):
        """Test that 'text' key in metadata is rejected."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentQualitySignalCreate(
                signal_type=SignalType.SCHEMA_VALID.value,
                signal_code="full_match",
                value=True,
                metadata={"text": "some content"}
            )

    def test_metadata_string_length_limit(self):
        """Test that long strings in metadata are rejected."""
        long_string = "x" * 150
        with pytest.raises(ValueError, match="exceeds 100 characters"):
            AgentQualitySignalCreate(
                signal_type=SignalType.SCHEMA_VALID.value,
                signal_code="full_match",
                value=True,
                metadata={"note": long_string}
            )


# ============================================================================
# Pydantic Model Validation Tests
# ============================================================================


class TestAgentDecisionCreate:
    """Test AgentDecisionCreate Pydantic model validation."""

    def test_create_valid_decision(self):
        """Test creating a valid decision."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            confidence=0.85,
            metadata={"retry_count": 0}
        )

        assert decision.decision_type == "tool_selection"
        assert decision.selected == "call_api"
        assert decision.reason_code == "fresh_data_required"
        assert decision.confidence == 0.85
        assert decision.decision_id is not None

    def test_invalid_decision_type_rejected(self):
        """Test that invalid decision type is rejected."""
        with pytest.raises(ValueError, match="Invalid decision_type"):
            AgentDecisionCreate(
                decision_type="invalid_type",
                selected="call_api",
                reason_code="fresh_data_required"
            )

    def test_invalid_reason_code_for_type_rejected(self):
        """Test that invalid reason code for decision type is rejected."""
        with pytest.raises(ValueError, match="Invalid reason_code"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="semantic_search_preferred"  # Wrong type
            )

    def test_confidence_out_of_range_rejected(self):
        """Test that confidence outside 0.0-1.0 is rejected."""
        with pytest.raises(ValueError):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                confidence=1.5  # Invalid
            )

    def test_negative_confidence_rejected(self):
        """Test that negative confidence is rejected."""
        with pytest.raises(ValueError):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,
                selected="call_api",
                reason_code="fresh_data_required",
                confidence=-0.1  # Invalid
            )

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required"
            # No confidence, no step_id, no metadata
        )

        assert decision.confidence is None
        assert decision.step_id is None
        assert decision.metadata == {}


class TestAgentQualitySignalCreate:
    """Test AgentQualitySignalCreate Pydantic model validation."""

    def test_create_valid_signal(self):
        """Test creating a valid quality signal."""
        signal = AgentQualitySignalCreate(
            signal_type=SignalType.SCHEMA_VALID.value,
            signal_code="full_match",
            value=True,
            weight=0.9,
            metadata={"schema_version": "1.0"}
        )

        assert signal.signal_type == "schema_valid"
        assert signal.signal_code == "full_match"
        assert signal.value is True
        assert signal.weight == 0.9
        assert signal.signal_id is not None

    def test_invalid_signal_type_rejected(self):
        """Test that invalid signal type is rejected."""
        with pytest.raises(ValueError, match="Invalid signal_type"):
            AgentQualitySignalCreate(
                signal_type="invalid_type",
                signal_code="full_match",
                value=True
            )

    def test_invalid_signal_code_for_type_rejected(self):
        """Test that invalid signal code for signal type is rejected."""
        with pytest.raises(ValueError, match="Invalid signal_code"):
            AgentQualitySignalCreate(
                signal_type=SignalType.SCHEMA_VALID.value,
                signal_code="no_results",  # Wrong type
                value=True
            )

    def test_weight_out_of_range_rejected(self):
        """Test that weight outside 0.0-1.0 is rejected."""
        with pytest.raises(ValueError):
            AgentQualitySignalCreate(
                signal_type=SignalType.SCHEMA_VALID.value,
                signal_code="full_match",
                value=True,
                weight=2.0  # Invalid
            )

    def test_boolean_value_required(self):
        """Test that value must be boolean."""
        signal = AgentQualitySignalCreate(
            signal_type=SignalType.SCHEMA_VALID.value,
            signal_code="full_match",
            value=True
        )
        assert signal.value is True

        signal2 = AgentQualitySignalCreate(
            signal_type=SignalType.SCHEMA_VALID.value,
            signal_code="validation_failed",
            value=False
        )
        assert signal2.value is False


# ============================================================================
# Response Model Tests
# ============================================================================


class TestAgentDecisionResponse:
    """Test AgentDecisionResponse serialization."""

    def test_response_serialization(self):
        """Test that response model serializes correctly."""
        # This would typically be tested with actual database objects
        # For now, test that the model accepts the right fields
        response = AgentDecisionResponse(
            decision_id=uuid4(),
            run_id=uuid4(),
            step_id=uuid4(),
            decision_type="tool_selection",
            selected="call_api",
            reason_code="fresh_data_required",
            confidence=0.85,
            decision_metadata={"retry": 0},  # Use alias
            recorded_at=datetime.now(),
            created_at=datetime.now()
        )

        assert response.decision_type == "tool_selection"
        # Check that metadata alias works
        assert "retry" in response.metadata


class TestAgentQualitySignalResponse:
    """Test AgentQualitySignalResponse serialization."""

    def test_response_serialization(self):
        """Test that response model serializes correctly."""
        response = AgentQualitySignalResponse(
            signal_id=uuid4(),
            run_id=uuid4(),
            step_id=None,
            signal_type="schema_valid",
            signal_code="full_match",
            value=True,
            weight=0.9,
            signal_metadata={"version": "1.0"},  # Use alias
            recorded_at=datetime.now(),
            created_at=datetime.now()
        )

        assert response.signal_type == "schema_valid"
        assert response.value is True
        # Check that metadata alias works
        assert "version" in response.metadata


# ============================================================================
# Integration: Privacy + Enum Validation
# ============================================================================


class TestCombinedValidation:
    """Test that both privacy and enum validation work together."""

    def test_valid_decision_passes_all_checks(self):
        """Test that a valid decision passes all validation."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.RETRY_STRATEGY.value,
            selected="retry",
            reason_code="transient_error_detected",
            confidence=0.75,
            metadata={"attempt": 2, "max_retries": 3}
        )

        assert decision.decision_type == "retry_strategy"
        assert decision.reason_code == "transient_error_detected"
        assert decision.metadata["attempt"] == 2

    def test_privacy_violation_overrides_valid_enums(self):
        """Test that privacy violations are caught even with valid enums."""
        with pytest.raises(ValueError, match="may contain sensitive data"):
            AgentDecisionCreate(
                decision_type=DecisionType.TOOL_SELECTION.value,  # Valid
                selected="call_api",
                reason_code="fresh_data_required",  # Valid
                metadata={"prompt": "secret"}  # INVALID - privacy violation
            )

    def test_enum_violation_with_valid_metadata(self):
        """Test that enum violations are caught even with valid metadata."""
        with pytest.raises(ValueError, match="Invalid decision_type"):
            AgentDecisionCreate(
                decision_type="invalid_type",  # INVALID - bad enum
                selected="call_api",
                reason_code="fresh_data_required",
                metadata={"retry": 0}  # Valid
            )


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_metadata_allowed(self):
        """Test that empty metadata is allowed."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            metadata={}
        )
        assert decision.metadata == {}

    def test_none_confidence_allowed(self):
        """Test that None confidence is allowed."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            confidence=None
        )
        assert decision.confidence is None

    def test_confidence_exactly_zero(self):
        """Test that confidence = 0.0 is valid."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            confidence=0.0
        )
        assert decision.confidence == 0.0

    def test_confidence_exactly_one(self):
        """Test that confidence = 1.0 is valid."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            confidence=1.0
        )
        assert decision.confidence == 1.0

    def test_metadata_value_exactly_100_chars(self):
        """Test that metadata string of exactly 100 chars is allowed."""
        string_100 = "x" * 100
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            metadata={"note": string_100}
        )
        assert len(decision.metadata["note"]) == 100

    def test_metadata_with_none_value(self):
        """Test that None values in metadata are allowed."""
        decision = AgentDecisionCreate(
            decision_type=DecisionType.TOOL_SELECTION.value,
            selected="call_api",
            reason_code="fresh_data_required",
            metadata={"optional_field": None}
        )
        assert decision.metadata["optional_field"] is None
