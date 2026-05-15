"""Workspace service — business logic for the multi-tenancy layer.

Covers (a) auto-creating a personal Org+Workspace+owner-Member tuple
at signup, (b) CRUD on user workspaces, and (c) invitation flow.
Resource-scope filtering by ``workspace_id`` is handled by each
resource's own service (agents, tools, …) — this module owns the
tenancy primitives, not the resources inside them.
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import ORG_PLAN_FREE, Organization
from app.models.organization_member import (
    ORG_ROLE_OWNER,
    ORG_ROLE_VIEWER,
    OrganizationMember,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import (
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLES,
    WorkspaceMember,
)

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
            user.default_organization_id = existing_org.id
            await _ensure_org_owner_member(db, existing_org.id, user.id)
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

    await _ensure_org_owner_member(db, org.id, user.id)

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
    user.default_organization_id = org.id
    await db.flush()
    return workspace


async def _ensure_org_owner_member(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    """Idempotently ensure ``(organization_id, user_id)`` exists as an
    owner row in ``organization_members``. Called from
    :func:`ensure_personal_workspace` for the auto-created personal
    org, and reusable for any future "user just joined this org as
    owner" flow."""
    await _ensure_org_member(db, organization_id, user_id, ORG_ROLE_OWNER)


async def _ensure_org_member(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> None:
    """Idempotently ensure a user is a member of an org at the given
    role. Used both for personal-account owner seeding and for the
    auto-promotion that runs when a user accepts a *workspace*
    invitation into an org they aren't otherwise a member of —
    without this row the org never shows up in the user's org
    switcher.

    Does NOT upgrade an existing membership; the inviter's workspace
    role is the workspace's business, the org role is the org's.
    Demotion/promotion of an existing org_member happens through the
    org member-management endpoint, not as a side effect of a
    workspace invite.
    """
    existing = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if existing is not None:
        return
    db.add(
        OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
    )
    await db.flush()


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


# ─── Workspace CRUD ────────────────────────────────────────────────


_SLUG_FALLBACK = re.compile(r"[^a-z0-9-]+")


def _slugify(name: str) -> str:
    """Best-effort slug from a workspace name.

    Not collision-checked here — the caller retries with a suffix if
    the unique constraint fires. Empty result means caller should
    generate from random bytes.
    """
    base = name.strip().lower()
    base = base.replace(" ", "-")
    base = _SLUG_FALLBACK.sub("", base)
    base = base.strip("-")
    return base[:48]


async def list_user_workspaces(
    db: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Workspace, str]]:
    """Workspaces ``user_id`` is a member of, paired with their role.

    Returns the workspace + the caller's role string so the UI can
    show role-aware affordances (hide ``Delete`` for non-owners,
    grey out invite for editors, etc.) in a single round-trip.
    """
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .options(selectinload(Workspace.organization))
        .order_by(Workspace.is_personal.desc(), Workspace.name)
    )
    return [(ws, role) for ws, role in result.all()]


async def get_workspace_with_member(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Workspace, WorkspaceMember] | None:
    """Return ``(workspace, member)`` if the user is a member, else
    ``None``. Used by the permission dep to gate every workspace-scoped
    endpoint in one query."""
    result = await db.execute(
        select(Workspace, WorkspaceMember)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id, WorkspaceMember.user_id == user_id)
        .options(selectinload(Workspace.organization))
    )
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


async def create_team_workspace(
    db: AsyncSession,
    *,
    creator: User,
    name: str,
    slug: str | None = None,
    organization_id: uuid.UUID | None = None,
) -> Workspace:
    """Create a non-personal workspace + insert the creator as owner.

    When ``organization_id`` is given the workspace attaches there
    (creator must already be a member of *some* workspace under that
    org — checked by caller). When omitted, we spin up a fresh org
    around this workspace so a user can build a team without first
    being part of one.
    """
    if organization_id is None:
        # Brand-new org for this team. Slug derives from the workspace
        # name with a short random suffix to avoid collisions.
        org_slug = _slugify(name) or "team"
        org_slug = f"{org_slug}-{secrets.token_hex(3)}"
        org = Organization(
            name=name,
            slug=org_slug,
            billing_email=creator.email,
            plan=ORG_PLAN_FREE,
        )
        db.add(org)
        await db.flush()
        organization_id = org.id

    base_slug = (slug and _slugify(slug)) or _slugify(name) or "workspace"
    ws_slug = base_slug
    # Retry with a numeric suffix on the (organization_id, slug) unique
    # constraint — keeps the surface clean for the caller.
    for attempt in range(5):
        ws = Workspace(
            organization_id=organization_id,
            name=name,
            slug=ws_slug,
            is_personal=False,
        )
        db.add(ws)
        try:
            await db.flush()
            break
        except IntegrityError:
            await db.rollback()
            ws_slug = f"{base_slug}-{attempt + 2}"
    else:
        raise ValueError("Could not allocate a unique slug after 5 attempts")

    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=creator.id,
            role=WORKSPACE_ROLE_OWNER,
        )
    )
    await db.flush()
    return ws


