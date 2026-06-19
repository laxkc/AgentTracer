"""
Unit Tests: Behavior Profile Builder

Tests profile building, distribution calculations, and statistical aggregations.
Uses mocks to avoid database dependencies.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from server.core.behavior_profiles import (
    BehaviorProfileBuilder,
    InsufficientDataError,
)


class TestProfileBuilding:
    """Test profile building with sufficient data."""

    @patch.object(BehaviorProfileBuilder, "_count_runs")
    @patch.object(BehaviorProfileBuilder, "_compute_decision_distributions")
    @patch.object(BehaviorProfileBuilder, "_compute_signal_distributions")
    @patch.object(BehaviorProfileBuilder, "_compute_latency_stats")
    def test_build_profile_success(self, mock_latency, mock_signals, mock_decisions, mock_count):
        """Test successful profile building with sufficient data."""
        # Mock data
        mock_count.return_value = 150
        mock_decisions.return_value = {
            "tool_selection": {"api": 0.65, "cache": 0.30, "database": 0.05}
        }
        mock_signals.return_value = {
            "schema_valid": {"full_match": 0.92, "partial_match": 0.06, "no_match": 0.02}
        }
        mock_latency.return_value = {
            "mean_run_duration_ms": 1234.5,
            "p50_run_duration_ms": 1100.0,
            "p95_run_duration_ms": 2300.0,
            "p99_run_duration_ms": 3100.0,
            "sample_count": 150,
        }

        db = Mock()
        builder = BehaviorProfileBuilder(db)

        profile = builder.build_profile(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            window_start=datetime.now(),
            window_end=datetime.now() + timedelta(days=7),
            min_sample_size=100,
        )

        assert profile["sample_size"] == 150
        assert "tool_selection" in profile["decision_distributions"]
        assert "schema_valid" in profile["signal_distributions"]
        assert profile["latency_stats"]["mean_run_duration_ms"] == 1234.5

    @patch.object(BehaviorProfileBuilder, "_count_runs")
    def test_build_profile_insufficient_data(self, mock_count):
        """Test that InsufficientDataError is raised when sample size is too small."""
        mock_count.return_value = 50  # Below minimum

        db = Mock()
        builder = BehaviorProfileBuilder(db)

        with pytest.raises(InsufficientDataError, match="50 runs found, minimum 100 required"):
            builder.build_profile(
                agent_id="test_agent",
                agent_version="1.0.0",
                environment="production",
                window_start=datetime.now(),
                window_end=datetime.now() + timedelta(days=7),
                min_sample_size=100,
            )


class TestDistributionNormalization:
    """Test distribution normalization logic."""

    def test_normalize_distributions(self):
        """Test that distributions are normalized to sum to 1.0."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        distributions = {"tool_selection": {"api": 65, "cache": 30, "database": 5}}
        type_totals = {"tool_selection": 100}

        normalized = builder._normalize_distributions(distributions, type_totals)

        assert normalized["tool_selection"]["api"] == 0.65
        assert normalized["tool_selection"]["cache"] == 0.30
        assert normalized["tool_selection"]["database"] == 0.05

        # Sum should be 1.0
        total = sum(normalized["tool_selection"].values())
        assert abs(total - 1.0) < 0.01

    def test_normalize_empty_distribution(self):
        """Test normalization with zero total."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        distributions = {"empty_type": {}}
        type_totals = {"empty_type": 0}

        normalized = builder._normalize_distributions(distributions, type_totals)

        assert normalized["empty_type"] == {}


class TestLatencyStatistics:
    """Test latency statistics calculations."""

    def test_calculate_percentiles(self):
        """Test percentile calculations."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        durations = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

        stats = builder._calculate_percentiles(durations)

        assert stats["mean_run_duration_ms"] == 550.0
        assert stats["p50_run_duration_ms"] == 500
        assert stats["p95_run_duration_ms"] == 900
        assert stats["p99_run_duration_ms"] == 900
        assert stats["sample_count"] == 10

    def test_calculate_percentiles_single_value(self):
        """Test percentiles with single data point."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        durations = [500.0]

        stats = builder._calculate_percentiles(durations)

        assert stats["mean_run_duration_ms"] == 500.0
        assert stats["p50_run_duration_ms"] == 500.0
        assert stats["p95_run_duration_ms"] == 500.0
        assert stats["p99_run_duration_ms"] == 500.0
        assert stats["sample_count"] == 1

    def test_percentile_monotonicity(self):
        """Test that percentiles are monotonically increasing."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        durations = list(range(1, 1001))  # 1 to 1000

        stats = builder._calculate_percentiles(durations)

        assert stats["p50_run_duration_ms"] <= stats["p95_run_duration_ms"]
        assert stats["p95_run_duration_ms"] <= stats["p99_run_duration_ms"]


class TestDecisionDistributions:
    """Test decision distribution calculations."""

    def test_compute_decision_distributions(self):
        """Test computing decision distributions from query results."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        # Mock query results: (decision_type, selected, count)
        mock_results = [
            ("tool_selection", "api", 65),
            ("tool_selection", "cache", 30),
            ("tool_selection", "database", 5),
            ("retry_strategy", "retry", 15),
            ("retry_strategy", "no_retry", 85),
        ]

        builder._query_decision_counts = Mock(return_value=mock_results)

        distributions = builder._compute_decision_distributions(
            "test_agent", "1.0.0", "production", datetime.now(), datetime.now()
        )

        # Check tool_selection distribution
        assert "tool_selection" in distributions
        assert abs(distributions["tool_selection"]["api"] - 0.65) < 0.01
        assert abs(distributions["tool_selection"]["cache"] - 0.30) < 0.01

        # Check retry_strategy distribution
        assert "retry_strategy" in distributions
        assert abs(distributions["retry_strategy"]["retry"] - 0.15) < 0.01
        assert abs(distributions["retry_strategy"]["no_retry"] - 0.85) < 0.01


class TestSignalDistributions:
    """Test quality signal distribution calculations."""

    def test_compute_signal_distributions(self):
        """Test computing signal distributions from query results."""
        db = Mock()
        builder = BehaviorProfileBuilder(db)

        # Mock query results: (signal_type, signal_code, count)
        mock_results = [
            ("schema_valid", "full_match", 92),
            ("schema_valid", "partial_match", 6),
            ("schema_valid", "no_match", 2),
        ]

        builder._query_signal_counts = Mock(return_value=mock_results)

        distributions = builder._compute_signal_distributions(
            "test_agent", "1.0.0", "production", datetime.now(), datetime.now()
        )

        assert "schema_valid" in distributions
        assert abs(distributions["schema_valid"]["full_match"] - 0.92) < 0.01
        assert abs(distributions["schema_valid"]["partial_match"] - 0.06) < 0.01
        assert abs(distributions["schema_valid"]["no_match"] - 0.02) < 0.01

        # Should sum to 1.0
        total = sum(distributions["schema_valid"].values())
        assert abs(total - 1.0) < 0.01
