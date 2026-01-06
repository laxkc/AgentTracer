"""
Enum Definitions for AgentTracer Platform

This module defines all enums for decision and quality signal tracking:
- Decision types and reason codes
- Signal types and signal codes

These enums enforce structured, privacy-safe metadata capture.
"""

from enum import Enum
from typing import Dict, List


# Decision Types

class DecisionType(str, Enum):
    """
    Types of decisions that agents can make.

    These represent high-level decision categories that agents
    explicitly record during execution.
    """
    TOOL_SELECTION = "tool_selection"
    RETRIEVAL_STRATEGY = "retrieval_strategy"
    RESPONSE_MODE = "response_mode"
    RETRY_STRATEGY = "retry_strategy"
    ORCHESTRATION_PATH = "orchestration_path"


# Reason Codes (by Decision Type)

class ToolSelectionReason(str, Enum):
    """Reason codes for tool_selection decisions."""
    FRESH_DATA_REQUIRED = "fresh_data_required"
    CACHED_DATA_SUFFICIENT = "cached_data_sufficient"
    TOOL_UNAVAILABLE = "tool_unavailable"
    COST_OPTIMIZATION = "cost_optimization"
    LATENCY_OPTIMIZATION = "latency_optimization"
    ACCURACY_REQUIRED = "accuracy_required"


class RetrievalStrategyReason(str, Enum):
    """Reason codes for retrieval_strategy decisions."""
    SEMANTIC_SEARCH_PREFERRED = "semantic_search_preferred"
    KEYWORD_MATCH_SUFFICIENT = "keyword_match_sufficient"
    HYBRID_APPROACH_NEEDED = "hybrid_approach_needed"
    FILTER_APPLIED = "filter_applied"
    RERANK_REQUIRED = "rerank_required"


class ResponseModeReason(str, Enum):
    """Reason codes for response_mode decisions."""
    STREAMING_REQUESTED = "streaming_requested"
    BATCH_PREFERRED = "batch_preferred"
    FORMAT_CONSTRAINT = "format_constraint"
    LENGTH_CONSTRAINT = "length_constraint"


class RetryStrategyReason(str, Enum):
    """Reason codes for retry_strategy decisions."""
    TRANSIENT_ERROR_DETECTED = "transient_error_detected"
    RATE_LIMIT_ENCOUNTERED = "rate_limit_encountered"
    NO_RETRY_TERMINAL_ERROR = "no_retry_terminal_error"
    RETRY_BUDGET_EXHAUSTED = "retry_budget_exhausted"
    BACKOFF_REQUIRED = "backoff_required"


class OrchestrationPathReason(str, Enum):
    """Reason codes for orchestration_path decisions."""
    SEQUENTIAL_REQUIRED = "sequential_required"
    PARALLEL_PREFERRED = "parallel_preferred"
    CONDITIONAL_BRANCH = "conditional_branch"
    EARLY_EXIT = "early_exit"
    FALLBACK_PATH = "fallback_path"


# Decision Reason Code Mapping

DECISION_REASON_CODES: Dict[DecisionType, List[str]] = {
    DecisionType.TOOL_SELECTION: [e.value for e in ToolSelectionReason],
    DecisionType.RETRIEVAL_STRATEGY: [e.value for e in RetrievalStrategyReason],
    DecisionType.RESPONSE_MODE: [e.value for e in ResponseModeReason],
    DecisionType.RETRY_STRATEGY: [e.value for e in RetryStrategyReason],
    DecisionType.ORCHESTRATION_PATH: [e.value for e in OrchestrationPathReason],
}


# Signal Types

class SignalType(str, Enum):
    """
    Types of quality signals that can be observed.

    These represent atomic, factual indicators correlated with
    outcome quality. Signals are non-judgmental observations.
    """
    SCHEMA_VALID = "schema_valid"
    EMPTY_RETRIEVAL = "empty_retrieval"
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILURE = "tool_failure"
    RETRY_OCCURRED = "retry_occurred"
    LATENCY_THRESHOLD = "latency_threshold"
    TOKEN_USAGE = "token_usage"


# Signal Codes (by Signal Type)

class SchemaValidSignal(str, Enum):
    """Signal codes for schema_valid signal type."""
    FULL_MATCH = "full_match"
    PARTIAL_MATCH = "partial_match"
    VALIDATION_FAILED = "validation_failed"
    NO_SCHEMA_DEFINED = "no_schema_defined"


