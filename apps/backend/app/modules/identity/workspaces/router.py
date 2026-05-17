"""Workspace + membership + invitation HTTP endpoints.

All endpoints are cookie/Bearer authenticated. Workspace-scoped routes
mount :func:`require_workspace_role` to enforce the caller is a member
with sufficient role.

Role gating per endpoint family:
  - List/get workspace, members, invitations → viewer+
  - Patch workspace, manage members, manage invitations → admin+
  - Delete workspace → owner only
  - Accept invitation → any authenticated user (token is the auth)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models.organization_member import (
    ORG_ROLE_ADMIN,
    ORG_ROLE_OWNER,
    OrganizationMember,
)
from app.models.user import User
from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
    WorkspaceMember,
)
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.workspaces import service
from app.modules.identity.workspaces.permissions import require_workspace_role, role_at_least
from app.modules.identity.workspaces.schemas import (
    AddableMember,
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationResponse,
    MemberAddRequest,
    MemberResponse,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceSummary,
    WorkspaceUpdate,
)
from app.modules.ops.audit import service as audit_service
from app.platform.db.session import get_db

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _to_summary(ws, role: str) -> WorkspaceSummary:
    """Build the response shape used in list + create + accept flows."""
    return WorkspaceSummary(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        is_personal=ws.is_personal,
        organization=ws.organization,
        settings=ws.settings or {},
        monthly_token_quota_override=ws.monthly_token_quota_override,
        monthly_kb_query_quota_override=ws.monthly_kb_query_quota_override,
        role=role,
        created_at=ws.created_at,
    )


# ─── Workspace CRUD ────────────────────────────────────────────────


@router.get("", response_model=list[WorkspaceSummary])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List every workspace the caller is a member of, paired with
    the caller's role in each."""
    rows = await service.list_user_workspaces(db, current_user.id)
    return [_to_summary(ws, role) for ws, role in rows]