_NULLABLE_PATCH_FIELDS = frozenset(
    {
        # Quota overrides — None here legitimately means "clear the cap".
        "monthly_token_quota_override",
        "monthly_kb_query_quota_override",
    }
)


async def update_workspace(
    db: AsyncSession, workspace: Workspace, **fields
) -> Workspace:
    """Patch a workspace. Service-level guard: slug stays unique per
    org — caller catches IntegrityError if conflict.

    ``None`` is normally skipped (defense against accidental nulling
    of required fields like ``name`` / ``slug``), but for nullable
    quota-override columns we treat None as "clear the cap".
    """
    for key, value in fields.items():
        if value is None and key not in _NULLABLE_PATCH_FIELDS:
            continue
        if key == "slug" and value is not None:
            value = _slugify(value) or workspace.slug
        if hasattr(workspace, key):
            setattr(workspace, key, value)
    await db.flush()
    await db.refresh(workspace)
    return workspace


async def delete_workspace(db: AsyncSession, workspace: Workspace) -> None:
    """Hard-delete a workspace. Cascades through members, invitations,
    and (eventually, after step-2 rollout) every resource pinned to it.

    Refuses to delete personal workspaces — those are tied to a user
    account and must be removed by deleting the user instead. UI
    should never offer this affordance for personal."""
    if workspace.is_personal:
        raise ValueError("Cannot delete personal workspace")
    await db.delete(workspace)
    await db.flush()


# ─── Members ───────────────────────────────────────────────────────


async def list_members(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[WorkspaceMember]:
    """All members of a workspace with their user row eager-loaded so
    the API can render name + email without an N+1."""
    result = await db.scalars(
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .options(selectinload(WorkspaceMember.user))
        .order_by(WorkspaceMember.joined_at)
    )
    return list(result)


async def get_member(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    return await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )


async def list_addable_members(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[tuple[OrganizationMember, User]]:
    """Org members who aren't yet in this workspace — feeds the
    workspace's "Add member" picker.

    Workspace admins add from this list rather than typing an email,
    because workspace membership requires an existing org membership
    (the parent-org membership is established at /org/members; this
    endpoint just slices it down to "not already in this workspace").
    """
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        return []
    existing_ws_member_ids = (
        await db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id
            )
        )
    ).scalars().all()

    stmt = (
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == ws.organization_id)
    )
    if existing_ws_member_ids:
        stmt = stmt.where(~OrganizationMember.user_id.in_(existing_ws_member_ids))
    rows = await db.execute(stmt)
    return [(om, user) for om, user in rows.all()]


async def add_existing_member(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    invited_by: uuid.UUID,
) -> WorkspaceMember:
    """Add an *existing org member* directly to a workspace — no
    invitation token, no email round-trip. Used by the
    /ws/settings members picker.

    Verifies:
      1. Target user is a member of the workspace's parent org.
      2. Not already a workspace member (returns the existing row
         instead of erroring — idempotent on the membership pair).
      3. Role is valid + caller can't grant ``owner`` via this
         path (owner role is reserved for promotion of an existing
         member, same convention as the invitation flow).
    """
    if role not in WORKSPACE_ROLES or role == WORKSPACE_ROLE_OWNER:
        raise ValueError(f"Invalid member role: {role}")

    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise ValueError("workspace_not_found")

    # Caller must be org-member.
    org_member = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == ws.organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if org_member is None:
        raise ValueError("not_org_member")

    # Idempotent.
    existing = await get_member(db, workspace_id, user_id)
    if existing is not None:
        return existing

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.flush()
    return member


async def _count_owners(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WORKSPACE_ROLE_OWNER,
        )
    ) or 0


async def update_member_role(
    db: AsyncSession, member: WorkspaceMember, new_role: str
) -> WorkspaceMember:
    """Change a member's role. Refuses to demote the last owner —
    every workspace must always have at least one owner so admin
    operations stay reachable."""
    if new_role not in WORKSPACE_ROLES:
        raise ValueError(f"Unknown role: {new_role}")
    if (
        member.role == WORKSPACE_ROLE_OWNER
        and new_role != WORKSPACE_ROLE_OWNER
        and await _count_owners(db, member.workspace_id) <= 1
    ):
        raise ValueError("Cannot demote the last owner")
    member.role = new_role
    await db.flush()
    return member


async def remove_member(db: AsyncSession, member: WorkspaceMember) -> None:
    """Remove a member. Refuses to remove the last owner (same
    rationale as :func:`update_member_role`)."""
    if (
        member.role == WORKSPACE_ROLE_OWNER
        and await _count_owners(db, member.workspace_id) <= 1
    ):
        raise ValueError("Cannot remove the last owner")
    await db.delete(member)
    await db.flush()


# ─── Invitations ───────────────────────────────────────────────────


# Pending invites expire after this window. Keeps a sloppy ops setup
# from leaving stale links accepting auth forever.
_INVITATION_TTL_DAYS = 7


def _mint_invitation_token() -> str:
    return secrets.token_urlsafe(32)


