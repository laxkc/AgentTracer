"""
Integration Tests

Tests requiring external dependencies (database, APIs).
Validates end-to-end workflows and cross-component interactions.

Prerequisites:
- PostgreSQL running: docker-compose up -d postgres
- Database schema applied: alembic upgrade head

Run with: pytest tests/integration -v
"""
