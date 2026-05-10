"""Smoke test for the integration-test harness.

Validates that the testcontainer + alembic + db_session pipeline works
end-to-end: container is up, migrations applied, async session can
read/write, transaction rolls back between tests.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from tests.factories import UserFactory, create


async def test_user_create_and_query(db_session) -> None:
    """Create a user, read it back. Proves the migration applied and
    the async session is wired."""
    user = await create(db_session, UserFactory, email="smoke@example.com")
    assert user.id is not None

    fetched = await db_session.scalar(select(User).where(User.email == "smoke@example.com"))
    assert fetched is not None
    assert fetched.id == user.id


async def test_rollback_isolates_tests(db_session) -> None:
    """The user inserted by the previous test must NOT leak into this
    one — the per-test transaction-rollback fixture handles that."""
    leaked = await db_session.scalar(select(User).where(User.email == "smoke@example.com"))
    assert leaked is None, "Previous test's row leaked — rollback isolation is broken"
