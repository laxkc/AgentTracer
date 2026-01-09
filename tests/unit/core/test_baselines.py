"""
Unit Tests: Baseline Manager

Tests baseline creation, validation, and state management.
Uses mocks to avoid database dependencies.
"""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from server.core.baselines import (
    BaselineManager,
    BaselineNotFoundError,
)


class TestBaselineCreation:
    """Test baseline creation and validation."""

    def test_create_baseline_success(self):
        """Test successful baseline creation."""
        db_mock = Mock()
        db_mock.add = Mock()
        db_mock.flush = Mock()
        db_mock.commit = Mock()

        manager = BaselineManager(db_mock)

        baseline = manager.create_baseline(
            profile_id=uuid4(),
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            baseline_type="version",
            approved_by="admin@example.com",
            description="Initial production baseline",
        )

        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
        assert baseline.baseline_type == "version"
        assert baseline.approved_by == "admin@example.com"

    def test_create_baseline_invalid_type(self):
        """Test that invalid baseline types are rejected."""
        db_mock = Mock()
        manager = BaselineManager(db_mock)

        with pytest.raises(ValueError, match="Invalid baseline_type"):
            manager.create_baseline(
                profile_id=uuid4(),
                agent_id="test_agent",
                agent_version="1.0.0",
                environment="production",
                baseline_type="invalid_type",
            )

    @pytest.mark.parametrize(
        "baseline_type",
        ["version", "time_window", "manual"],
    )
    def test_create_baseline_valid_types(self, baseline_type):
        """Test that all valid baseline types are accepted."""
        db_mock = Mock()
        db_mock.add = Mock()
        db_mock.flush = Mock()
        db_mock.commit = Mock()

        manager = BaselineManager(db_mock)

        baseline = manager.create_baseline(
            profile_id=uuid4(),
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            baseline_type=baseline_type,
        )

        assert baseline.baseline_type == baseline_type


class TestBaselineDescriptionValidation:
    """Test privacy-safe description validation."""

    def test_description_too_long(self):
        """Test that descriptions over 200 chars are rejected."""
        db_mock = Mock()
        manager = BaselineManager(db_mock)

        long_description = "x" * 201

        with pytest.raises(ValueError, match="too long"):
            manager.create_baseline(
                profile_id=uuid4(),
                agent_id="test_agent",
                agent_version="1.0.0",
                environment="production",
                baseline_type="version",
                description=long_description,
            )

    @pytest.mark.parametrize(
        "keyword",
        ["prompt", "response", "reasoning", "thought", "message", "content"],
    )
    def test_description_forbidden_keywords(self, keyword):
        """Test that descriptions with forbidden keywords are rejected."""
        db_mock = Mock()
        manager = BaselineManager(db_mock)

        unsafe_description = f"Baseline contains {keyword} data"

        with pytest.raises(ValueError, match=f"forbidden keyword: '{keyword}'"):
            manager.create_baseline(
                profile_id=uuid4(),
                agent_id="test_agent",
                agent_version="1.0.0",
                environment="production",
                baseline_type="version",
                description=unsafe_description,
            )

    def test_description_safe_content(self):
        """Test that safe descriptions are accepted."""
        db_mock = Mock()
        db_mock.add = Mock()
        db_mock.flush = Mock()
        db_mock.commit = Mock()

        manager = BaselineManager(db_mock)

        safe_description = "Baseline for production deployment v1.0.0"

        baseline = manager.create_baseline(
            profile_id=uuid4(),
            agent_id="test_agent",
            agent_version="1.0.0",
            environment="production",
            baseline_type="version",
            description=safe_description,
        )

        assert baseline.description == safe_description


