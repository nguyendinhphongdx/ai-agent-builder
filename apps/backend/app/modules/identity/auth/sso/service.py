"""SSO + SCIM + workspace-IP services.

Three thin CRUD layers — the heavy auth-flow logic for OIDC/SAML
lives in their own modules (Block 2 onwards). This module owns
the persistence + secret encryption + token hashing primitives.
"""
from __future__ import annotations

import hashlib
import ipaddress
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.scim_token import SCIMToken
from app.models.sso_configuration import (
    SSO_PROVIDERS,
    SSOConfiguration,
)
from app.models.workspace_ip_rule import WorkspaceIPRule
from app.platform.security.crypto import decrypt_secret, encrypt_secret

# ─── SSO configuration ─────────────────────────────────────────────


async def get_sso_config_by_org(
    db: AsyncSession, organization_id: uuid.UUID, *, provider: str | None = None
) -> SSOConfiguration | None:
    """Resolve an org's active SSO config. When ``provider`` is omitted,
    returns the first ``is_active=true`` row — most orgs have only one."""
    stmt = select(SSOConfiguration).where(
        SSOConfiguration.organization_id == organization_id,
        SSOConfiguration.is_active.is_(True),
    )
    if provider is not None:
        stmt = stmt.where(SSOConfiguration.provider == provider)
    return await db.scalar(stmt)


async def get_sso_config_by_org_slug(
    db: AsyncSession, org_slug: str, *, provider: str | None = None
) -> SSOConfiguration | None:
    """Same as above but starting from the org's URL slug — used by
    the public login endpoints (``/api/sso/oidc/{org_slug}/login``)."""
    org = await db.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None:
        return None
    return await get_sso_config_by_org(db, org.id, provider=provider)


async def upsert_sso_config(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    provider: str,
    display_name: str,
    is_active: bool = False,
    default_role: str = "editor",
    jit_provisioning: bool = True,
    attribute_mapping: dict[str, Any] | None = None,
    # Provider-specific kwargs — only the matching set is read.
    oidc_issuer: str | None = None,
    oidc_client_id: str | None = None,
    oidc_client_secret: str | None = None,
    oidc_scopes: list[str] | None = None,
    saml_idp_entity_id: str | None = None,
    saml_idp_sso_url: str | None = None,
    saml_idp_x509_cert: str | None = None,
    saml_sp_entity_id: str | None = None,
) -> SSOConfiguration:
    """Create or update the SSO config for ``(organization_id, provider)``.

    UNIQUE constraint ensures one row per (org, provider). Secret
    plaintext is encrypted on write; never persisted in cleartext.
    """
    if provider not in SSO_PROVIDERS:
        raise ValueError(f"Unknown SSO provider: {provider!r}")

    existing = await db.scalar(
        select(SSOConfiguration).where(
            SSOConfiguration.organization_id == organization_id,
            SSOConfiguration.provider == provider,
        )
    )

    encrypted_secret: str | None = None
    if oidc_client_secret:
        encrypted_secret = encrypt_secret(oidc_client_secret)

    if existing is not None:
        existing.display_name = display_name
        existing.is_active = is_active
        existing.default_role = default_role
        existing.jit_provisioning = jit_provisioning
        if attribute_mapping is not None:
            existing.attribute_mapping = attribute_mapping
        if provider == "oidc":
            if oidc_issuer is not None:
                existing.oidc_issuer = oidc_issuer
            if oidc_client_id is not None:
                existing.oidc_client_id = oidc_client_id
            if encrypted_secret is not None:
                existing.oidc_client_secret_encrypted = encrypted_secret
            if oidc_scopes is not None:
                existing.oidc_scopes = oidc_scopes
        elif provider == "saml":
            if saml_idp_entity_id is not None:
                existing.saml_idp_entity_id = saml_idp_entity_id
            if saml_idp_sso_url is not None:
                existing.saml_idp_sso_url = saml_idp_sso_url
            if saml_idp_x509_cert is not None:
                existing.saml_idp_x509_cert = saml_idp_x509_cert
            if saml_sp_entity_id is not None:
                existing.saml_sp_entity_id = saml_sp_entity_id
        await db.flush()
        return existing

    row = SSOConfiguration(
        organization_id=organization_id,
        provider=provider,
        display_name=display_name,
        is_active=is_active,
        default_role=default_role,
        jit_provisioning=jit_provisioning,
        attribute_mapping=attribute_mapping or {},
        oidc_issuer=oidc_issuer,
        oidc_client_id=oidc_client_id,
        oidc_client_secret_encrypted=encrypted_secret,
        oidc_scopes=oidc_scopes or ["openid", "email", "profile"],
        saml_idp_entity_id=saml_idp_entity_id,
        saml_idp_sso_url=saml_idp_sso_url,
        saml_idp_x509_cert=saml_idp_x509_cert,
        saml_sp_entity_id=saml_sp_entity_id,
    )
    db.add(row)
    await db.flush()
    return row


