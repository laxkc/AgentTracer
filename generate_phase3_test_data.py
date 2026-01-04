"""
Phase 3 - Comprehensive Test Data Generator

Generates realistic test data to demonstrate Phase 3 drift detection:
- Multiple agents with different versions
- Sufficient sample sizes for baselines (100+ runs)
- Behavioral variations over time (to demonstrate drift)
- Diverse decision and quality signal distributions

Usage:
    python generate_phase3_test_data.py
"""

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import random

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import (
    AgentRunDB,
    AgentDecisionDB,
    AgentQualitySignalDB,
    AgentStepDB,
)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/agent_observability"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# Test Data Configurations
# =============================================================================

AGENTS = [
    {
        "agent_id": "customer_support_agent",
        "versions": ["1.0.0", "1.1.0", "2.0.0"],
        "environments": ["production", "staging"],
    },
    {
        "agent_id": "sales_assistant",
        "versions": ["1.0.0", "1.5.0"],
        "environments": ["production", "staging"],
    },
    {
        "agent_id": "code_reviewer",
        "versions": ["2.0.0", "2.1.0", "3.0.0"],
        "environments": ["production", "staging", "development"],
    },
    {
        "agent_id": "data_analyst_agent",
        "versions": ["1.0.0", "1.2.0"],
        "environments": ["production"],
    },
]

DECISION_TYPES = {
    "tool_selection": ["api_call", "database_query", "cache_lookup", "search_docs"],
    "retry_strategy": ["retry", "fallback", "skip", "abort"],
    "response_format": ["json", "markdown", "plain_text"],
    "data_source": ["primary_db", "cache", "external_api", "local_file"],
}

QUALITY_SIGNAL_TYPES = {
    "schema_validation": ["valid", "invalid", "partial"],
    "response_completeness": ["complete", "incomplete", "empty"],
    "data_freshness": ["fresh", "stale", "expired"],
    "error_handling": ["handled", "unhandled", "partial"],
}


# =============================================================================
# Data Generation Functions
# =============================================================================

def generate_run_with_data(
    db,
    agent_id,
    agent_version,
    environment,
    base_time,
    decision_probs,
    signal_probs,
    latency_range,
):
    """
    Generate a single agent run with steps, decisions, and quality signals.

    Args:
        db: Database session
        agent_id: Agent identifier
        agent_version: Agent version
        environment: Deployment environment
        base_time: Base timestamp for this run
        decision_probs: Probabilities for decision selections
        signal_probs: Probabilities for signal values
        latency_range: Tuple of (min_latency, max_latency) in ms
    """
    # Create run
    run_latency = random.uniform(latency_range[0], latency_range[1])
    started_at = base_time
    ended_at = started_at + timedelta(milliseconds=run_latency)

    run = AgentRunDB(
        run_id=uuid4(),
        agent_id=agent_id,
        agent_version=agent_version,
        environment=environment,
        status=random.choices(["success", "failure"], weights=[0.95, 0.05])[0],
        started_at=started_at,
        ended_at=ended_at,
    )
    db.add(run)
    db.flush()

    # Create 3-5 steps per run
    num_steps = random.randint(3, 5)
    steps = []

    for i in range(num_steps):
        step_latency = random.randint(50, 500)
        step_start = started_at + timedelta(milliseconds=i * step_latency)
        step_end = step_start + timedelta(milliseconds=step_latency)

        step = AgentStepDB(
            step_id=uuid4(),
            run_id=run.run_id,
            step_type=random.choice(["plan", "retrieve", "tool", "respond"]),
            name=f"step_{i+1}",
            latency_ms=step_latency,
            seq=i + 1,
            started_at=step_start,
            ended_at=step_end,
        )
        db.add(step)
        db.flush()
        steps.append(step)

    # Add decisions (1-2 per run)
    num_decisions = random.randint(1, 2)
    for _ in range(num_decisions):
        decision_type = random.choice(list(DECISION_TYPES.keys()))
        candidates = DECISION_TYPES[decision_type]

        # Use provided probabilities or random
        if decision_type in decision_probs:
            selected = random.choices(
                candidates,
                weights=decision_probs[decision_type],
            )[0]
        else:
            selected = random.choice(candidates)

        decision = AgentDecisionDB(
            decision_id=uuid4(),
            run_id=run.run_id,
            step_id=random.choice(steps).step_id,
            decision_type=decision_type,
            selected=selected,
            reason_code=f"{selected}_reason",
            confidence=random.uniform(0.6, 0.99),
            recorded_at=started_at,
        )
        db.add(decision)

    # Add quality signals (2-3 per run)
    num_signals = random.randint(2, 3)
    for _ in range(num_signals):
        signal_type = random.choice(list(QUALITY_SIGNAL_TYPES.keys()))
        codes = QUALITY_SIGNAL_TYPES[signal_type]

        # Use provided probabilities or random
        if signal_type in signal_probs:
            code = random.choices(
                codes,
                weights=signal_probs[signal_type],
            )[0]
        else:
            code = random.choice(codes)

        # Convert code to boolean value
        value = code in ["valid", "complete", "fresh", "handled"]

        signal = AgentQualitySignalDB(
            signal_id=uuid4(),
            run_id=run.run_id,
            step_id=random.choice(steps).step_id,
            signal_type=signal_type,
            signal_code=code,
            value=value,
            weight=1.0,
        )
        db.add(signal)


