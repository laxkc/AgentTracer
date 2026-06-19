"""
AgentTracer Platform - Core Data Models

This module implements data models for comprehensive agent observability:

Execution Observability:
- AgentRun: Represents a single agent execution
- AgentStep: Ordered step within a run with latency tracking
- AgentFailure: Semantic failure classification

Decision & Quality Observability:
- AgentDecision: Structured decision points
- AgentQualitySignal: Observable quality indicators

Privacy constraints:
- NO raw prompts or LLM responses
- NO chain-of-thought storage
- NO PII
- Safe, structured metadata only
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Type Definitions

StepType = Literal["plan", "retrieve", "tool", "respond", "other"]
RunStatus = Literal["success", "failure", "partial"]
FailureType = Literal["tool", "model", "retrieval", "orchestration"]

# SQLAlchemy Base

Base = declarative_base()


# SQLAlchemy ORM Models (Database Layer)


class AgentRunDB(Base):
    """
    Database model for agent_runs table.

    Represents a single execution of an agent from start to completion.
    """

    __tablename__ = "agent_runs"

    run_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(String(255), nullable=False, index=True)
    agent_version = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), nullable=False, default="production", index=True)
    status = Column(String(20), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    steps = relationship("AgentStepDB", back_populates="run", cascade="all, delete-orphan")
    failures = relationship("AgentFailureDB", back_populates="run", cascade="all, delete-orphan")
    # Optional decision and quality signal relationships
    decisions = relationship("AgentDecisionDB", back_populates="run", cascade="all, delete-orphan")
    quality_signals = relationship(
        "AgentQualitySignalDB", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('success', 'failure', 'partial')", name="valid_status"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="valid_end_time"),
    )


class AgentStepDB(Base):
    """
    Database model for agent_steps table.

    Represents an ordered step within an agent run.
    Each retry is a separate step span for accurate latency tracking.
    """

    __tablename__ = "agent_steps"

    step_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=False)

    # Safe metadata only (no prompts, no responses, no PII)
    # Note: Using 'step_metadata' as Python attr to avoid conflict with Base.metadata
    step_metadata = Column("metadata", JSON, nullable=False, default={})

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("AgentRunDB", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("run_id", "seq", name="unique_step_seq"),
        CheckConstraint(
            "step_type IN ('plan', 'retrieve', 'tool', 'respond', 'other')",
            name="valid_step_type",
        ),
        CheckConstraint("latency_ms >= 0", name="valid_latency"),
        CheckConstraint("ended_at >= started_at", name="valid_step_timing"),
    )


class AgentFailureDB(Base):
    """
    Database model for agent_failures table.

    Semantic failure classification with structured taxonomy.
    """

    __tablename__ = "agent_failures"

    failure_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_steps.step_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Mandatory failure taxonomy
    failure_type = Column(String(50), nullable=False, index=True)
    failure_code = Column(String(100), nullable=False, index=True)

    # Human-readable message (no PII, no prompt content)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("AgentRunDB", back_populates="failures")

    __table_args__ = (
        CheckConstraint(
            "failure_type IN ('tool', 'model', 'retrieval', 'orchestration')",
            name="valid_failure_type",
        ),
        CheckConstraint("LENGTH(failure_code) > 0", name="valid_failure_code"),
    )


# Decision & Quality Signal ORM Models


class AgentDecisionDB(Base):
    """
    Database model for agent_decisions table.

    Represents a structured decision point made by an agent.
    This is additive to the core execution tracking - no existing tables modified.

    Privacy guarantee: Only structured enums and numeric values stored.
    """

    __tablename__ = "agent_decisions"

    decision_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_steps.step_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Decision metadata (all enum-based)
    decision_type = Column(String(100), nullable=False, index=True)
    selected = Column(String(200), nullable=False)
    reason_code = Column(String(100), nullable=False, index=True)
    confidence = Column(Float, nullable=True)

    # Structured metadata only (validated for privacy)
    decision_metadata = Column("metadata", JSON, nullable=False, default={})

    recorded_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("AgentRunDB", back_populates="decisions")

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="valid_confidence_range",
        ),
        CheckConstraint("LENGTH(decision_type) > 0", name="valid_decision_type"),
        CheckConstraint("LENGTH(selected) > 0", name="valid_selected"),
        CheckConstraint("LENGTH(reason_code) > 0", name="valid_reason_code"),
    )


class AgentQualitySignalDB(Base):
    """
    Database model for agent_quality_signals table.

    Represents an atomic quality signal correlated with outcomes.
    This is additive to the core execution tracking - no existing tables modified.

    Privacy guarantee: Only structured enums, booleans, and numeric values stored.
    """

    __tablename__ = "agent_quality_signals"

    signal_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("agent_steps.step_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Signal metadata (all enum-based)
    signal_type = Column(String(100), nullable=False, index=True)
    signal_code = Column(String(100), nullable=False, index=True)
    value = Column(Boolean, nullable=False)
    weight = Column(Float, nullable=True)

    # Structured metadata only (validated for privacy)
    signal_metadata = Column("metadata", JSON, nullable=False, default={})

    recorded_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    run = relationship("AgentRunDB", back_populates="quality_signals")

    __table_args__ = (
        CheckConstraint(
            "weight IS NULL OR (weight >= 0.0 AND weight <= 1.0)",
            name="valid_weight_range",
        ),
        CheckConstraint("LENGTH(signal_type) > 0", name="valid_signal_type"),
        CheckConstraint("LENGTH(signal_code) > 0", name="valid_signal_code"),
    )


# Pydantic Models (API Layer - Validation & Serialization)


class AgentStepCreate(BaseModel):
    """
    Schema for creating an agent step (ingest API).

    Enforces privacy constraints:
    - No prompt or response content
    - Safe metadata only
    """

    step_id: UUID = Field(default_factory=uuid4)
    seq: int = Field(..., ge=0, description="Step sequence number (0-indexed)")
    step_type: StepType
    name: str = Field(..., min_length=1, max_length=255)
    latency_ms: int = Field(..., ge=0, description="Step latency in milliseconds")
    started_at: datetime
    ended_at: datetime

    # Safe metadata only - enforced by validation
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_safe_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure metadata contains no sensitive data.

        Allowed: tool names, HTTP codes, retry counts, numeric values
        Forbidden: prompts, responses, PII, text content
        """
        # This is a basic check - in production, implement stricter validation
        forbidden_keys = {"prompt", "response", "output", "input", "content", "text", "message"}
        for key in v.keys():
            # Use exact key matching, not substring matching
            if key.lower() in forbidden_keys:
                raise ValueError(
                    f"Metadata key '{key}' may contain sensitive data. "
                    f"Only safe metadata allowed (tool names, codes, counts)."
                )
        return v

    @field_validator("ended_at")
    @classmethod
    def validate_timing(cls, v: datetime, info) -> datetime:
        """Ensure ended_at >= started_at"""
        if "started_at" in info.data and v < info.data["started_at"]:
            raise ValueError("ended_at must be >= started_at")
        return v


