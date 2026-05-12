"""Public ``/external/conversations/*`` — list + read history."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.api.external.schemas import ConversationSummary, MessageOut
from app.modules.identity.auth.dependencies import get_current_user, require_scope
from app.modules.runtime.chat.conversations.service import (
    get_conversation,
    get_messages,
    list_conversations,
)
from app.platform.db.session import get_db

# Auth gate runs once per request — `get_current_user` resolves the bearer
# token and writes the user to `app.platform.context`, so endpoints/services don't have
# to thread it through.
router = APIRouter(
    prefix="/conversations",
    tags=["external:conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    response_model=list[ConversationSummary],
    dependencies=[Depends(require_scope("conversations:read"))],
)
async def list_endpoint(
    agent_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    convs = await list_conversations(db, agent_id)
    return [ConversationSummary.model_validate(c, from_attributes=True) for c in convs]


@router.get(
    "/{conv_id}/messages",
    response_model=list[MessageOut],
    dependencies=[Depends(require_scope("conversations:read"))],
)
async def messages_endpoint(
    conv_id: uuid.UUID,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    msgs = await get_messages(db, conv_id, limit, offset)
    return [MessageOut.model_validate(m, from_attributes=True) for m in msgs]