def generate_baseline_period(
    db,
    agent_id,
    agent_version,
    environment,
    start_date,
    num_runs,
):
    """
    Generate stable baseline data with consistent distributions.

    This creates a consistent behavioral profile suitable for baseline creation.
    """
    print(f"  Generating baseline period: {num_runs} runs...")

    # Stable decision probabilities
    decision_probs = {
        "tool_selection": [0.40, 0.30, 0.20, 0.10],  # Balanced distribution
        "retry_strategy": [0.20, 0.50, 0.25, 0.05],  # Prefer fallback
        "response_format": [0.60, 0.30, 0.10],       # Prefer JSON
        "data_source": [0.50, 0.30, 0.15, 0.05],    # Prefer primary DB
    }

    # Stable signal probabilities
    signal_probs = {
        "schema_validation": [0.85, 0.10, 0.05],     # Mostly valid
        "response_completeness": [0.80, 0.15, 0.05], # Mostly complete
        "data_freshness": [0.70, 0.25, 0.05],        # Mostly fresh
        "error_handling": [0.90, 0.08, 0.02],        # Mostly handled
    }

    # Stable latency range
    latency_range = (100, 500)  # 100-500ms

    for i in range(num_runs):
        run_time = start_date + timedelta(minutes=i * 10)
        generate_run_with_data(
            db, agent_id, agent_version, environment,
            run_time, decision_probs, signal_probs, latency_range
        )

    db.commit()


def generate_drift_period(
    db,
    agent_id,
    agent_version,
    environment,
    start_date,
    num_runs,
    drift_type,
):
    """
    Generate data with behavioral drift to demonstrate detection.

    Args:
        drift_type: Type of drift to introduce
            - "decision_shift": Change decision distributions
            - "signal_degradation": Decrease quality signals
            - "latency_increase": Increase latency
            - "all": Combination of all
    """
    print(f"  Generating drift period ({drift_type}): {num_runs} runs...")

    # Modified probabilities based on drift type
    decision_probs = {
        "tool_selection": [0.40, 0.30, 0.20, 0.10],
        "retry_strategy": [0.20, 0.50, 0.25, 0.05],
        "response_format": [0.60, 0.30, 0.10],
        "data_source": [0.50, 0.30, 0.15, 0.05],
    }

    signal_probs = {
        "schema_validation": [0.85, 0.10, 0.05],
        "response_completeness": [0.80, 0.15, 0.05],
        "data_freshness": [0.70, 0.25, 0.05],
        "error_handling": [0.90, 0.08, 0.02],
    }

    latency_range = (100, 500)

    # Apply drift
    if drift_type in ["decision_shift", "all"]:
        # Significant shift in tool selection (more API calls)
        decision_probs["tool_selection"] = [0.70, 0.15, 0.10, 0.05]
        # More retries
        decision_probs["retry_strategy"] = [0.50, 0.30, 0.15, 0.05]

    if drift_type in ["signal_degradation", "all"]:
        # Decrease in quality signals
        signal_probs["schema_validation"] = [0.60, 0.25, 0.15]  # Less valid
        signal_probs["response_completeness"] = [0.65, 0.25, 0.10]  # Less complete
        signal_probs["data_freshness"] = [0.50, 0.35, 0.15]  # Less fresh

    if drift_type in ["latency_increase", "all"]:
        # Significant latency increase
        latency_range = (300, 1200)  # 3x increase

    for i in range(num_runs):
        run_time = start_date + timedelta(minutes=i * 10)
        generate_run_with_data(
            db, agent_id, agent_version, environment,
            run_time, decision_probs, signal_probs, latency_range
        )

    db.commit()


