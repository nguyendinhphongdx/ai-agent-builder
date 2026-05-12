"""Integration tests for workspace CRUD + member + invitation service.

Block-1 service-layer coverage. HTTP-level routing tests can layer on
top later via a FastAPI test client; for now we exercise the same
functions the router calls, since that's where the business rules
(last-owner guards, idempotent accept, role validation) live.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
)
from app.modules.identity.workspaces import service
from app.modules.identity.workspaces.permissions import role_at_least
from tests.factories import (
    OrganizationFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceInvitationFactory,
    WorkspaceMemberFactory,
    create,
)

# ─── Workspace CRUD ────────────────────────────────────────────────


async def test_create_team_workspace_creates_org_and_owner(db_session) -> None:
    """Without an existing org, we spin up a fresh one + insert the
    creator as owner of the new workspace."""
    user = await create(db_session, UserFactory)

    ws = await service.create_team_workspace(
        db_session, creator=user, name="Engineering"
    )

    assert ws.name == "Engineering"
    assert ws.is_personal is False
    assert ws.organization_id is not None

    member = await service.get_member(db_session, ws.id, user.id)
    assert member is not None
    assert member.role == WORKSPACE_ROLE_OWNER


async def test_create_team_workspace_attaches_to_existing_org(db_session) -> None:
    """When ``organization_id`` is supplied, no new org is created."""
    user = await create(db_session, UserFactory)
    org = await create(db_session, OrganizationFactory)

    ws = await service.create_team_workspace(
        db_session, creator=user, name="Design", organization_id=org.id
    )
    assert ws.organization_id == org.id


async def test_create_team_workspace_unique_slug_per_org(db_session) -> None:
    """Two team workspaces with same name in same org get unique slugs
    via the retry-with-suffix path — no IntegrityError leaks out."""
    user = await create(db_session, UserFactory)
    org = await create(db_session, OrganizationFactory)

    ws1 = await service.create_team_workspace(
        db_session, creator=user, name="Team", organization_id=org.id
    )
    ws2 = await service.create_team_workspace(
        db_session, creator=user, name="Team", organization_id=org.id
    )
    assert ws1.slug != ws2.slug


async def test_list_user_workspaces_returns_role(db_session) -> None:
    """List includes the caller's role per workspace so the UI can
    gate affordances without a second round-trip."""
    user = await create(db_session, UserFactory)
    other = await create(db_session, UserFactory)
    org = await create(db_session, OrganizationFactory)
    ws_a = await create(db_session, WorkspaceFactory, organization_id=org.id)
    ws_b = await create(db_session, WorkspaceFactory, organization_id=org.id)
    # User has 2 memberships at different roles. Other user has 1 — should not surface.
    await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws_a.id, user_id=user.id, role=WORKSPACE_ROLE_OWNER,
    )
    await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws_b.id, user_id=user.id, role=WORKSPACE_ROLE_VIEWER,
    )
    await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws_b.id, user_id=other.id, role=WORKSPACE_ROLE_OWNER,
    )

    rows = await service.list_user_workspaces(db_session, user.id)
    seen = {ws.id: role for ws, role in rows}
    assert seen == {ws_a.id: WORKSPACE_ROLE_OWNER, ws_b.id: WORKSPACE_ROLE_VIEWER}


async def test_update_workspace_patches_fields(db_session) -> None:
    user = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Old")

    updated = await service.update_workspace(
        db_session, ws, name="New", settings={"theme": "dark"}
    )
    assert updated.name == "New"
    assert updated.settings == {"theme": "dark"}


async def test_delete_workspace_refuses_personal(db_session) -> None:
    """Personal workspaces are tied to user accounts — deleting them
    via this API would orphan the user. Service must refuse."""
    user = await create(db_session, UserFactory)
    personal = await service.ensure_personal_workspace(db_session, user)

    with pytest.raises(ValueError, match="personal"):
        await service.delete_workspace(db_session, personal)


async def test_delete_workspace_removes_non_personal(db_session) -> None:
    user = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Tmp")
    ws_id = ws.id

    await service.delete_workspace(db_session, ws)
    row = await service.get_workspace_with_member(db_session, ws_id, user.id)
    assert row is None


# ─── Members ───────────────────────────────────────────────────────


async def test_update_member_role_blocks_last_owner_demotion(db_session) -> None:
    """Every workspace needs at least one owner so admin ops stay
    reachable. Service refuses to demote when only one owner remains."""
    user = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Solo")
    owner_member = await service.get_member(db_session, ws.id, user.id)
    assert owner_member is not None

    with pytest.raises(ValueError, match="last owner"):
        await service.update_member_role(db_session, owner_member, WORKSPACE_ROLE_ADMIN)


async def test_update_member_role_promotes_to_owner(db_session) -> None:
    user = await create(db_session, UserFactory)
    other = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Team")
    new_member = await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws.id, user_id=other.id, role=WORKSPACE_ROLE_EDITOR,
    )
    await service.update_member_role(db_session, new_member, WORKSPACE_ROLE_OWNER)
    assert new_member.role == WORKSPACE_ROLE_OWNER


async def test_remove_member_blocks_last_owner(db_session) -> None:
    """Same invariant as demotion — can't remove the only owner."""
    user = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Solo")
    member = await service.get_member(db_session, ws.id, user.id)
    assert member is not None

    with pytest.raises(ValueError, match="last owner"):
        await service.remove_member(db_session, member)


