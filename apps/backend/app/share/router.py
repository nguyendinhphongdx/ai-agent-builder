"""Public ``/api/share/*`` endpoints — no auth, used by the embed widget.

Auth model: the URL path itself carries an opaque ``share_token`` minted by
the agent owner. There is no user identity here — every conversation is
created/owned by the agent's owner. Anti-abuse is handled by the per-IP
rate limit dependency mounted at the router level.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import execute_agent_stream
from app.ai_credentials.service import get_plaintext_key_by_id
from app.conversations.service import (
    create_conversation,
    get_conversation,
    get_messages,
    save_message,
)
from app.db.session import get_db
from app.rate_limit import enforce_share_rate_limit
from app.share.schemas import (
    ShareChatRequest,
    ShareChatResponse,
    SharedAgentInfo,
)
from app.share.service import get_agent_by_share_token

logger = logging.getLogger("agentforge")

router = APIRouter(
    prefix="/share",
    tags=["share"],
    dependencies=[Depends(enforce_share_rate_limit)],
)


async def _resolve_or_create_conv(
    db: AsyncSession,
    agent_id: uuid.UUID,
    owner_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    title_seed: str,
):
    """Pin a conversation under the agent owner so it shows up in the dashboard.

    Anonymous callers can pass back ``conversation_id`` to keep the thread, but
    we still verify it belongs to *this* agent — preventing token abuse to
    inject into someone else's conversation.
    """
    if conversation_id:
        conv = await get_conversation(db, conversation_id, owner_id)
        if not conv or conv.agent_id != agent_id:
            raise HTTPException(404, "Conversation not found")
        return conv

    title = title_seed[:80] + ("…" if len(title_seed) > 80 else "")
    return await create_conversation(db, owner_id, agent_id, title)


@router.get("/{share_token}/agent", response_model=SharedAgentInfo)
async def get_shared_agent(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the public-facing info widget needs to render."""
    agent = await get_agent_by_share_token(db, share_token)
    if not agent:
        raise HTTPException(404, "Share link not found or revoked")
    return SharedAgentInfo(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        avatar_url=agent.avatar_url,
        welcome_message=agent.welcome_message,
        settings=agent.share_settings or {},
    )


@router.post("/{share_token}/chat", response_model=ShareChatResponse)
async def share_chat_sync(
    share_token: str,
    body: ShareChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Sync chat — wait for the full response, return as JSON."""
    agent = await get_agent_by_share_token(db, share_token)
    if not agent:
        raise HTTPException(404, "Share link not found or revoked")

    api_key = (
        await get_plaintext_key_by_id(db, agent.credential_id)
        if agent.credential_id
        else None
    )
    if not api_key:
        # Don't leak provider/credential details to anonymous callers.
        raise HTTPException(503, "Agent unavailable")

    conv = await _resolve_or_create_conv(
        db, agent.id, agent.user_id, body.conversation_id, body.message
    )

    await save_message(db, conv.id, role="user", content=body.message)
    await db.commit()

    history = await get_messages(db, conv.id, limit=50)
    started = time.time()
    full = ""
    async for event in execute_agent_stream(agent, history, db, api_key=api_key):
        if event.type == "token":
            full += event.data.get("content", "")

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

    return ShareChatResponse(
        conversation_id=conv.id,
        message_id=msg.id,
        response=full,
        latency_ms=latency_ms,
    )


@router.post("/{share_token}/stream")
async def share_chat_stream(
    share_token: str,
    body: ShareChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream agent response as Server-Sent Events.

    Mirrors the internal SSE handler but bypasses user-ownership checks since
    the share token is the only auth.
    """
    agent = await get_agent_by_share_token(db, share_token)
    if not agent:
        raise HTTPException(404, "Share link not found or revoked")

    api_key = (
        await get_plaintext_key_by_id(db, agent.credential_id)
        if agent.credential_id
        else None
    )
    if not api_key:
        raise HTTPException(503, "Agent unavailable")

    conv = await _resolve_or_create_conv(
        db, agent.id, agent.user_id, body.conversation_id, body.message
    )

    await save_message(db, conv.id, role="user", content=body.message)
    await db.commit()

    _agent = agent
    _api_key = api_key
    _conv_id = conv.id

    async def event_generator():
        start = time.time()
        full = ""
        try:
            # First event: hand the conversation_id back so the widget can
            # persist it for follow-up turns. Saves a round-trip.
            yield f"data: {json.dumps({'type': 'meta', 'conversation_id': str(_conv_id)})}\n\n"

            history = await get_messages(db, _conv_id, limit=50)
            async for event in execute_agent_stream(
                _agent, history, db, api_key=_api_key
            ):
                event_dict = event.to_dict()
                if event.type == "token":
                    full += event_dict.get("content", "")
                    yield f"data: {json.dumps(event_dict)}\n\n"
                elif event.type in ("tool_start", "tool_end"):
                    yield f"data: {json.dumps(event_dict)}\n\n"

            latency_ms = int((time.time() - start) * 1000)
            if full:
                await save_message(
                    db,
                    _conv_id,
                    role="assistant",
                    content=full,
                    llm_model=_agent.model_id,
                    latency_ms=latency_ms,
                )
                await db.commit()
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as exc:
            logger.exception("share stream crashed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
