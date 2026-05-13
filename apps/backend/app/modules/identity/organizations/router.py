"""Organizations API.

  GET    /api/organizations                  list orgs the user belongs to
  POST   /api/organizations                  create a new org (caller = owner)
  GET    /api/organizations/{org_id}         read
  PATCH  /api/organizations/{org_id}         update name / billing_email / settings
  DELETE /api/organizations/{org_id}         delete org + cascade

  GET    /api/organizations/{org_id}/members
  POST   /api/organizations/{org_id}/members  invite (email of an existing user)
  PATCH  /api/organizations/{org_id}/members/{user_id}    change role
  DELETE /api/organizations/{org_id}/members/{user_id}    remove

Org permissions resolve through ``require_org_permission`` which
reads ``current_organization_id`` from the ContextVar — clients
should send ``X-Organization-Id`` (or rely on
``user.default_organization_id``) so the dependency picks up the
right org. Endpoints that explicitly take ``{org_id}`` in the URL
also pass it through for the service call.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.organizations import service
from app.modules.identity.organizations.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberInvite,
    OrgMemberResponse,
    OrgMemberRoleUpdate,
)
from app.modules.identity.workspaces.permissions import require_org_permission
from app.platform.db.session import get_db
from app.platform.permissions import catalogue as P

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ─── Org CRUD ──────────────────────────────────────────────────────


@router.get("", response_model=list[dict])
async def list_orgs_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Every org the user belongs to, with their role. Powers the
    org-switcher in the nav."""
    rows = await service.list_user_organizations(db, current_user.id)
    return [
        {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "role": role,
            "is_default": org.id == current_user.default_organization_id,
        }
        for org, role in rows
    ]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_org_endpoint(
    body: OrganizationCreate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Any authenticated user can create a new org. They become the
    first owner automatically (see service.create_organization)."""
    try:
        org = await service.create_organization(
            db,
            name=body.name,
            slug=body.slug,
            billing_email=body.billing_email,
        )
    except service.OrganizationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    await db.commit()
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org_endpoint(
    org_id: uuid.UUID,
    _: Any = Depends(require_org_permission(P.ORG_SETTINGS_READ)),
    db: AsyncSession = Depends(get_db),
):
    org = await service.get_organization(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_org_endpoint(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    _: Any = Depends(require_org_permission(P.ORG_SETTINGS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    org = await service.get_organization(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    org = await service.update_organization(
        db,
        org,
        name=body.name,
        billing_email=body.billing_email,
        settings=body.settings,
    )
    await db.commit()
    return OrganizationResponse.model_validate(org)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_endpoint(
    org_id: uuid.UUID,
    _: Any = Depends(require_org_permission(P.ORG_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    org = await service.get_organization(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    await service.delete_organization(db, org)
    await db.commit()


# ─── Members ───────────────────────────────────────────────────────


@router.get("/{org_id}/members", response_model=list[OrgMemberResponse])
async def list_members_endpoint(
    org_id: uuid.UUID,
    _: Any = Depends(require_org_permission(P.ORG_MEMBER_READ)),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_members(db, org_id)
    return [
        OrgMemberResponse(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            invited_by=member.invited_by,
            joined_at=member.joined_at,
        )
        for member, user in rows
    ]


@router.post(
    "/{org_id}/members",
    response_model=OrgMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member_endpoint(
    org_id: uuid.UUID,
    body: OrgMemberInvite,
    _: Any = Depends(require_org_permission(P.ORG_MEMBER_INVITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await service.invite_member(
            db, org_id, email=body.email, role=body.role
        )
    except service.OrganizationServiceError as exc:
        code = str(exc)
        http_status = (
            status.HTTP_404_NOT_FOUND
            if code == "user_not_found"
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=http_status, detail=code) from exc
    await db.commit()
    # Reload user for the response shape.
    rows = await service.list_members(db, org_id)
    for m, u in rows:
        if m.user_id == member.user_id:
            return OrgMemberResponse(
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=m.role,
                invited_by=m.invited_by,
                joined_at=m.joined_at,
            )
    # Defensive — shouldn't hit since we just inserted.
    raise HTTPException(status_code=500, detail="member_lookup_failed")


@router.patch(
    "/{org_id}/members/{user_id}", response_model=OrgMemberResponse
)
async def update_member_role_endpoint(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: OrgMemberRoleUpdate,
    _: Any = Depends(require_org_permission(P.ORG_MEMBER_ROLE_CHANGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.update_member_role(db, org_id, user_id, role=body.role)
    except service.OrganizationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    await db.commit()
    rows = await service.list_members(db, org_id)
    for m, u in rows:
        if m.user_id == user_id:
            return OrgMemberResponse(
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=m.role,
                invited_by=m.invited_by,
                joined_at=m.joined_at,
            )
    raise HTTPException(status_code=404, detail="not_a_member")


@router.delete(
    "/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member_endpoint(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    _: Any = Depends(require_org_permission(P.ORG_MEMBER_REMOVE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.remove_member(db, org_id, user_id)
    except service.OrganizationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    await db.commit()