class EmptyRetrievalSignal(str, Enum):
    """Signal codes for empty_retrieval signal type."""
    NO_RESULTS = "no_results"
    FILTERED_OUT = "filtered_out"
    INDEX_EMPTY = "index_empty"


class ToolSuccessSignal(str, Enum):
    """Signal codes for tool_success signal type."""
    FIRST_ATTEMPT = "first_attempt"
    AFTER_RETRY = "after_retry"
    FALLBACK_USED = "fallback_used"


class ToolFailureSignal(str, Enum):
    """Signal codes for tool_failure signal type."""
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_FAILED = "authentication_failed"


class RetryOccurredSignal(str, Enum):
    """Signal codes for retry_occurred signal type."""
    SINGLE_RETRY = "single_retry"
    MULTIPLE_RETRIES = "multiple_retries"
    MAX_RETRIES_REACHED = "max_retries_reached"


class LatencyThresholdSignal(str, Enum):
    """Signal codes for latency_threshold signal type."""
    UNDER_THRESHOLD = "under_threshold"
    EXCEEDED_THRESHOLD = "exceeded_threshold"
    SIGNIFICANTLY_EXCEEDED = "significantly_exceeded"


class TokenUsageSignal(str, Enum):
    """Signal codes for token_usage signal type."""
    LOW_USAGE = "low_usage"
    MODERATE_USAGE = "moderate_usage"
    HIGH_USAGE = "high_usage"
    LIMIT_APPROACHED = "limit_approached"


# Signal Code Mapping

SIGNAL_CODES: Dict[SignalType, List[str]] = {
    SignalType.SCHEMA_VALID: [e.value for e in SchemaValidSignal],
    SignalType.EMPTY_RETRIEVAL: [e.value for e in EmptyRetrievalSignal],
    SignalType.TOOL_SUCCESS: [e.value for e in ToolSuccessSignal],
    SignalType.TOOL_FAILURE: [e.value for e in ToolFailureSignal],
    SignalType.RETRY_OCCURRED: [e.value for e in RetryOccurredSignal],
    SignalType.LATENCY_THRESHOLD: [e.value for e in LatencyThresholdSignal],
    SignalType.TOKEN_USAGE: [e.value for e in TokenUsageSignal],
}


# Validation Functions

def validate_decision_type(decision_type: str) -> bool:
    """
    Validate that decision_type is a valid enum value.

    Args:
        decision_type: The decision type string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        DecisionType(decision_type)
        return True
    except ValueError:
        return False


def validate_reason_code(decision_type: str, reason_code: str) -> bool:
    """
    Validate that reason_code is valid for the given decision_type.

    Args:
        decision_type: The decision type
        reason_code: The reason code to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        dt = DecisionType(decision_type)
        return reason_code in DECISION_REASON_CODES.get(dt, [])
    except ValueError:
        return False


def validate_signal_type(signal_type: str) -> bool:
    """
    Validate that signal_type is a valid enum value.

    Args:
        signal_type: The signal type string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        SignalType(signal_type)
        return True
    except ValueError:
        return False


def validate_signal_code(signal_type: str, signal_code: str) -> bool:
    """
    Validate that signal_code is valid for the given signal_type.

    Args:
        signal_type: The signal type
        signal_code: The signal code to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        st = SignalType(signal_type)
        return signal_code in SIGNAL_CODES.get(st, [])
    except ValueError:
        return False


def get_valid_reason_codes(decision_type: str) -> List[str]:
    """
    Get all valid reason codes for a given decision type.

    Args:
        decision_type: The decision type

    Returns:
        List of valid reason codes, or empty list if invalid decision type
    """
    try:
        dt = DecisionType(decision_type)
        return DECISION_REASON_CODES.get(dt, [])
    except ValueError:
        return []


def get_valid_signal_codes(signal_type: str) -> List[str]:
    """
    Get all valid signal codes for a given signal type.

    Args:
        signal_type: The signal type

    Returns:
        List of valid signal codes, or empty list if invalid signal type
    """
    try:
        st = SignalType(signal_type)
        return SIGNAL_CODES.get(st, [])
    except ValueError:
        return []
