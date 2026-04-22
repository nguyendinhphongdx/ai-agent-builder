"""SSE streaming handler for agent chat."""
from __future__ import annotations

import json
import time
import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.executor import execute_agent_stream
from app.agents.service import get_agent
from app.ai_credentials.service import get_plaintext_key_by_id
from app.conversations.service import get_conversation, get_messages, save_message


async def chat_sse(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
    db: AsyncSession,
) -> StreamingResponse:
    """Stream agent response as Server-Sent Events."""
    conv = await get_conversation(db, conversation_id, user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent = await get_agent(db, conv.agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    api_key = await get_plaintext_key_by_id(db, agent.credential_id) if agent.credential_id else None

    await save_message(db, conversation_id, role="user", content=content)
    await db.commit()

    # Capture for use inside the generator
    _agent = agent
    _api_key = api_key
    _conv_id = conversation_id

    async def event_generator():
        start_time = time.time()
        full_response = ""

        try:
            history = await get_messages(db, _conv_id, limit=50)

            async for event in execute_agent_stream(_agent, history, db, api_key=_api_key):
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
