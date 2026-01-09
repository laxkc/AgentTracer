"""
Unit Tests: AgentTracer

Tests AgentTracer initialization and configuration.
"""

import pytest

from sdk.agenttrace import AgentTracer


class TestTracerInitialization:
    """Test AgentTracer initialization."""

    def test_create_tracer(self):
        """Test basic tracer creation."""
        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
        )

        assert tracer.agent_id == "test_agent"
        assert tracer.agent_version == "1.0.0"
        assert tracer.environment == "production"  # Default
        assert tracer.api_url == "http://localhost:8000"  # Default

    def test_tracer_with_custom_environment(self):
        """Test tracer with custom environment."""
        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="staging",
        )

        assert tracer.environment == "staging"

    def test_tracer_with_custom_api_url(self):
        """Test tracer with custom API URL."""
        tracer = AgentTracer(
            agent_id="test_agent",
            agent_version="1.0.0",
            api_url="http://custom-api:9000",
        )

        assert tracer.api_url == "http://custom-api:9000"

    def test_tracer_requires_agent_id(self):
        """Test that agent_id is required."""
        with pytest.raises(TypeError):
            AgentTracer(agent_version="1.0.0")

    def test_tracer_requires_agent_version(self):
        """Test that agent_version is required."""
        with pytest.raises(TypeError):
            AgentTracer(agent_id="test_agent")


class TestTracerContextManager:
    """Test tracer as context manager."""

    def test_tracer_as_context_manager(self):
        """Test using tracer with context manager."""
        with AgentTracer(agent_id="test", agent_version="1.0.0") as tracer:
            assert tracer.agent_id == "test"
            assert tracer.agent_version == "1.0.0"

        # Client should be closed after exit
        assert tracer._client.is_closed
