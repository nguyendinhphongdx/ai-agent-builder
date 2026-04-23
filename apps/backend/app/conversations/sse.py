"""SSE streaming handler for agent chat."""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import execute_agent_stream
from app.agents.service import get_agent
from app.ai_credentials.service import get_plaintext_key_by_id
from app.conversations.service import get_conversation, get_messages, save_message
from app.models.file import File as FileModel

logger = logging.getLogger("agentforge")


async def _load_user_attachments(
    db: AsyncSession,
    attachment_ids: list[uuid.UUID],
    user_id: uuid.UUID,
) -> list[FileModel]:
    """Load ``File`` rows the caller attached, in the requested order.

    Silently drops IDs not owned by ``user_id`` — stale/invalid IDs from the
    FE shouldn't kill the whole chat turn.
    """
    if not attachment_ids:
        return []

    result = await db.execute(
        select(FileModel).where(
            FileModel.id.in_(attachment_ids),
            FileModel.owner_id == user_id,
        )
    )
    by_id = {f.id: f for f in result.scalars()}
    return [by_id[aid] for aid in attachment_ids if aid in by_id]


def _attachment_meta(files: list[FileModel]) -> list[dict]:
    """Persist just the fields the FE needs to render a history thumbnail."""
    return [
        {
            "id": str(f.id),
            "file_name": f.original_name,
            "mime_type": f.mime_type,
            "size": f.size,
        }
        for f in files
    ]


async def chat_sse(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    db: AsyncSession,
    attachment_ids: list[uuid.UUID] | None = None,
) -> StreamingResponse:
    """Stream agent response as Server-Sent Events."""
    conv = await get_conversation(db, conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent = await get_agent(db, conv.agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    api_key = (
        await get_plaintext_key_by_id(db, agent.credential_id)
        if agent.credential_id
        else None
    )

    logger.info(
        f"chat_sse agent={agent.id} model={agent.model_id} "
        f"credential_id={agent.credential_id} api_key={'<set>' if api_key else '<MISSING>'}"
    )
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Agent chưa có credential cho provider này. "
                "Mở agent editor → tab Model → Connect / chọn credential rồi Save."
            ),
        )

    attachments = await _load_user_attachments(db, attachment_ids or [], user_id)

    # Persist user turn with attachment metadata — history UI reads this to
    # render thumbnails on refresh.
    await save_message(
        db,
        conversation_id,
        role="user",
        content=content,
        attachments=_attachment_meta(attachments),
    )
    await db.commit()

    # Capture for use inside the generator
    _agent = agent
    _api_key = api_key
    _conv_id = conversation_id
    _attachments = attachments

    async def event_generator():
        start_time = time.time()
        full_response = ""

        try:
            history = await get_messages(db, _conv_id, limit=50)

            async for event in execute_agent_stream(
                _agent,
                history,
                db,
                api_key=_api_key,
                current_attachments=_attachments,
            ):
                event_dict = event.to_dict()

                if event.type == "token":
                    full_response += event_dict.get("content", "")
                    yield f"data: {json.dumps(event_dict)}\n\n"
                elif event.type in ("tool_start", "tool_end"):
                    yield f"data: {json.dumps(event_dict)}\n\n"

            latency_ms = int((time.time() - start_time) * 1000)

            if full_response:
                await save_message(
                    db,
                    _conv_id,
                    role="assistant",
                    content=full_response,
                    llm_model=_agent.model_id,
                    latency_ms=latency_ms,
                )
                await db.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("chat_sse stream crashed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
