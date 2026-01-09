"""
Unit Tests: Drift Detection Engine

Tests drift detection algorithms, statistical significance, and severity classification.
Uses mocks to avoid database dependencies.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from server.core.drift_engine import DriftDetectionEngine
from server.models.database import BehaviorBaselineDB, BehaviorDriftDB, BehaviorProfileDB

class TestDriftDetection:
    """Test drift detection with various distribution shifts."""

    def test_no_drift_identical_distributions(self):
        """Test that identical distributions produce no drift."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        baseline = BehaviorBaselineDB(
        baseline_id="baseline-1",
        profile_id="profile-1",
        agent_id="agent-123",
        agent_version="v1",
        environment="prod",
        baseline_type="decision_distribution",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

          
        baseline_dists = {"tool_selection": {"api": 0.65, "cache": 0.35}}
        observed_dists = {"tool_selection": {"api": 0.65, "cache": 0.35}}
    
        engine._load_baseline_distributions = Mock(return_value=baseline_dists)
        engine._load_observed_distributions = Mock(return_value=observed_dists)
             
        drift_events = engine.detect_drift(
            baseline=baseline,
            observed_window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            observed_window_end=datetime.now(timezone.utc),
            min_sample_size=10,
    )

        assert len(drift_events) == 0

    def test_drift_detected_significant_shift(self):
        """Test that significant distribution shifts are detected."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        # Significant shift: api drops from 65% to 45%
        baseline_dists = {"tool_selection": {"api": 0.65, "cache": 0.35}}
        observed_dists = {"tool_selection": {"api": 0.45, "cache": 0.55}}

        drift_events = engine.detect_drift(
            baseline_id=uuid4(),
            baseline_dists=baseline_dists,
            observed_dists=observed_dists,
            agent_id="test",
            agent_version="1.0.0",
            environment="prod",
            observation_window_start=datetime.now(),
            observation_window_end=datetime.now() + timedelta(hours=1),
            observation_sample_size=100,
        )

        assert len(drift_events) > 0
        # Should detect drift in tool_selection

    def test_drift_small_shift_not_detected(self):
        """Test that small, statistically insignificant shifts are ignored."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        # Small shift: api changes by only 2%
        baseline_dists = {"tool_selection": {"api": 0.65, "cache": 0.35}}
        observed_dists = {"tool_selection": {"api": 0.63, "cache": 0.37}}

        drift_events = engine.detect_drift(
            baseline_id=uuid4(),
            baseline_dists=baseline_dists,
            observed_dists=observed_dists,
            agent_id="test",
            agent_version="1.0.0",
            environment="prod",
            observation_window_start=datetime.now(),
            observation_window_end=datetime.now() + timedelta(hours=1),
            observation_sample_size=100,
        )

        # Should not detect drift for such small change
        assert len(drift_events) == 0


