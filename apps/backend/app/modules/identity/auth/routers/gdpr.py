"""GDPR-lite endpoints — data export + account delete.

Mandated by Nghị định 13/2023/NĐ-CP (and equivalent GDPR Articles 15
+ 17). The Privacy Policy promises these — the endpoints back them.

* GET    /api/auth/me/export  — JSON of every personal-data row we
                                hold about the caller. Synchronous;
                                fine for small accounts. Large
                                tenants would graduate to "email a
                                signed download link" — out of scope
                                for v1.

* DELETE /api/auth/me         — hard-delete the caller's user row.
                                FK cascades sweep agents / KBs /
                                conversations / tokens / credentials.
                                Workspace memberships drop too (the
                                workspace itself stays; other members
                                keep working). Stripe customer + sub
                                are NOT auto-cancelled — we leave that
                                to the org-owner flow so a single
                                member self-deleting doesn't kill
                                billing for the whole team.

Two-step delete prevents accident: caller posts ``{"confirm": email}``
matching their own address. Same pattern Stripe + Linear use.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.modules.identity.auth._internal import AUTH_USER_LIMIT
from app.modules.identity.auth.dependencies import get_current_user
from app.platform.db.session import get_db

logger = logging.getLogger("agentforge")

router = APIRouter()


# ─── Data export (Right to Access) ──────────────────────────────────


@router.get("/me/export", dependencies=[AUTH_USER_LIMIT])
async def export_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single JSON blob with every personal-data row tied to
    the caller's user id.

    Includes metadata only for sensitive child resources — encrypted
    API keys, MFA secrets, and hashed passwords stay opaque (their
    plaintext was never available to us in the first place, and
    leaking the hash would just shift the attack surface).

    Pagination intentionally omitted — for power users with tens of
    thousands of rows we'll add an async-email-link variant later.
    """
    from app.models.agent import Agent
    from app.models.ai_credential import AICredential
    from app.models.conversation import Conversation
    from app.models.knowledge_base import KnowledgeBase
    from app.models.personal_access_token import PersonalAccessToken
    from app.models.tool import Tool
    from app.models.workspace_member import WorkspaceMember

    profile = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": (
            user.last_login_at.isoformat() if user.last_login_at else None
        ),
        "mfa_enabled": user.mfa_enabled,
        "default_workspace_id": (
            str(user.default_workspace_id) if user.default_workspace_id else None
        ),
        "default_organization_id": (
            str(user.default_organization_id)
            if user.default_organization_id
            else None
        ),
    }

    async def _rows(model, attrs: tuple[str, ...]):
        rows = (
            await db.execute(select(model).where(model.user_id == user.id))
        ).scalars()
        return [{a: _serialise(getattr(r, a, None)) for a in attrs} for r in rows]

    agents = await _rows(
        Agent,
        ("id", "name", "description", "model_id", "system_prompt", "created_at"),
    )
    tools = await _rows(
        Tool, ("id", "name", "description", "tool_type", "created_at")
    )
    kbs = await _rows(
        KnowledgeBase,
        ("id", "name", "description", "chunk_size", "created_at"),
    )
    conversations = await _rows(
        Conversation, ("id", "title", "agent_id", "created_at")
    )
    creds = (
        await db.execute(
            select(AICredential).where(AICredential.user_id == user.id)
        )
    ).scalars()
    credentials_meta = [
        {
            "id": str(c.id),
            "provider": c.provider,
            "name": c.name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            # encrypted_key intentionally omitted — opaque ciphertext.
        }
        for c in creds
    ]
    pats = (
        await db.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.user_id == user.id
            )
        )
    ).scalars()
    pat_meta = [
        {
            "id": str(t.id),
            "name": t.name,
            "scopes": t.scopes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_used_at": (
                t.last_used_at.isoformat() if t.last_used_at else None
            ),
        }
        for t in pats
    ]
    memberships = (
        await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
        )
    ).scalars()
    membership_rows = [
        {
            "workspace_id": str(m.workspace_id),
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in memberships
    ]

    return {
        "exported_at": None,  # set below to a UTC ISO timestamp
        "profile": profile,
        "agents": agents,
        "tools": tools,
        "knowledge_bases": kbs,
        "conversations": conversations,
        "ai_credentials": credentials_meta,
        "personal_access_tokens": pat_meta,
        "workspace_memberships": membership_rows,
    } | {"exported_at": _utc_now_iso()}


# ─── Account delete (Right to Erasure) ──────────────────────────────


class DeleteAccountRequest(BaseModel):
    # Match-your-own-email confirm. Same pattern Stripe + Linear use
    # — far cheaper than a multi-step email loop and just as effective
    # against accidents (the request can't be triggered by a JS prompt
    # that silently steals focus, only by a typed string match).
    confirm: str


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    body: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete the caller's user row. Cascades through agents,
    tools, KBs, conversations, credentials, personal access tokens,
    and workspace memberships.

    Org-owned resources (workspaces the user is a member of but does
    not own personally, the org itself, the org subscription) are NOT
    deleted — a self-leaving member must not be able to nuke their
    employer's billing. The user is removed from the membership
    table; another owner remains in charge.

    No grace period in v1 — once the row is gone, it's gone. A future
    iteration can flip this to "soft delete with 30-day undo" by
    adding a ``deleted_at`` column on users + service-layer filter.
    Until then, the front-end confirm dialog is the safety net.
    """
    if body.confirm.strip().lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation email does not match",
        )

    logger.info("gdpr.account.delete user_id=%s email=%s", user.id, user.email)

    # Delete by id rather than session.delete() — the loaded ORM
    # object holds relationships that would issue extra SELECTs.
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()


# ─── helpers ────────────────────────────────────────────────────────


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _serialise(value):
    """JSON-safe serialiser for ORM column values."""
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    if value is None:
        return None
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
