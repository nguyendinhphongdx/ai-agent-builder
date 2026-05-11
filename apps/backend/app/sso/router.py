"""Admin endpoints for SSO config, SCIM tokens, and workspace IP
allowlists. The user-facing OIDC login lives in ``oidc_router.py``
(unauthenticated by design); this surface is cookie-auth + role-gated.

Endpoint groups:
  /api/orgs/{org_id}/sso/*       SSO config CRUD (admin role)
  /api/orgs/{org_id}/scim-tokens SCIM bearer mint/list/revoke
  /api/workspaces/{id}/ip-rules  CIDR allowlist management
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.scim_token import SCIMToken
from app.models.sso_configuration import (
    SSO_PROVIDERS,
    SSOConfiguration,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLE_ADMIN, WorkspaceMember
from app.sso import service as sso_service
from app.workspaces.permissions import require_workspace_role, role_at_least

router = APIRouter(tags=["sso-admin"])


# ─── Helpers ───────────────────────────────────────────────────────


async def _require_org_admin(
    db: AsyncSession,
    user: User,
    org_id: uuid.UUID,
) -> None:
    """Org admin = admin+ in any workspace under the org. Mirrors the
    workspace-create permission model from Block 1 of Phase 1.1."""
    rows = await db.execute(
        select(WorkspaceMember.role)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(
            Workspace.organization_id == org_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if not any(role_at_least(r, WORKSPACE_ROLE_ADMIN) for (r,) in rows.all()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org admin role required",
        )

    org = await db.scalar(select(Organization).where(Organization.id == org_id))
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")


# ─── Schemas ───────────────────────────────────────────────────────


class SSOConfigPayload(BaseModel):
    provider: str
    display_name: str = Field(min_length=1, max_length=255)
    is_active: bool = False
    default_role: str = "editor"
    jit_provisioning: bool = True
    attribute_mapping: dict[str, Any] = Field(default_factory=dict)
    # OIDC
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    """Plaintext — encrypted server-side before persisting."""
    oidc_scopes: list[str] | None = None
    # SAML (placeholders — full SAML lands in Block 6)
    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_x509_cert: str | None = None
    saml_sp_entity_id: str | None = None


class SSOConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    display_name: str
    is_active: bool
    default_role: str
    jit_provisioning: bool
    attribute_mapping: dict[str, Any]
    # OIDC public fields — secret never leaves the server.
    oidc_issuer: str | None
    oidc_client_id: str | None
    oidc_scopes: list[str]
    # SAML public fields.
    saml_idp_entity_id: str | None
    saml_idp_sso_url: str | None
    saml_sp_entity_id: str | None


def _to_sso_response(row: SSOConfiguration) -> SSOConfigResponse:
    return SSOConfigResponse(
        id=row.id,
        organization_id=row.organization_id,
        provider=row.provider,
        display_name=row.display_name,
        is_active=row.is_active,
        default_role=row.default_role,
        jit_provisioning=row.jit_provisioning,
        attribute_mapping=row.attribute_mapping or {},
        oidc_issuer=row.oidc_issuer,
        oidc_client_id=row.oidc_client_id,
        oidc_scopes=row.oidc_scopes or [],
        saml_idp_entity_id=row.saml_idp_entity_id,
        saml_idp_sso_url=row.saml_idp_sso_url,
        saml_sp_entity_id=row.saml_sp_entity_id,
    )


# ─── SSO config CRUD ───────────────────────────────────────────────


@router.get("/orgs/{org_id}/sso", response_model=list[SSOConfigResponse])
async def list_sso_configs(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    rows = (
        await db.scalars(
            select(SSOConfiguration).where(SSOConfiguration.organization_id == org_id)
        )
    ).all()
    return [_to_sso_response(r) for r in rows]


@router.put("/orgs/{org_id}/sso", response_model=SSOConfigResponse)
async def upsert_sso_config(
    org_id: uuid.UUID,
    body: SSOConfigPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotent upsert — UNIQUE(org_id, provider) means one row per
    pair. Re-PUT with the same provider updates in place."""
    await _require_org_admin(db, current_user, org_id)
    if body.provider not in SSO_PROVIDERS:
        raise HTTPException(400, detail=f"Unknown provider {body.provider!r}")
    try:
        row = await sso_service.upsert_sso_config(
            db,
            organization_id=org_id,
            provider=body.provider,
            display_name=body.display_name,
            is_active=body.is_active,
            default_role=body.default_role,
            jit_provisioning=body.jit_provisioning,
            attribute_mapping=body.attribute_mapping,
            oidc_issuer=body.oidc_issuer,
            oidc_client_id=body.oidc_client_id,
            oidc_client_secret=body.oidc_client_secret,
            oidc_scopes=body.oidc_scopes,
            saml_idp_entity_id=body.saml_idp_entity_id,
            saml_idp_sso_url=body.saml_idp_sso_url,
            saml_idp_x509_cert=body.saml_idp_x509_cert,
            saml_sp_entity_id=body.saml_sp_entity_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await audit_service.log_event(
        db,
        action="sso.config.update",
        resource_type="sso_configuration",
        resource_id=row.id,
        organization_id=org_id,
        metadata={
            "provider": row.provider,
            "is_active": row.is_active,
            "jit_provisioning": row.jit_provisioning,
        },
    )
    await db.commit()
    return _to_sso_response(row)


@router.delete(
    "/orgs/{org_id}/sso/{provider}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_sso_config(
    org_id: uuid.UUID,
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    row = await db.scalar(
        select(SSOConfiguration).where(
            SSOConfiguration.organization_id == org_id,
            SSOConfiguration.provider == provider,
        )
    )
    if row is not None:
        await db.delete(row)
        await audit_service.log_event(
            db,
            action="sso.config.delete",
            resource_type="sso_configuration",
            resource_id=row.id,
            organization_id=org_id,
            metadata={"provider": provider},
        )
        await db.commit()


# ─── SCIM tokens ───────────────────────────────────────────────────


class SCIMTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expires_at: datetime | None = None


class SCIMTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class SCIMTokenCreatedResponse(SCIMTokenResponse):
    """Returned ONLY at mint time — includes plaintext."""
    plaintext: str


@router.get("/orgs/{org_id}/scim-tokens", response_model=list[SCIMTokenResponse])
async def list_scim_tokens(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    rows = (
        await db.scalars(
            select(SCIMToken).where(SCIMToken.organization_id == org_id)
        )
    ).all()
    return [SCIMTokenResponse.model_validate(r) for r in rows]


@router.post(
    "/orgs/{org_id}/scim-tokens",
    response_model=SCIMTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scim_token(
    org_id: uuid.UUID,
    body: SCIMTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    row, plaintext = await sso_service.create_scim_token(
        db,
        organization_id=org_id,
        name=body.name,
        created_by=current_user.id,
        expires_at=body.expires_at,
    )
    await audit_service.log_event(
        db,
        action="scim.token.mint",
        resource_type="scim_token",
        resource_id=row.id,
        organization_id=org_id,
        metadata={"name": row.name, "expires_at": row.expires_at.isoformat() if row.expires_at else None},
    )
    await db.commit()
    payload = SCIMTokenResponse.model_validate(row).model_dump()
    payload["plaintext"] = plaintext
    return payload


@router.delete(
    "/orgs/{org_id}/scim-tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_scim_token(
    org_id: uuid.UUID,
    token_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_admin(db, current_user, org_id)
    # Verify the token belongs to this org before revoking — prevents
    # cross-org tampering even if the token_id is leaked.
    row = await db.scalar(
        select(SCIMToken).where(
            SCIMToken.id == token_id, SCIMToken.organization_id == org_id
        )
    )
    if row is None:
        raise HTTPException(404, detail="SCIM token not found")
    await sso_service.revoke_scim_token(db, token_id)
    await audit_service.log_event(
        db,
        action="scim.token.revoke",
        resource_type="scim_token",
        resource_id=token_id,
        organization_id=org_id,
        metadata={"name": row.name},
    )
    await db.commit()


# ─── Workspace IP rules ───────────────────────────────────────────


class IPRulePayload(BaseModel):
    cidr: str
    description: str | None = None


class IPRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    workspace_id: uuid.UUID
    cidr: str
    description: str | None
    created_at: datetime


@router.get(
    "/workspaces/{workspace_id}/ip-rules", response_model=list[IPRuleResponse]
)
async def list_workspace_ip_rules(
    workspace_id: uuid.UUID,
    _: Any = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    rules = await sso_service.list_ip_rules(db, workspace_id)
    return [IPRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/workspaces/{workspace_id}/ip-rules",
    response_model=IPRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_ip_rule(
    workspace_id: uuid.UUID,
    body: IPRulePayload,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await sso_service.create_ip_rule(
            db,
            workspace_id=workspace_id,
            cidr=body.cidr,
            description=body.description,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    await audit_service.log_event(
        db,
        action="ip_rule.create",
        resource_type="ip_rule",
        resource_id=row.id,
        workspace_id=workspace_id,
        metadata={"cidr": row.cidr, "description": row.description},
    )
    await db.commit()
    return IPRuleResponse.model_validate(row)


@router.delete(
    "/workspaces/{workspace_id}/ip-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workspace_ip_rule(
    workspace_id: uuid.UUID,
    rule_id: uuid.UUID,
    _: Any = Depends(require_workspace_role(WORKSPACE_ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    ok = await sso_service.delete_ip_rule(db, rule_id)
    if not ok:
        raise HTTPException(404, detail="IP rule not found")
    await audit_service.log_event(
        db,
        action="ip_rule.delete",
        resource_type="ip_rule",
        resource_id=rule_id,
        workspace_id=workspace_id,
    )
    await db.commit()
