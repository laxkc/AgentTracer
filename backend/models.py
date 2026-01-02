"""
AgentTracer Platform - Core Data Models

This module implements data models for both Phase 1 and Phase 2:

Phase 1 (Execution Observability):
- AgentRun: Represents a single agent execution
- AgentStep: Ordered step within a run with latency tracking
- AgentFailure: Semantic failure classification

Phase 2 (Decision & Quality Observability - ADDITIVE ONLY):
- AgentDecision: Structured decision points
- AgentQualitySignal: Observable quality indicators

Privacy constraints (both phases):
- NO raw prompts or LLM responses
- NO chain-of-thought storage
- NO PII
- Safe, structured metadata only
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
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

# ============================================================================
# Type Definitions (Phase-1 Enums)
# ============================================================================

StepType = Literal["plan", "retrieve", "tool", "respond", "other"]
RunStatus = Literal["success", "failure", "partial"]
FailureType = Literal["tool", "model", "retrieval", "orchestration"]

# ============================================================================
# SQLAlchemy Base
# ============================================================================

Base = declarative_base()


# ============================================================================
# SQLAlchemy ORM Models (Database Layer)
# ============================================================================


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
    steps = relationship(
        "AgentStepDB", back_populates="run", cascade="all, delete-orphan"
    )
    failures = relationship(
        "AgentFailureDB", back_populates="run", cascade="all, delete-orphan"
    )
    # Phase 2: Optional decision and quality signal relationships
    decisions = relationship(
        "AgentDecisionDB", back_populates="run", cascade="all, delete-orphan"
    )
    quality_signals = relationship(
        "AgentQualitySignalDB", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failure', 'partial')", name="valid_status"
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="valid_end_time"
        ),
    )


class AgentStepDB(Base):
    """
    Database model for agent_steps table.

    Represents an ordered step within an agent run.
    Each retry is a separate step span (critical for Phase-1).
    """

    __tablename__ = "agent_steps"

    step_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
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

    Semantic failure classification using Phase-1 taxonomy.
    """

    __tablename__ = "agent_failures"

    failure_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(
        PGUUID(as_uuid=True), ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
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


# ============================================================================
# Phase 2 SQLAlchemy ORM Models (ADDITIVE ONLY - NO PHASE 1 CHANGES)
# ============================================================================


class AgentDecisionDB(Base):
    """
    Database model for agent_decisions table (Phase 2).

    Represents a structured decision point made by an agent.
    This is ADDITIVE to Phase 1 - NO PHASE 1 TABLES MODIFIED.

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
    Database model for agent_quality_signals table (Phase 2).

    Represents an atomic quality signal correlated with outcomes.
    This is ADDITIVE to Phase 1 - NO PHASE 1 TABLES MODIFIED.

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


# ============================================================================
# Pydantic Models (API Layer - Validation & Serialization)
# ============================================================================


class AgentStepCreate(BaseModel):
    """
    Schema for creating an agent step (ingest API).

    Enforces Phase-1 constraints:
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
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_safe_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
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
                    f"Phase-1 only allows safe metadata (tool names, codes, counts)."
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

    step_id: Optional[UUID] = Field(None, description="Optional step where failure occurred")
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
                    f"Phase-1 requires privacy-safe messages only."
                )
        return v


# ============================================================================
# Phase 2 Pydantic Models - MUST BE BEFORE AgentRunCreate
# ============================================================================


