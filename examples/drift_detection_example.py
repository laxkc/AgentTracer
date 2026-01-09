"""
Phase 3 - Real-World Usage Example

This script demonstrates how to integrate Phase 3 drift detection
into your agent observability workflow.

Usage:
    python examples/phase3_usage_example.py
"""

import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.alerts import AlertEmitter
from backend.baselines import BaselineManager
from backend.behavior_profiles import BehaviorProfileBuilder
from backend.drift_engine import BehaviorProfileDB, DriftDetectionEngine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def setup_database():
    """Initialize database connection."""
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/agent_observability"
    )

    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return SessionLocal()


def example_create_baseline(db, agent_id, agent_version, environment):
    """
    Example: Create a behavioral baseline for an agent.

    This should be run after an agent has stabilized in production
    to establish a baseline for drift detection.
    """
    print(f"\n{'=' * 80}")
    print(f"EXAMPLE 1: Creating Baseline for {agent_id} v{agent_version}")
    print(f"{'=' * 80}\n")

    # Step 1: Build a behavioral profile from the last 7 days
    print("Step 1: Building behavioral profile from last 7 days...")

    builder = BehaviorProfileBuilder(db)

    profile_data = builder.build_profile(
        agent_id=agent_id,
        agent_version=agent_version,
        environment=environment,
        window_start=datetime.utcnow() - timedelta(days=7),
        window_end=datetime.utcnow(),
        min_sample_size=100,  # Require at least 100 runs
    )

    # Save profile to database
    profile = BehaviorProfileDB(
        agent_id=profile_data["agent_id"],
        agent_version=profile_data["agent_version"],
        environment=profile_data["environment"],
        window_start=profile_data["window_start"],
        window_end=profile_data["window_end"],
        sample_size=profile_data["sample_size"],
        decision_distributions=profile_data["decision_distributions"],
        signal_distributions=profile_data["signal_distributions"],
        latency_stats=profile_data["latency_stats"],
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    print(f"  ✓ Profile created: {profile.profile_id}")
    print(f"  - Sample size: {profile.sample_size} runs")
    print(f"  - Decision types tracked: {list(profile.decision_distributions.keys())}")
    print(f"  - Signal types tracked: {list(profile.signal_distributions.keys())}")

    # Step 2: Create baseline from profile
    print("\nStep 2: Creating baseline from profile...")

    manager = BaselineManager(db)

    baseline = manager.create_baseline(
        profile_id=profile.profile_id,
        agent_id=agent_id,
        agent_version=agent_version,
        environment=environment,
        baseline_type="version",  # version, environment, or experiment
        approved_by="ops_team",
        description=f"Production baseline for {agent_id} v{agent_version}",
        auto_activate=True,  # Automatically activate this baseline
    )

    print(f"  ✓ Baseline created: {baseline.baseline_id}")
    print(f"  - Type: {baseline.baseline_type}")
    print(f"  - Active: {baseline.is_active}")
    print(f"  - Created at: {baseline.created_at}")

    return baseline


def example_detect_drift(db, agent_id, agent_version, environment):
    """
    Example: Run drift detection against active baseline.

    This should be run periodically (e.g., hourly or daily) to
    detect behavioral changes in your agents.
    """
    print(f"\n{'=' * 80}")
    print(f"EXAMPLE 2: Detecting Drift for {agent_id} v{agent_version}")
    print(f"{'=' * 80}\n")

    # Step 1: Get active baseline
    print("Step 1: Finding active baseline...")

    manager = BaselineManager(db)
    baseline = manager.get_active_baseline(agent_id, agent_version, environment)

    if not baseline:
        print(f"  ✗ No active baseline found for {agent_id} v{agent_version} ({environment})")
        print("  Run example_create_baseline() first!")
        return

    print(f"  ✓ Active baseline found: {baseline.baseline_id}")
    print(f"  - Created: {baseline.created_at}")
    print(f"  - Approved by: {baseline.approved_by}")

    # Step 2: Run drift detection on last hour
    print("\nStep 2: Running drift detection on last hour...")

    engine = DriftDetectionEngine(db)

    drift_events = engine.detect_drift(
        baseline=baseline,
        observed_window_start=datetime.utcnow() - timedelta(hours=1),
        observed_window_end=datetime.utcnow(),
        min_sample_size=50,  # Require at least 50 runs for comparison
    )

    print("  ✓ Drift detection complete")
    print(f"  - Drift events found: {len(drift_events)}")

    if drift_events:
        print("\n  Detected drift:")
        for drift in drift_events:
            change_verb = "increased" if drift.delta > 0 else "decreased"
            print(
                f"  - {drift.drift_type}.{drift.metric}: {change_verb} by {drift.delta_percent:+.1f}%"
            )
            print(f"    Severity: {drift.severity}, Significance: p={drift.significance:.4f}")
    else:
        print("\n  No significant drift detected. Agent behavior is stable.")

    return drift_events


def example_emit_alerts(drift_events):
    """
    Example: Emit alerts for detected drift.

    Alerts will be sent to configured channels (log, webhook, Slack, etc.)
    """
    print(f"\n{'=' * 80}")
    print("EXAMPLE 3: Emitting Alerts for Drift Events")
    print(f"{'=' * 80}\n")

    if not drift_events:
        print("  No drift events to alert on.")
        return

    emitter = AlertEmitter()

    print(f"Emitting {len(drift_events)} drift alerts...")

    for drift in drift_events:
        print(f"\n  Alerting on: {drift.drift_type}.{drift.metric}")
        emitter.emit(drift)
        print("  ✓ Alert emitted")

    print("\nAll alerts emitted successfully!")
    print("Check your configured channels (logs, Slack, webhooks, etc.)")


def example_resolve_drift(db, drift_id):
    """
    Example: Mark a drift event as resolved.

    Once you've investigated and addressed a drift event, mark it as resolved
    to remove it from active monitoring.
    """
    print(f"\n{'=' * 80}")
    print("EXAMPLE 4: Resolving Drift Event")
    print(f"{'=' * 80}\n")

    from backend.drift_engine import BehaviorDriftDB

    # Find drift event
    drift = db.query(BehaviorDriftDB).filter(BehaviorDriftDB.drift_id == drift_id).first()

    if not drift:
        print(f"  ✗ Drift event {drift_id} not found")
        return

    if drift.resolved_at:
        print(f"  ⚠ Drift event already resolved at {drift.resolved_at}")
        return

    # Mark as resolved
    drift.resolved_at = datetime.utcnow()
    db.commit()

    print("  ✓ Drift event resolved")
    print(f"  - Drift ID: {drift.drift_id}")
    print(f"  - Metric: {drift.drift_type}.{drift.metric}")
    print(f"  - Resolved at: {drift.resolved_at}")


def example_query_api():
    """
    Example: Query Phase 3 data via REST API.

    Shows how to retrieve drift events, baselines, and summaries
    programmatically.
    """
    print(f"\n{'=' * 80}")
    print("EXAMPLE 5: Querying Phase 3 Data via API")
    print(f"{'=' * 80}\n")

    import requests

    base_url = "http://localhost:8001/v1/phase3"

    # Query 1: Get all unresolved drift events
    print("Query 1: Get unresolved drift events...")
    response = requests.get(f"{base_url}/drift?resolved=false&limit=10")
    drift_events = response.json()

    print(f"  ✓ Found {len(drift_events)} unresolved drift events")
    for drift in drift_events[:3]:  # Show first 3
        print(
            f"  - {drift['agent_id']} v{drift['agent_version']}: "
            f"{drift['metric']} ({drift['severity']})"
        )

    # Query 2: Get drift summary for last 7 days
    print("\nQuery 2: Get drift summary for last 7 days...")
    response = requests.get(f"{base_url}/drift/summary?days=7")
    summary = response.json()

    print("  ✓ Summary retrieved")
    print(f"  - Total drift events: {summary['total_drift_events']}")
    print(f"  - Unresolved: {summary['unresolved_drift_events']}")
    print(f"  - By severity: {summary['drift_by_severity']}")
    print(f"  - Agents with drift: {summary['agents_with_drift']}")

    # Query 3: Get active baselines
    print("\nQuery 3: Get active baselines...")
    response = requests.get(f"{base_url}/baselines?is_active=true")
    baselines = response.json()

    print(f"  ✓ Found {len(baselines)} active baselines")
    for baseline in baselines[:3]:  # Show first 3
        print(
            f"  - {baseline['agent_id']} v{baseline['agent_version']} ({baseline['environment']})"
        )


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Phase 3 - Usage Examples")
    print("=" * 80)

    # Setup
    db = setup_database()

    # Example agent configuration
    agent_id = "customer_support_agent"
    agent_version = "2.0.0"
    environment = "production"

    try:
        # Example 1: Create baseline (run once per agent version)
        _baseline = example_create_baseline(db, agent_id, agent_version, environment)

        # Example 2: Detect drift (run periodically, e.g., hourly)
        drift_events = example_detect_drift(db, agent_id, agent_version, environment)

        # Example 3: Emit alerts
        if drift_events:
            example_emit_alerts(drift_events)

            # Example 4: Resolve drift (after investigation)
            first_drift_id = drift_events[0].drift_id
            example_resolve_drift(db, first_drift_id)

        # Example 5: Query via API
        example_query_api()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
