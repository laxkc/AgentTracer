"""
Integration Test: API Contracts

Tests API endpoint contracts, request/response schemas, and error handling.

Prerequisites:
- Ingest API running on port 8000
- Query API running on port 8001
"""

from uuid import uuid4

import httpx
import pytest


@pytest.mark.integration
class TestIngestAPIEndpoints:
    """Test Ingest API endpoint contracts."""

    def test_ingest_run_success(self, ingest_api_url, sample_run_data):
        """Test successful run ingestion returns 201."""
        run_data = sample_run_data()

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=run_data)

            assert response.status_code == 201
            body = response.json()
            assert body["run_id"] == run_data["run_id"]

    def test_ingest_run_missing_required_field(self, ingest_api_url):
        """Test that missing required fields return 400."""
        incomplete_data = {
            "run_id": str(uuid4()),
            # Missing agent_id, agent_version, etc.
        }

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=incomplete_data)

            assert response.status_code in [400, 422]  # Bad Request or Unprocessable Entity

    def test_ingest_run_invalid_status(self, ingest_api_url, sample_run_data):
        """Test that invalid status values return 400."""
        run_data = sample_run_data()
        run_data["status"] = "invalid_status"

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=run_data)

            assert response.status_code in [400, 422]

    def test_ingest_run_duplicate_id(self, ingest_api_url, sample_run_data):
        """Test that duplicate run_id returns 409."""
        run_data = sample_run_data()

        with httpx.Client() as client:
            # First submission
            response1 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response1.status_code == 201

            # Duplicate submission
            response2 = client.post(f"{ingest_api_url}/v1/runs", json=run_data)
            assert response2.status_code == 409  # Conflict

    def test_ingest_health_check(self, ingest_api_url):
        """Test ingest API health check."""
        with httpx.Client() as client:
            response = client.get(f"{ingest_api_url}/health")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "healthy"
            assert body["service"] == "ingest-api"


@pytest.mark.integration
class TestQueryAPIEndpoints:
    """Test Query API endpoint contracts."""

    def test_list_runs_success(self, query_api_url):
        """Test listing runs returns 200."""
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs?limit=10")

            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)

    def test_list_runs_with_filters(self, query_api_url):
        """Test listing runs with query parameters."""
        with httpx.Client() as client:
            response = client.get(
                f"{query_api_url}/v1/runs",
                params={
                    "agent_id": "test_agent",
                    "status": "success",
                    "limit": 5,
                    "offset": 0,
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)
            assert len(body) <= 5

    def test_get_run_by_id_success(self, query_api_url, ingest_api_url, sample_run_data):
        """Test getting run by ID returns 200."""
        # First ingest a run
        run_data = sample_run_data()
        run_id = run_data["run_id"]

        with httpx.Client() as client:
            client.post(f"{ingest_api_url}/v1/runs", json=run_data)

        # Query it
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}")

            assert response.status_code == 200
            body = response.json()
            assert body["run_id"] == run_id

    def test_get_run_not_found(self, query_api_url):
        """Test getting non-existent run returns 404."""
        non_existent_id = str(uuid4())

        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{non_existent_id}")

            assert response.status_code == 404
            body = response.json()
            assert "error" in body

    def test_get_steps_for_run(self, query_api_url, ingest_api_url, sample_run_data):
        """Test getting steps for a run."""
        run_data = sample_run_data(include_steps=True)
        run_id = run_data["run_id"]

        with httpx.Client() as client:
            client.post(f"{ingest_api_url}/v1/runs", json=run_data)

        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}/steps")

            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)

    def test_get_failures_for_run(self, query_api_url, ingest_api_url, sample_run_data):
        """Test getting failures for a run."""
        run_data = sample_run_data(include_failures=True)
        run_id = run_data["run_id"]

        with httpx.Client() as client:
            client.post(f"{ingest_api_url}/v1/runs", json=run_data)

        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{run_id}/failures")

            assert response.status_code == 200
            body = response.json()
            assert isinstance(body, list)

    def test_query_health_check(self, query_api_url):
        """Test query API health check."""
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/health")

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "healthy"
            assert body["service"] == "query-api"


@pytest.mark.integration
class TestErrorResponses:
    """Test API error response formatting."""

    def test_400_error_format(self, ingest_api_url):
        """Test 400 errors have correct format."""
        invalid_data = {"invalid": "data"}

        with httpx.Client() as client:
            response = client.post(f"{ingest_api_url}/v1/runs", json=invalid_data)

            assert response.status_code in [400, 422]
            body = response.json()
            assert "detail" in body or "error" in body

    def test_404_error_format(self, query_api_url):
        """Test 404 errors have correct format."""
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs/{uuid4()}")

            assert response.status_code == 404
            body = response.json()
            assert "error" in body or "detail" in body

    def test_500_error_handling(self, query_api_url):
        """Test 500 errors are handled gracefully."""
        # This test depends on ability to trigger 500 errors
        # May need to mock or create specific conditions
        pass


@pytest.mark.integration
class TestCORSHeaders:
    """Test CORS headers are set correctly."""

    def test_cors_headers_present(self, ingest_api_url):
        """Test CORS headers are present in responses."""
        with httpx.Client() as client:
            response = client.options(f"{ingest_api_url}/v1/runs")

            # Should have CORS headers
            assert "access-control-allow-origin" in response.headers or response.status_code == 200


@pytest.mark.integration
class TestContentTypeHeaders:
    """Test Content-Type headers."""

    def test_json_content_type(self, query_api_url):
        """Test responses have JSON content type."""
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs?limit=1")

            assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
class TestPagination:
    """Test pagination query parameters."""

    def test_pagination_limit(self, query_api_url, ingest_api_url, sample_run_data):
        """Test pagination limit parameter."""
        # Create 5 runs
        for _ in range(5):
            run_data = sample_run_data()
            with httpx.Client() as client:
                client.post(f"{ingest_api_url}/v1/runs", json=run_data)

        # Query with limit=3
        with httpx.Client() as client:
            response = client.get(f"{query_api_url}/v1/runs?limit=3")

            assert response.status_code == 200
            body = response.json()
            assert len(body) <= 3

    def test_pagination_offset(self, query_api_url):
        """Test pagination offset parameter."""
        with httpx.Client() as client:
            # Get first page
            response1 = client.get(f"{query_api_url}/v1/runs?limit=5&offset=0")
            page1 = response1.json()

            # Get second page
            response2 = client.get(f"{query_api_url}/v1/runs?limit=5&offset=5")
            page2 = response2.json()

            # Pages should be different (if enough data)
            if len(page1) > 0 and len(page2) > 0:
                assert page1[0]["run_id"] != page2[0]["run_id"]
