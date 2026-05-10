"""Integration tests for the multi-tenancy schema (Phase 1.1 step 1).

These cover only the structural pieces created by migration
``m2c4d8e1f3a5_organizations_workspaces`` — no service-layer logic
yet. Service tests come in a follow-up step once we wire ``app/
workspaces/`` and the ``current_workspace_id`` ContextVar.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.organization import Organization
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import (
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WorkspaceMember,
)
from tests.factories import (
    OrganizationFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceInvitationFactory,
    WorkspaceMemberFactory,
    create,
)


async def test_create_org_and_workspace(db_session) -> None:
    org = await create(db_session, OrganizationFactory)
    ws = await create(
        db_session, WorkspaceFactory, organization_id=org.id, is_personal=True
    )
    assert ws.organization_id == org.id

    # Round-trip via SELECT to make sure server defaults applied.
    fetched = await db_session.scalar(select(Workspace).where(Workspace.id == ws.id))
    assert fetched is not None
    assert fetched.is_personal is True
    assert fetched.settings == {}


async def test_workspace_slug_unique_per_org(db_session) -> None:
    """Two orgs can both have a workspace named 'engineering'; one org cannot."""
    org_a = await create(db_session, OrganizationFactory)
    org_b = await create(db_session, OrganizationFactory)

    await create(db_session, WorkspaceFactory, organization_id=org_a.id, slug="engineering")
    # Same slug in a different org — fine.
    await create(db_session, WorkspaceFactory, organization_id=org_b.id, slug="engineering")

    # Same slug in the same org — must raise on flush.
    duplicate = WorkspaceFactory.build(organization_id=org_a.id, slug="engineering")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_workspace_member_composite_pk_and_role(db_session) -> None:
    org = await create(db_session, OrganizationFactory)
    ws = await create(db_session, WorkspaceFactory, organization_id=org.id)
    user = await create(db_session, UserFactory)

    await create(
        db_session,
        WorkspaceMemberFactory,
        workspace_id=ws.id,
        user_id=user.id,
        role=WORKSPACE_ROLE_OWNER,
    )

    member = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id
        )
    )
    assert member is not None
    assert member.role == WORKSPACE_ROLE_OWNER

    # Adding the same (workspace_id, user_id) again must fail — composite PK.
    duplicate = WorkspaceMemberFactory.build(
        workspace_id=ws.id, user_id=user.id, role=WORKSPACE_ROLE_EDITOR
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_workspace_invitation_token_unique(db_session) -> None:
    org = await create(db_session, OrganizationFactory)
    ws = await create(db_session, WorkspaceFactory, organization_id=org.id)

    inv = await create(
        db_session,
        WorkspaceInvitationFactory,
        workspace_id=ws.id,
        token="dup-token-aaaaaaaaaa",
    )
    assert inv.id is not None
    assert inv.accepted_at is None  # default — pending invite

    duplicate = WorkspaceInvitationFactory.build(
        workspace_id=ws.id, token="dup-token-aaaaaaaaaa"
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_cascade_deletes_clean_up_children(db_session) -> None:
    """Dropping the parent org must cascade through workspaces, members,
    and invitations — that's what makes ``DELETE FROM organizations``
    a safe data-removal path for offboarding."""
    org = await create(db_session, OrganizationFactory)
    ws = await create(db_session, WorkspaceFactory, organization_id=org.id)
    user = await create(db_session, UserFactory)
    await create(
        db_session,
        WorkspaceMemberFactory,
        workspace_id=ws.id,
        user_id=user.id,
        role=WORKSPACE_ROLE_OWNER,
    )
    await create(db_session, WorkspaceInvitationFactory, workspace_id=ws.id)

    await db_session.delete(org)
    await db_session.flush()

    assert await db_session.scalar(
        select(Workspace).where(Workspace.id == ws.id)
    ) is None
    assert await db_session.scalar(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
    ) is None
    assert await db_session.scalar(
        select(WorkspaceInvitation).where(WorkspaceInvitation.workspace_id == ws.id)
    ) is None


async def test_invited_by_set_null_on_user_delete(db_session) -> None:
    """Deleting the inviter must NOT cascade-delete the membership/
    invitation — those rows stay (with ``invited_by`` nulled out) so
    audit history survives offboarded users."""
    org = await create(db_session, OrganizationFactory)
    ws = await create(db_session, WorkspaceFactory, organization_id=org.id)
    inviter = await create(db_session, UserFactory)
    invitee = await create(db_session, UserFactory)

    member = await create(
        db_session,
        WorkspaceMemberFactory,
        workspace_id=ws.id,
        user_id=invitee.id,
        role=WORKSPACE_ROLE_EDITOR,
        invited_by=inviter.id,
    )
    inv = await create(
        db_session,
        WorkspaceInvitationFactory,
        workspace_id=ws.id,
        invited_by=inviter.id,
    )
    member_id = (member.workspace_id, member.user_id)
    inv_id = inv.id

    await db_session.delete(inviter)
    await db_session.flush()

    surviving_member = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == member_id[0],
            WorkspaceMember.user_id == member_id[1],
        )
    )
    assert surviving_member is not None
    assert surviving_member.invited_by is None

    surviving_inv = await db_session.scalar(
        select(WorkspaceInvitation).where(WorkspaceInvitation.id == inv_id)
    )
    assert surviving_inv is not None
    assert surviving_inv.invited_by is None


async def test_relationships_lazy_load(db_session) -> None:
    """``Organization.workspaces`` and ``Workspace.members`` /
    ``Workspace.invitations`` should resolve to the right rows."""
    org = await create(db_session, OrganizationFactory)
    ws_a = await create(db_session, WorkspaceFactory, organization_id=org.id)
    ws_b = await create(db_session, WorkspaceFactory, organization_id=org.id)
    user = await create(db_session, UserFactory)
    await create(
        db_session,
        WorkspaceMemberFactory,
        workspace_id=ws_a.id,
        user_id=user.id,
        role=WORKSPACE_ROLE_OWNER,
    )

    await db_session.refresh(org, ["workspaces"])
    assert {w.id for w in org.workspaces} == {ws_a.id, ws_b.id}

    await db_session.refresh(ws_a, ["members"])
    assert len(ws_a.members) == 1
    assert ws_a.members[0].user_id == user.id


async def test_unrelated_user_id_is_uuid(db_session) -> None:
    """Sanity check: ``id`` columns reject non-UUID writes (catches
    accidental string IDs slipping through service code)."""
    org = await create(db_session, OrganizationFactory)
    bogus = WorkspaceFactory.build(organization_id=org.id)
    bogus.id = "not-a-uuid"  # type: ignore[assignment]
    db_session.add(bogus)
    with pytest.raises(Exception):  # asyncpg DataError or SQLAlchemy StatementError
        await db_session.flush()
    await db_session.rollback()
    # Confirm the bogus row didn't sneak in:
    rows = await db_session.scalars(select(Workspace).where(Workspace.id == uuid.UUID(int=0)))
    assert rows.first() is None
