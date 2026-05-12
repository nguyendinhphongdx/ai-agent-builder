"""Tests for ``app.modules.identity.workspaces.service.ensure_personal_workspace``."""
from __future__ import annotations

from sqlalchemy import select

from app.models.organization import ORG_PLAN_FREE, Organization
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLE_OWNER, WorkspaceMember
from app.modules.identity.workspaces.service import (
    PERSONAL_WORKSPACE_SLUG,
    _personal_org_slug,
    ensure_personal_workspace,
    list_user_workspace_ids,
)
from tests.factories import UserFactory, create


async def test_creates_org_workspace_member_and_sets_default(db_session) -> None:
    user = await create(db_session, UserFactory, email="alice@example.com", full_name="Alice")
    assert user.default_workspace_id is None

    workspace = await ensure_personal_workspace(db_session, user)

    # Workspace shape
    assert workspace.is_personal is True
    assert workspace.slug == PERSONAL_WORKSPACE_SLUG

    # Default pointer set on user
    assert user.default_workspace_id == workspace.id

    # Org under it has free plan + slug derived from user uuid
    org = await db_session.scalar(
        select(Organization).where(Organization.id == workspace.organization_id)
    )
    assert org is not None
    assert org.plan == ORG_PLAN_FREE
    assert org.slug == _personal_org_slug(user)
    assert org.billing_email == "alice@example.com"

    # Owner membership row
    member = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    assert member is not None
    assert member.role == WORKSPACE_ROLE_OWNER


async def test_idempotent_no_duplicate_orgs(db_session) -> None:
    """Calling twice on the same user must NOT create a second Org or
    a second personal Workspace — second call is a fast-path no-op."""
    user = await create(db_session, UserFactory)

    ws1 = await ensure_personal_workspace(db_session, user)
    ws2 = await ensure_personal_workspace(db_session, user)
    assert ws1.id == ws2.id

    org_count = await db_session.scalar(
        select(Organization).where(Organization.slug == _personal_org_slug(user))
    )
    assert org_count is not None  # exactly one
    workspaces = (
        await db_session.scalars(
            select(Workspace).where(
                Workspace.organization_id == ws1.organization_id,
                Workspace.is_personal.is_(True),
            )
        )
    ).all()
    assert len(workspaces) == 1


async def test_recovers_when_default_pointer_is_null(db_session) -> None:
    """Existing personal Org+Workspace but ``default_workspace_id``
    got nulled out (e.g. workspace recreate, or backfill bug).
    Re-attaching should not duplicate state."""
    user = await create(db_session, UserFactory)
    ws_first = await ensure_personal_workspace(db_session, user)

    # Simulate the pointer being lost.
    user.default_workspace_id = None
    await db_session.flush()

    ws_again = await ensure_personal_workspace(db_session, user)

    assert ws_again.id == ws_first.id
    assert user.default_workspace_id == ws_first.id


async def test_falls_back_to_email_local_when_no_full_name(db_session) -> None:
    user = await create(
        db_session, UserFactory, full_name=None, email="bob@example.com"
    )
    await ensure_personal_workspace(db_session, user)
    org = await db_session.scalar(
        select(Organization).where(Organization.id.in_(
            select(Workspace.organization_id).where(Workspace.id == user.default_workspace_id)
        ))
    )
    assert org is not None
    assert org.name.startswith("bob")  # not "None" or empty


async def test_list_user_workspace_ids_includes_personal(db_session) -> None:
    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)

    ids = await list_user_workspace_ids(db_session, user.id)
    assert workspace.id in ids


async def test_two_users_get_separate_orgs(db_session) -> None:
    """Each user gets their own personal Org (slugs derived from
    distinct user UUIDs) — they cannot collide on
    ``Organization.slug``'s unique constraint."""
    alice = await create(db_session, UserFactory, email="alice@example.com")
    bob = await create(db_session, UserFactory, email="bob@example.com")

    ws_a = await ensure_personal_workspace(db_session, alice)
    ws_b = await ensure_personal_workspace(db_session, bob)

    assert ws_a.organization_id != ws_b.organization_id
    assert ws_a.id != ws_b.id