class AgentDecisionCreate(BaseModel):
    """
    Schema for creating an agent decision (Phase 2 ingest API).

    Enforces strict validation:
    - decision_type must be valid enum
    - reason_code must be valid for the decision_type
    - confidence must be 0.0-1.0 if provided
    - metadata must be privacy-safe
    """

    decision_id: UUID = Field(default_factory=uuid4)
    step_id: Optional[UUID] = Field(None, description="Optional step where decision was made")
    decision_type: str = Field(..., min_length=1, max_length=100)
    selected: str = Field(..., min_length=1, max_length=200, description="The option that was selected")
    reason_code: str = Field(..., min_length=1, max_length=100, description="Structured reason code (enum)")
    candidates: Optional[List[str]] = Field(None, description="Other options considered (stored in metadata)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Decision confidence 0.0-1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured metadata only")

    @field_validator("decision_type")
    @classmethod
    def validate_decision_type_enum(cls, v: str) -> str:
        """Validate decision_type is a valid enum value."""
        from backend.enums import validate_decision_type

        if not validate_decision_type(v):
            from backend.enums import DecisionType
            valid_types = [dt.value for dt in DecisionType]
            raise ValueError(
                f"Invalid decision_type: '{v}'. "
                f"Must be one of: {valid_types}"
            )
        return v

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code_for_type(cls, v: str, info) -> str:
        """Validate reason_code is valid for the decision_type."""
        from backend.enums import validate_reason_code, get_valid_reason_codes

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
    def validate_metadata_privacy(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate metadata contains no sensitive data.

        Blocked keys: prompt, response, reasoning, thought, message, content, text, etc.
        Max string length: 100 characters
        Only primitive types allowed
        """
        BLOCKED_KEYS = {
            "prompt", "response", "reasoning", "thought",
            "message", "content", "text", "output", "input",
            "chain_of_thought", "explanation", "rationale"
        }

        for key, value in v.items():
            # Check blocked keys
            if key.lower() in BLOCKED_KEYS:
                raise ValueError(
                    f"Metadata key '{key}' may contain sensitive data and is not allowed. "
                    f"Phase 2 privacy constraint: no prompts, responses, or reasoning text."
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
                    f"Phase 2 privacy constraint: structured metadata only, no long text."
                )

        return v


class AgentQualitySignalCreate(BaseModel):
    """
    Schema for creating a quality signal (Phase 2 ingest API).

    Enforces strict validation:
    - signal_type must be valid enum
    - signal_code must be valid for the signal_type
    - value is boolean (signal present/absent)
    - weight must be 0.0-1.0 if provided
    - metadata must be privacy-safe
    """

    signal_id: UUID = Field(default_factory=uuid4)
    step_id: Optional[UUID] = Field(None, description="Optional step where signal was observed")
    signal_type: str = Field(..., min_length=1, max_length=100)
    signal_code: str = Field(..., min_length=1, max_length=100, description="Specific signal code")
    value: bool = Field(..., description="Signal present (True) or absent (False)")
    weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Signal weight for correlation 0.0-1.0")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured metadata only")

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type_enum(cls, v: str) -> str:
        """Validate signal_type is a valid enum value."""
        from backend.enums import validate_signal_type

        if not validate_signal_type(v):
            from backend.enums import SignalType
            valid_types = [st.value for st in SignalType]
            raise ValueError(
                f"Invalid signal_type: '{v}'. "
                f"Must be one of: {valid_types}"
            )
        return v

    @field_validator("signal_code")
    @classmethod
    def validate_signal_code_for_type(cls, v: str, info) -> str:
        """Validate signal_code is valid for the signal_type."""
        from backend.enums import validate_signal_code, get_valid_signal_codes

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
    def validate_metadata_privacy(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate metadata contains no sensitive data.

        Blocked keys: prompt, response, reasoning, thought, message, content, text, etc.
        Max string length: 100 characters
        Only primitive types allowed
        """
        BLOCKED_KEYS = {
            "prompt", "response", "reasoning", "thought",
            "message", "content", "text", "output", "input",
            "chain_of_thought", "explanation", "rationale"
        }

        for key, value in v.items():
            # Check blocked keys
            if key.lower() in BLOCKED_KEYS:
                raise ValueError(
                    f"Metadata key '{key}' may contain sensitive data and is not allowed. "
                    f"Phase 2 privacy constraint: no prompts, responses, or reasoning text."
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
                    f"Phase 2 privacy constraint: structured metadata only, no long text."
                )

        return v


class AgentRunCreate(BaseModel):
    """
    Schema for creating an agent run (ingest API).

    Complete run with steps and optional failure (Phase 1).
    Phase 2 adds optional decisions and quality signals.
    Enforces privacy and structural constraints.
    """

    run_id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(..., min_length=1, max_length=255)
    agent_version: str = Field(..., min_length=1, max_length=100)
    environment: str = Field(default="production", max_length=50)
    status: RunStatus
    started_at: datetime
    ended_at: Optional[datetime] = None

    steps: List[AgentStepCreate] = Field(default_factory=list)
    failure: Optional[AgentFailureCreate] = None

    # Phase 2: Optional decision and quality signal tracking
    decisions: Optional[List[AgentDecisionCreate]] = Field(default_factory=list)
    quality_signals: Optional[List[AgentQualitySignalCreate]] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def validate_step_sequence(cls, v: List[AgentStepCreate]) -> List[AgentStepCreate]:
        """
        Ensure steps are properly sequenced (0, 1, 2, ...).

        This is critical for Phase-1 timeline reconstruction.
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
    def validate_run_timing(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure ended_at >= started_at"""
        if v and "started_at" in info.data and v < info.data["started_at"]:
            raise ValueError("ended_at must be >= started_at")
        return v

    @field_validator("failure")
    @classmethod
    def validate_failure_on_failed_runs(cls, v: Optional[AgentFailureCreate], info) -> Optional[AgentFailureCreate]:
        """
        Ensure failed runs have a failure object.

        Phase-1 requires explicit failure classification.
        """
        if "status" in info.data:
            status = info.data["status"]
            if status == "failure" and v is None:
                raise ValueError(
                    "Runs with status='failure' must include a failure object "
                    "for semantic classification (Phase-1 requirement)"
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
    metadata: Dict[str, Any] = Field(validation_alias="step_metadata", serialization_alias="metadata")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AgentFailureResponse(BaseModel):
    """Schema for returning failure data (query API)"""

    failure_id: UUID
    run_id: UUID
    step_id: Optional[UUID]
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
    ended_at: Optional[datetime]
    created_at: datetime

    steps: List[AgentStepResponse] = []
    failures: List[AgentFailureResponse] = []

    # Phase 2: Optional decision and quality signal data
    decisions: List["AgentDecisionResponse"] = []
    quality_signals: List["AgentQualitySignalResponse"] = []

    class Config:
        from_attributes = True


# ============================================================================
# Phase 2 Pydantic Models (ADDITIVE ONLY - NO PHASE 1 CHANGES)
# ============================================================================

class AgentDecisionResponse(BaseModel):
    """Schema for returning decision data (query API)"""

    decision_id: UUID
    run_id: UUID
    step_id: Optional[UUID]
    decision_type: str
    selected: str
    reason_code: str
    confidence: Optional[float]
    metadata: Dict[str, Any] = Field(validation_alias="decision_metadata", serialization_alias="metadata")
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AgentQualitySignalResponse(BaseModel):
    """Schema for returning quality signal data (query API)"""

    signal_id: UUID
    run_id: UUID
    step_id: Optional[UUID]
    signal_type: str
    signal_code: str
    value: bool
    weight: Optional[float]
    metadata: Dict[str, Any] = Field(validation_alias="signal_metadata", serialization_alias="metadata")
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
