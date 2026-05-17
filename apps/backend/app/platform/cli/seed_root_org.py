"""Seed the platform's system (root) organization + staff users.

Pattern: ``Organization(slug='system')`` is THE org the platform-owning
company operates from — like Base.vn's organization id=1. Its members
are the staff who run AgentForge itself (admin, support, moderator),
not customers. They use the same UI + auth flow as everyone else; their
elevated capabilities come from being members of *this* org.

Once this seed runs, the staff users can sign in and access the admin
surface (``/system/*`` routes — to be wired up; current ``/admin/*``
also accepts them via ``users.role`` fallback).

Idempotent — re-running:
  * creates the system org if missing,
  * upserts the 3 staff users (passwords reset, accounts re-activated),
  * upserts their membership in the system org with the right role,
  * gives each user a personal Org+Workspace so the dashboard isn't
    empty when they switch out of the system context.

Usage:
    python -m app.platform.cli.seed_root_org
    python -m app.platform.cli.seed_root_org --domain mycompany.com
    python -m app.platform.cli.seed_root_org --password-prefix s3cret

Run inside the backend container:
    docker compose exec -e PYTHONPATH=/app backend \\
        python -m app.platform.cli.seed_root_org
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import SYSTEM_ORG_NAME, SYSTEM_ORG_SLUG, Organization
from app.models.organization_member import (
    ORG_ROLE_ADMIN,
    ORG_ROLE_EDITOR,
    ORG_ROLE_OWNER,
    OrganizationMember,
)
from app.models.user import User
from app.modules.identity.auth.permissions import UserRole
from app.modules.identity.auth.service import hash_password
from app.modules.identity.workspaces.service import ensure_personal_workspace
from app.platform.db.session import async_session_factory

def _staff_spec(domain: str, password_prefix: str) -> list[dict]:
    """3 staff personas with both platform and org roles.

    Platform role (``users.role``) drives existing ``/admin/*`` checks.
    Org role (``organization_members.role`` in the system org) drives
    the new ``/system/*`` checks. Keep them aligned so neither gate
    surprises anyone.
    """
    return [
        {
            "email": f"root@{domain}",
            "full_name": "Root Admin",
            "password": f"{password_prefix}-root",
            "platform_role": UserRole.ADMIN,
            "org_role": ORG_ROLE_OWNER,
        },
        {
            "email": f"support@{domain}",
            "full_name": "Support Staff",
            "password": f"{password_prefix}-support",
            "platform_role": UserRole.SUPPORT,
            "org_role": ORG_ROLE_ADMIN,
        },
        {
            "email": f"moderator@{domain}",
            "full_name": "Hub Moderator",
            "password": f"{password_prefix}-mod",
            "platform_role": UserRole.MODERATOR,
            "org_role": ORG_ROLE_EDITOR,
        },
    ]


async def _ensure_system_org(db: AsyncSession) -> Organization:
    # Look up by the flag (authoritative). Slug lookup is only the
    # fallback path for the very first run — once any row carries the
    # flag, that's what we trust.
    org = await db.scalar(select(Organization).where(Organization.is_system.is_(True)))
    if org is None:
        org = await db.scalar(
            select(Organization).where(Organization.slug == SYSTEM_ORG_SLUG)
        )
    if org is None:
        org = Organization(
            name=SYSTEM_ORG_NAME,
            slug=SYSTEM_ORG_SLUG,
            plan="enterprise",
            is_system=True,
        )
        db.add(org)
        await db.flush()
        print(f"✓ Created system org {SYSTEM_ORG_NAME} (id={org.id})")
    else:
        # Promote a legacy row that was created before the column existed.
        if not org.is_system:
            org.is_system = True
            await db.flush()
            print(f"✓ Promoted legacy org to system (id={org.id})")
        else:
            print(f"✓ System org already exists (id={org.id})")
    return org


async def _ensure_user(db: AsyncSession, spec: dict) -> User:
    user = await db.scalar(select(User).where(User.email == spec["email"]))
    if user is None:
        user = User(
            email=spec["email"],
            hashed_password=hash_password(spec["password"]),
            full_name=spec["full_name"],
            role=spec["platform_role"].value,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        print(f"  ✓ Created {spec['email']} (id={user.id})")
    else:
        user.hashed_password = hash_password(spec["password"])
        user.full_name = spec["full_name"]
        user.role = spec["platform_role"].value
        user.is_active = True
        user.is_verified = True
        await db.flush()
        print(f"  ✓ Updated {spec['email']} (id={user.id})")
    # Personal landing space — staff still need a normal dashboard.
    await ensure_personal_workspace(db, user)
    return user


async def _ensure_membership(
    db: AsyncSession, org: Organization, user: User, role: str
) -> None:
    existing = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing is None:
        db.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role=role,
            )
        )
        print(f"      → added to system org as {role}")
    elif existing.role != role:
        existing.role = role
        print(f"      → reassigned to {role}")
    else:
        print(f"      → already {role}")


async def _seed(domain: str, password_prefix: str) -> int:
    async with async_session_factory() as db:
        org = await _ensure_system_org(db)
        for spec in _staff_spec(domain, password_prefix):
            user = await _ensure_user(db, spec)
            await _ensure_membership(db, org, user, spec["org_role"])
        await db.commit()

    print()
    print(f"System org slug: {SYSTEM_ORG_SLUG!r} (is_system=true)")
    print("Staff accounts seeded. Login with:")
    for spec in _staff_spec(domain, password_prefix):
        print(
            f"  {spec['email']:30s} {spec['password']:20s}"
            f"  (platform={spec['platform_role'].value}, org={spec['org_role']})"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="seed_root_org",
        description="Create the system org + 3 staff users (root/support/moderator).",
    )
    parser.add_argument(
        "--domain",
        default="agentforge.dev",
        # Real-looking TLD (not ``.local`` / ``.test``) — pydantic's
        # EmailStr rejects reserved/special-use TLDs, so seeded staff
        # accounts must use a domain that actually validates at login.
        help="Email domain for the 3 staff accounts (default: agentforge.dev)",
    )
    parser.add_argument(
        "--password-prefix",
        default="dev1234",
        help="Prefix used to build each staff password (default: dev1234)",
    )
    args = parser.parse_args()
    return asyncio.run(_seed(args.domain, args.password_prefix))


if __name__ == "__main__":
    sys.exit(main())
