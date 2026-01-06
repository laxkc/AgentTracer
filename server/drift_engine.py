"""
Drift Detection Engine

This module detects behavioral drift via statistical comparison.
Drift is purely observational - it describes change, not quality.

Constraints:
- Drift is descriptive, not evaluative
- No quality judgments (drift ≠ bad)
- Uses statistical methods (Chi-square, percent thresholds)
- Purely observational - no behavior modification
- Language must be neutral ("observed change", not "degraded")
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import yaml
import os

from sqlalchemy.orm import Session
from scipy import stats

from server.behavior_profiles import BehaviorProfileBuilder, InsufficientDataError
from server.baselines import BehaviorBaselineDB
from server.models import Base


# Database model for behavior_drift
class BehaviorDriftDB(Base):
    """
    SQLAlchemy model for behavior_drift table.
    """
    __tablename__ = "behavior_drift"

    from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    drift_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    baseline_id = Column(PGUUID(as_uuid=True), ForeignKey("behavior_baselines.baseline_id", ondelete="CASCADE"), nullable=False)

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


# Database model for behavior_profiles (minimal definition for querying)
class BehaviorProfileDB(Base):
    """
    SQLAlchemy model for behavior_profiles table.
    """
    __tablename__ = "behavior_profiles"

    from sqlalchemy import Column, DateTime, Integer, String
    from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

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


class DriftDetectionEngine:
    """
    Detects behavioral drift via statistical comparison.

    Purpose:
    - Compare observed behavior against baselines
    - Run statistical tests (Chi-square, percent thresholds)
    - Detect significant drift
    - Persist drift records

    Drift is purely observational - describes change, not quality.
    """

    def __init__(self, db: Session, config_path: Optional[str] = None):
        """
        Initialize drift detection engine.

        Args:
            db: SQLAlchemy database session
            config_path: Path to drift thresholds config file (optional)
        """
        self.db = db
        self.threshold_config = self._load_thresholds(config_path)

    def _build_observed_profile(
        self,
        baseline: BehaviorBaselineDB,
        observed_window_start: datetime,
        observed_window_end: datetime,
        min_sample_size: int,
    ) -> Dict:
        """
        Build profile for observed window.

        Args:
            baseline: Baseline containing agent context
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            min_sample_size: Minimum runs required

        Returns:
            Dict containing observed profile data

        Raises:
            InsufficientDataError: If not enough observed data
        """
        profile_builder = BehaviorProfileBuilder(self.db)
        return profile_builder.build_profile(
            agent_id=baseline.agent_id,
            agent_version=baseline.agent_version,
            environment=baseline.environment,
            window_start=observed_window_start,
            window_end=observed_window_end,
            min_sample_size=min_sample_size,
        )

    def _load_baseline_profile(self, baseline: BehaviorBaselineDB) -> BehaviorProfileDB:
        """
        Load baseline profile from database.

        Args:
            baseline: Baseline containing profile_id

        Returns:
            BehaviorProfileDB object

        Raises:
            ValueError: If profile not found
        """
        baseline_profile = (
            self.db.query(BehaviorProfileDB)
            .filter(BehaviorProfileDB.profile_id == baseline.profile_id)
            .first()
        )

        if not baseline_profile:
            raise ValueError(f"Baseline profile {baseline.profile_id} not found")

        return baseline_profile

    def _collect_all_drifts(
        self,
        baseline: BehaviorBaselineDB,
        baseline_profile: BehaviorProfileDB,
        observed_profile: Dict,
        observed_window_start: datetime,
        observed_window_end: datetime,
    ) -> List[BehaviorDriftDB]:
        """
        Collect drift records across all dimensions.

        Args:
            baseline: Baseline to compare against
            baseline_profile: Baseline profile data
            observed_profile: Observed profile data
            observed_window_start: Start of observation window
            observed_window_end: End of observation window

        Returns:
            List of all detected drift records
        """
        drift_records = []
        observed_sample_size = observed_profile["sample_size"]

        # Compare decision distributions
        decision_drifts = self._compare_decision_distributions(
            baseline=baseline,
            baseline_profile=baseline_profile,
            observed_profile=observed_profile,
            observed_window_start=observed_window_start,
            observed_window_end=observed_window_end,
            observed_sample_size=observed_sample_size,
        )
        drift_records.extend(decision_drifts)

        # Compare signal distributions
        signal_drifts = self._compare_signal_distributions(
            baseline=baseline,
            baseline_profile=baseline_profile,
            observed_profile=observed_profile,
            observed_window_start=observed_window_start,
            observed_window_end=observed_window_end,
            observed_sample_size=observed_sample_size,
        )
        drift_records.extend(signal_drifts)

        # Compare latency stats
        latency_drifts = self._compare_latency_stats(
            baseline=baseline,
            baseline_profile=baseline_profile,
            observed_profile=observed_profile,
            observed_window_start=observed_window_start,
            observed_window_end=observed_window_end,
            observed_sample_size=observed_sample_size,
        )
        drift_records.extend(latency_drifts)

        return drift_records

    def detect_drift(
        self,
        baseline: BehaviorBaselineDB,
        observed_window_start: datetime,
        observed_window_end: datetime,
        min_sample_size: int = 100,
    ) -> List[BehaviorDriftDB]:
        """
        Detect drift by comparing baseline to observed behavior.

        Steps:
        1. Build profile for observed window
        2. Load baseline profile
        3. Compare decision distributions
        4. Compare signal distributions
        5. Compare latency stats
        6. Create drift records for significant changes

        Args:
            baseline: Baseline to compare against
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            min_sample_size: Minimum runs required (default: 100)

        Returns:
            List of BehaviorDriftDB objects (empty if no drift detected)

        Raises:
            InsufficientDataError: If not enough observed data
        """
        # Build observed profile
        observed_profile_data = self._build_observed_profile(
            baseline, observed_window_start, observed_window_end, min_sample_size
        )

        # Load baseline profile
        baseline_profile = self._load_baseline_profile(baseline)

        # Detect drift across all dimensions
        drift_records = self._collect_all_drifts(
            baseline,
            baseline_profile,
            observed_profile_data,
            observed_window_start,
            observed_window_end,
        )

        # Persist drift records
        for drift in drift_records:
            self.db.add(drift)

        self.db.commit()

        return drift_records

    def _create_drift_record(
        self,
        baseline: BehaviorBaselineDB,
        drift_type: str,
        metric: str,
        baseline_value: float,
        observed_value: float,
        delta: float,
        delta_percent: float,
        p_value: float,
        test_method: str,
        severity: str,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> BehaviorDriftDB:
        """
        Create a drift record with all required fields.

        Args:
            baseline: Baseline being compared against
            drift_type: Type of drift (decision, signal, latency)
            metric: Specific metric name
            baseline_value: Baseline metric value
            observed_value: Observed metric value
            delta: Absolute change
            delta_percent: Percent change
            p_value: Statistical significance
            test_method: Statistical test used
            severity: Drift severity (low, medium, high)
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            observed_sample_size: Number of samples observed

        Returns:
            BehaviorDriftDB record
        """
        return BehaviorDriftDB(
            baseline_id=baseline.baseline_id,
            agent_id=baseline.agent_id,
            agent_version=baseline.agent_version,
            environment=baseline.environment,
            drift_type=drift_type,
            metric=metric,
            baseline_value=baseline_value,
            observed_value=observed_value,
            delta=delta,
            delta_percent=delta_percent,
            significance=p_value,
            test_method=test_method,
            severity=severity,
            detected_at=datetime.utcnow(),
            observation_window_start=observed_window_start,
            observation_window_end=observed_window_end,
            observation_sample_size=observed_sample_size,
        )

    def _check_option_drift(
        self,
        baseline: BehaviorBaselineDB,
        decision_type: str,
        baseline_dist: Dict,
        observed_dist: Dict,
        p_value: float,
        test_method: str,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> List[BehaviorDriftDB]:
        """
        Check each option in a decision type for drift.

        Args:
            baseline: Baseline being compared
            decision_type: Type of decision
            baseline_dist: Baseline distribution
            observed_dist: Observed distribution
            p_value: Statistical test p-value
            test_method: Statistical test method
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            observed_sample_size: Sample size

        Returns:
            List of drift records for significant changes
        """
        drift_records = []
        all_options = set(baseline_dist.keys()) | set(observed_dist.keys())

        for option in all_options:
            baseline_value = baseline_dist.get(option, 0.0)
            observed_value = observed_dist.get(option, 0.0)

            delta = observed_value - baseline_value
            delta_percent = (delta / baseline_value * 100) if baseline_value > 0 else 0.0

            # Check if significant
            if self._is_significant(p_value, abs(delta_percent), "decision"):
                metric = f"{decision_type}.{option}"
                severity = self._calculate_severity(abs(delta_percent), "decision")

                drift = self._create_drift_record(
                    baseline=baseline,
                    drift_type="decision",
                    metric=metric,
                    baseline_value=baseline_value,
                    observed_value=observed_value,
                    delta=delta,
                    delta_percent=delta_percent,
                    p_value=p_value,
                    test_method=test_method,
                    severity=severity,
                    observed_window_start=observed_window_start,
                    observed_window_end=observed_window_end,
                    observed_sample_size=observed_sample_size,
                )
                drift_records.append(drift)

        return drift_records

    def _compare_decision_distributions(
        self,
        baseline: BehaviorBaselineDB,
        baseline_profile: BehaviorProfileDB,
        observed_profile: Dict,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> List[BehaviorDriftDB]:
        """
        Compare decision distributions using Chi-square test.

        Returns drift records for significant changes.
        """
        drift_records = []

        baseline_dists = baseline_profile.decision_distributions or {}
        observed_dists = observed_profile["decision_distributions"] or {}

        # Get all decision types
        all_types = set(baseline_dists.keys()) | set(observed_dists.keys())

        for decision_type in all_types:
            baseline_dist = baseline_dists.get(decision_type, {})
            observed_dist = observed_dists.get(decision_type, {})

            # Skip if either is empty
            if not baseline_dist or not observed_dist:
                continue

            # Run statistical test
            p_value, test_method = self._run_chi_square_test(baseline_dist, observed_dist)

            # Check each selection option for drift
            option_drifts = self._check_option_drift(
                baseline=baseline,
                decision_type=decision_type,
                baseline_dist=baseline_dist,
                observed_dist=observed_dist,
                p_value=p_value,
                test_method=test_method,
                observed_window_start=observed_window_start,
                observed_window_end=observed_window_end,
                observed_sample_size=observed_sample_size,
            )
            drift_records.extend(option_drifts)

        return drift_records

    def _check_signal_code_drift(
        self,
        baseline: BehaviorBaselineDB,
        signal_type: str,
        baseline_dist: Dict,
        observed_dist: Dict,
        p_value: float,
        test_method: str,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> List[BehaviorDriftDB]:
        """
        Check each signal code for drift.

        Args:
            baseline: Baseline being compared
            signal_type: Type of signal
            baseline_dist: Baseline distribution
            observed_dist: Observed distribution
            p_value: Statistical test p-value
            test_method: Statistical test method
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            observed_sample_size: Sample size

        Returns:
            List of drift records for significant changes
        """
        drift_records = []
        all_codes = set(baseline_dist.keys()) | set(observed_dist.keys())

        for code in all_codes:
            baseline_value = baseline_dist.get(code, 0.0)
            observed_value = observed_dist.get(code, 0.0)

            delta = observed_value - baseline_value
            delta_percent = (delta / baseline_value * 100) if baseline_value > 0 else 0.0

            # Check if significant
            if self._is_significant(p_value, abs(delta_percent), "signal"):
                metric = f"{signal_type}.{code}"
                severity = self._calculate_severity(abs(delta_percent), "signal")

                drift = self._create_drift_record(
                    baseline=baseline,
                    drift_type="signal",
                    metric=metric,
                    baseline_value=baseline_value,
                    observed_value=observed_value,
                    delta=delta,
                    delta_percent=delta_percent,
                    p_value=p_value,
                    test_method=test_method,
                    severity=severity,
                    observed_window_start=observed_window_start,
                    observed_window_end=observed_window_end,
                    observed_sample_size=observed_sample_size,
                )
                drift_records.append(drift)

        return drift_records

    def _compare_signal_distributions(
        self,
        baseline: BehaviorBaselineDB,
        baseline_profile: BehaviorProfileDB,
        observed_profile: Dict,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> List[BehaviorDriftDB]:
        """
        Compare signal distributions using Chi-square test.

        Returns drift records for significant changes.
        """
        drift_records = []

        baseline_dists = baseline_profile.signal_distributions or {}
        observed_dists = observed_profile["signal_distributions"] or {}

        # Get all signal types
        all_types = set(baseline_dists.keys()) | set(observed_dists.keys())

        for signal_type in all_types:
            baseline_dist = baseline_dists.get(signal_type, {})
            observed_dist = observed_dists.get(signal_type, {})

            # Skip if either is empty
            if not baseline_dist or not observed_dist:
                continue

            # Run statistical test
            p_value, test_method = self._run_chi_square_test(baseline_dist, observed_dist)

            # Check each signal code for drift
            code_drifts = self._check_signal_code_drift(
                baseline=baseline,
                signal_type=signal_type,
                baseline_dist=baseline_dist,
                observed_dist=observed_dist,
                p_value=p_value,
                test_method=test_method,
                observed_window_start=observed_window_start,
                observed_window_end=observed_window_end,
                observed_sample_size=observed_sample_size,
            )
            drift_records.extend(code_drifts)

        return drift_records

    def _check_latency_metric_drift(
        self,
        baseline: BehaviorBaselineDB,
        metric: str,
        baseline_value: float,
        observed_value: float,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> Optional[BehaviorDriftDB]:
        """
        Check a single latency metric for drift.

        Args:
            baseline: Baseline being compared
            metric: Metric name
            baseline_value: Baseline metric value
            observed_value: Observed metric value
            observed_window_start: Start of observation window
            observed_window_end: End of observation window
            observed_sample_size: Sample size

        Returns:
            Drift record if significant, None otherwise
        """
        # Skip if either is zero
        if baseline_value == 0 or observed_value == 0:
            return None

        delta = observed_value - baseline_value
        delta_percent = (delta / baseline_value * 100)

        # Use percent threshold (no statistical test for latency)
        if self._is_significant(1.0, abs(delta_percent), "latency"):
            severity = self._calculate_severity(abs(delta_percent), "latency")

            return self._create_drift_record(
                baseline=baseline,
                drift_type="latency",
                metric=metric,
                baseline_value=baseline_value,
                observed_value=observed_value,
                delta=delta,
                delta_percent=delta_percent,
                p_value=1.0,  # No p-value for percent threshold
                test_method="percent_threshold",
                severity=severity,
                observed_window_start=observed_window_start,
                observed_window_end=observed_window_end,
                observed_sample_size=observed_sample_size,
            )

        return None

    def _compare_latency_stats(
        self,
        baseline: BehaviorBaselineDB,
        baseline_profile: BehaviorProfileDB,
        observed_profile: Dict,
        observed_window_start: datetime,
        observed_window_end: datetime,
        observed_sample_size: int,
    ) -> List[BehaviorDriftDB]:
        """
        Compare latency statistics using percent threshold.

        Returns drift records for significant changes.
        """
        drift_records = []

        baseline_stats = baseline_profile.latency_stats or {}
        observed_stats = observed_profile["latency_stats"] or {}

        # Latency metrics to check
        metrics = ["mean_run_duration_ms", "p95_run_duration_ms"]

        for metric in metrics:
            baseline_value = baseline_stats.get(metric, 0.0)
            observed_value = observed_stats.get(metric, 0.0)

            drift = self._check_latency_metric_drift(
                baseline=baseline,
                metric=metric,
                baseline_value=baseline_value,
                observed_value=observed_value,
                observed_window_start=observed_window_start,
                observed_window_end=observed_window_end,
                observed_sample_size=observed_sample_size,
            )

            if drift:
                drift_records.append(drift)

        return drift_records

    def _run_chi_square_test(
        self, baseline_dist: Dict, observed_dist: Dict
    ) -> Tuple[float, str]:
        """
        Run Chi-square test on two distributions.

        Args:
            baseline_dist: Baseline distribution {"option": probability}
            observed_dist: Observed distribution {"option": probability}

        Returns:
            (p_value, test_method)
        """
        # Get all options
        all_options = set(baseline_dist.keys()) | set(observed_dist.keys())

        if len(all_options) < 2:
            return (1.0, "chi_square")  # Not enough categories

        # Build frequency arrays
        baseline_freqs = [baseline_dist.get(opt, 0.0) for opt in sorted(all_options)]
        observed_freqs = [observed_dist.get(opt, 0.0) for opt in sorted(all_options)]

        # Convert probabilities to counts (multiply by 1000 for precision)
        baseline_counts = [f * 1000 for f in baseline_freqs]
        observed_counts = [f * 1000 for f in observed_freqs]

        # Run Chi-square test
        try:
            _, p_value = stats.chisquare(
                f_obs=observed_counts, f_exp=baseline_counts
            )
            return (p_value, "chi_square")
        except (ValueError, ZeroDivisionError):
            # If test fails, return non-significant p-value
            return (1.0, "chi_square")

    def _is_significant(
        self, p_value: float, delta_percent: float, drift_type: str
    ) -> bool:
        """
        Determine if drift is statistically significant.

        Args:
            p_value: Statistical p-value (1.0 if no test)
            delta_percent: Absolute percent change
            drift_type: Type of drift ('decision', 'signal', 'latency')

        Returns:
            True if drift is significant
        """
        config = self.threshold_config.get(f"{drift_type}_drift", {})

        # Check p-value threshold (if applicable)
        p_threshold = config.get("p_value_threshold", 0.05)
        if p_value < 1.0 and p_value > p_threshold:
            return False  # Not statistically significant

        # Check delta threshold
        min_delta = config.get("min_delta_percent", 10.0)
        if delta_percent < min_delta:
            return False  # Change too small

        return True

    def _calculate_severity(self, delta_percent: float, _drift_type: str = None) -> str:
        """
        Calculate severity based purely on magnitude of change.

        Not a quality judgment - just change magnitude.

        Args:
            delta_percent: Absolute percent change
            _drift_type: Type of drift (unused, reserved for future use)

        Returns:
            "low", "medium", or "high"
        """
        severity_config = self.threshold_config.get("severity_thresholds", {})

        # Default thresholds
        low_threshold = severity_config.get("low", {}).get("max_delta_percent", 15.0)
        medium_threshold = severity_config.get("medium", {}).get("max_delta_percent", 30.0)

        if delta_percent <= low_threshold:
            return "low"
        elif delta_percent <= medium_threshold:
            return "medium"
        else:
            return "high"

    def _load_thresholds(self, config_path: Optional[str] = None) -> Dict:
        """
        Load drift detection thresholds from config.

        Args:
            config_path: Path to config file (optional)

        Returns:
            Dict of threshold configuration
        """
        # Default thresholds
        default_config = {
            "decision_drift": {
                "p_value_threshold": 0.05,
                "min_delta_percent": 10.0,
            },
            "signal_drift": {
                "p_value_threshold": 0.05,
                "min_delta_percent": 15.0,
            },
            "latency_drift": {
                "min_delta_percent": 20.0,
            },
            "severity_thresholds": {
                "low": {"max_delta_percent": 15.0},
                "medium": {"max_delta_percent": 30.0},
            },
        }

        # Load from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        # Merge with defaults
                        for key, value in loaded_config.items():
                            if isinstance(value, dict):
                                default_config[key] = {**default_config.get(key, {}), **value}
                            else:
                                default_config[key] = value
            except Exception:
                pass  # Use defaults if config fails to load

        return default_config


# Convenience function

def detect_drift_for_baseline(
    db: Session,
    baseline: BehaviorBaselineDB,
    observed_window_start: datetime,
    observed_window_end: datetime,
    min_sample_size: int = 100,
    config_path: Optional[str] = None,
) -> List[BehaviorDriftDB]:
    """
    Convenience function to detect drift for a baseline.

    Args:
        db: Database session
        baseline: Baseline to compare against
        observed_window_start: Start of observation window
        observed_window_end: End of observation window
        min_sample_size: Minimum runs required (default: 100)
        config_path: Path to drift config (optional)

    Returns:
        List of BehaviorDriftDB objects
    """
    engine = DriftDetectionEngine(db, config_path)
    return engine.detect_drift(
        baseline=baseline,
        observed_window_start=observed_window_start,
        observed_window_end=observed_window_end,
        min_sample_size=min_sample_size,
    )
