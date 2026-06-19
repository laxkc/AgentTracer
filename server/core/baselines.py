"""
Baseline Manager

This module manages behavioral baselines for drift detection.
Baselines are immutable snapshots of expected agent behavior.

Constraints:
- Baselines are immutable after creation (except activation status)
- Only one active baseline per (agent_id, agent_version, environment)
- Baselines must be privacy-safe (no prompts, responses, reasoning)
- Purely observational - no behavior modification
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.models.database import BehaviorBaselineDB


class BaselineExistsError(Exception):
    """Raised when trying to create a baseline that already exists."""

    pass


class BaselineNotFoundError(Exception):
    """Raised when baseline is not found."""

    pass


class ActiveBaselineConflictError(Exception):
    """Raised when trying to activate a baseline conflicts with existing active baseline."""

    pass


class BaselineManager:
    """
    Manages behavioral baselines.

    Purpose:
    - Create baselines from behavior profiles
    - Approve baselines (human-in-the-loop)
    - Activate/deactivate baselines
    - Enforce immutability and unique constraints

    Baselines are the foundation for drift detection.
    """

    def __init__(self, db: Session):
        """
        Initialize baseline manager.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_baseline(
        self,
        profile_id: UUID,
        agent_id: str,
        agent_version: str,
        environment: str,
        baseline_type: str,
        approved_by: str | None = None,
        description: str | None = None,
        auto_activate: bool = False,
    ) -> BehaviorBaselineDB:
        """
        Create an immutable baseline from a profile.

        Args:
            profile_id: UUID of behavior profile
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment
            baseline_type: Type of baseline ('version', 'time_window', 'manual')
            approved_by: User ID or email who approved (optional)
            description: Privacy-safe description (max 200 chars, optional)
            auto_activate: Automatically activate this baseline (default: False)

        Returns:
            Created BehaviorBaselineDB object

        Raises:
            ValueError: If description contains forbidden keywords
            BaselineExistsError: If baseline already exists
        """
        # Validate description is privacy-safe (database trigger also validates)
        self._validate_description(description)

        # Validate baseline type
        valid_types = ["version", "time_window", "manual"]
        if baseline_type not in valid_types:
            raise ValueError(
                f"Invalid baseline_type: {baseline_type}. Must be one of {valid_types}"
            )

        # Create baseline
        baseline = BehaviorBaselineDB(
            profile_id=profile_id,
            agent_id=agent_id,
            agent_version=agent_version,
            environment=environment,
            baseline_type=baseline_type,
            approved_by=approved_by,
            approved_at=datetime.utcnow() if approved_by else None,
            description=description,
            is_active=False,  # Always create as inactive, then activate if requested
        )

        try:
            self.db.add(baseline)
            self.db.flush()

            # Auto-activate if requested
            if auto_activate:
                self.activate_baseline(baseline.baseline_id)

            self.db.commit()
            return baseline

        except IntegrityError as e:
            self.db.rollback()
            if "unique_profile" in str(e).lower():
                raise BaselineExistsError(
                    f"Baseline already exists for profile {profile_id}"
                ) from e
            raise

    def approve_baseline(
        self,
        baseline_id: UUID,
        approved_by: str,
    ) -> BehaviorBaselineDB:
        """
        Mark baseline as approved by human.

        Args:
            baseline_id: UUID of baseline to approve
            approved_by: User ID or email who approved

        Returns:
            Updated BehaviorBaselineDB object

        Raises:
            BaselineNotFoundError: If baseline not found
        """
        baseline = self.get_baseline(baseline_id)

        if not baseline:
            raise BaselineNotFoundError(f"Baseline {baseline_id} not found")

        # Update approval fields (allowed by trigger)
        baseline.approved_by = approved_by
        baseline.approved_at = datetime.utcnow()

        self.db.commit()
        return baseline

    def activate_baseline(self, baseline_id: UUID) -> BehaviorBaselineDB:
        """
        Set baseline as active for drift comparison.

        Deactivates any existing active baseline for same (agent, version, env).
        Database unique constraint enforces only one active baseline.

        Args:
            baseline_id: UUID of baseline to activate

        Returns:
            Activated BehaviorBaselineDB object

        Raises:
            BaselineNotFoundError: If baseline not found
        """
        baseline = self.get_baseline(baseline_id)

        if not baseline:
            raise BaselineNotFoundError(f"Baseline {baseline_id} not found")

        # Deactivate existing active baseline for same agent/version/env
        existing_active = self.get_active_baseline(
            baseline.agent_id,
            baseline.agent_version,
            baseline.environment,
        )

        if existing_active and existing_active.baseline_id != baseline_id:
            existing_active.is_active = False

        # Activate new baseline
        baseline.is_active = True

        self.db.commit()
        return baseline

    def deactivate_baseline(self, baseline_id: UUID) -> BehaviorBaselineDB:
        """
        Deactivate baseline (stop using for drift detection).

        Does not delete - baselines are immutable.

        Args:
            baseline_id: UUID of baseline to deactivate

        Returns:
            Deactivated BehaviorBaselineDB object

        Raises:
            BaselineNotFoundError: If baseline not found
        """
        baseline = self.get_baseline(baseline_id)

        if not baseline:
            raise BaselineNotFoundError(f"Baseline {baseline_id} not found")

        baseline.is_active = False

        self.db.commit()
        return baseline

    def get_baseline(self, baseline_id: UUID) -> BehaviorBaselineDB | None:
        """
        Get baseline by ID.

        Args:
            baseline_id: UUID of baseline

        Returns:
            BehaviorBaselineDB object or None if not found
        """
        return (
            self.db.query(BehaviorBaselineDB)
            .filter(BehaviorBaselineDB.baseline_id == baseline_id)
            .first()
        )

    def get_active_baseline(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
    ) -> BehaviorBaselineDB | None:
        """
        Get currently active baseline for drift comparison.

        Args:
            agent_id: Agent identifier
            agent_version: Agent version
            environment: Deployment environment

        Returns:
            Active BehaviorBaselineDB object or None if no active baseline
        """
        return (
            self.db.query(BehaviorBaselineDB)
            .filter(
                and_(
                    BehaviorBaselineDB.agent_id == agent_id,
                    BehaviorBaselineDB.agent_version == agent_version,
                    BehaviorBaselineDB.environment == environment,
                    BehaviorBaselineDB.is_active,
                )
            )
            .first()
        )

    def list_baselines(
        self,
        agent_id: str | None = None,
        agent_version: str | None = None,
        environment: str | None = None,
        baseline_type: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BehaviorBaselineDB]:
        """
        List baselines with optional filtering.

        Args:
            agent_id: Filter by agent ID (optional)
            agent_version: Filter by version (optional)
            environment: Filter by environment (optional)
            baseline_type: Filter by type (optional)
            is_active: Filter by active status (optional)
            limit: Maximum results (default: 100)
            offset: Pagination offset (default: 0)

        Returns:
            List of BehaviorBaselineDB objects
        """
        query = self.db.query(BehaviorBaselineDB)

        # Apply filters
        if agent_id:
            query = query.filter(BehaviorBaselineDB.agent_id == agent_id)
        if agent_version:
            query = query.filter(BehaviorBaselineDB.agent_version == agent_version)
        if environment:
            query = query.filter(BehaviorBaselineDB.environment == environment)
        if baseline_type:
            query = query.filter(BehaviorBaselineDB.baseline_type == baseline_type)
        if is_active is not None:
            query = query.filter(BehaviorBaselineDB.is_active == is_active)

        # Order by created_at descending
        query = query.order_by(BehaviorBaselineDB.created_at.desc())

        # Pagination
        query = query.limit(limit).offset(offset)

        return query.all()

    def _validate_description(self, description: str | None) -> None:
        """
        Validate baseline description is privacy-safe.

        Args:
            description: Description text to validate

        Raises:
            ValueError: If description contains forbidden keywords or too long
        """
        if description is None:
            return

        # Forbidden keywords (privacy-sensitive terms)
        forbidden_keywords = [
            "prompt",
            "response",
            "reasoning",
            "thought",
            "message",
            "content",
            "text",
            "output",
            "input",
            "chain_of_thought",
            "explanation",
            "rationale",
        ]

        description_lower = description.lower()
        for keyword in forbidden_keywords:
            if keyword in description_lower:
                raise ValueError(f"Baseline description contains forbidden keyword: '{keyword}'")

        # Length check
        if len(description) > 200:
            raise ValueError("Baseline description too long (max 200 characters)")


