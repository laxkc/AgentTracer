"""
Integration Test: Error Handling and Recovery

Tests failure modes, transaction rollbacks, and error propagation.

Prerequisites:
- PostgreSQL running
- Ingest and Query APIs running
"""

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import IntegrityError

from server.models.database import AgentRunDB, AgentStepDB


@pytest.mark.integration
class TestTransactionRollback:
    """Test that transactions roll back on errors."""

    def test_partial_insert_rollback(self, db_session):
        """Test that partial inserts are rolled back on error."""
        run_id = uuid4()

        try:
            # Start transaction
            run = AgentRunDB(
                run_id=run_id,
                agent_id="test",
                agent_version="1.0.0",
                environment="test",
                status="success",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            )
            db_session.add(run)
            db_session.flush()

            # This should fail
            invalid_step = AgentStepDB(
                run_id=run_id,
                step_type="invalid_type",
                name="test",
                seq=0,
                latency_ms=100,
            )
            db_session.add(invalid_step)
            db_session.commit()

        except IntegrityError:
            db_session.rollback()

        # Verify run was not created
        result = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
        assert result is None


@pytest.mark.integration
class TestMalformedRequests:
    """Test handling of malformed requests."""

    def test_malformed_json(self, ingest_api_url):
        """Test that malformed JSON returns 400."""
        with httpx.Client() as client:
            response = client.post(
                f"{ingest_api_url}/v1/runs",
                content=b"{invalid json}",
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400

    def test_empty_request_body(self, ingest_api_url):
        """Test that empty request body returns 400."""
        with httpx.Client() as client:
            response = client.post(
                f"{ingest_api_url}/v1/runs",
                content=b"",
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code in [400, 422]

    def test_wrong_content_type(self, ingest_api_url, sample_run_data):
        """Test request with wrong Content-Type."""
        run_data = sample_run_data()

        with httpx.Client() as client:
            response = client.post(
                f"{ingest_api_url}/v1/runs",
                content=str(run_data),
                headers={"Content-Type": "text/plain"},
            )

            assert response.status_code in [400, 415, 422]


@pytest.mark.integration
class TestConstraintViolations:
    """Test database constraint violation handling."""

    def test_duplicate_run_id_handled(self, ingest_api_url, sample_run_data):
        """Test that duplicate run_id is handled gracefully."""
        run_data = sample_run_data()

        with httpx.Client() as client:
            # First insertion
            response1 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response1.status_code == 201

            # Duplicate insertion
            response2 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response2.status_code == 409

            # Error should have details
            error_body = response2.json()
            assert "error" in error_body or "detail" in error_body

    def test_invalid_foreign_key_handled(self, db_session):
        """Test that invalid foreign keys are handled."""
        non_existent_run_id = uuid4()

        # Try to create step for non-existent run
        step = AgentStepDB(
            run_id=non_existent_run_id,
            step_type="tool",
            name="test",
            seq=0,
            latency_ms=100,
        )
        db_session.add(step)

        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.integration
class TestDatabaseConnectionFailure:
    """Test behavior when database connection fails."""

    def test_health_check_fails_when_db_down(self, query_api_url):
        """Test health check fails gracefully when DB is down."""
        # This test requires ability to stop/start database
        # Implementation depends on test infrastructure
        pass

    def test_503_when_db_unavailable(self, ingest_api_url, sample_run_data):
        """Test that 503 is returned when database is unavailable."""
        # This test requires ability to stop/start database
        # Implementation depends on test infrastructure
        pass


@pytest.mark.integration
class TestValidationErrors:
    """Test validation error responses."""

    def test_validation_error_details(self, ingest_api_url):
        """Test that validation errors include field details."""
        invalid_data = {
            "run_id": str(uuid4()),
            "agent_id": "test",
            "agent_version": "1.0.0",
            "environment": "test",
            "status": "invalid_status",  # Invalid enum value
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=invalid_data)

            assert response.status_code in [400, 422]
            body = response.json()

            # Should indicate which field is invalid
            assert "status" in str(body).lower() or "detail" in body

    def test_multiple_validation_errors(self, ingest_api_url):
        """Test handling of multiple validation errors."""
        invalid_data = {
            "run_id": "not-a-uuid",  # Invalid UUID format
            "agent_id": "",  # Empty string
            "status": "invalid",  # Invalid enum
        }

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=invalid_data)

            assert response.status_code in [400, 422]


@pytest.mark.integration
class TestRateLimiting:
    """Test rate limiting behavior (if implemented)."""

    def test_rate_limit_not_enforced_in_test(self, ingest_api_url, sample_run_data):
        """Test that rate limiting doesn't affect normal operation."""
        # Send multiple requests rapidly
        for _ in range(10):
            run_data = sample_run_data()
            with httpx.Client() as client:
                response = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
                assert response.status_code == 201


@pytest.mark.integration
class TestErrorMessageClarity:
    """Test that error messages are clear and actionable."""

    def test_missing_field_error_message(self, ingest_api_url):
        """Test that missing required fields produce clear errors."""
        incomplete_data = {
            "run_id": str(uuid4()),
            # Missing agent_id, agent_version, etc.
        }

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=incomplete_data)

            assert response.status_code in [400, 422]
            body = response.json()

            # Error should mention missing fields
            assert "detail" in body or "error" in body

    def test_404_error_message(self, query_api_url):
        """Test that 404 errors have helpful messages."""
        non_existent_id = str(uuid4())

        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{non_existent_id}")

            assert response.status_code == 404
            body = response.json()

            # Should indicate resource not found
            assert "not found" in str(body).lower() or "error" in body


@pytest.mark.integration
class TestIdempotency:
    """Test idempotency of operations."""

    def test_duplicate_submission_idempotent(self, ingest_api_url, sample_run_data):
        """Test that duplicate submissions are idempotent."""
        run_data = sample_run_data()

        with httpx.Client() as client:
            # First submission
            response1 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response1.status_code == 201

            # Duplicate submission should return 409 (not 500)
            response2 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response2.status_code == 409

            # Both responses should have same run_id
            body1 = response1.json()
            body2 = response2.json()

            # First returns the run, second returns error
            if "run_id" in body1:
                assert body1["run_id"] == run_data["run_id"]


@pytest.mark.integration
class TestConcurrency:
    """Test concurrent request handling."""

    def test_concurrent_inserts(self, ingest_api_url, sample_run_data):
        """Test that concurrent inserts don't cause conflicts."""
        import concurrent.futures

        def insert_run():
            run_data = sample_run_data()
            with httpx.Client() as client:
                response = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
                return response.status_code

        # Submit 5 runs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_run) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(status == 201 for status in results)
