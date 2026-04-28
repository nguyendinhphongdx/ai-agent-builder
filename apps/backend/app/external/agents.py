"""Public ``/external/agents/*`` endpoints — list + chat (sync + stream).

All endpoints in this file are scope-guarded for API tokens. Cookie sessions
bypass scope checks (the user is the resource owner).
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import execute_agent_stream
from app.agents.service import get_agent, list_agents
from app.ai_credentials.service import get_plaintext_key_by_id
from app.auth.dependencies import get_current_user, require_scope
from app.conversations.service import (
    create_conversation,
    get_conversation,
    get_messages,
    save_message,
)
from app.db.session import get_db
from app.external.schemas import AgentSummary, ChatRequest, ChatResponse
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["external:agents"])


@router.get(
    "",
    response_model=list[AgentSummary],
    dependencies=[Depends(require_scope("agents:read"))],
)
async def list_agents_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agents accessible to the caller."""
    agents = await list_agents(db, current_user.id)
    return [AgentSummary.model_validate(a, from_attributes=True) for a in agents]


@router.post(
    "/{agent_id}/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_scope("agents:chat"))],
)
async def chat_sync(
    agent_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync chat — wait for the full response, return it as JSON.

    For streaming, use ``POST /external/agents/{id}/stream`` instead.
    """
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    api_key = (
        await get_plaintext_key_by_id(db, agent.credential_id)
        if agent.credential_id
        else None
    )
    if not api_key:
        raise HTTPException(
            400,
            "Agent has no credential configured for its provider — open the agent "
            "editor and connect a credential before chatting.",
        )

    # Resolve / create conversation (must belong to the same user)
    if body.conversation_id:
        conv = await get_conversation(db, body.conversation_id, current_user.id)
        if not conv or conv.agent_id != agent_id:
            raise HTTPException(404, "Conversation not found")
    else:
        title = body.message[:80] + ("…" if len(body.message) > 80 else "")
        conv = await create_conversation(db, current_user.id, agent_id, title)

    # Save user turn
    await save_message(db, conv.id, role="user", content=body.message)
    await db.commit()

    # Run agent and accumulate full response
    history = await get_messages(db, conv.id, limit=50)
    started = time.time()
    full = ""
    async for event in execute_agent_stream(agent, history, db, api_key=api_key):
        if event.type == "token":
            full += event.data.get("content", "")
        # tool_start / tool_end / done — ignored in sync mode

    latency_ms = int((time.time() - started) * 1000)
    msg = await save_message(
        db,
        conv.id,
        role="assistant",
        content=full,
        llm_model=agent.model_id,
        latency_ms=latency_ms,
    )
    await db.commit()

    return ChatResponse(
        conversation_id=conv.id,
        message_id=msg.id,
        response=full,
        latency_ms=latency_ms,
    )


@router.post(
    "/{agent_id}/stream",
    dependencies=[Depends(require_scope("agents:chat"))],
)
async def chat_stream(
    agent_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Streaming chat — Server-Sent Events. Same auth + payload as ``/chat``.

    Reuses the existing ``chat_sse`` handler so behaviour is identical to the
    internal browser-facing stream.
    """
    from app.conversations.sse import chat_sse  # local import to avoid cycle

    # Reuse internal SSE handler. It expects an existing conversation, so
    # create one first if the caller didn't supply an id.
    if body.conversation_id is None:
        agent = await get_agent(db, agent_id, current_user.id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        title = body.message[:80] + ("…" if len(body.message) > 80 else "")
        conv = await create_conversation(db, current_user.id, agent_id, title)
        await db.commit()
        conv_id = conv.id
    else:
        conv = await get_conversation(db, body.conversation_id, current_user.id)
        if not conv or conv.agent_id != agent_id:
            raise HTTPException(404, "Conversation not found")
        conv_id = conv.id

    return await chat_sse(conv_id, current_user.id, body.message, db)
