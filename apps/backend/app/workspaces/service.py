"""Workspace service — business logic for the multi-tenancy layer.

Phase 1.1 step 1 surface: just enough to (a) auto-create a personal
Org+Workspace+owner-Member tuple at signup and (b) point ``User.
default_workspace_id`` at it. CRUD on workspaces, member management,
invitation flows come in follow-up phases.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import ORG_PLAN_FREE, Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLE_OWNER, WorkspaceMember


# Personal workspaces always use this slug — uniqueness is per-org so
# the constraint stays well-defined even when every personal Org has a
# child workspace called ``personal``.
PERSONAL_WORKSPACE_SLUG = "personal"
PERSONAL_WORKSPACE_NAME = "Personal"

# Org slug is derived from the user — unique-globally — so we anchor it
# on the user UUID rather than a guess off email/name. ``user-`` prefix
# keeps it human-recognisable in URLs (``/o/user-a3f9c8b2/...``).
_ORG_SLUG_PREFIX = "user-"
_SLUG_SAFE = re.compile(r"[^a-z0-9-]+")


def _personal_org_slug(user: User) -> str:
    return f"{_ORG_SLUG_PREFIX}{user.id.hex[:8]}"


def _personal_org_name(user: User) -> str:
    """Human label for the auto-created personal Organization. Falls
    back through full_name → email-local → 'My' so we always have
    something reasonable to show in the UI."""
    if user.full_name:
        base = user.full_name.strip()
    elif user.email:
        base = user.email.split("@", 1)[0]
    else:
        base = "My"
    return f"{base}'s Account"


async def ensure_personal_workspace(db: AsyncSession, user: User) -> Workspace:
    """Idempotently make sure ``user`` has a personal Org+Workspace+
    owner-Member set up, and that ``user.default_workspace_id`` points
    at the personal workspace.

    Safe to call:
      - at signup (always creates everything fresh),
      - after each login (no-op when state is already correct),
      - from a backfill script over existing users.

    Returns the personal :class:`Workspace`. Caller is responsible for
    committing — the function only flushes so generated IDs are
    available to whatever else is in the same transaction.
    """
    # Fast path: user already has a default workspace pointer that
    # resolves to a personal workspace they own. Don't touch anything.
    if user.default_workspace_id is not None:
        existing = await db.scalar(
            select(Workspace).where(
                Workspace.id == user.default_workspace_id,
                Workspace.is_personal.is_(True),
            )
        )
        if existing is not None:
            return existing

    # Slower path: maybe they have a personal workspace under their
    # auto-org but the default pointer was nulled (workspace deleted
    # then recreated, or default never set). Re-attach instead of
    # creating a duplicate.
    org_slug = _personal_org_slug(user)
    existing_org = await db.scalar(
        select(Organization).where(Organization.slug == org_slug)
    )
    if existing_org is not None:
        existing_personal = await db.scalar(
            select(Workspace).where(
                Workspace.organization_id == existing_org.id,
                Workspace.is_personal.is_(True),
            )
        )
        if existing_personal is not None:
            user.default_workspace_id = existing_personal.id
            await db.flush()
            return existing_personal
        # Org without personal workspace — likely manual cleanup. Reuse
        # the org and create just the workspace + member below.
        org = existing_org
    else:
        org = Organization(
            name=_personal_org_name(user),
            slug=org_slug,
            billing_email=user.email,
            plan=ORG_PLAN_FREE,
        )
        db.add(org)
        await db.flush()

    workspace = Workspace(
        organization_id=org.id,
        name=PERSONAL_WORKSPACE_NAME,
        slug=PERSONAL_WORKSPACE_SLUG,
        is_personal=True,
    )
    db.add(workspace)
    await db.flush()

    # Ownership row — without this the workspace is orphaned: schema
    # allows it but services that filter by membership would refuse to
    # show it back to the user who just paid for it.
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WORKSPACE_ROLE_OWNER,
    )
    db.add(member)

    user.default_workspace_id = workspace.id
    await db.flush()
    return workspace


async def list_user_workspace_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Return every workspace id ``user_id`` is a member of.

    Used by tenant-scoped service queries — anything pulling resources
    for a user should filter ``WHERE workspace_id IN (...)`` against
    this list (or restrict to one specific workspace inside it).
    """
    result = await db.scalars(
        select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
    )
    return list(result)