class AgentFailureCreate(BaseModel):
    """
    Schema for creating an agent failure (ingest API).

    Enforces mandatory failure taxonomy.
    """

    step_id: UUID | None = Field(None, description="Optional step where failure occurred")
    failure_type: FailureType
    failure_code: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, description="Human-readable failure description")

    @field_validator("message")
    @classmethod
    def validate_no_sensitive_data(cls, v: str) -> str:
        """
        Ensure failure message contains no PII or sensitive data.

        This is a basic check - in production, implement NLP-based PII detection.
        """
        # Basic check for obvious PII patterns
        sensitive_patterns = ["password", "api_key", "token", "secret"]
        lower_msg = v.lower()
        for pattern in sensitive_patterns:
            if pattern in lower_msg:
                raise ValueError(
                    f"Failure message may contain sensitive data ('{pattern}'). "
                    f"Privacy-safe messages required."
                )
        return v


# Decision & Quality Signal Pydantic Models


class AgentDecisionCreate(BaseModel):
    """
    Schema for creating an agent decision (ingest API).

    Enforces strict validation:
    - decision_type must be valid enum
    - reason_code must be valid for the decision_type
    - confidence must be 0.0-1.0 if provided
    - metadata must be privacy-safe
    """

    decision_id: UUID = Field(default_factory=uuid4)
    step_id: UUID | None = Field(None, description="Optional step where decision was made")
    decision_type: str = Field(..., min_length=1, max_length=100)
    selected: str = Field(
        ..., min_length=1, max_length=200, description="The option that was selected"
    )
    reason_code: str = Field(
        ..., min_length=1, max_length=100, description="Structured reason code (enum)"
    )
    candidates: list[str] | None = Field(
        None, description="Other options considered (stored in metadata)"
    )
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Decision confidence 0.0-1.0"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured metadata only")

    @field_validator("decision_type")
    @classmethod
    def validate_decision_type_enum(cls, v: str) -> str:
        """Validate decision_type is a valid enum value."""
        from server.models.enums import validate_decision_type

        if not validate_decision_type(v):
            from server.models.enums import DecisionType

            valid_types = [dt.value for dt in DecisionType]
            raise ValueError(f"Invalid decision_type: '{v}'. Must be one of: {valid_types}")
        return v

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code_for_type(cls, v: str, info) -> str:
        """Validate reason_code is valid for the decision_type."""
        from server.models.enums import get_valid_reason_codes, validate_reason_code

        if "decision_type" in info.data:
            decision_type = info.data["decision_type"]
            if not validate_reason_code(decision_type, v):
                valid_codes = get_valid_reason_codes(decision_type)
                raise ValueError(
                    f"Invalid reason_code '{v}' for decision_type '{decision_type}'. "
                    f"Valid codes: {valid_codes}"
                )
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_privacy(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate metadata contains no sensitive data.

        Blocked keys: prompt, response, reasoning, thought, message, content, text, etc.
        Max string length: 100 characters
        Only primitive types allowed
        """
        BLOCKED_KEYS = {
            "prompt",
            "response",
            "reasoning",
            "thought",
            "message",
            "content",
            "text",
            "output",
            "input",
            "chain_of_thought",
            "explanation",
            "rationale",
        }

        for key, value in v.items():
            # Check blocked keys
            if key.lower() in BLOCKED_KEYS:
                raise ValueError(
                    f"Metadata key '{key}' may contain sensitive data and is not allowed. "
                    f"Privacy constraint: no prompts, responses, or reasoning text."
                )

            # Check value types (primitives only)
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError(
                    f"Metadata value for '{key}' must be primitive type (str, int, float, bool, None). "
                    f"Got: {type(value).__name__}"
                )

            # Check string lengths
            if isinstance(value, str) and len(value) > 100:
                raise ValueError(
                    f"Metadata string '{key}' exceeds 100 characters. "
                    f"Privacy constraint: structured metadata only, no long text."
                )

        return v


class AgentQualitySignalCreate(BaseModel):
    """
    Schema for creating a quality signal (ingest API).

    Enforces strict validation:
    - signal_type must be valid enum
    - signal_code must be valid for the signal_type
    - value is boolean (signal present/absent)
    - weight must be 0.0-1.0 if provided
    - metadata must be privacy-safe
    """

    signal_id: UUID = Field(default_factory=uuid4)
    step_id: UUID | None = Field(None, description="Optional step where signal was observed")
    signal_type: str = Field(..., min_length=1, max_length=100)
    signal_code: str = Field(..., min_length=1, max_length=100, description="Specific signal code")
    value: bool = Field(..., description="Signal present (True) or absent (False)")
    weight: float | None = Field(
        None, ge=0.0, le=1.0, description="Signal weight for correlation 0.0-1.0"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured metadata only")

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type_enum(cls, v: str) -> str:
        """Validate signal_type is a valid enum value."""
        from server.models.enums import validate_signal_type

        if not validate_signal_type(v):
            from server.models.enums import SignalType

            valid_types = [st.value for st in SignalType]
            raise ValueError(f"Invalid signal_type: '{v}'. Must be one of: {valid_types}")
        return v

    @field_validator("signal_code")
    @classmethod
    def validate_signal_code_for_type(cls, v: str, info) -> str:
        """Validate signal_code is valid for the signal_type."""
        from server.models.enums import get_valid_signal_codes, validate_signal_code

        if "signal_type" in info.data:
            signal_type = info.data["signal_type"]
            if not validate_signal_code(signal_type, v):
                valid_codes = get_valid_signal_codes(signal_type)
                raise ValueError(
                    f"Invalid signal_code '{v}' for signal_type '{signal_type}'. "
                    f"Valid codes: {valid_codes}"
                )
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_privacy(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate metadata contains no sensitive data.

        Blocked keys: prompt, response, reasoning, thought, message, content, text, etc.
        Max string length: 100 characters
        Only primitive types allowed
        """
        BLOCKED_KEYS = {
            "prompt",
            "response",
            "reasoning",
            "thought",
            "message",
            "content",
            "text",
            "output",
            "input",
            "chain_of_thought",
            "explanation",
            "rationale",
        }

        for key, value in v.items():
            # Check blocked keys
            if key.lower() in BLOCKED_KEYS:
                raise ValueError(
                    f"Metadata key '{key}' may contain sensitive data and is not allowed. "
                    f"Privacy constraint: no prompts, responses, or reasoning text."
                )

            # Check value types (primitives only)
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError(
                    f"Metadata value for '{key}' must be primitive type (str, int, float, bool, None). "
                    f"Got: {type(value).__name__}"
                )

            # Check string lengths
            if isinstance(value, str) and len(value) > 100:
                raise ValueError(
                    f"Metadata string '{key}' exceeds 100 characters. "
                    f"Privacy constraint: structured metadata only, no long text."
                )

        return v


class AgentRunCreate(BaseModel):
    """
    Schema for creating an agent run (ingest API).

    Complete run with steps, optional failure, decisions, and quality signals.
    Enforces privacy and structural constraints.
    """

    run_id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(..., min_length=1, max_length=255)
    agent_version: str = Field(..., min_length=1, max_length=100)
    environment: str = Field(default="production", max_length=50)
    status: RunStatus
    started_at: datetime
    ended_at: datetime | None = None

    steps: list[AgentStepCreate] = Field(default_factory=list)
    failure: AgentFailureCreate | None = None

    # Optional decision and quality signal tracking
    decisions: list[AgentDecisionCreate] | None = Field(default_factory=list)
    quality_signals: list[AgentQualitySignalCreate] | None = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def validate_step_sequence(cls, v: list[AgentStepCreate]) -> list[AgentStepCreate]:
        """
        Ensure steps are properly sequenced (0, 1, 2, ...).

        This is critical for timeline reconstruction.
        """
        if not v:
            return v

        sequences = [step.seq for step in v]
        expected = list(range(len(v)))

        if sorted(sequences) != expected:
            raise ValueError(
                f"Steps must have sequential seq values starting from 0. "
                f"Got: {sorted(sequences)}, expected: {expected}"
            )

        return v

    @field_validator("ended_at")
    @classmethod
    def validate_run_timing(cls, v: datetime | None, info) -> datetime | None:
        """Ensure ended_at >= started_at"""
        if v and "started_at" in info.data and v < info.data["started_at"]:
            raise ValueError("ended_at must be >= started_at")
        return v

    @field_validator("failure")
    @classmethod
    def validate_failure_on_failed_runs(
        cls, v: AgentFailureCreate | None, info
    ) -> AgentFailureCreate | None:
        """
        Ensure failed runs have a failure object.

        Explicit failure classification required for all failed runs.
        """
        if "status" in info.data:
            status = info.data["status"]
            if status == "failure" and v is None:
                raise ValueError(
                    "Runs with status='failure' must include a failure object "
                    "for semantic classification"
                )
        return v


class AgentStepResponse(BaseModel):
    """Schema for returning step data (query API)"""

    step_id: UUID
    run_id: UUID
    seq: int
    step_type: StepType
    name: str
    latency_ms: int
    started_at: datetime
    ended_at: datetime
    metadata: dict[str, Any] = Field(
        validation_alias="step_metadata", serialization_alias="metadata"
    )
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AgentFailureResponse(BaseModel):
    """Schema for returning failure data (query API)"""

    failure_id: UUID
    run_id: UUID
    step_id: UUID | None
    failure_type: FailureType
    failure_code: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgentRunResponse(BaseModel):
    """Schema for returning run data with steps and failures (query API)"""

    run_id: UUID
    agent_id: str
    agent_version: str
    environment: str
    status: RunStatus
    started_at: datetime
    ended_at: datetime | None
    created_at: datetime

    steps: list[AgentStepResponse] = []
    failures: list[AgentFailureResponse] = []

    # Optional decision and quality signal data
    decisions: list["AgentDecisionResponse"] = []
    quality_signals: list["AgentQualitySignalResponse"] = []

    class Config:
        from_attributes = True


# Decision & Quality Signal Response Models


class AgentDecisionResponse(BaseModel):
    """Schema for returning decision data (query API)"""

    decision_id: UUID
    run_id: UUID
    step_id: UUID | None
    decision_type: str
    selected: str
    reason_code: str
    confidence: float | None
    metadata: dict[str, Any] = Field(
        validation_alias="decision_metadata", serialization_alias="metadata"
    )
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AgentQualitySignalResponse(BaseModel):
    """Schema for returning quality signal data (query API)"""

    signal_id: UUID
    run_id: UUID
    step_id: UUID | None
    signal_type: str
    signal_code: str
    value: bool
    weight: float | None
    metadata: dict[str, Any] = Field(
        validation_alias="signal_metadata", serialization_alias="metadata"
    )
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


# ============================================================================
# Drift Detection Models
# ============================================================================


class BehaviorProfileDB(Base):
    """
    SQLAlchemy model for behavior_profiles table.
    Statistical snapshots of agent behavior over time windows.
    """

    __tablename__ = "behavior_profiles"

    from sqlalchemy import Column, DateTime, Integer, String
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    profile_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    agent_id = Column(String(255), nullable=False)
    agent_version = Column(String(100), nullable=False)
    environment = Column(String(50), nullable=False)

    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    sample_size = Column(Integer, nullable=False)

    decision_distributions = Column(JSONB, nullable=False, default={})
    signal_distributions = Column(JSONB, nullable=False, default={})
    latency_stats = Column(JSONB, nullable=False, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BehaviorBaselineDB(Base):
    """
    SQLAlchemy model for behavior_baselines table.
    Immutable snapshots of expected agent behavior.
    """

    __tablename__ = "behavior_baselines"

    from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    baseline_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    profile_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("behavior_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_id = Column(String(255), nullable=False, index=True)
    agent_version = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), nullable=False, index=True)

    baseline_type = Column(String(50), nullable=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    description = Column(String(200), nullable=True)

    is_active = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BehaviorDriftDB(Base):
    """
    SQLAlchemy model for behavior_drift table.
    Detected behavioral drift events.
    """

    __tablename__ = "behavior_drift"

    from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    drift_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    baseline_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("behavior_baselines.baseline_id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_id = Column(String(255), nullable=False, index=True)
    agent_version = Column(String(100), nullable=False, index=True)
    environment = Column(String(50), nullable=False, index=True)

    drift_type = Column(String(50), nullable=False, index=True)
    metric = Column(String(255), nullable=False)

    baseline_value = Column(Float, nullable=False)
    observed_value = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    delta_percent = Column(Float, nullable=False)

    significance = Column(Float, nullable=False)
    test_method = Column(String(50), nullable=False)

    severity = Column(String(20), nullable=False, index=True)

    detected_at = Column(DateTime, nullable=False, index=True)
    observation_window_start = Column(DateTime, nullable=False)
    observation_window_end = Column(DateTime, nullable=False)
    observation_sample_size = Column(Integer, nullable=False)

    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
