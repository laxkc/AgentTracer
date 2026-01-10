import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from server.config.settings import settings
from server.database import engine


@pytest.fixture(scope="session")
def ingest_api_url() -> str:
    return os.getenv("INGEST_API_URL", f"http://localhost:{settings.INGEST_API_PORT}")


@pytest.fixture(scope="session")
def query_api_url() -> str:
    return os.getenv("QUERY_API_URL", f"http://localhost:{settings.QUERY_API_PORT}")


@pytest.fixture

def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = Session()

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture

def sample_run_data():
    def _factory(include_steps: bool = False, include_failures: bool = False, agent_id: str = "test_agent"):
        started_at = datetime.now(timezone.utc)
        ended_at = started_at + timedelta(seconds=1)

        steps = []
        step_id = None
        if include_steps or include_failures:
            step_id = str(uuid4())
            steps = [
                {
                    "step_id": step_id,
                    "seq": 0,
                    "step_type": "tool",
                    "name": "api_call",
                    "latency_ms": 100,
                    "started_at": started_at.isoformat(),
                    "ended_at": ended_at.isoformat(),
                    "metadata": {},
                }
            ]

        run_data = {
            "run_id": str(uuid4()),
            "agent_id": agent_id,
            "agent_version": "1.0.0",
            "environment": "test",
            "status": "success",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "steps": steps,
            "decisions": [],
            "quality_signals": [],
        }

        if include_failures:
            run_data["status"] = "failure"
            run_data["failure"] = {
                "step_id": step_id,
                "failure_type": "tool",
                "failure_code": "timeout",
                "message": "API timeout",
            }

        return run_data

    return _factory