@router.post("", response_model=WorkspaceSummary, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new (non-personal) workspace.

    With ``organization_id`` set, attaches to that org — but only if
    the caller is already an admin+ in *some* workspace under it.
    Without ``organization_id`` we spin up a fresh org around the new
    workspace and the caller becomes owner of both.
    """
    if body.organization_id is not None:
        # Authorization: either
        #   (a) ``organization_members.role >= admin`` for the target org
        #       (covers org owners + admins, including the system org's
        #       owner who otherwise has zero workspaces and would be
        #       locked out by the workspace-only check below), OR
        #   (b) ``workspace_members.role >= admin`` in *any* workspace
        #       under the target org (covers workspace-admins promoted
        #       through the team flow).
        org_member_role = await db.scalar(
            select(OrganizationMember.role).where(
                OrganizationMember.organization_id == body.organization_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        is_org_admin = org_member_role in (ORG_ROLE_OWNER, ORG_ROLE_ADMIN)

        if not is_org_admin:
            result = await service.list_user_workspaces(db, current_user.id)
            is_ws_admin = any(
                ws.organization_id == body.organization_id
                and role_at_least(role, WORKSPACE_ROLE_ADMIN)
                for ws, role in result
            )
            if not is_ws_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorised to create workspaces in this organization",
                )

    try:
        ws = await service.create_team_workspace(
            db,
            creator=current_user,
            name=body.name,
            slug=body.slug,
            organization_id=body.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await audit_service.log_event(
        db,
        action="workspace.create",
        resource_type="workspace",
        resource_id=ws.id,
        organization_id=ws.organization_id,
        workspace_id=ws.id,
        metadata={"name": ws.name, "slug": ws.slug},
    )
    await db.commit()
    # Eager-load org for the response shape.
    await db.refresh(ws, ["organization"])
    return _to_summary(ws, WORKSPACE_ROLE_OWNER)


@router.get("/{workspace_id}", response_model=WorkspaceSummary)
async def get_workspace(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_workspace_with_member(db, workspace_id, member.user_id)
    if row is None:
        # Should be unreachable — require_workspace_role would have 404'd.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ws, _ = row
    return _to_summary(ws, member.role)


@router.patch("/{workspace_id}", response_model=WorkspaceSummary)
async def patch_workspace(
    workspace_id: uuid.UUID,
    body: WorkspaceUpdate,
    member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_workspace_with_member(db, workspace_id, member.user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ws, _ = row
    try:
        ws = await service.update_workspace(db, ws, **body.model_dump(exclude_unset=True))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already in use within this organization",
        )
    await db.commit()
    await db.refresh(ws, ["organization"])
    return _to_summary(ws, member.role)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_OWNER)),
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_workspace_with_member(db, workspace_id, member.user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ws, _ = row
    try:
        await service.delete_workspace(db, ws)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Audit BEFORE commit so the row carries on the same txn — if the
    # delete somehow rolls back, the audit row goes with it.
    await audit_service.log_event(
        db,
        action="workspace.delete",
        resource_type="workspace",
        resource_id=ws.id,
        organization_id=ws.organization_id,
        # Pass workspace_id explicitly — it's being deleted in the same
        # txn so the ContextVar default would point to a doomed row.
        workspace_id=None,
        metadata={"name": ws.name, "slug": ws.slug},
    )
    await db.commit()


# ─── Members ───────────────────────────────────────────────────────


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    _member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    members = await service.list_members(db, workspace_id)
    return [MemberResponse.model_validate(m) for m in members]


@router.get(
    "/{workspace_id}/addable-members",
    response_model=list[AddableMember],
)
async def list_addable_workspace_members(
    workspace_id: uuid.UUID,
    _member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Org members not yet in this workspace — picker source for the
    workspace's "Add member" UI. Workspace admins assign from this
    list instead of typing an email; new-to-the-platform invites
    happen at /org/members."""
    rows = await service.list_addable_members(db, workspace_id)
    return [
        AddableMember(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            org_role=om.role,
        )
        for om, user in rows
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member_endpoint(
    workspace_id: uuid.UUID,
    body: MemberAddRequest,
    caller: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Add an existing org member to this workspace directly — no
    invitation token. Org membership is verified server-side; new
    platform users still need to come through /org/members first.
    """
    try:
        member = await service.add_existing_member(
            db,
            workspace_id=workspace_id,
            user_id=body.user_id,
            role=body.role,
            invited_by=caller.user_id,
        )
    except ValueError as e:
        msg = str(e)
        code = (
            status.HTTP_404_NOT_FOUND
            if msg in ("workspace_not_found", "not_org_member")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg)

    await audit_service.log_event(
        db,
        action="workspace.member.add",
        resource_type="workspace_member",
        resource_id=member.user_id,
        workspace_id=workspace_id,
        metadata={"role": member.role},
    )
    await db.commit()
    # Reload with user eager-loaded so the response matches the list shape.
    await db.refresh(member, ["user"])
    return MemberResponse.model_validate(member)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberResponse,
)
async def update_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberRoleUpdate,
    caller: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Change a member's role.

    Only owners can promote someone to owner (admins can shuffle
    viewer/editor/admin freely). Service layer additionally refuses to
    demote the last owner.
    """
    target = await service.get_member(db, workspace_id, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if body.role == WORKSPACE_ROLE_OWNER and caller.role != WORKSPACE_ROLE_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can grant the owner role",
        )

    old_role = target.role
    try:
        await service.update_member_role(db, target, body.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await audit_service.log_event(
        db,
        action="workspace.member.role_change",
        resource_type="user",
        resource_id=target.user_id,
        workspace_id=workspace_id,
        metadata={"from": old_role, "to": body.role},
    )
    await db.commit()
    await db.refresh(target, ["user"])
    return MemberResponse.model_validate(target)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member, or leave the workspace if removing yourself.

    Self-removal is allowed at any role (the user can always leave).
    Removing someone else requires admin+. Service layer refuses to
    remove the last owner.
    """
    is_self = caller.user_id == user_id
    if not is_self and not role_at_least(caller.role, WORKSPACE_ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove other members",
        )

    target = await service.get_member(db, workspace_id, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    old_role = target.role
    try:
        await service.remove_member(db, target)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await audit_service.log_event(
        db,
        action="workspace.member.remove" if not is_self else "workspace.member.leave",
        resource_type="user",
        resource_id=user_id,
        workspace_id=workspace_id,
        metadata={"role": old_role},
    )
    await db.commit()


# ─── Invitations ───────────────────────────────────────────────────


@router.get(
    "/{workspace_id}/invitations",
    response_model=list[InvitationResponse],
)
async def list_workspace_invitations(
    workspace_id: uuid.UUID,
    _member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    invites = await service.list_invitations(db, workspace_id)
    return [InvitationResponse.model_validate(inv) for inv in invites]


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_invitation(
    workspace_id: uuid.UUID,
    body: InvitationCreate,
    caller: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Mint a pending invitation. Caller passes the token to the
    invitee out-of-band (or via a mail service that reads
    ``WorkspaceInvitation`` rows)."""
    try:
        inv = await service.create_invitation(
            db,
            workspace_id=workspace_id,
            email=body.email,
            role=body.role,
            invited_by=caller.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await audit_service.log_event(
        db,
        action="workspace.member.invite",
        resource_type="invitation",
        resource_id=inv.id,
        workspace_id=workspace_id,
        metadata={"email": inv.email, "role": inv.role},
    )
    await db.commit()
    return InvitationResponse.model_validate(inv)


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_workspace_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    _member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    # Fetch + verify scope before delete so token leaks across workspaces
    # are caught.
    from sqlalchemy import select

    from app.models.workspace_invitation import WorkspaceInvitation

    inv = await db.scalar(
        select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == workspace_id,
        )
    )
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    await service.revoke_invitation(db, inv)
    await audit_service.log_event(
        db,
        action="workspace.member.invite_revoke",
        resource_type="invitation",
        resource_id=invitation_id,
        workspace_id=workspace_id,
        metadata={"email": inv.email, "role": inv.role},
    )
    await db.commit()


# Accept lives outside the workspace prefix because the caller doesn't
# yet *know* the workspace id — the token is the lookup key. Mounted
# under the same router so it ships with the rest of the surface.
@router.post(
    "/invitations/{token}/accept",
    response_model=InvitationAcceptResponse,
)
async def accept_workspace_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Materialise a pending invitation. Caller must be authenticated;
    the invite's email is intentionally NOT cross-checked against the
    caller's email — an admin can forward a link to anyone they trust
    on the team, and the recipient signs in as themselves to accept."""
    inv = await service.get_invitation_by_token(db, token)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or expired",
        )
    member = await service.accept_invitation(db, inv, current_user)
    await audit_service.log_event(
        db,
        action="workspace.member.accept_invitation",
        resource_type="user",
        resource_id=current_user.id,
        workspace_id=inv.workspace_id,
        metadata={"role": member.role, "email": inv.email},
    )
    await db.commit()

    row = await service.get_workspace_with_member(db, inv.workspace_id, current_user.id)
    if row is None:
        # Shouldn't happen — accept_invitation just inserted the member.
        raise HTTPException(status_code=500, detail="Workspace not resolvable after accept")
    ws, _ = row
    return InvitationAcceptResponse(workspace=_to_summary(ws, member.role))
