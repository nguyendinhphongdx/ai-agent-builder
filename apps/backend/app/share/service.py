"""Share-token lifecycle helpers + lookup by token."""
from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent


def _mint_token() -> str:
    """43-char URL-safe token (`secrets.token_urlsafe(32)`).

    Long enough that brute-force is hopeless; URL-safe so it works in widget
    `data-token` attributes and config snippets without escaping.
    """
    return secrets.token_urlsafe(32)


async def get_agent_by_share_token(
    db: AsyncSession, token: str
) -> Agent | None:
    """Resolve a public share token to its agent. Returns None when revoked
    or unknown."""
    if not token:
        return None
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools), selectinload(Agent.knowledge_bases))
        .where(Agent.share_token == token)
    )
    return result.scalar_one_or_none()


async def enable_share(db: AsyncSession, agent: Agent, *, rotate: bool = False) -> Agent:
    """Mint a share token if missing, or rotate when explicitly asked."""
    if rotate or not agent.share_token:
        agent.share_token = _mint_token()
    await db.flush()
    await db.refresh(agent)
    return agent


async def disable_share(db: AsyncSession, agent: Agent) -> Agent:
    """Revoke share access — clears the token. Does NOT touch share_settings,
    so re-enabling later restores the same theme."""
    agent.share_token = None
    await db.flush()
    await db.refresh(agent)
    return agent


async def update_share_settings(
    db: AsyncSession, agent: Agent, settings: dict
) -> Agent:
    """Replace share_settings wholesale. Caller validates shape (free-form JSON)."""
    agent.share_settings = settings or {}
    await db.flush()
    await db.refresh(agent)
    return agent