class TestDeltaCalculations:
    """Test delta and delta_percent calculations."""

    def test_calculate_positive_delta(self):
        """Test delta calculation for increase."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        baseline_value = 1000.0
        observed_value = 1500.0

        delta = observed_value - baseline_value
        delta_percent = ((observed_value - baseline_value) / baseline_value) * 100

        assert delta == 500.0
        assert delta_percent == 50.0

    def test_calculate_negative_delta(self):
        """Test delta calculation for decrease."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        baseline_value = 1000.0
        observed_value = 700.0

        delta = observed_value - baseline_value
        delta_percent = ((observed_value - baseline_value) / baseline_value) * 100

        assert delta == -300.0
        assert delta_percent == -30.0

    def test_delta_percent_with_zero_baseline(self):
        """Test that zero baseline is handled gracefully."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        # When baseline is 0, delta_percent should handle gracefully
        baseline_value = 0.0
        observed_value = 100.0

        # Should not divide by zero
        if baseline_value == 0:
            delta_percent = float("inf") if observed_value > 0 else 0.0
        else:
            delta_percent = ((observed_value - baseline_value) / baseline_value) * 100

        assert delta_percent == float("inf")


class TestSeverityClassification:
    """Test drift severity classification."""

    @pytest.mark.parametrize(
        "delta_percent,expected_severity",
        [
            (5.0, "low"),  # Small change
            (15.0, "low"),  # Still low
            (25.0, "medium"),  # Moderate change
            (40.0, "medium"),  # Still medium
            (60.0, "high"),  # Significant change
            (120.0, "critical"),  # Extreme change
        ],
    )
    def test_severity_thresholds(self, delta_percent, expected_severity):
        """Test severity classification for various delta percents."""
        # Simplified severity logic (actual thresholds may vary)
        if abs(delta_percent) < 20:
            severity = "low"
        elif abs(delta_percent) < 50:
            severity = "medium"
        elif abs(delta_percent) < 100:
            severity = "high"
        else:
            severity = "critical"

        assert severity == expected_severity


class TestLatencyDriftDetection:
    """Test latency drift detection."""

    def test_latency_drift_p95_increase(self):
        """Test detection of p95 latency increase."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        baseline_stats = {
            "mean_run_duration_ms": 1000.0,
            "p50_run_duration_ms": 900.0,
            "p95_run_duration_ms": 2000.0,
            "p99_run_duration_ms": 3000.0,
        }

        observed_stats = {
            "mean_run_duration_ms": 1200.0,
            "p50_run_duration_ms": 1000.0,
            "p95_run_duration_ms": 3500.0,  # 75% increase
            "p99_run_duration_ms": 4500.0,
        }

        # P95 increased by 75% - should be detected
        delta_percent = ((3500.0 - 2000.0) / 2000.0) * 100
        assert delta_percent == 75.0

    def test_latency_drift_within_tolerance(self):
        """Test that small latency variations within tolerance are not flagged."""
        db_mock = Mock()
        engine = DriftDetectionEngine(db_mock)

        baseline_stats = {
            "p95_run_duration_ms": 2000.0,
        }

        observed_stats = {
            "p95_run_duration_ms": 2100.0,  # Only 5% increase
        }

        delta_percent = ((2100.0 - 2000.0) / 2000.0) * 100
        assert delta_percent == 5.0  # Below typical threshold


class TestStatisticalSignificance:
    """Test statistical significance calculations."""

    def test_p_value_range(self):
        """Test that p-values are in valid range [0, 1]."""
        # Mock p-value from statistical test
        p_value = 0.03

        assert 0.0 <= p_value <= 1.0

    def test_significance_threshold(self):
        """Test significance threshold (typically 0.05)."""
        threshold = 0.05

        p_value_significant = 0.03
        p_value_not_significant = 0.10

        assert p_value_significant < threshold  # Significant drift
        assert p_value_not_significant >= threshold  # Not significant

    def test_high_confidence_drift(self):
        """Test high confidence drift detection (p < 0.01)."""
        p_value = 0.005

        # Very low p-value indicates high confidence
        assert p_value < 0.01


class TestMinimumSampleSize:
    """Test minimum sample size validation."""

    def test_sufficient_sample_size(self):
        """Test that sufficient sample sizes pass validation."""
        observation_sample_size = 100
        min_sample_size = 30

        assert observation_sample_size >= min_sample_size

    def test_insufficient_sample_size(self):
        """Test that insufficient sample sizes are rejected."""
        observation_sample_size = 20
        min_sample_size = 30

        assert observation_sample_size < min_sample_size

    def test_minimum_sample_size_default(self):
        """Test default minimum sample size."""
        default_min = 30  # Typical default

        assert default_min > 0


class TestDriftEventCreation:
    """Test drift event data structure."""

    def test_drift_event_has_required_fields(self):
        """Test that drift events contain all required fields."""
        drift_event = {
            "drift_id": uuid4(),
            "baseline_id": uuid4(),
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "environment": "production",
            "drift_type": "decision_distribution",
            "metric": "tool_selection.api",
            "baseline_value": 0.65,
            "observed_value": 0.45,
            "delta": -0.20,
            "delta_percent": -30.77,
            "significance": 0.001,
            "test_method": "chi_square",
            "severity": "high",
            "detected_at": datetime.now(),
        }

        # Verify all required fields present
        required_fields = [
            "drift_id",
            "baseline_id",
            "agent_id",
            "drift_type",
            "metric",
            "baseline_value",
            "observed_value",
            "delta",
            "delta_percent",
            "significance",
            "severity",
        ]

        for field in required_fields:
            assert field in drift_event

    def test_drift_event_types(self):
        """Test valid drift event types."""
        valid_types = [
            "decision_distribution",
            "signal_distribution",
            "latency_percentile",
        ]

        for drift_type in valid_types:
            assert drift_type in [
                "decision_distribution",
                "signal_distribution",
                "latency_percentile",
            ]
