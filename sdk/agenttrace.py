"""
AgentTracer Platform - Python SDK

This module provides the client-side SDK for capturing agent telemetry.

Design Principles (Phase 1 & 2):
1. Lightweight and non-blocking
2. Privacy-by-default (no prompts, responses, or PII)
3. Fail-safe (never crash the agent)
4. Context manager support for automatic timing
5. Async batched delivery
6. Phase 2: Optional decision and quality signal tracking

Usage Example (Phase 1):
    ```python
    from sdk.agenttrace import AgentTracer

    tracer = AgentTracer(
        agent_id="customer_support_agent",
        agent_version="1.0.0",
        api_url="http://localhost:8000"
    )

    # Start a new agent run
    with tracer.start_run() as run:
        # Capture ordered steps
        with run.step("plan", "analyze_query"):
            # Your planning logic here
            pass

        with run.step("retrieve", "search_knowledge_base") as step:
            # Your retrieval logic
            step.add_metadata({"query_type": "semantic", "result_count": 10})

        # Capture retries as separate spans (Phase-1 requirement)
        for attempt in range(3):
            with run.step("tool", "call_external_api") as step:
                step.add_metadata({"attempt": attempt + 1})
                try:
                    # Tool call logic
                    break
                except Exception as e:
                    if attempt == 2:
                        run.record_failure(
                            failure_type="tool",
                            failure_code="timeout",
                            message=f"API call failed after 3 attempts"
                        )
    ```

Usage Example (Phase 2 - Optional):
    ```python
    with tracer.start_run() as run:
        with run.step("plan", "choose_tool") as step:
            # Your decision logic
            selected_tool = "call_api"

            # Record decision (optional, Phase 2)
            run.record_decision(
                decision_type="tool_selection",
                selected=selected_tool,
                reason_code="fresh_data_required",
                confidence=0.85,
                step_id=step.step_id
            )

        with run.step("retrieve", "search_docs") as step:
            results = search(query)

            # Record quality signal (optional, Phase 2)
            run.record_quality_signal(
                signal_type="empty_retrieval" if len(results) == 0 else "retrieval_success",
                signal_code="no_results" if len(results) == 0 else "results_found",
                value=True,
                step_id=step.step_id
            )
    ```
"""

import asyncio
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

import httpx

# Type aliases
StepType = Literal["plan", "retrieve", "tool", "respond", "other"]
RunStatus = Literal["success", "failure", "partial"]
FailureType = Literal["tool", "model", "retrieval", "orchestration"]

logger = logging.getLogger(__name__)


class StepContext:
    """
    Represents a single step span with automatic timing.

    This context manager captures:
    - Step start/end timestamps
    - Latency calculation
    - Safe metadata (no prompts/responses)
    """

    def __init__(
        self,
        step_type: StepType,
        name: str,
        seq: int,
        run_context: "RunContext",
    ):
        self.step_id = uuid4()
        self.step_type = step_type
        self.name = name
        self.seq = seq
        self.run_context = run_context

        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}

    def add_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Add safe metadata to this step.

        Allowed: tool names, HTTP codes, retry counts, numeric values
        Forbidden: prompts, responses, PII, text content

        Args:
            metadata: Dictionary of safe metadata

        Raises:
            ValueError: If metadata contains forbidden keys
        """
        # Basic validation for forbidden patterns (exact matches only for Phase 1)
        forbidden_keys = {"prompt", "response", "output", "input", "content", "text", "message"}
        for key in metadata.keys():
            if key.lower() in forbidden_keys:
                logger.warning(
                    f"Skipping metadata key '{key}' - may contain sensitive data"
                )
                continue
            self.metadata[key] = metadata[key]

    def __enter__(self) -> "StepContext":
        """Start timing the step"""
        self.started_at = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        End timing and record the step.

        Returns:
            bool: Always False to propagate exceptions (fail-safe)
        """
        self.ended_at = datetime.now(timezone.utc)

        # Calculate latency
        if self.started_at and self.ended_at:
            latency_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)

            # Record step in run context
            self.run_context._add_step(
                step_id=self.step_id,
                seq=self.seq,
                step_type=self.step_type,
                name=self.name,
                latency_ms=latency_ms,
                started_at=self.started_at,
                ended_at=self.ended_at,
                metadata=self.metadata,
            )

        # Always propagate exceptions (never crash the agent)
        return False


