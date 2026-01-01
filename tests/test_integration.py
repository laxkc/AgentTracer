"""
Integration Tests for Agent Observability Platform

These tests verify end-to-end functionality of the entire system:
- SDK telemetry capture
- Ingest API
- Query API
- Database persistence

Prerequisites:
- PostgreSQL running (docker-compose up -d postgres)
- Database schema applied (./db/setup.sh)

Run with: pytest tests/test_integration.py -v
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.models import AgentRunDB, AgentStepDB, AgentFailureDB
from sdk.agenttrace import AgentTracer

# Test configuration
INGEST_API_URL = "http://localhost:8000"
QUERY_API_URL = "http://localhost:8001"
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/agent_observability"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def db_session():
    """Create a database session for verification"""
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def http_client():
    """Create HTTP client for API calls"""
    client = httpx.Client(timeout=10.0)
    yield client
    client.close()


@pytest.fixture(autouse=True)
def cleanup_test_data(db_session):
    """Clean up test data after each test"""
    yield
    # Clean up runs created during tests (cascade will handle steps/failures)
    db_session.execute(
        text("DELETE FROM agent_runs WHERE agent_id LIKE 'test_%'")
    )
    db_session.commit()


# ============================================================================
# Health Check Tests
# ============================================================================


def test_ingest_api_health(http_client):
    """Test that ingest API is healthy"""
    response = http_client.get(f"{INGEST_API_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ingest-api"


def test_query_api_health(http_client):
    """Test that query API is healthy"""
    response = http_client.get(f"{QUERY_API_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "query-api"


# ============================================================================
# SDK to Ingest API Integration Tests
# ============================================================================


def test_sdk_successful_run_ingestion(db_session):
    """Test that SDK can successfully ingest a complete run"""
    tracer = AgentTracer(
        agent_id="test_sdk_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None

    with tracer.start_run() as run:
        run_id = run.run_id

        with run.step("plan", "test_planning") as step:
            step.add_metadata({"test": "metadata"})
            time.sleep(0.05)

        with run.step("tool", "test_tool") as step:
            step.add_metadata({"tool_name": "test_api"})
            time.sleep(0.1)

    # Verify run was persisted to database
    db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
    assert db_run is not None
    assert db_run.agent_id == "test_sdk_agent"
    assert db_run.status == "success"
    assert len(db_run.steps) == 2


def test_sdk_failed_run_ingestion(db_session):
    """Test that SDK can ingest a failed run with failure classification"""
    tracer = AgentTracer(
        agent_id="test_sdk_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None

    with tracer.start_run() as run:
        run_id = run.run_id

        with run.step("tool", "failing_tool"):
            time.sleep(0.05)

        run.record_failure(
            failure_type="tool",
            failure_code="test_failure",
            message="Test failure message",
        )

    # Verify failure was persisted
    db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
    assert db_run is not None
    assert db_run.status == "failure"
    assert len(db_run.failures) == 1
    assert db_run.failures[0].failure_type == "tool"
    assert db_run.failures[0].failure_code == "test_failure"


def test_sdk_retry_modeling(db_session):
    """Test that retries are captured as separate step spans"""
    tracer = AgentTracer(
        agent_id="test_sdk_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None

    with tracer.start_run() as run:
        run_id = run.run_id

        # Simulate 3 retry attempts
        for attempt in range(3):
            with run.step("tool", "api_call") as step:
                step.add_metadata({"attempt": attempt + 1})
                time.sleep(0.02)

    # Verify all 3 attempts are separate steps
    db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
    assert len(db_run.steps) == 3
    assert db_run.steps[0].metadata["attempt"] == 1
    assert db_run.steps[1].metadata["attempt"] == 2
    assert db_run.steps[2].metadata["attempt"] == 3


# ============================================================================
# Ingest API Tests
# ============================================================================


def test_ingest_api_duplicate_run_idempotency(http_client, db_session):
    """Test that duplicate run_id is handled idempotently"""
    run_id = str(uuid4())

    payload = {
        "run_id": run_id,
        "agent_id": "test_idempotency_agent",
        "agent_version": "1.0.0",
        "environment": "test",
        "status": "success",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "steps": [
            {
                "step_id": str(uuid4()),
                "seq": 0,
                "step_type": "plan",
                "name": "test_step",
                "latency_ms": 100,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {},
            }
        ],
    }

    # First ingestion - should succeed with 201
    response1 = http_client.post(f"{INGEST_API_URL}/v1/runs", json=payload)
    assert response1.status_code == 201

    # Second ingestion with same run_id - should succeed with 200 (idempotent)
    response2 = http_client.post(f"{INGEST_API_URL}/v1/runs", json=payload)
    assert response2.status_code in [200, 201]  # Both are acceptable for idempotency

    # Verify only one run exists in DB
    count = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).count()
    assert count == 1


def test_ingest_api_privacy_validation(http_client):
    """Test that ingest API rejects sensitive data in metadata"""
    payload = {
        "run_id": str(uuid4()),
        "agent_id": "test_privacy_agent",
        "agent_version": "1.0.0",
        "environment": "test",
        "status": "success",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "steps": [
            {
                "step_id": str(uuid4()),
                "seq": 0,
                "step_type": "plan",
                "name": "test_step",
                "latency_ms": 100,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"prompt": "This should be rejected"},  # Forbidden!
            }
        ],
    }

    response = http_client.post(f"{INGEST_API_URL}/v1/runs", json=payload)
    # Should reject due to privacy violation
    assert response.status_code == 422  # Validation error


# ============================================================================
# Query API Tests
# ============================================================================


def test_query_api_list_runs(http_client, db_session):
    """Test querying runs with filters"""
    # Create test run
    tracer = AgentTracer(
        agent_id="test_query_agent",
        agent_version="2.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    with tracer.start_run() as run:
        with run.step("plan", "test"):
            time.sleep(0.01)

    # Query all runs
    response = http_client.get(f"{QUERY_API_URL}/v1/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) > 0


def test_query_api_get_specific_run(http_client):
    """Test getting a specific run by ID"""
    # Create test run
    tracer = AgentTracer(
        agent_id="test_specific_query_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None

    with tracer.start_run() as run:
        run_id = run.run_id
        with run.step("plan", "test"):
            time.sleep(0.01)

    # Query specific run
    response = http_client.get(f"{QUERY_API_URL}/v1/runs/{run_id}")
    assert response.status_code == 200
    run_data = response.json()
    assert run_data["run_id"] == str(run_id)
    assert len(run_data["steps"]) == 1


def test_query_api_run_not_found(http_client):
    """Test that querying non-existent run returns 404"""
    fake_run_id = str(uuid4())
    response = http_client.get(f"{QUERY_API_URL}/v1/runs/{fake_run_id}")
    assert response.status_code == 404


def test_query_api_filter_by_agent_id(http_client):
    """Test filtering runs by agent_id"""
    # Create run with specific agent_id
    tracer = AgentTracer(
        agent_id="test_filter_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    with tracer.start_run() as run:
        with run.step("plan", "test"):
            time.sleep(0.01)

    # Filter by agent_id
    response = http_client.get(
        f"{QUERY_API_URL}/v1/runs?agent_id=test_filter_agent"
    )
    assert response.status_code == 200
    runs = response.json()
    assert all(r["agent_id"] == "test_filter_agent" for r in runs)


def test_query_api_stats(http_client):
    """Test aggregated statistics endpoint"""
    # Create some test runs
    tracer = AgentTracer(
        agent_id="test_stats_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    # Successful run
    with tracer.start_run() as run:
        with run.step("plan", "test"):
            time.sleep(0.01)

    # Failed run
    with tracer.start_run() as run:
        with run.step("plan", "test"):
            time.sleep(0.01)
        run.record_failure(
            failure_type="tool", failure_code="test", message="Test failure"
        )

    # Query stats
    response = http_client.get(
        f"{QUERY_API_URL}/v1/stats?agent_id=test_stats_agent"
    )
    assert response.status_code == 200
    stats = response.json()

    assert "total_runs" in stats
    assert "total_failures" in stats
    assert "success_rate" in stats
    assert "avg_latency_ms" in stats
    assert stats["total_runs"] >= 2


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


def test_end_to_end_customer_support_workflow(http_client, db_session):
    """
    Test complete customer support agent workflow:
    1. SDK captures telemetry
    2. Ingest API persists data
    3. Query API retrieves data
    4. Data is accurate and complete
    """
    tracer = AgentTracer(
        agent_id="test_e2e_support_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None

    # Step 1: Capture telemetry
    with tracer.start_run() as run:
        run_id = run.run_id

        with run.step("plan", "analyze_query") as step:
            step.add_metadata({"query_type": "billing"})
            time.sleep(0.05)

        with run.step("retrieve", "search_kb") as step:
            step.add_metadata({"result_count": 5})
            time.sleep(0.1)

        with run.step("tool", "call_api") as step:
            step.add_metadata({"api": "customer_data", "http_status": 200})
            time.sleep(0.2)

        with run.step("respond", "generate") as step:
            step.add_metadata({"response_length": 300})
            time.sleep(0.15)

    # Step 2: Verify persistence
    db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
    assert db_run is not None
    assert db_run.status == "success"
    assert len(db_run.steps) == 4

    # Step 3: Query via API
    response = http_client.get(f"{QUERY_API_URL}/v1/runs/{run_id}")
    assert response.status_code == 200
    run_data = response.json()

    # Step 4: Verify data accuracy
    assert run_data["agent_id"] == "test_e2e_support_agent"
    assert len(run_data["steps"]) == 4
    assert run_data["steps"][0]["step_type"] == "plan"
    assert run_data["steps"][1]["step_type"] == "retrieve"
    assert run_data["steps"][2]["step_type"] == "tool"
    assert run_data["steps"][3]["step_type"] == "respond"

    # Verify metadata is preserved
    assert run_data["steps"][0]["metadata"]["query_type"] == "billing"
    assert run_data["steps"][1]["metadata"]["result_count"] == 5

    # Verify timing
    assert all(step["latency_ms"] > 0 for step in run_data["steps"])


def test_end_to_end_failure_workflow(http_client, db_session):
    """
    Test failure capture and retrieval workflow:
    1. Agent fails with semantic classification
    2. Failure is persisted with step linkage
    3. Query API retrieves failure details
    """
    tracer = AgentTracer(
        agent_id="test_e2e_failure_agent",
        agent_version="1.0.0",
        api_url=INGEST_API_URL,
        environment="test",
    )

    run_id = None
    failure_step_id = None

    with tracer.start_run() as run:
        run_id = run.run_id

        with run.step("plan", "analyze"):
            time.sleep(0.05)

        with run.step("tool", "failing_tool") as step:
            failure_step_id = step.step_id
            time.sleep(0.1)

        run.record_failure(
            failure_type="tool",
            failure_code="timeout",
            message="Tool failed after timeout",
            step_id=failure_step_id,
        )

    # Query failures via API
    response = http_client.get(f"{QUERY_API_URL}/v1/runs/{run_id}/failures")
    assert response.status_code == 200
    failures = response.json()

    assert len(failures) == 1
    assert failures[0]["failure_type"] == "tool"
    assert failures[0]["failure_code"] == "timeout"
    assert failures[0]["step_id"] == str(failure_step_id)


# ============================================================================
# Performance Tests (Basic)
# ============================================================================


def test_ingest_latency(http_client):
    """Test that ingest API meets <200ms p99 latency requirement"""
    latencies = []

    for _ in range(10):
        payload = {
            "run_id": str(uuid4()),
            "agent_id": "test_perf_agent",
            "agent_version": "1.0.0",
            "environment": "test",
            "status": "success",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "steps": [
                {
                    "step_id": str(uuid4()),
                    "seq": 0,
                    "step_type": "plan",
                    "name": "test",
                    "latency_ms": 100,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {},
                }
            ],
        }

        start = time.time()
        response = http_client.post(f"{INGEST_API_URL}/v1/runs", json=payload)
        latency = (time.time() - start) * 1000  # Convert to ms

        assert response.status_code == 201
        latencies.append(latency)

    # Check p99 latency
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
    print(f"\nIngest API p99 latency: {p99:.2f}ms")

    # Phase-1 requirement: <200ms p99
    assert p99 < 200, f"p99 latency {p99:.2f}ms exceeds 200ms requirement"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