async def test_remove_member_allows_leave_when_other_owner_present(db_session) -> None:
    """Two owners → either can leave."""
    user = await create(db_session, UserFactory)
    other = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Team")
    other_owner = await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws.id, user_id=other.id, role=WORKSPACE_ROLE_OWNER,
    )
    original = await service.get_member(db_session, ws.id, user.id)
    assert original is not None

    # First owner leaves — other_owner is still there, so allowed.
    await service.remove_member(db_session, original)
    assert await service.get_member(db_session, ws.id, user.id) is None
    # Second owner would now be the last — must refuse.
    with pytest.raises(ValueError, match="last owner"):
        await service.remove_member(db_session, other_owner)


# ─── Invitations ───────────────────────────────────────────────────


async def test_create_invitation_rejects_owner_role(db_session) -> None:
    """Owner is granted only via promotion. Invites at owner level
    would mean instant takeover — refuse at the service layer."""
    user = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=user, name="Team")

    with pytest.raises(ValueError, match="role"):
        await service.create_invitation(
            db_session,
            workspace_id=ws.id,
            email="new@example.com",
            role=WORKSPACE_ROLE_OWNER,
            invited_by=user.id,
        )


async def test_create_and_accept_invitation_flow(db_session) -> None:
    """Happy path: admin invites → invitee accepts → member row exists,
    invite stamped accepted_at."""
    admin_user = await create(db_session, UserFactory)
    invitee = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=admin_user, name="Team")

    inv = await service.create_invitation(
        db_session,
        workspace_id=ws.id,
        email=invitee.email,
        role=WORKSPACE_ROLE_EDITOR,
        invited_by=admin_user.id,
    )
    assert inv.token
    assert inv.accepted_at is None

    fetched = await service.get_invitation_by_token(db_session, inv.token)
    assert fetched is not None

    member = await service.accept_invitation(db_session, fetched, invitee)
    assert member.role == WORKSPACE_ROLE_EDITOR
    assert member.user_id == invitee.id
    assert fetched.accepted_at is not None


async def test_get_invitation_by_token_rejects_expired(db_session) -> None:
    """Expired tokens never resolve. Caller doesn't need to
    distinguish expired from unknown — both surface as 404."""
    ws = await create(
        db_session, WorkspaceFactory,
        organization_id=(await create(db_session, OrganizationFactory)).id,
    )
    expired = await create(
        db_session, WorkspaceInvitationFactory,
        workspace_id=ws.id,
        token="expired-token",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert await service.get_invitation_by_token(db_session, expired.token) is None


async def test_get_invitation_by_token_rejects_already_accepted(db_session) -> None:
    """Re-using an accepted token is a replay — refuse."""
    ws = await create(
        db_session, WorkspaceFactory,
        organization_id=(await create(db_session, OrganizationFactory)).id,
    )
    used = await create(
        db_session, WorkspaceInvitationFactory,
        workspace_id=ws.id,
        token="used-token",
        accepted_at=datetime.now(timezone.utc),
    )
    assert await service.get_invitation_by_token(db_session, used.token) is None


async def test_accept_invitation_is_idempotent_for_existing_member(db_session) -> None:
    """If the invitee is already a member, accepting just stamps the
    invite. Doesn't error or upgrade their role."""
    admin_user = await create(db_session, UserFactory)
    invitee = await create(db_session, UserFactory)
    ws = await service.create_team_workspace(db_session, creator=admin_user, name="Team")
    # Invitee already an editor.
    await create(
        db_session, WorkspaceMemberFactory,
        workspace_id=ws.id, user_id=invitee.id, role=WORKSPACE_ROLE_EDITOR,
    )
    inv = await service.create_invitation(
        db_session,
        workspace_id=ws.id,
        email=invitee.email,
        role=WORKSPACE_ROLE_ADMIN,  # would-be upgrade if invites granted role
        invited_by=admin_user.id,
    )
    member = await service.accept_invitation(db_session, inv, invitee)
    assert member.role == WORKSPACE_ROLE_EDITOR  # unchanged
    assert inv.accepted_at is not None


# ─── Permission helpers ────────────────────────────────────────────


def test_role_at_least_ordering() -> None:
    assert role_at_least(WORKSPACE_ROLE_OWNER, WORKSPACE_ROLE_VIEWER)
    assert role_at_least(WORKSPACE_ROLE_ADMIN, WORKSPACE_ROLE_EDITOR)
    assert role_at_least(WORKSPACE_ROLE_VIEWER, WORKSPACE_ROLE_VIEWER)
    assert not role_at_least(WORKSPACE_ROLE_VIEWER, WORKSPACE_ROLE_ADMIN)
    assert not role_at_least(WORKSPACE_ROLE_EDITOR, WORKSPACE_ROLE_OWNER)
    # Unknown role falls below everything.
    assert not role_at_least("unknown", WORKSPACE_ROLE_VIEWER)