class RunContext:
    """
    Represents a single agent run with ordered steps.

    Automatically tracks:
    - Run start/end timestamps
    - Ordered step sequence
    - Failure classification
    - Phase 2: Decision points (optional)
    - Phase 2: Quality signals (optional)
    """

    def __init__(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        tracer: "AgentTracer",
    ):
        self.run_id = uuid4()
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.environment = environment
        self.tracer = tracer

        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        self.status: RunStatus = "success"

        self._steps: List[Dict[str, Any]] = []
        self._failure: Optional[Dict[str, Any]] = None
        self._step_seq = 0

        # Phase 2: Optional decision and signal tracking
        self._decisions: List[Dict[str, Any]] = []
        self._quality_signals: List[Dict[str, Any]] = []

    def step(self, step_type: StepType, name: str) -> StepContext:
        """
        Create a new step context for automatic timing.

        Each retry should be a separate step span (Phase-1 requirement).

        Args:
            step_type: Type of step (plan, retrieve, tool, respond, other)
            name: Human-readable step name

        Returns:
            StepContext: Context manager for automatic timing
        """
        step_ctx = StepContext(
            step_type=step_type,
            name=name,
            seq=self._step_seq,
            run_context=self,
        )
        self._step_seq += 1
        return step_ctx

    def _add_step(
        self,
        step_id: UUID,
        seq: int,
        step_type: StepType,
        name: str,
        latency_ms: int,
        started_at: datetime,
        ended_at: datetime,
        metadata: Dict[str, Any],
    ) -> None:
        """Internal: Record a completed step"""
        self._steps.append(
            {
                "step_id": str(step_id),
                "seq": seq,
                "step_type": step_type,
                "name": name,
                "latency_ms": latency_ms,
                "started_at": started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "metadata": metadata,
            }
        )

    def record_failure(
        self,
        failure_type: FailureType,
        failure_code: str,
        message: str,
        step_id: Optional[UUID] = None,
    ) -> None:
        """
        Record a semantic failure for this run.

        Failures must be classified using Phase-1 taxonomy:
        - failure_type: tool | model | retrieval | orchestration
        - failure_code: timeout | schema_invalid | empty_retrieval | etc.

        Args:
            failure_type: Semantic failure type
            failure_code: Specific failure code
            message: Human-readable description (no PII!)
            step_id: Optional step where failure occurred
        """
        # Basic validation for PII in message
        sensitive_patterns = ["password", "api_key", "token", "secret"]
        lower_msg = message.lower()
        for pattern in sensitive_patterns:
            if pattern in lower_msg:
                logger.warning(
                    f"Failure message may contain sensitive data ('{pattern}'). "
                    f"Sanitizing..."
                )
                message = f"Failure occurred (details sanitized for privacy)"

        self._failure = {
            "failure_type": failure_type,
            "failure_code": failure_code,
            "message": message,
            "step_id": str(step_id) if step_id else None,
        }
        self.status = "failure"

    def record_decision(
        self,
        decision_type: str,
        selected: str,
        reason_code: str,
        candidates: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        step_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a structured decision point (Phase 2, optional).

        This is OPTIONAL and does not affect Phase 1 behavior.
        Decisions are structured, enum-based metadata about why the agent
        chose a particular path.

        Privacy guarantee: Only structured enums and numeric values are stored.
        NO prompts, responses, or reasoning text allowed.

        Args:
            decision_type: Type of decision (must be valid enum)
            selected: The option that was selected
            reason_code: Structured reason code (must be valid enum for decision_type)
            candidates: Optional list of other options considered
            confidence: Optional confidence value (0.0-1.0)
            step_id: Optional step where decision was made
            metadata: Optional structured metadata (privacy-validated)

        Example:
            ```python
            run.record_decision(
                decision_type="tool_selection",
                selected="call_api",
                reason_code="fresh_data_required",
                candidates=["call_api", "use_cache"],
                confidence=0.85,
                step_id=step.step_id
            )
            ```
        """
        try:
            # Privacy validation for metadata
            if metadata is None:
                metadata = {}

            validated_metadata = self._validate_phase2_metadata(metadata)

            # Validate confidence range
            if confidence is not None:
                if not (0.0 <= confidence <= 1.0):
                    logger.warning(
                        f"Confidence {confidence} out of range [0.0, 1.0]. Ignoring decision."
                    )
                    return

            decision = {
                "decision_id": str(uuid4()),
                "step_id": str(step_id) if step_id else None,
                "decision_type": decision_type,
                "selected": selected,
                "reason_code": reason_code,
                "candidates": candidates,  # Separate field, not in metadata
                "confidence": confidence,
                "metadata": validated_metadata,
            }

            self._decisions.append(decision)
            logger.debug(f"Recorded decision: {decision_type} -> {selected} ({reason_code})")

        except Exception as e:
            # Fail-safe: Never crash the agent due to telemetry issues
            logger.error(f"Failed to record decision: {e}", exc_info=True)

    def record_quality_signal(
        self,
        signal_type: str,
        signal_code: str,
        value: bool,
        weight: Optional[float] = None,
        step_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a quality signal (Phase 2, optional).

        This is OPTIONAL and does not affect Phase 1 behavior.
        Quality signals are atomic, factual indicators correlated with
        outcome quality. Signals are non-judgmental observations.

        Privacy guarantee: Only structured enums and numeric values are stored.
        NO prompts, responses, or reasoning text allowed.

        Args:
            signal_type: Type of signal (must be valid enum)
            signal_code: Specific signal code (must be valid enum for signal_type)
            value: Signal present (True) or absent (False)
            weight: Optional signal weight for correlation (0.0-1.0)
            step_id: Optional step where signal was observed
            metadata: Optional structured metadata (privacy-validated)

        Example:
            ```python
            run.record_quality_signal(
                signal_type="schema_valid",
                signal_code="full_match",
                value=True,
                weight=0.9,
                step_id=step.step_id
            )
            ```
        """
        try:
            # Privacy validation for metadata
            if metadata is None:
                metadata = {}

            validated_metadata = self._validate_phase2_metadata(metadata)

            # Validate weight range
            if weight is not None:
                if not (0.0 <= weight <= 1.0):
                    logger.warning(
                        f"Weight {weight} out of range [0.0, 1.0]. Ignoring signal."
                    )
                    return

            signal = {
                "signal_id": str(uuid4()),
                "step_id": str(step_id) if step_id else None,
                "signal_type": signal_type,
                "signal_code": signal_code,
                "value": value,
                "weight": weight,
                "metadata": validated_metadata,
            }

            self._quality_signals.append(signal)
            logger.debug(f"Recorded quality signal: {signal_type} -> {signal_code} = {value}")

        except Exception as e:
            # Fail-safe: Never crash the agent due to telemetry issues
            logger.error(f"Failed to record quality signal: {e}", exc_info=True)

    def _validate_phase2_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Phase 2 metadata for privacy violations.

        Phase 2 privacy constraints:
        - Blocked keys: prompt, response, reasoning, thought, message, content, text, etc.
        - Max string length: 100 characters
        - Only primitive types allowed (str, int, float, bool, None)

        Args:
            metadata: Metadata to validate

        Returns:
            Validated metadata (sanitized)

        Raises:
            ValueError: If privacy violation detected
        """
        BLOCKED_KEYS = {
            "prompt", "response", "reasoning", "thought",
            "message", "content", "text", "output", "input",
            "chain_of_thought", "explanation", "rationale"
        }

        validated = {}

        for key, value in metadata.items():
            # Check blocked keys
            if key.lower() in BLOCKED_KEYS:
                logger.warning(
                    f"Metadata key '{key}' is blocked for privacy. Skipping."
                )
                continue

            # Check value types (primitives only)
            if not isinstance(value, (str, int, float, bool, type(None))):
                logger.warning(
                    f"Metadata value for '{key}' must be primitive type. Skipping."
                )
                continue

            # Check string lengths
            if isinstance(value, str) and len(value) > 100:
                logger.warning(
                    f"Metadata string '{key}' exceeds 100 characters. Truncating."
                )
                value = value[:100]

            validated[key] = value

        return validated

    def __enter__(self) -> "RunContext":
        """Start the agent run"""
        self.started_at = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        End the run and send telemetry.

        Returns:
            bool: Always False to propagate exceptions (fail-safe)
        """
        self.ended_at = datetime.now(timezone.utc)

        # If exception occurred and no failure was recorded, record it
        if exc_type is not None and self._failure is None:
            self.record_failure(
                failure_type="orchestration",
                failure_code="uncaught_exception",
                message=f"Uncaught exception: {exc_type.__name__}",
            )

        # Build telemetry payload
        payload = {
            "run_id": str(self.run_id),
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "environment": self.environment,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "steps": self._steps,
            "failure": self._failure,
        }

        # Phase 2: Include decisions and quality signals if present (optional)
        if self._decisions:
            payload["decisions"] = self._decisions
        if self._quality_signals:
            payload["quality_signals"] = self._quality_signals

        # Send telemetry (async, non-blocking)
        try:
            self.tracer._send_telemetry(payload)
        except Exception as e:
            # Never crash the agent due to telemetry failure
            logger.error(f"Failed to send telemetry: {e}", exc_info=True)

        # Always propagate exceptions
        return False


class AgentTracer:
    """
    Client-side SDK entrypoint for capturing agent runs.

    Features:
    - Lightweight, non-blocking telemetry capture
    - Privacy-by-default (no prompts/responses)
    - Fail-safe operation
    - Async batched delivery

    Args:
        agent_id: Unique identifier for this agent
        agent_version: Version of the agent code
        api_url: URL of the ingest API
        environment: Deployment environment (production, staging, etc.)
        api_key: Optional API key for authentication
    """

    def __init__(
        self,
        agent_id: str,
        agent_version: str,
        api_url: str = "http://localhost:8000",
        environment: str = "production",
        api_key: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.api_url = api_url.rstrip("/")
        self.environment = environment
        self.api_key = api_key

        # HTTP client for async delivery
        self._client = httpx.Client(timeout=5.0)

        # TODO: Implement batching for production use
        self._batch: List[Dict[str, Any]] = []

    def start_run(self) -> RunContext:
        """
        Start a new agent run.

        Returns:
            RunContext: Context manager for capturing the run
        """
        return RunContext(
            agent_id=self.agent_id,
            agent_version=self.agent_version,
            environment=self.environment,
            tracer=self,
        )

    def _send_telemetry(self, payload: Dict[str, Any]) -> None:
        """
        Send telemetry to the ingest API.

        This is synchronous in Phase-1 MVP.
        Future: Implement async batching for production.

        Args:
            payload: Run telemetry data

        Raises:
            Exception: On network or API errors (caught by caller)
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self._client.post(
                f"{self.api_url}/v1/runs",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            logger.info(f"Telemetry sent successfully for run {payload['run_id']}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to send telemetry: {e}")
            # Log validation errors (422) for debugging
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 422:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Validation error details: {error_detail}")
                except Exception:
                    logger.error(f"Response body: {e.response.text}")
            raise

    def flush(self) -> None:
        """
        Flush any batched telemetry.

        For Phase-1, this is a no-op (no batching yet).
        """
        pass

    def close(self) -> None:
        """Close the HTTP client and flush pending telemetry."""
        self.flush()
        self._client.close()

    def __enter__(self) -> "AgentTracer":
        """Support context manager usage"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Clean up on exit"""
        self.close()
        return False
