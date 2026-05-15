"""Two-stage auth session endpoints.

Implements the workspace-in-token model — see
``docs/architecture/hub-auth-refactor.md`` for the full design.

  GET  /api/auth/session            current token state — token_scope,
                                    workspace_id (if any), organization_id

  POST /api/auth/enter-workspace    body: { workspace_id }
                                    verifies membership, replaces the
                                    access_token cookie with a
                                    workspace-scoped token, returns the
                                    workspace + organization rows.

  POST /api/auth/exit-workspace     replaces the access_token cookie
                                    with a user-scoped token (back to
                                    /hub).

The cookie name stays ``access_token`` across scopes so the FE has one
cookie slot to reason about; the ``scope`` claim inside the payload
discriminates user vs workspace.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.modules.identity.auth._internal import AUTH_USER_LIMIT, set_auth_cookies
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.auth.service import decode_token
from app.platform.db.session import get_db

router = APIRouter()


# ─── Read current session state ────────────────────────────────────


class SessionState(BaseModel):
    """What the FE needs after a page reload to decide where to land.

    ``token_scope == "user"`` → land on /hub.
    ``token_scope == "workspace"`` → land on /app/{workspace_slug}.
    """

    token_scope: str
    user_id: uuid.UUID
    workspace_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None


@router.get("/session", response_model=SessionState)
async def read_session(
    access_token: str | None = Cookie(default=None),
    current_user: User = Depends(get_current_user),
):
    """Inspect the active access_token and return its scope + claims.

    Decoding here (cheap, signature already verified by the auth dep)
    avoids a second DB call — get_current_user already gave us the
    user; we just need to surface the ``scope``/``ws``/``org`` claims
    the FE doesn't otherwise see (cookies are HttpOnly).
    """
    payload: dict[str, Any] = decode_token(access_token) if access_token else {}
    scope = payload.get("scope", "user")
    ws_raw = payload.get("ws")
    org_raw = payload.get("org")

    def _uuid(value: Any) -> uuid.UUID | None:
        if value is None:
            return None
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError):
            return None

    return SessionState(
        token_scope=scope,
        user_id=current_user.id,
        workspace_id=_uuid(ws_raw),
        organization_id=_uuid(org_raw),
    )


# ─── Enter workspace ───────────────────────────────────────────────


class EnterWorkspaceRequest(BaseModel):
    workspace_id: uuid.UUID


class EnterWorkspaceResponse(BaseModel):
    workspace_id: uuid.UUID
    workspace_slug: str
    workspace_name: str
    organization_id: uuid.UUID
    organization_slug: str


@router.post(
    "/enter-workspace",
    response_model=EnterWorkspaceResponse,
    dependencies=[AUTH_USER_LIMIT],
)
async def enter_workspace(
    body: EnterWorkspaceRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify membership + mint a workspace-scoped access_token.

    Membership check uses the *effective* role rule from the
    permission catalogue: org-admins and org-owners are treated as
    workspace members of every workspace under their org even when
    no ``workspace_members`` row exists. That way an org-admin who
    has never joined a workspace personally can still ENTER it from
    the Hub.

    Returns the workspace + organization tuple the FE needs to route
    to ``/app/{workspace_slug}/home``.
    """
    workspace = await db.scalar(
        select(Workspace)
        .where(Workspace.id == body.workspace_id)
        .options(selectinload(Workspace.organization))
    )
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    if not await _user_can_enter(db, current_user, workspace):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    set_auth_cookies(
        response,
        str(current_user.id),
        token_version=current_user.token_version,
        workspace_id=str(workspace.id),
        organization_id=str(workspace.organization_id),
    )

    return EnterWorkspaceResponse(
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        workspace_name=workspace.name,
        organization_id=workspace.organization_id,
        organization_slug=workspace.organization.slug,
    )


# ─── Exit workspace ────────────────────────────────────────────────


@router.post("/exit-workspace", status_code=status.HTTP_204_NO_CONTENT)
async def exit_workspace(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Replace the workspace-scoped token with a user-scoped token.

    Used by the "Back to Hub" affordance. After this, the FE can route
    to ``/hub`` and tenant-scoped endpoints will reject the token
    until the user re-enters a workspace.
    """
    set_auth_cookies(
        response,
        str(current_user.id),
        token_version=current_user.token_version,
        # workspace_id omitted → mints scope=user token
    )


# ─── Membership resolver ───────────────────────────────────────────


async def _user_can_enter(
    db: AsyncSession, user: User, workspace: Workspace
) -> bool:
    """True iff the user has any path to this workspace:

    1. Direct ``workspace_members`` row, OR
    2. ``organization_members`` row at admin/owner — the effective
       role rule promotes them to workspace-owner everywhere in the
       org.
    """
    from app.models.organization_member import (
        ORG_ROLE_ADMIN,
        ORG_ROLE_OWNER,
        OrganizationMember,
    )

    direct = await db.scalar(
        select(WorkspaceMember.user_id).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if direct is not None:
        return True

    org_role = await db.scalar(
        select(OrganizationMember.role).where(
            OrganizationMember.organization_id == workspace.organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    return org_role in (ORG_ROLE_ADMIN, ORG_ROLE_OWNER)
