"""
Behavior Profile Builder

This module builds statistical behavior profiles from decision and quality signal data.
It aggregates agent_decisions and agent_quality_signals over time windows
to create behavioral snapshots for baseline creation and drift detection.

Constraints:
- Read-only with respect to core tracking tables
- No access to prompts, responses, or reasoning
- Purely observational - no behavior modification
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from server.models import (
    AgentDecisionDB,
    AgentQualitySignalDB,
    AgentRunDB,
)


class InsufficientDataError(Exception):
    """Raised when insufficient data exists to build a valid profile."""
    pass


class BehaviorProfile:
    """
    Statistical snapshot of agent behavior over a time window.
    Built from decision and quality signal data.
    """

    def __init__(
        self,
        profile_id: UUID,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
        sample_size: int,
        decision_distributions: Dict,
        signal_distributions: Dict,
        latency_stats: Dict,
        created_at: datetime,
    ):
        self.profile_id = profile_id
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.environment = environment
        self.window_start = window_start
        self.window_end = window_end
        self.sample_size = sample_size
        self.decision_distributions = decision_distributions
        self.signal_distributions = signal_distributions
        self.latency_stats = latency_stats
        self.created_at = created_at


class BehaviorProfileBuilder:
    """
    Builds statistical behavior profiles from decision and quality signal data.

    Purpose:
    - Aggregate decision distributions from agent_decisions
    - Aggregate quality signal distributions from agent_quality_signals
    - Compute latency statistics from agent_runs
    - Create baseline-ready behavioral snapshots

    This component is read-only and observational only.
    """

    def __init__(self, db: Session):
        """
        Initialize profile builder.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def build_profile(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
        min_sample_size: int = 100,
    ) -> Dict:
        """
        Build a behavior profile from decision and quality signal data.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            window_start: Start of aggregation window
            window_end: End of aggregation window
            min_sample_size: Minimum number of runs required (default: 100)

        Returns:
            Dict containing profile data ready for database insertion

        Raises:
            InsufficientDataError: If sample_size < min_sample_size
        """
        # Count runs in window
        sample_size = self._count_runs(
            agent_id, agent_version, environment, window_start, window_end
        )

        # Validate sufficient data
        self._validate_sample_size(sample_size, min_sample_size)

        # Compute distributions and statistics
        decision_distributions = self._compute_decision_distributions(
            agent_id, agent_version, environment, window_start, window_end
        )

        signal_distributions = self._compute_signal_distributions(
            agent_id, agent_version, environment, window_start, window_end
        )

        latency_stats = self._compute_latency_stats(
            agent_id, agent_version, environment, window_start, window_end
        )

        return {
            "agent_id": agent_id,
            "agent_version": agent_version,
            "environment": environment,
            "window_start": window_start,
            "window_end": window_end,
            "sample_size": sample_size,
            "decision_distributions": decision_distributions,
            "signal_distributions": signal_distributions,
            "latency_stats": latency_stats,
        }

    def _count_runs(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        """
        Count runs in the time window.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            window_start: Start of window
            window_end: End of window

        Returns:
            Number of runs in window
        """
        count = (
            self.db.query(func.count(AgentRunDB.run_id))
            .filter(
                and_(
                    AgentRunDB.agent_id == agent_id,
                    AgentRunDB.agent_version == agent_version,
                    AgentRunDB.environment == environment,
                    AgentRunDB.started_at >= window_start,
                    AgentRunDB.started_at < window_end,
                )
            )
            .scalar()
        )

        return count or 0

    def _query_decision_counts(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List:
        """
        Query decision type and selected combinations with counts.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            window_start: Start of window
            window_end: End of window

        Returns:
            List of (decision_type, selected, count) tuples
        """
        return (
            self.db.query(
                AgentDecisionDB.decision_type,
                AgentDecisionDB.selected,
                func.count(AgentDecisionDB.decision_id).label("count"),
            )
            .join(AgentRunDB, AgentDecisionDB.run_id == AgentRunDB.run_id)
            .filter(
                and_(
                    AgentRunDB.agent_id == agent_id,
                    AgentRunDB.agent_version == agent_version,
                    AgentRunDB.environment == environment,
                    AgentRunDB.started_at >= window_start,
                    AgentRunDB.started_at < window_end,
                )
            )
            .group_by(AgentDecisionDB.decision_type, AgentDecisionDB.selected)
            .all()
        )

    def _normalize_distributions(self, distributions: Dict, type_totals: Dict) -> Dict:
        """
        Normalize count distributions to probabilities (sum to 1.0).

        Args:
            distributions: Dict of {type: {selection: count}}
            type_totals: Dict of {type: total_count}

        Returns:
            Normalized distributions {type: {selection: probability}}
        """
        normalized = {}
        for decision_type, selections in distributions.items():
            total = type_totals[decision_type]
            if total > 0:
                normalized[decision_type] = {
                    selected: count / total for selected, count in selections.items()
                }
            else:
                normalized[decision_type] = selections

        return normalized

    def _compute_decision_distributions(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict:
        """
        Aggregate decision distributions from agent_decisions table.

        Example query:
        SELECT decision_type, selected, COUNT(*)
        FROM agent_decisions d
        JOIN agent_runs r ON d.run_id = r.run_id
        WHERE r.agent_id = ? AND ...
        GROUP BY decision_type, selected

        Returns:
            Normalized distributions:
            {
              "tool_selection": {"api": 0.65, "cache": 0.30, "database": 0.05},
              "retry_strategy": {"retry": 0.15, "no_retry": 0.85}
            }
        """
        # Query decision counts
        results = self._query_decision_counts(
            agent_id, agent_version, environment, window_start, window_end
        )

        # Build distributions
        distributions = {}
        type_totals = {}

        for decision_type, selected, count in results:
            if decision_type not in distributions:
                distributions[decision_type] = {}
                type_totals[decision_type] = 0

            distributions[decision_type][selected] = count
            type_totals[decision_type] += count

        # Normalize to probabilities
        return self._normalize_distributions(distributions, type_totals)

    def _query_signal_counts(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List:
        """
        Query signal type and code combinations with counts.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            window_start: Start of window
            window_end: End of window

        Returns:
            List of (signal_type, signal_code, count) tuples
        """
        return (
            self.db.query(
                AgentQualitySignalDB.signal_type,
                AgentQualitySignalDB.signal_code,
                func.count(AgentQualitySignalDB.signal_id).label("count"),
            )
            .join(AgentRunDB, AgentQualitySignalDB.run_id == AgentRunDB.run_id)
            .filter(
                and_(
                    AgentRunDB.agent_id == agent_id,
                    AgentRunDB.agent_version == agent_version,
                    AgentRunDB.environment == environment,
                    AgentRunDB.started_at >= window_start,
                    AgentRunDB.started_at < window_end,
                )
            )
            .group_by(AgentQualitySignalDB.signal_type, AgentQualitySignalDB.signal_code)
            .all()
        )

    def _compute_signal_distributions(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict:
        """
        Aggregate quality signal distributions from agent_quality_signals table.

        Returns:
            Normalized distributions:
            {
              "schema_valid": {"full_match": 0.92, "partial_match": 0.06, "no_match": 0.02},
              "tool_success": {"first_attempt": 0.88, "after_retry": 0.10, "failed": 0.02}
            }
        """
        # Query signal counts
        results = self._query_signal_counts(
            agent_id, agent_version, environment, window_start, window_end
        )

        # Build distributions
        distributions = {}
        type_totals = {}

        for signal_type, signal_code, count in results:
            if signal_type not in distributions:
                distributions[signal_type] = {}
                type_totals[signal_type] = 0

            distributions[signal_type][signal_code] = count
            type_totals[signal_type] += count

        # Normalize to probabilities
        return self._normalize_distributions(distributions, type_totals)

    def _query_run_durations(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[float]:
        """
        Query all run durations in time window.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            window_start: Start of window
            window_end: End of window

        Returns:
            List of durations in milliseconds
        """
        runs = (
            self.db.query(
                func.extract("epoch", AgentRunDB.ended_at - AgentRunDB.started_at).label(
                    "duration_seconds"
                )
            )
            .filter(
                and_(
                    AgentRunDB.agent_id == agent_id,
                    AgentRunDB.agent_version == agent_version,
                    AgentRunDB.environment == environment,
                    AgentRunDB.started_at >= window_start,
                    AgentRunDB.started_at < window_end,
                    AgentRunDB.ended_at.isnot(None),  # Only completed runs
                )
            )
            .all()
        )

        # Extract durations in milliseconds (convert Decimal to float)
        return [float(d.duration_seconds) * 1000 for d in runs if d.duration_seconds]

    def _calculate_percentiles(self, sorted_durations: List[float]) -> Dict:
        """
        Calculate percentile statistics from sorted durations.

        Args:
            sorted_durations: List of durations sorted in ascending order

        Returns:
            Dict of percentile statistics
        """
        n = len(sorted_durations)
        mean = sum(sorted_durations) / n
        p50 = sorted_durations[int(n * 0.50)]
        p95 = sorted_durations[int(n * 0.95)] if n > 1 else sorted_durations[0]
        p99 = sorted_durations[int(n * 0.99)] if n > 1 else sorted_durations[0]

        return {
            "mean_run_duration_ms": round(mean, 2),
            "p50_run_duration_ms": round(p50, 2),
            "p95_run_duration_ms": round(p95, 2),
            "p99_run_duration_ms": round(p99, 2),
            "sample_count": n,
        }

    def _compute_latency_stats(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict:
        """
        Compute latency statistics from agent_runs table.

        Returns:
            Statistical summary:
            {
              "mean_run_duration_ms": 1234.5,
              "p50_run_duration_ms": 1100.0,
              "p95_run_duration_ms": 2300.0,
              "p99_run_duration_ms": 3100.0
            }
        """
        # Query run durations
        durations_ms = self._query_run_durations(
            agent_id, agent_version, environment, window_start, window_end
        )

        if not durations_ms:
            return {
                "mean_run_duration_ms": 0.0,
                "p50_run_duration_ms": 0.0,
                "p95_run_duration_ms": 0.0,
                "p99_run_duration_ms": 0.0,
                "sample_count": 0,
            }

        # Sort for percentile calculation
        durations_ms.sort()

        # Calculate statistics
        return self._calculate_percentiles(durations_ms)

    def _validate_sample_size(self, count: int, min_size: int) -> None:
        """
        Validate that sufficient data exists.

        Args:
            count: Actual sample size
            min_size: Minimum required sample size

        Raises:
            InsufficientDataError: If count < min_size
        """
        if count < min_size:
            raise InsufficientDataError(
                f"Insufficient data: {count} runs found, minimum {min_size} required"
            )


def create_behavior_profile(
    db: Session,
    agent_id: str,
    agent_version: str,
    environment: str,
    window_start: datetime,
    window_end: datetime,
    min_sample_size: int = 100,
) -> Dict:
    """
    Convenience function to build and return a behavior profile.

    Args:
        db: Database session
        agent_id: Agent identifier
        agent_version: Agent version
        environment: Deployment environment
        window_start: Start of aggregation window
        window_end: End of aggregation window
        min_sample_size: Minimum runs required (default: 100)

    Returns:
        Dict containing profile data

    Raises:
        InsufficientDataError: If not enough data exists
    """
    builder = BehaviorProfileBuilder(db)
    return builder.build_profile(
        agent_id=agent_id,
        agent_version=agent_version,
        environment=environment,
        window_start=window_start,
        window_end=window_end,
        min_sample_size=min_sample_size,
    )
