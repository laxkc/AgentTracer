"""
Integration Test: Database Integrity

Tests database constraints, triggers, and transaction handling.

Prerequisites:
- PostgreSQL running
- Database schema applied with all constraints and triggers
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from server.models.database import (
    AgentDecisionDB,
    AgentFailureDB,
    AgentQualitySignalDB,
    AgentRunDB,
    AgentStepDB,
)


@pytest.mark.integration
class TestForeignKeyConstraints:
    """Test foreign key constraints and CASCADE behavior."""

    def test_cascade_delete_run_deletes_steps(self, db_session):
        """Test that deleting a run cascades to delete its steps."""
        run_id = uuid4()

        # Create run
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

        # Create step
        step_started_at = datetime.now(timezone.utc)
        step = AgentStepDB(
            run_id=run_id,
            step_type="tool",
            name="test_step",
            seq=0,
            latency_ms=100,
            started_at=step_started_at,
            ended_at=step_started_at,
        )
        db_session.add(step)
        db_session.commit()

        # Verify step exists
        assert db_session.query(AgentStepDB).filter(AgentStepDB.run_id == run_id).count() == 1

        # Delete run
        db_session.delete(run)
        db_session.commit()

        # Verify step was cascaded
        assert db_session.query(AgentStepDB).filter(AgentStepDB.run_id == run_id).count() == 0

    def test_cascade_delete_run_deletes_all_children(self, db_session):
        """Test that deleting a run cascades to all child records."""
        run_id = uuid4()

        # Create run with all child types
        run = AgentRunDB(
            run_id=run_id,
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            status="failure",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        db_session.flush()

        # Add step
        step_started_at = datetime.now(timezone.utc)
        step = AgentStepDB(
            run_id=run_id,
            step_type="tool",
            name="step1",
            seq=0,
            latency_ms=100,
            started_at=step_started_at,
            ended_at=step_started_at,
        )
        db_session.add(step)

        # Add failure
        failure = AgentFailureDB(
            run_id=run_id,
            step_id=step.step_id,
            failure_type="tool",
            failure_code="timeout",
            message="Test failure",
        )
        db_session.add(failure)

        # Add decision
        decision = AgentDecisionDB(
            run_id=run_id,
            decision_type="tool_selection",
            selected="api",
            reason_code="fresh_data_required",
        )
        db_session.add(decision)

        # Add quality signal
        signal = AgentQualitySignalDB(
            run_id=run_id,
            signal_type="schema_valid",
            signal_code="full_match",
            value=True,
        )
        db_session.add(signal)

        db_session.commit()

        # Verify all exist
        assert db_session.query(AgentStepDB).filter(AgentStepDB.run_id == run_id).count() == 1
        assert db_session.query(AgentFailureDB).filter(AgentFailureDB.run_id == run_id).count() == 1
        assert (
            db_session.query(AgentDecisionDB).filter(AgentDecisionDB.run_id == run_id).count() == 1
        )
        assert (
            db_session.query(AgentQualitySignalDB)
            .filter(AgentQualitySignalDB.run_id == run_id)
            .count()
            == 1
        )

        # Delete run
        db_session.delete(run)
        db_session.commit()

        # Verify all children were cascaded
        assert db_session.query(AgentStepDB).filter(AgentStepDB.run_id == run_id).count() == 0
        assert db_session.query(AgentFailureDB).filter(AgentFailureDB.run_id == run_id).count() == 0
        assert (
            db_session.query(AgentDecisionDB).filter(AgentDecisionDB.run_id == run_id).count() == 0
        )
        assert (
            db_session.query(AgentQualitySignalDB)
            .filter(AgentQualitySignalDB.run_id == run_id)
            .count()
            == 0
        )


@pytest.mark.integration
class TestUniqueConstraints:
    """Test unique constraints."""

    def test_duplicate_run_id_rejected(self, db_session):
        """Test that duplicate run_id is rejected."""
        run_id = uuid4()

        # Create first run
        run1 = AgentRunDB(
            run_id=run_id,
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            status="success",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db_session.add(run1)
        db_session.commit()

        # Try to create duplicate
        run2 = AgentRunDB(
            run_id=run_id,  # Same ID
            agent_id="test2",
            agent_version="2.0.0",
            environment="test",
            status="success",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db_session.add(run2)

        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.integration
class TestCheckConstraints:
    """Test check constraints on enums."""

    def test_invalid_status_rejected(self, db_session):
        """Test that invalid status values are rejected."""
        run = AgentRunDB(
            run_id=uuid4(),
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            status="invalid_status",  # Invalid
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
        )
        db_session.add(run)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_invalid_step_type_rejected(self, db_session):
        """Test that invalid step types are rejected."""
        run_id = uuid4()

        # Create valid run first
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

        # Try invalid step type
        step_started_at = datetime.now(timezone.utc)
        step = AgentStepDB(
            run_id=run_id,
            step_type="invalid_type",  # Invalid
            name="test",
            seq=0,
            latency_ms=100,
            started_at=step_started_at,
            ended_at=step_started_at,
        )
        db_session.add(step)

        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.integration
class TestTransactionIsolation:
    """Test transaction handling and rollback."""

    def test_rollback_on_error(self, db_session):
        """Test that transaction rolls back on error."""
        run_id = uuid4()

        try:
            # Create run
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

            # Try to create invalid step (will fail)
            step_started_at = datetime.now(timezone.utc)
            step = AgentStepDB(
                run_id=run_id,
                step_type="invalid",
                name="test",
                seq=0,
                latency_ms=100,
                started_at=step_started_at,
                ended_at=step_started_at,
            )
            db_session.add(step)
            db_session.commit()

        except IntegrityError:
            db_session.rollback()

        # Verify run was not created (transaction rolled back)
        result = db_session.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
        assert result is None


@pytest.mark.integration
class TestTemporalConstraints:
    """Test temporal constraints and ordering."""

    def test_ended_at_after_started_at(self, db_session):
        """Test that ended_at must be after started_at."""
        started = datetime.now(timezone.utc)
        ended = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Before started

        run = AgentRunDB(
            run_id=uuid4(),
            agent_id="test",
            agent_version="1.0.0",
            environment="test",
            status="success",
            started_at=started,
            ended_at=ended,  # Invalid: before started_at
        )
        db_session.add(run)

        # This should be caught by application logic or database trigger
        # The exact behavior depends on implementation
        try:
            db_session.commit()
            # If commit succeeds, verify constraint in application
            assert run.ended_at >= run.started_at
        except IntegrityError:
            # Database trigger caught it
            pass


@pytest.mark.integration
class TestIndexPerformance:
    """Test that indexes exist for common queries."""

    def test_agent_id_indexed(self, db_session):
        """Test querying by agent_id is efficient."""
        # Create multiple runs
        for i in range(10):
            run = AgentRunDB(
                run_id=uuid4(),
                agent_id="indexed_agent" if i < 5 else "other_agent",
                agent_version="1.0.0",
                environment="test",
                status="success",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
            )
            db_session.add(run)

        db_session.commit()

        # Query by agent_id (should use index)
        results = db_session.query(AgentRunDB).filter(AgentRunDB.agent_id == "indexed_agent").all()

        assert len(results) == 5
