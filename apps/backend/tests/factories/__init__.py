"""Test data factories.

factory-boy gives us Sequences + Faker + composition for fixture data
without the boilerplate of hand-rolling ``User(email="...", name="...")``
in every test. We use the plain ``factory.Factory`` (not
``SQLAlchemyModelFactory``) because the rest of the app is async and
factory-boy doesn't ship an async persistence backend — call
``UserFactory.build()`` to get a detached model instance, then add
it to ``db_session`` yourself.

Convenience helper:

    user = await create(db_session, UserFactory, email="x@y.z")
"""
from __future__ import annotations

from typing import TypeVar

import factory
from sqlalchemy.ext.asyncio import AsyncSession

from .users import UserFactory
from .workspaces import (
    OrganizationFactory,
    WorkspaceFactory,
    WorkspaceInvitationFactory,
    WorkspaceMemberFactory,
)

__all__ = [
    "UserFactory",
    "OrganizationFactory",
    "WorkspaceFactory",
    "WorkspaceMemberFactory",
    "WorkspaceInvitationFactory",
    "create",
]


T = TypeVar("T")


async def create(session: AsyncSession, factory_cls: type[factory.Factory], **overrides) -> T:
    """Build a model from ``factory_cls``, add to ``session``, flush.

    Returns the persisted instance with PK populated. Test still owns
    the transaction — call ``await session.commit()`` (or rely on the
    rollback fixture) to control durability.
    """
    instance = factory_cls.build(**overrides)
    session.add(instance)
    await session.flush()
    return instance