async def list_invitations(
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[WorkspaceInvitation]:
    """Pending (not yet accepted) invitations for a workspace."""
    result = await db.scalars(
        select(WorkspaceInvitation)
        .where(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.accepted_at.is_(None),
        )
        .order_by(WorkspaceInvitation.created_at.desc())
    )
    return list(result)


async def create_invitation(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    email: str,
    role: str,
    invited_by: uuid.UUID,
) -> WorkspaceInvitation:
    """Mint a pending invitation. Caller is responsible for sending the
    email containing the token; we return the row so the response can
    include a copy-able URL for the admin to share manually if mail
    delivery hasn't been wired up yet."""
    if role not in WORKSPACE_ROLES or role == WORKSPACE_ROLE_OWNER:
        # Owner is granted only by promotion of an existing member.
        raise ValueError(f"Invalid invite role: {role}")

    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=email.lower().strip(),
        role=role,
        token=_mint_invitation_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_INVITATION_TTL_DAYS),
        invited_by=invited_by,
    )
    db.add(invitation)
    await db.flush()

    # If the invitee already has an account, ping their inbox so
    # they see the invite without waiting on email delivery.
    await _notify_invitee_if_user(db, invitation)

    return invitation


async def _notify_invitee_if_user(
    db: AsyncSession, invitation: WorkspaceInvitation
) -> None:
    """Best-effort inbox ping when the invited email matches a user.

    No-op when the email isn't on the platform yet — they get the
    email-based magic link instead.
    """
    try:
        invitee = await db.scalar(
            select(User).where(User.email == invitation.email)
        )
        if invitee is None:
            return
        ws = await db.get(Workspace, invitation.workspace_id)
        if ws is None:
            return
        from app.models.notification import TYPE_MEMBER_INVITED
        from app.modules.runtime.notifications import inbox as inbox_service

        await inbox_service.notify(
            db,
            user_id=invitee.id,
            type=TYPE_MEMBER_INVITED,
            title=f"You've been invited to {ws.name}",
            body=f"Accept the invite to join as {invitation.role}.",
            link_url=f"/invitations/{invitation.token}",
            workspace_id=None,  # cross-workspace — show in all contexts
            extra={"invitation_id": str(invitation.id), "role": invitation.role},
        )
    except Exception:  # noqa: BLE001
        # Telemetry-flavoured — invitation creation must not fail
        # because the inbox write hiccuped.
        pass


async def revoke_invitation(
    db: AsyncSession, invitation: WorkspaceInvitation
) -> None:
    """Hard-delete a pending invitation. Already-accepted invitations
    are historical and don't need revoking."""
    await db.delete(invitation)
    await db.flush()


async def get_invitation_by_token(
    db: AsyncSession, token: str
) -> WorkspaceInvitation | None:
    """Resolve a token to its invite. Returns ``None`` for unknown,
    expired, or already-accepted tokens — caller doesn't need to
    distinguish (all three end with the same 404)."""
    inv = await db.scalar(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token == token)
    )
    if inv is None or inv.accepted_at is not None:
        return None
    if inv.expires_at < datetime.now(timezone.utc):
        return None
    return inv


async def accept_invitation(
    db: AsyncSession, invitation: WorkspaceInvitation, user: User
) -> WorkspaceMember:
    """Materialise an invitation into a workspace_members row.

    Idempotent on the user side: if the user is already a member of
    this workspace we just stamp the invite as accepted (no role
    upgrade — invitations don't change roles, admins do that via
    PATCH /members/{id}).
    """
    existing = await get_member(db, invitation.workspace_id, user.id)
    if existing is not None:
        invitation.accepted_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    member = WorkspaceMember(
        workspace_id=invitation.workspace_id,
        user_id=user.id,
        role=invitation.role,
        invited_by=invitation.invited_by,
    )
    db.add(member)
    invitation.accepted_at = datetime.now(timezone.utc)
    await db.flush()

    # Auto-add as org viewer if they aren't already a member of the
    # workspace's parent org — otherwise the org never appears in the
    # user's org switcher even though they have access to one of its
    # workspaces. Existing org_members are left alone (idempotent).
    workspace = await db.get(Workspace, invitation.workspace_id)
    if workspace is not None:
        await _ensure_org_member(
            db, workspace.organization_id, user.id, ORG_ROLE_VIEWER
        )

    # Ping the inviter so they know the seat is filled.
    if invitation.invited_by is not None:
        try:
            ws = await db.get(Workspace, invitation.workspace_id)
            from app.models.notification import TYPE_MEMBER_INVITED
            from app.modules.runtime.notifications import inbox as inbox_service

            await inbox_service.notify(
                db,
                user_id=invitation.invited_by,
                type=TYPE_MEMBER_INVITED,
                title=f"{user.full_name or user.email} joined {ws.name if ws else 'the workspace'}",
                body=None,
                link_url="/settings/workspace",
                workspace_id=invitation.workspace_id,
                extra={"user_id": str(user.id), "role": invitation.role},
            )
        except Exception:  # noqa: BLE001
            pass
    return member