# Convenience functions


def create_baseline_from_profile(
    db: Session,
    profile_id: UUID,
    agent_id: str,
    agent_version: str,
    environment: str,
    baseline_type: str,
    approved_by: str | None = None,
    description: str | None = None,
    auto_activate: bool = False,
) -> BehaviorBaselineDB:
    """
    Convenience function to create a baseline from a profile.

    Args:
        db: Database session
        profile_id: UUID of behavior profile
        agent_id: Agent identifier
        agent_version: Agent version
        environment: Deployment environment
        baseline_type: Type of baseline ('version', 'time_window', 'manual')
        approved_by: User ID or email who approved (optional)
        description: Privacy-safe description (optional)
        auto_activate: Automatically activate this baseline (default: False)

    Returns:
        Created BehaviorBaselineDB object
    """
    manager = BaselineManager(db)
    return manager.create_baseline(
        profile_id=profile_id,
        agent_id=agent_id,
        agent_version=agent_version,
        environment=environment,
        baseline_type=baseline_type,
        approved_by=approved_by,
        description=description,
        auto_activate=auto_activate,
    )


def get_active_baseline_for_agent(
    db: Session,
    agent_id: str,
    agent_version: str,
    environment: str,
) -> BehaviorBaselineDB | None:
    """
    Convenience function to get active baseline for an agent.

    Args:
        db: Database session
        agent_id: Agent identifier
        agent_version: Agent version
        environment: Deployment environment

    Returns:
        Active BehaviorBaselineDB object or None
    """
    manager = BaselineManager(db)
    return manager.get_active_baseline(agent_id, agent_version, environment)
