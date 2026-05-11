"""Custom role admin + permission catalogue.

Two endpoint groups under one router:

  GET  /api/permissions                Public-ish read of the
                                       catalogue + built-in role
                                       definitions. Used by the FE
                                       permission picker.

  /api/orgs/{org_id}/custom-roles      Org-admin-gated CRUD on
                                       org-defined roles. Slug
                                       collisions with built-ins
                                       are rejected. Cannot delete
                                       a role still in use.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.custom_role import CustomRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLES, WorkspaceMember
from app.permissions.catalogue import ALL_PERMISSIONS, is_known_permission
from app.permissions.roles import BUILTIN_ROLE_PERMISSIONS

router = APIRouter(tags=["permissions"])


# ─── Catalogue ─────────────────────────────────────────────────────


class CatalogueResponse(BaseModel):
    """What the FE needs to build a permission-picker / role inspector."""

    permissions: list[str]
    builtin_roles: dict[str, list[str]]


@router.get("/permissions", response_model=CatalogueResponse)
async def get_catalogue() -> CatalogueResponse:
    """Static read — caller can cache for the life of the page."""
    return CatalogueResponse(
        permissions=list(ALL_PERMISSIONS),
        builtin_roles={
            role: sorted(perms)
            for role, perms in BUILTIN_ROLE_PERMISSIONS.items()
        },
    )


# ─── Custom role CRUD ──────────────────────────────────────────────


_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")


class CustomRoleCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class CustomRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    permissions: list[str] | None = None


class CustomRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


async def _require_org_admin(
    db: AsyncSession, user: User, org_id: uuid.UUID
) -> None:
    """Reuse the SSO router's helper — same semantics here."""
    from app.sso.router import _require_org_admin as _impl

    await _impl(db, user, org_id)


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="slug must be lowercase letters/digits/hyphens (3-64 chars)",
        )
    if slug in WORKSPACE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"slug {slug!r} collides with a built-in role",
        )


def _validate_permissions(perms: list[str]) -> None:
    unknown = [p for p in perms if not is_known_permission(p)]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown permissions: {sorted(set(unknown))}",
        )


@router.get(
    "/orgs/{org_id}/custom-roles",
    response_model=list[CustomRoleResponse],
)
async def list_custom_roles(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    rows = (
        await db.scalars(
            select(CustomRole)
            .where(CustomRole.organization_id == org_id)
            .order_by(CustomRole.created_at)
        )
    ).all()
    return [CustomRoleResponse.model_validate(r) for r in rows]


@router.post(
    "/orgs/{org_id}/custom-roles",
    response_model=CustomRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_role(
    org_id: uuid.UUID,
    body: CustomRoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    _validate_slug(body.slug)
    _validate_permissions(body.permissions)

    # UNIQUE(org, slug) will catch a race — but check first for a
    # friendlier error than IntegrityError.
    existing = await db.scalar(
        select(CustomRole).where(
            CustomRole.organization_id == org_id,
            CustomRole.slug == body.slug,
        )
    )
    if existing is not None:
        raise HTTPException(409, detail=f"Role slug {body.slug!r} already exists")

    row = CustomRole(
        organization_id=org_id,
        slug=body.slug,
        name=body.name,
        description=body.description,
        permissions=sorted(set(body.permissions)),
    )
    db.add(row)
    await db.flush()
    await audit_service.log_event(
        db,
        action="role.custom.create",
        resource_type="custom_role",
        resource_id=row.id,
        organization_id=org_id,
        metadata={"slug": row.slug, "permissions_count": len(row.permissions)},
    )
    await db.commit()
    await db.refresh(row)
    return CustomRoleResponse.model_validate(row)


@router.patch(
    "/orgs/{org_id}/custom-roles/{role_id}",
    response_model=CustomRoleResponse,
)
async def update_custom_role(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    body: CustomRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    row = await db.scalar(
        select(CustomRole).where(
            CustomRole.id == role_id,
            CustomRole.organization_id == org_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="Role not found")

    if body.name is not None:
        row.name = body.name
    if body.description is not None:
        row.description = body.description
    if body.permissions is not None:
        _validate_permissions(body.permissions)
        row.permissions = sorted(set(body.permissions))

    await audit_service.log_event(
        db,
        action="role.custom.update",
        resource_type="custom_role",
        resource_id=row.id,
        organization_id=org_id,
        metadata={"slug": row.slug},
    )
    await db.commit()
    await db.refresh(row)
    return CustomRoleResponse.model_validate(row)


@router.delete(
    "/orgs/{org_id}/custom-roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_custom_role(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refuses to delete a role that's still assigned to a member.
    Admin must reassign affected members to a built-in role first
    (the FE should surface the affected count before letting the
    user click delete)."""
    await _require_org_admin(db, current_user, org_id)
    row = await db.scalar(
        select(CustomRole).where(
            CustomRole.id == role_id,
            CustomRole.organization_id == org_id,
        )
    )
    if row is None:
        raise HTTPException(404, detail="Role not found")

    in_use = await db.scalar(
        select(WorkspaceMember.user_id)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(
            Workspace.organization_id == org_id,
            WorkspaceMember.role == row.slug,
        )
        .limit(1)
    )
    if in_use is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Role still assigned to one or more members. "
                "Reassign them before deleting."
            ),
        )

    await db.delete(row)
    await audit_service.log_event(
        db,
        action="role.custom.delete",
        resource_type="custom_role",
        resource_id=role_id,
        organization_id=org_id,
        metadata={"slug": row.slug},
    )
    await db.commit()
