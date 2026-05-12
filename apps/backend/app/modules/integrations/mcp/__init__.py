"""MCP integration status — tells the Settings page whether the user's
chosen token is wired up correctly + previews which tools the MCP server will
register on the host (Claude Desktop / Cursor).
"""
from __future__ import annotations

import re
import unicodedata
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_access_token import PersonalAccessToken
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.studio.agents.service import list_agents
from app.platform.context import current_user_id
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/integrations/mcp",
    tags=["integrations:mcp"],
    dependencies=[Depends(get_current_user)],
)

# Scopes the MCP server requires to call list-agents + chat.
REQUIRED_SCOPES = ["agents:read", "agents:chat"]


# ─── Tool name slugification (mirror packages/mcp-agent/src/tools.ts) ───


def _slugify(name: str) -> str:
    """Match the slugify rule used by the MCP server so the preview
    matches the tool names actually registered on the host."""
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", norm.lower())
    slug = slug.strip("_")[:40]
    return slug or "agent"


# ─── Schemas ────────────────────────────────────────────────────────


class AgentToolPreview(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: uuid.UUID
    name: str
    tool_name: str
    description: str | None
    model_id: str


class McpStatusResponse(BaseModel):
    token_ok: bool
    token_last_used_at: str | None
    required_scopes: list[str]
    missing_scopes: list[str]
    agents: list[AgentToolPreview]


# ─── Endpoint ───────────────────────────────────────────────────────


@router.get("/status", response_model=McpStatusResponse)
async def mcp_status(
    token_id: uuid.UUID = Query(..., description="Personal access token to check"),
    db: AsyncSession = Depends(get_db),
):
    """Verify a token is suitable for the MCP server + preview its tools.

    Cookie-auth only — used by the Settings UI to render the MCP setup page.
    External clients use ``/api/external/agents`` directly.
    """
    # Look up the token, scoped to the current user (no cross-user reads).
    result = await db.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == current_user_id(),
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    missing = [s for s in REQUIRED_SCOPES if s not in (token.scopes or [])]
    token_active = token.revoked_at is None
    token_ok = token_active and not missing

    # Preview tool names — only meaningful when token has the scopes (otherwise
    # the MCP server won't be able to list agents anyway). We still return
    # the preview so the UI can show the tool list right after fixing scopes.
    agents = await list_agents(db)
    previews = [
        AgentToolPreview(
            id=a.id,
            name=a.name,
            tool_name=f"chat_with_{_slugify(a.name)}",
            description=a.description,
            model_id=a.model_id,
        )
        for a in agents
    ]

    return McpStatusResponse(
        token_ok=token_ok,
        token_last_used_at=token.last_used_at.isoformat() if token.last_used_at else None,
        required_scopes=REQUIRED_SCOPES,
        missing_scopes=missing,
        agents=previews,
    )
