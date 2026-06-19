"""
Integration Test: Drift Detection Workflow

Tests: Profile → Baseline → Drift Detection pipeline

Prerequisites:
- PostgreSQL running
- Database schema applied
- Sufficient test data (100+ runs)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from server.core.baselines import BaselineManager
from server.core.behavior_profiles import BehaviorProfileBuilder
from server.core.drift_engine import DriftDetectionEngine
from server.models.database import (
    AgentDecisionDB,
    AgentQualitySignalDB,
    AgentRunDB,
    BehaviorProfileDB,
)


@pytest.mark.integration
class TestProfileCreation:
    """Test behavior profile creation from runs."""

    def test_create_profile_with_sufficient_data(self, db_session):
        """Test creating profile with 100+ runs."""
        agent_id = "profile_test_agent"
        agent_version = "1.0.0"
        environment = "test"

        # Create 100 runs with decisions
        window_start = datetime.now(timezone.utc) - timedelta(days=7)
        window_end = datetime.now(timezone.utc)

        for i in range(100):
            run_id = uuid4()
            run = AgentRunDB(
                run_id=run_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                status="success",
                started_at=window_start + timedelta(hours=i),
                ended_at=window_start + timedelta(hours=i, minutes=5),
            )
            db_session.add(run)
            db_session.flush()

            # Add decision
            decision = AgentDecisionDB(
                run_id=run_id,
                decision_type="tool_selection",
                selected="api" if i < 65 else "cache",
                reason_code="fresh_data_required" if i < 65 else "cached_data_sufficient",
            )
            db_session.add(decision)

        db_session.commit()

        # Build profile
        builder = BehaviorProfileBuilder(db_session)
        profile = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=window_start,
            window_end=window_end,
            min_sample_size=100,
        )

        assert profile["sample_size"] == 100
        assert "tool_selection" in profile["decision_distributions"]


@pytest.mark.integration
class TestBaselineCreation:
    """Test baseline creation from profiles."""

    def test_create_baseline_from_profile(self, db_session):
        """Test creating baseline from profile."""
        profile_id = uuid4()
        agent_id = "baseline_test_agent"
        agent_version = "1.0.0"
        environment = "test"

        window_start = datetime.now(timezone.utc) - timedelta(hours=1)
        window_end = datetime.now(timezone.utc)
        profile = BehaviorProfileDB(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=window_start,
            window_end=window_end,
            sample_size=1,
            decision_distributions={},
            signal_distributions={},
            latency_stats={},
        )
        db_session.add(profile)
        db_session.commit()

        manager = BaselineManager(db_session)

        baseline = manager.create_baseline(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type="version",
            description="Test baseline",
        )

        assert baseline.profile_id == profile_id
        assert baseline.agent_id == agent_id
        assert baseline.is_active is False  # Created inactive

    def test_activate_baseline(self, db_session):
        """Test activating a baseline."""
        profile_id = uuid4()
        agent_id = "activate_test_agent"
        agent_version = "1.0.0"
        environment = "test"

        window_start = datetime.now(timezone.utc) - timedelta(hours=1)
        window_end = datetime.now(timezone.utc)
        profile = BehaviorProfileDB(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=window_start,
            window_end=window_end,
            sample_size=1,
            decision_distributions={},
            signal_distributions={},
            latency_stats={},
        )
        db_session.add(profile)
        db_session.commit()

        manager = BaselineManager(db_session)

        baseline = manager.create_baseline(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type="version",
        )

        # Activate
        activated = manager.activate_baseline(baseline.baseline_id)

        assert activated.is_active is True


@pytest.mark.integration
class TestDriftDetection:
    """Test drift detection against baselines."""

    def test_detect_drift_with_distribution_shift(self, db_session):
        """Test detecting drift when distributions shift."""
        agent_id = "drift_test_agent"
        agent_version = "1.0.0"
        environment = "test"

        # Create baseline period (100 runs, 65% api, 35% cache)
        baseline_start = datetime.now(timezone.utc) - timedelta(days=14)
        baseline_end = datetime.now(timezone.utc) - timedelta(days=7)

        for i in range(100):
            run_id = uuid4()
            run = AgentRunDB(
                run_id=run_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                status="success",
                started_at=baseline_start + timedelta(hours=i),
                ended_at=baseline_start + timedelta(hours=i, minutes=5),
            )
            db_session.add(run)
            db_session.flush()

            decision = AgentDecisionDB(
                run_id=run_id,
                decision_type="tool_selection",
                selected="api" if i < 65 else "cache",
                reason_code="fresh_data_required" if i < 65 else "cached_data_sufficient",
            )
            db_session.add(decision)

        db_session.commit()

        # Build baseline profile
        builder = BehaviorProfileBuilder(db_session)
        baseline_profile = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=baseline_start,
            window_end=baseline_end,
            min_sample_size=100,
        )

        # Create and activate baseline
        manager = BaselineManager(db_session)
        profile_id = uuid4()
        db_session.add(
            BehaviorProfileDB(
                profile_id=profile_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                window_start=baseline_start,
                window_end=baseline_end,
                sample_size=baseline_profile["sample_size"],
                decision_distributions=baseline_profile["decision_distributions"],
                signal_distributions=baseline_profile["signal_distributions"],
                latency_stats=baseline_profile["latency_stats"],
            )
        )
        db_session.commit()
        baseline = manager.create_baseline(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type="time_window",
        )
        manager.activate_baseline(baseline.baseline_id)

        # Create observation period with shift (45% api, 55% cache)
        observation_start = datetime.now(timezone.utc) - timedelta(hours=50)
        observation_end = datetime.now(timezone.utc)

        for i in range(50):
            run_id = uuid4()
            run = AgentRunDB(
                run_id=run_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                status="success",
                started_at=observation_start + timedelta(hours=i),
                ended_at=observation_start + timedelta(hours=i, minutes=5),
            )
            db_session.add(run)
            db_session.flush()

            decision = AgentDecisionDB(
                run_id=run_id,
                decision_type="tool_selection",
                selected="api" if i < 23 else "cache",  # 45% api
                reason_code="fresh_data_required" if i < 23 else "cached_data_sufficient",
            )
            db_session.add(decision)

        db_session.commit()

        # Build observation profile
        observation_profile = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=observation_start,
            window_end=observation_end,
            min_sample_size=30,
        )

        # Detect drift
        engine = DriftDetectionEngine(db_session)
        drift_events = engine.detect_drift(
            baseline=baseline,
            observed_window_start=observation_start,
            observed_window_end=observation_end,
            min_sample_size=30,
        )

        # Should detect drift due to 20% shift
        assert len(drift_events) > 0


@pytest.mark.integration
class TestDriftResolution:
    """Test marking drift as resolved."""

    def test_resolve_drift_event(self, db_session):
        """Test resolving a drift event."""
        # This would require creating a drift event first
        # Then marking it as resolved
        # Verify resolved_at is set
        pass


@pytest.mark.integration
class TestEndToEndDriftPipeline:
    """Test complete drift detection pipeline."""

    def test_full_drift_pipeline(self, db_session):
        """Test: Runs → Profile → Baseline → Drift Detection."""
        agent_id = "pipeline_test_agent"
        agent_version = "1.0.0"
        environment = "test"

        # Step 1: Create baseline data
        baseline_start = datetime.now(timezone.utc) - timedelta(days=14)
        baseline_end = datetime.now(timezone.utc) - timedelta(days=7)

        for i in range(100):
            run_id = uuid4()
            run = AgentRunDB(
                run_id=run_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                status="success",
                started_at=baseline_start + timedelta(hours=i),
                ended_at=baseline_start + timedelta(hours=i, minutes=5),
            )
            db_session.add(run)
            db_session.flush()

            signal = AgentQualitySignalDB(
                run_id=run_id,
                signal_type="schema_valid",
                signal_code="full_match" if i < 92 else "partial_match",
                value=True,
            )
            db_session.add(signal)

        db_session.commit()

        # Step 2: Build and activate baseline
        builder = BehaviorProfileBuilder(db_session)
        baseline_profile = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=baseline_start,
            window_end=baseline_end,
            min_sample_size=100,
        )

        manager = BaselineManager(db_session)
        profile_id = uuid4()
        db_session.add(
            BehaviorProfileDB(
                profile_id=profile_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                window_start=baseline_start,
                window_end=baseline_end,
                sample_size=baseline_profile["sample_size"],
                decision_distributions=baseline_profile["decision_distributions"],
                signal_distributions=baseline_profile["signal_distributions"],
                latency_stats=baseline_profile["latency_stats"],
            )
        )
        db_session.commit()
        baseline = manager.create_baseline(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type="time_window",
        )
        manager.activate_baseline(baseline.baseline_id)

        # Step 3: Create observation data (no drift)
        observation_start = datetime.now(timezone.utc) - timedelta(hours=6)
        observation_end = datetime.now(timezone.utc)

        for i in range(50):
            run_id = uuid4()
            run = AgentRunDB(
                run_id=run_id,
                agent_id=agent_id,
                agent_version=agent_version,
                environment=environment,
                status="success",
                started_at=observation_start + timedelta(minutes=i * 7),
                ended_at=observation_start + timedelta(minutes=i * 7 + 5),
            )
            db_session.add(run)
            db_session.flush()

            signal = AgentQualitySignalDB(
                run_id=run_id,
                signal_type="schema_valid",
                signal_code="full_match" if i < 46 else "partial_match",
                value=True,
            )
            db_session.add(signal)

        db_session.commit()

        # Step 4: Detect drift
        observation_profile = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=observation_start,
            window_end=observation_end,
            min_sample_size=30,
        )

        engine = DriftDetectionEngine(db_session)
        drift_events = engine.detect_drift(
            baseline=baseline,
            observed_window_start=observation_start,
            observed_window_end=observation_end,
            min_sample_size=30,
        )

        # Similar distributions should not trigger drift
        assert len(drift_events) == 0