def generate_agent_data(db, agent_config):
    """
    Generate complete test data for a single agent.

    Creates baseline periods and drift periods for all versions and environments.
    """
    agent_id = agent_config["agent_id"]
    print(f"\n{'='*80}")
    print(f"Generating data for: {agent_id}")
    print(f"{'='*80}")

    for version in agent_config["versions"]:
        for environment in agent_config["environments"]:
            print(f"\n{agent_id} v{version} ({environment})")

            # Baseline period: 30 days ago to 7 days ago
            baseline_start = datetime.utcnow() - timedelta(days=30)
            generate_baseline_period(
                db,
                agent_id,
                version,
                environment,
                baseline_start,
                num_runs=150,  # 150 runs for solid baseline
            )

            # Recent period with drift: last 7 days
            drift_start = datetime.utcnow() - timedelta(days=7)

            # Different drift types for different agents/versions
            if version.startswith("1."):
                drift_type = "decision_shift"
            elif version.startswith("2."):
                drift_type = "signal_degradation"
            else:
                drift_type = "latency_increase"

            generate_drift_period(
                db,
                agent_id,
                version,
                environment,
                drift_start,
                num_runs=100,  # 100 runs showing drift
                drift_type=drift_type,
            )


def cleanup_existing_data(db):
    """
    Clean up existing Phase 3 test data to start fresh.
    """
    print("\n" + "="*80)
    print("Cleaning up existing test data...")
    print("="*80 + "\n")

    # Delete in correct order (children first)
    db.query(AgentQualitySignalDB).delete()
    db.query(AgentDecisionDB).delete()
    db.query(AgentStepDB).delete()
    db.query(AgentRunDB).delete()

    db.commit()
    print("✓ Cleanup complete\n")


def print_summary(db):
    """
    Print summary of generated data.
    """
    print("\n" + "="*80)
    print("DATA GENERATION COMPLETE")
    print("="*80 + "\n")

    total_runs = db.query(AgentRunDB).count()
    total_decisions = db.query(AgentDecisionDB).count()
    total_signals = db.query(AgentQualitySignalDB).count()
    total_steps = db.query(AgentStepDB).count()

    print(f"Generated:")
    print(f"  - Agent runs: {total_runs:,}")
    print(f"  - Decisions: {total_decisions:,}")
    print(f"  - Quality signals: {total_signals:,}")
    print(f"  - Steps: {total_steps:,}")

    # Breakdown by agent
    print(f"\nBreakdown by agent:")
    from sqlalchemy import func
    agent_breakdown = (
        db.query(
            AgentRunDB.agent_id,
            AgentRunDB.agent_version,
            AgentRunDB.environment,
            func.count(AgentRunDB.run_id).label("count")
        )
        .group_by(AgentRunDB.agent_id, AgentRunDB.agent_version, AgentRunDB.environment)
        .order_by(AgentRunDB.agent_id, AgentRunDB.agent_version)
        .all()
    )

    for agent_id, version, env, count in agent_breakdown:
        print(f"  - {agent_id} v{version} ({env}): {count} runs")

    print(f"\n{'='*80}")
    print("Ready for Phase 3 testing!")
    print("="*80 + "\n")

    print("Next steps:")
    print("  1. Create behavioral profiles: python examples/phase3_usage_example.py")
    print("  2. View in UI: http://localhost:3001/behaviors")
    print("  3. Run drift detection to see behavioral changes")
    print()


def main():
    """
    Generate comprehensive Phase 3 test data.
    """
    db = SessionLocal()

    try:
        # Step 1: Clean up existing data
        cleanup_existing_data(db)

        # Step 2: Generate data for all agents
        for agent_config in AGENTS:
            generate_agent_data(db, agent_config)

        # Step 3: Print summary
        print_summary(db)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
