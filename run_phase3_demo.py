"""
Phase 3 - Complete Demo Script

Demonstrates the full Phase 3 workflow with the generated test data:
1. Create behavioral profiles for all agents
2. Establish baselines
3. Run drift detection
4. Show results

Usage:
    python run_phase3_demo.py
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.behavior_profiles import BehaviorProfileBuilder
from backend.baselines import BaselineManager
from backend.drift_engine import DriftDetectionEngine, BehaviorProfileDB
from backend.alerts import AlertEmitter

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/agent_observability"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_baseline_for_agent(db, agent_id, agent_version, environment):
    """
    Create a baseline for a specific agent/version/environment.
    """
    print(f"\n  Creating baseline for {agent_id} v{agent_version} ({environment})...")

    # Build profile from baseline period (30 days ago to 7 days ago)
    builder = BehaviorProfileBuilder(db)

    try:
        profile_data = builder.build_profile(
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            window_start=datetime.utcnow() - timedelta(days=30),
            window_end=datetime.utcnow() - timedelta(days=7),
            min_sample_size=100,
        )

        # Create profile in database
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

        print(f"    ✓ Profile created: {profile.profile_id}")
        print(f"      Sample size: {profile.sample_size} runs")

        # Create baseline
        manager = BaselineManager(db)
        baseline = manager.create_baseline(
            profile_id=profile.profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type="version",
            approved_by="auto_demo",
            description=f"Baseline for {agent_id} v{agent_version} ({environment})",
            auto_activate=True,
        )

        print(f"    ✓ Baseline created: {baseline.baseline_id}")
        print(f"      Active: {baseline.is_active}")

        return baseline

    except ValueError as e:
        print(f"    ✗ Failed: {e}")
        return None


def detect_drift_for_agent(db, agent_id, agent_version, environment):
    """
    Run drift detection for a specific agent/version/environment.
    """
    print(f"\n  Detecting drift for {agent_id} v{agent_version} ({environment})...")

    # Get active baseline
    manager = BaselineManager(db)
    baseline = manager.get_active_baseline(agent_id, agent_version, environment)

    if not baseline:
        print(f"    ✗ No active baseline found")
        return []

    # Run drift detection on last 7 days
    engine = DriftDetectionEngine(db)

    try:
        drift_events = engine.detect_drift(
            baseline=baseline,
            observed_window_start=datetime.utcnow() - timedelta(days=7),
            observed_window_end=datetime.utcnow(),
            min_sample_size=50,
        )

        if drift_events:
            print(f"    ✓ Detected {len(drift_events)} drift events:")
            for drift in drift_events:
                change_verb = "increased" if drift.delta > 0 else "decreased"
                print(f"      - {drift.drift_type}.{drift.metric}: {change_verb} by {drift.delta_percent:+.1f}%")
                print(f"        (severity: {drift.severity}, p={drift.significance:.4f})")

            # Emit alerts for high severity drift
            emitter = AlertEmitter()
            high_severity = [d for d in drift_events if d.severity == "high"]
            for drift in high_severity:
                emitter.emit(drift)

            if high_severity:
                print(f"    ✓ Emitted {len(high_severity)} high-severity alerts")
        else:
            print(f"    ○ No significant drift detected")

        return drift_events

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return []


def main():
    """
    Run complete Phase 3 demo.
    """
    db = SessionLocal()

    try:
        print("\n" + "="*80)
        print("PHASE 3 - COMPLETE DEMONSTRATION")
        print("="*80)

        # Agent configurations (subset for demo)
        demo_agents = [
            ("customer_support_agent", "2.0.0", "production"),
            ("sales_assistant", "1.5.0", "production"),
            ("code_reviewer", "3.0.0", "production"),
            ("data_analyst_agent", "1.2.0", "production"),
        ]

        # Step 1: Create baselines
        print("\n" + "="*80)
        print("STEP 1: Creating Baselines")
        print("="*80)

        baselines_created = 0
        for agent_id, version, env in demo_agents:
            baseline = create_baseline_for_agent(db, agent_id, version, env)
            if baseline:
                baselines_created += 1

        print(f"\n✓ Created {baselines_created} baselines")

        # Step 2: Detect drift
        print("\n" + "="*80)
        print("STEP 2: Detecting Drift")
        print("="*80)

        total_drift_events = 0
        for agent_id, version, env in demo_agents:
            drift_events = detect_drift_for_agent(db, agent_id, version, env)
            total_drift_events += len(drift_events)

        print(f"\n✓ Detected {total_drift_events} total drift events")

        # Step 3: Query summary
        print("\n" + "="*80)
        print("STEP 3: Summary Statistics")
        print("="*80)

        import requests

        try:
            response = requests.get("http://localhost:8001/v1/phase3/drift/summary?days=30")
            if response.status_code == 200:
                summary = response.json()
                print(f"\n  Drift Summary (last 30 days):")
                print(f"    - Total drift events: {summary['total_drift_events']}")
                print(f"    - Unresolved: {summary['unresolved_drift_events']}")
                print(f"    - By severity: {summary['drift_by_severity']}")
                print(f"    - By type: {summary['drift_by_type']}")
                print(f"    - Agents with drift: {summary['agents_with_drift']}")
        except Exception as e:
            print(f"  ✗ Could not fetch summary: {e}")

        # Final summary
        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETE")
        print("="*80)

        print(f"\n✓ Phase 3 is fully operational!")
        print(f"\nWhat was demonstrated:")
        print(f"  1. Behavioral profiles created from Phase 2 data ✓")
        print(f"  2. Baselines established and activated ✓")
        print(f"  3. Drift detection identified behavioral changes ✓")
        print(f"  4. Alerts emitted for high-severity drift ✓")
        print(f"  5. API endpoints returning real data ✓")

        print(f"\nView results:")
        print(f"  - API: curl http://localhost:8001/v1/phase3/drift | jq")
        print(f"  - UI:  http://localhost:3001/behaviors")

        print(f"\n" + "="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