def get_oidc_client_secret(config: SSOConfiguration) -> str | None:
    """Decrypt the OIDC client secret for use at handshake time."""
    if not config.oidc_client_secret_encrypted:
        return None
    return decrypt_secret(config.oidc_client_secret_encrypted)


# ─── SCIM tokens ───────────────────────────────────────────────────


# Plaintext format mirrors the personal-access-token convention: a
# prefix lets users eyeball "yes this is a SCIM token, not an AFPT".
_SCIM_TOKEN_PREFIX = "afsc_"
_SCIM_TOKEN_BYTES = 32  # 43 chars after base64-url-safe encoding


def _hash_scim_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _mint_scim_token() -> str:
    return _SCIM_TOKEN_PREFIX + secrets.token_urlsafe(_SCIM_TOKEN_BYTES)


async def create_scim_token(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    name: str,
    created_by: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> tuple[SCIMToken, str]:
    """Mint a SCIM token. Returns (row, plaintext) — caller must
    surface the plaintext exactly once and drop it. Only the hash
    is persisted."""
    plaintext = _mint_scim_token()
    row = SCIMToken(
        organization_id=organization_id,
        name=name,
        token_hash=_hash_scim_token(plaintext),
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row, plaintext


async def verify_scim_token(
    db: AsyncSession, plaintext: str
) -> SCIMToken | None:
    """Resolve a raw SCIM bearer to its row. Rejects malformed prefix,
    unknown hash, revoked, and expired tokens. Refreshes last_used_at
    so admins can see which tokens are still in flight."""
    if not plaintext.startswith(_SCIM_TOKEN_PREFIX):
        return None
    digest = _hash_scim_token(plaintext)
    row = await db.scalar(select(SCIMToken).where(SCIMToken.token_hash == digest))
    if row is None or row.revoked_at is not None:
        return None
    if row.expires_at is not None and row.expires_at <= datetime.now(timezone.utc):
        return None
    row.last_used_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def revoke_scim_token(db: AsyncSession, token_id: uuid.UUID) -> bool:
    """Soft-revoke (audit-friendly). Lookups by hash return None for
    revoked rows."""
    row = await db.scalar(select(SCIMToken).where(SCIMToken.id == token_id))
    if row is None:
        return False
    row.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return True


# ─── Workspace IP rules ────────────────────────────────────────────


async def list_ip_rules(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[WorkspaceIPRule]:
    return list(
        (
            await db.scalars(
                select(WorkspaceIPRule)
                .where(WorkspaceIPRule.workspace_id == workspace_id)
                .order_by(WorkspaceIPRule.created_at)
            )
        ).all()
    )


async def create_ip_rule(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    cidr: str,
    description: str | None,
    created_by: uuid.UUID | None,
) -> WorkspaceIPRule:
    """Insert a CIDR rule. Validates the input — bad strings raise
    ``ValueError`` so the router translates to 400."""
    try:
        # ``strict=False`` accepts host bits set in the CIDR — Postgres
        # would canonicalise on the way in anyway, but we normalise
        # early so the stored value matches the user's expectation.
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise ValueError(f"Invalid CIDR: {cidr!r}") from exc

    row = WorkspaceIPRule(
        workspace_id=workspace_id,
        cidr=str(net),
        description=description,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def delete_ip_rule(db: AsyncSession, rule_id: uuid.UUID) -> bool:
    row = await db.scalar(
        select(WorkspaceIPRule).where(WorkspaceIPRule.id == rule_id)
    )
    if row is None:
        return False
    await db.delete(row)
    await db.flush()
    return True


def ip_matches_any(client_ip: str, rules: list[WorkspaceIPRule]) -> bool:
    """True iff ``client_ip`` falls inside any rule's CIDR.

    Used by the auth dep to enforce the allowlist:
      - empty rules list → ``True`` (no restriction).
      - non-empty + no match → ``False`` → 403 from the caller.
    """
    if not rules:
        return True
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        # Malformed client IP (e.g. unknown forwarded format) — fail
        # closed when rules exist; safer than silently allowing.
        return False
    for rule in rules:
        if addr in ipaddress.ip_network(rule.cidr, strict=False):
            return True
    return False