class TestBaselineStateManagement:
    """Test baseline activation and deactivation."""

    def test_activate_baseline(self):
        """Test baseline activation."""
        db_mock = Mock()
        db_mock.commit = Mock()

        baseline_id = uuid4()
        baseline_mock = Mock()
        baseline_mock.baseline_id = baseline_id
        baseline_mock.agent_id = "test_agent"
        baseline_mock.agent_version = "1.0.0"
        baseline_mock.environment = "production"
        baseline_mock.is_active = False

        manager = BaselineManager(db_mock)
        manager.get_baseline = Mock(return_value=baseline_mock)
        manager.get_active_baseline = Mock(return_value=None)

        result = manager.activate_baseline(baseline_id)

        assert result.is_active is True
        db_mock.commit.assert_called_once()

    def test_deactivate_baseline(self):
        """Test baseline deactivation."""
        db_mock = Mock()
        db_mock.commit = Mock()

        baseline_id = uuid4()
        baseline_mock = Mock()
        baseline_mock.baseline_id = baseline_id
        baseline_mock.is_active = True

        manager = BaselineManager(db_mock)
        manager.get_baseline = Mock(return_value=baseline_mock)

        result = manager.deactivate_baseline(baseline_id)

        assert result.is_active is False
        db_mock.commit.assert_called_once()

    def test_activate_replaces_existing_active(self):
        """Test that activating a baseline deactivates the existing one."""
        db_mock = Mock()
        db_mock.commit = Mock()

        new_baseline_id = uuid4()
        old_baseline_id = uuid4()

        new_baseline = Mock()
        new_baseline.baseline_id = new_baseline_id
        new_baseline.agent_id = "test_agent"
        new_baseline.agent_version = "1.0.0"
        new_baseline.environment = "production"
        new_baseline.is_active = False

        old_baseline = Mock()
        old_baseline.baseline_id = old_baseline_id
        old_baseline.is_active = True

        manager = BaselineManager(db_mock)
        manager.get_baseline = Mock(return_value=new_baseline)
        manager.get_active_baseline = Mock(return_value=old_baseline)

        result = manager.activate_baseline(new_baseline_id)

        assert old_baseline.is_active is False  # Old deactivated
        assert new_baseline.is_active is True  # New activated
        db_mock.commit.assert_called_once()


class TestBaselineApproval:
    """Test baseline approval workflow."""

    def test_approve_baseline(self):
        """Test approving a baseline."""
        db_mock = Mock()
        db_mock.commit = Mock()

        baseline_id = uuid4()
        baseline_mock = Mock()
        baseline_mock.baseline_id = baseline_id
        baseline_mock.approved_by = None
        baseline_mock.approved_at = None

        manager = BaselineManager(db_mock)
        manager.get_baseline = Mock(return_value=baseline_mock)

        result = manager.approve_baseline(baseline_id, "admin@example.com")

        assert result.approved_by == "admin@example.com"
        assert isinstance(result.approved_at, datetime)
        db_mock.commit.assert_called_once()

    def test_approve_nonexistent_baseline(self):
        """Test that approving nonexistent baseline raises error."""
        db_mock = Mock()
        manager = BaselineManager(db_mock)
        manager.get_baseline = Mock(return_value=None)

        with pytest.raises(BaselineNotFoundError):
            manager.approve_baseline(uuid4(), "admin@example.com")


class TestBaselineQueries:
    """Test baseline query methods."""

    def test_get_baseline(self):
        """Test getting baseline by ID."""
        baseline_id = uuid4()
        baseline_mock = Mock()

        db_mock = Mock()
        query_mock = Mock()
        filter_mock = Mock()

        db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = baseline_mock

        manager = BaselineManager(db_mock)
        result = manager.get_baseline(baseline_id)

        assert result == baseline_mock

    def test_get_active_baseline(self):
        """Test getting active baseline for agent."""
        baseline_mock = Mock()
        baseline_mock.is_active = True

        db_mock = Mock()
        query_mock = Mock()
        filter_mock = Mock()

        db_mock.query.return_value = query_mock
        query_mock.filter.return_value = filter_mock
        filter_mock.first.return_value = baseline_mock

        manager = BaselineManager(db_mock)
        result = manager.get_active_baseline("test_agent", "1.0.0", "production")

        assert result == baseline_mock
        assert result.is_active is True
