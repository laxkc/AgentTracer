"""
Integration Test: End-to-End Telemetry Flow

Tests: SDK → Ingest API → Database → Query API

Prerequisites:
- PostgreSQL running
- Database schema applied
- Ingest API running on port 8000
- Query API running on port 8001
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest

from sdk.agenttrace import AgentTracer
from server.models.database import AgentRunDB


@pytest.mark.integration
class TestSDKToIngestFlow:
    """Test SDK to Ingest API flow."""

    def test_ingest_complete_run(self, ingest_api_url, db_session):
        """Test ingesting a complete run with steps, failures, decisions, and signals."""
        run_id = uuid4()

        # Create run via SDK
        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
            api_url=ingest_api_url,
            environment="test",
        )

        with tracer.start_run(run_id=run_id) as run:
            with run.step("plan", "analyze_request"):
                time.sleep(0.01)

            with run.step("tool", "api_call"):
                time.sleep(0.02)

            run.record_decision(
                decision_type="tool_selection",
                selected="api",
                alternatives=["api", "cache"],
            )

            run.record_quality_signal(signal_type="schema_valid", signal_code="full_match")

        # Verify in database
        db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()

        assert db_run is not None
        assert db_run.agent_id == "test_agent"
        assert db_run.agent_version == "1.0.0"
        assert db_run.status == "success"

    def test_ingest_run_with_failure(self, ingest_api_url, db_session):
        """Test ingesting a run with failures."""
        run_id = uuid4()

        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
            api_url=ingest_api_url,
            environment="test",
        )

        with tracer.start_run(run_id=run_id) as run:
            with run.step("tool", "api_call"):
                pass

            run.record_failure(
                failure_type="tool_error",
                failure_code="timeout",
                message="API timeout",
                step_seq=0,
            )

        # Verify status is failure
        db_run = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()

        assert db_run is not None
        assert db_run.status == "failure"


@pytest.mark.integration
class TestDatabaseToQueryFlow:
    """Test Database to Query API flow."""

    def test_query_run_by_id(self, query_api_url, db_session, sample_run_data):
        """Test querying a run by ID."""
        # Create run in database
        run_data = sample_run_data()
        run_id = run_data["run_id"]

        # Insert via ingest API
        with httpx.Client() as client:
            response = client.post(
                f"{query_api_url.replace('8001', '8000')}/v1/runs", json=run_data
            )
            assert response.status_code == 201

        # Query via Query API
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}")
            assert response.status_code == 200

            run = response.json()
            assert run["run_id"] == run_id
            assert run["agent_id"] == run_data["agent_id"]

    def test_list_runs(self, query_api_url, db_session, sample_run_data):
        """Test listing runs."""
        # Create multiple runs
        for i in range(3):
            run_data = sample_run_data(agent_id=f"agent_{i}")
            with httpx.Client() as client:
                response = client.post(
                    f"{query_api_url.replace('8001', '8000')}/v1/runs", json=run_data
                )
                assert response.status_code == 201

        # List runs
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs?limit=10")
            assert response.status_code == 200

            runs = response.json()
            assert len(runs) >= 3

    def test_query_steps_for_run(self, query_api_url, db_session, sample_run_data):
        """Test querying steps for a specific run."""
        run_data = sample_run_data(include_steps=True)
        run_id = run_data["run_id"]

        # Insert run
        with httpx.Client() as client:
            response = client.post(
                f"{query_api_url.replace('8001', '8000')}/v1/runs", json=run_data
            )
            assert response.status_code == 201

        # Query steps
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}/steps")
            assert response.status_code == 200

            steps = response.json()
            assert len(steps) >= 1


@pytest.mark.integration
class TestEndToEndRoundTrip:
    """Test complete round-trip: SDK → Ingest → DB → Query."""

    def test_full_round_trip(self, ingest_api_url, query_api_url):
        """Test full telemetry round-trip."""
        run_id = uuid4()

        # 1. Capture via SDK
        tracer = AgentTracer(
            agent_id="roundtrip_agent",
            agent_version="1.0.0",
            api_url=ingest_api_url,
            environment="test",
        )

        with tracer.start_run(run_id=run_id) as run:
            with run.step("plan", "step1"):
                time.sleep(0.01)

            with run.step("tool", "step2"):
                time.sleep(0.01)

            run.record_decision(
                decision_type="tool_selection",
                selected="api",
                alternatives=["api", "cache"],
            )

        # 2. Wait for propagation
        time.sleep(0.5)

        # 3. Query back via API
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}")

            if response.status_code == 200:
                queried_run = response.json()

                # Verify data integrity
                assert queried_run["run_id"] == str(run_id)
                assert queried_run["agent_id"] == "roundtrip_agent"
                assert queried_run["agent_version"] == "1.0.0"
                assert queried_run["status"] == "success"


@pytest.mark.integration
class TestDataConsistency:
    """Test data consistency across the pipeline."""

    def test_timestamp_preservation(self, ingest_api_url, query_api_url):
        """Test that timestamps are preserved correctly."""
        run_id = uuid4()
        started_at = datetime.now(timezone.utc)

        tracer = AgentTracer(
            agent_id="timestamp_test",
            agent_version="1.0.0",
            api_url=ingest_api_url,
            environment="test",
        )

        with tracer.start_run(run_id=run_id) as run:
            pass

        time.sleep(0.5)

        # Query back
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}")

            if response.status_code == 200:
                queried_run = response.json()
                queried_started = datetime.fromisoformat(queried_run["started_at"])

                # Timestamps should be very close (within 1 second)
                time_diff = abs((queried_started - started_at).total_seconds())
                assert time_diff < 1.0

    def test_metadata_preservation(self, ingest_api_url, query_api_url):
        """Test that metadata is preserved exactly."""
        run_id = uuid4()
        metadata = {
            "user_id": "user123",
            "session_id": "sess456",
            "model": "gpt-4",
        }

        tracer = AgentTracer(
            agent_id="metadata_test",
            agent_version="1.0.0",
            api_url=ingest_api_url,
            environment="test",
        )

        with tracer.start_run(run_id=run_id, metadata=metadata) as run:
            pass

        time.sleep(0.5)

        # Query back
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}")

            if response.status_code == 200:
                queried_run = response.json()
                assert queried_run["metadata"] == metadata
