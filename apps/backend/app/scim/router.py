"""SCIM v2 User endpoint — JIT-style user lifecycle for IdP-driven
provisioning + deprovisioning.

We implement the *minimum* SCIM 2.0 surface that real IdPs use:
  GET  /Users           list + filter (mostly used by IdP to dedupe)
  POST /Users           create
  GET  /Users/{id}      retrieve
  PUT  /Users/{id}      full replace (Okta uses this on update)
  PATCH /Users/{id}     partial update (used by deactivate flow)
  DELETE /Users/{id}    not all IdPs use; we treat as deactivate

Groups are NOT implemented yet — most IdPs gate on roles, which we
map via SSO config's ``default_role`` for now. Group endpoints will
come once we have a fine-grained RBAC story.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.scim.auth import require_scim_token

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/scim/v2", tags=["scim"])


# ─── SCIM resource shapes ─────────────────────────────────────────


class SCIMName(BaseModel):
    """Minimal Name complex attribute. SCIM standard has formatted,
    familyName, givenName, etc.; we collapse to ``formatted`` since
    AgentForge stores full_name as a single string."""

    formatted: str | None = None


class SCIMEmail(BaseModel):
    value: EmailStr
    type: str | None = "work"
    primary: bool = True


class SCIMUserResource(BaseModel):
    """Outbound shape — what IdPs see when they GET a user."""

    model_config = ConfigDict(populate_by_name=True)

    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"],
    )
    id: str
    userName: str  # SCIM unique identifier — we use email.
    name: SCIMName | None = None
    emails: list[SCIMEmail] = Field(default_factory=list)
    active: bool = True
    meta: dict[str, Any] = Field(default_factory=dict)


class SCIMUserCreate(BaseModel):
    """Inbound shape for POST /Users and PUT /Users/{id}.

    SCIM lets clients send extra fields we don't track — pydantic's
    ``model_config = {"extra": "ignore"}`` would drop them silently
    which matches the spec ("server MAY ignore unknown attributes").
    """

    model_config = ConfigDict(extra="ignore")

    userName: EmailStr
    name: SCIMName | None = None
    emails: list[SCIMEmail] = Field(default_factory=list)
    active: bool = True


def _to_resource(user: User) -> SCIMUserResource:
    return SCIMUserResource(
        id=str(user.id),
        userName=user.email,
        name=SCIMName(formatted=user.full_name) if user.full_name else None,
        emails=[SCIMEmail(value=user.email, primary=True, type="work")],
        active=bool(user.is_active),
        meta={
            "resourceType": "User",
            "created": user.created_at.isoformat() if user.created_at else None,
            "lastModified": user.updated_at.isoformat() if user.updated_at else None,
        },
    )


async def _resolve_email_field(body: SCIMUserCreate) -> str:
    """Pick the canonical email — userName takes precedence, then the
    primary email from the emails list."""
    if body.userName:
        return body.userName.lower().strip()
    for e in body.emails:
        if e.primary:
            return e.value.lower().strip()
    if body.emails:
        return body.emails[0].value.lower().strip()
    raise HTTPException(
        status_code=400, detail="Missing userName or primary email"
    )


# ─── List ──────────────────────────────────────────────────────────


@router.get("/Users")
async def list_users_endpoint(
    organization_id: uuid.UUID = Depends(require_scim_token),
    filter: str | None = Query(default=None, description="SCIM filter — currently only userName eq supported"),
    startIndex: int = Query(default=1, ge=1),
    count: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """RFC 7644 list response. ``filter=userName eq "alice@..."`` is
    the IdP-dedupe pattern we have to support; broader filtering can
    wait until a customer actually asks for it."""
    # Scope to org via membership in any workspace under the org.
    stmt = (
        select(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(Workspace.organization_id == organization_id)
        .distinct()
        .order_by(User.created_at)
        .offset(startIndex - 1)
        .limit(count)
    )
    if filter:
        # Crude parser — only handle the userName eq path that Okta etc. send.
        if "userName eq" in filter:
            try:
                _, value = filter.split("userName eq", 1)
                value = value.strip().strip('"').lower()
                stmt = stmt.where(User.email == value)
            except ValueError:
                pass

    users = (await db.execute(stmt)).scalars().unique().all()
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(users),
        "startIndex": startIndex,
        "itemsPerPage": len(users),
        "Resources": [_to_resource(u).model_dump(exclude_none=True) for u in users],
    }


# ─── Create ────────────────────────────────────────────────────────


@router.post("/Users", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    body: SCIMUserCreate,
    organization_id: uuid.UUID = Depends(require_scim_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Idempotent on email — if a user with this email already exists,
    add them to the org's default workspace (no new user row).

    Returns 201 with the resource representation. RFC 7644 allows
    409 for conflicts; we prefer idempotency for IdP retries."""
    email = await _resolve_email_field(body)
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is None:
        user = User(
            email=email,
            hashed_password=None,
            full_name=(body.name.formatted if body.name else None),
            is_active=bool(body.active),
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()

        from app.workspaces.service import ensure_personal_workspace

        await ensure_personal_workspace(db, user)
    else:
        # Reactivate if previously deactivated via SCIM.
        if body.active and not existing.is_active:
            existing.is_active = True
        if body.name and body.name.formatted and not existing.full_name:
            existing.full_name = body.name.formatted
        user = existing

    # Ensure org-default-workspace membership.
    await _ensure_org_member(db, user.id, organization_id)
    await db.commit()
    return _to_resource(user).model_dump(exclude_none=True)


# ─── Retrieve ──────────────────────────────────────────────────────


@router.get("/Users/{user_id}")
async def get_user_endpoint(
    user_id: uuid.UUID,
    organization_id: uuid.UUID = Depends(require_scim_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await _get_org_user(db, user_id, organization_id)
    if user is None:
        raise HTTPException(404, detail={"detail": "User not found", "status": "404"})
    return _to_resource(user).model_dump(exclude_none=True)


# ─── Replace ───────────────────────────────────────────────────────


@router.put("/Users/{user_id}")
async def replace_user_endpoint(
    user_id: uuid.UUID,
    body: SCIMUserCreate,
    organization_id: uuid.UUID = Depends(require_scim_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await _get_org_user(db, user_id, organization_id)
    if user is None:
        raise HTTPException(404, detail={"detail": "User not found", "status": "404"})

    new_email = await _resolve_email_field(body)
    if new_email != user.email:
        # SCIM PUT can rename the user. Guard against email collision.
        conflict = await db.scalar(select(User).where(User.email == new_email))
        if conflict is not None and conflict.id != user.id:
            raise HTTPException(
                409, detail={"detail": "userName already in use", "status": "409"}
            )
        user.email = new_email

    if body.name and body.name.formatted:
        user.full_name = body.name.formatted
    # active=false from IdP = deactivate (the offboarding signal).
    user.is_active = bool(body.active)
    await db.commit()
    return _to_resource(user).model_dump(exclude_none=True)


# ─── Patch (the deactivate path Okta uses) ─────────────────────────


class SCIMPatchOp(BaseModel):
    op: str
    path: str | None = None
    value: Any = None


class SCIMPatchRequest(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    )
    Operations: list[SCIMPatchOp]


@router.patch("/Users/{user_id}")
async def patch_user_endpoint(
    user_id: uuid.UUID,
    body: SCIMPatchRequest,
    organization_id: uuid.UUID = Depends(require_scim_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Apply RFC 7644 patch ops. We handle the common ones:
    ``replace`` on ``active`` (the deactivate signal) and on
    ``name.formatted`` / ``displayName``. Unknown paths are silently
    ignored per spec."""
    user = await _get_org_user(db, user_id, organization_id)
    if user is None:
        raise HTTPException(404, detail={"detail": "User not found", "status": "404"})

    for op in body.Operations:
        verb = op.op.lower()
        path = (op.path or "").lower()
        if verb in ("replace", "add"):
            # Whole-object replace (no path): "value" carries the new shape.
            if not path and isinstance(op.value, dict):
                if "active" in op.value:
                    user.is_active = bool(op.value["active"])
                if "displayName" in op.value:
                    user.full_name = op.value["displayName"]
                continue
            if path == "active":
                user.is_active = bool(op.value)
            elif path in ("name.formatted", "displayname"):
                user.full_name = (op.value or None)
        elif verb == "remove":
            if path == "name.formatted":
                user.full_name = None
    await db.commit()
    return _to_resource(user).model_dump(exclude_none=True)


# ─── Delete (treat as deactivate) ─────────────────────────────────


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    organization_id: uuid.UUID = Depends(require_scim_token),
    db: AsyncSession = Depends(get_db),
):
    """SCIM DELETE → deactivate (we never hard-delete from SCIM; ops
    might need the row for audit). Removes the user from the org's
    workspaces. To purge entirely, an admin uses the user-delete
    endpoint."""
    user = await _get_org_user(db, user_id, organization_id)
    if user is None:
        return  # idempotent
    user.is_active = False
    # Drop org memberships so they can't see any data even if
    # is_active flips back somehow.
    members = (
        await db.scalars(
            select(WorkspaceMember)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user.id,
                Workspace.organization_id == organization_id,
            )
        )
    ).all()
    for m in members:
        await db.delete(m)
    await db.commit()


# ─── Helpers ──────────────────────────────────────────────────────


async def _get_org_user(
    db: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID
) -> User | None:
    """Fetch a user only when they're a member of the calling org —
    prevents cross-org enumeration via SCIM."""
    stmt = (
        select(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(User.id == user_id, Workspace.organization_id == organization_id)
        .distinct()
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _ensure_org_member(
    db: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID
) -> None:
    """Idempotently add the user to the org's default workspace.

    Default workspace = first non-personal workspace. If the org has
    none yet (unusual), we silently no-op — admin must create one.
    """
    ws = await db.scalar(
        select(Workspace)
        .where(
            Workspace.organization_id == organization_id,
            Workspace.is_personal.is_(False),
        )
        .order_by(Workspace.created_at)
    )
    if ws is None:
        return
    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if existing is not None:
        return
    # Default role for SCIM-provisioned users: pull from the SSO
    # config if one exists, else fall back to "editor".
    from app.sso.service import get_sso_config_by_org

    sso = await get_sso_config_by_org(db, organization_id)
    role = sso.default_role if sso else "editor"
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user_id, role=role))
    await db.flush()
