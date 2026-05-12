"""SSE streaming handler for agent chat."""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File as FileModel
from app.modules.integrations.llm.credentials.service import get_plaintext_key_by_id
from app.modules.runtime.chat.conversations.service import (
    get_conversation,
    get_messages,
    save_message,
)
from app.modules.studio.agents.executor import execute_agent_stream
from app.modules.studio.agents.service import get_agent

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
    request: "Request | None" = None,
) -> StreamingResponse:
    """Stream agent response as Server-Sent Events."""
    # `get_conversation` reads the user from request context — caller still
    # passes user_id explicitly because SSE may outlive the immediate request
    # task and we want the user to be resolved before streaming starts.
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    agent = await get_agent(db, conv.agent_id)
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

    # Enforce token quota before saving the user turn. Done after
    # agent/api-key checks so a misconfigured agent still 400s with
    # the right message rather than a misleading 402.
    from app.modules.commerce.payments.subscriptions.quota import enforce_tokens

    await enforce_tokens(db, workspace_id=None)  # ContextVar resolves it

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
        from app.modules.commerce.usage import service as usage_service

        start_time = time.time()
        full_response = ""
        client_gone = False
        # Captured from the executor's `on_chat_model_end` event so
        # we can write a usage row alongside the assistant message.
        # The executor emits it once per LLM call — agents with tool
        # loops can emit multiple, but for v1 we record the last one
        # (single-turn cost) and let analytics interpret.
        usage_payload: dict | None = None

        try:
            history = await get_messages(db, _conv_id, limit=50)

            async for event in execute_agent_stream(
                _agent,
                history,
                db,
                api_key=_api_key,
                current_attachments=_attachments,
            ):
                # Cancel-on-disconnect: stop pulling tokens from the LLM
                # the moment the browser tab closed. Without this we'd
                # burn the owner's credit on a response no one will see.
                if request is not None and await request.is_disconnected():
                    client_gone = True
                    logger.info(
                        f"chat_sse client disconnected — aborting stream "
                        f"conv={_conv_id} after {len(full_response)} chars"
                    )
                    break

                event_dict = event.to_dict()

                if event.type == "token":
                    full_response += event_dict.get("content", "")
                    yield f"data: {json.dumps(event_dict)}\n\n"
                elif event.type in ("tool_start", "tool_end"):
                    yield f"data: {json.dumps(event_dict)}\n\n"
                elif event.type == "usage":
                    # Don't forward to the client — token counts are
                    # ops/billing telemetry, not user-facing data.
                    usage_payload = event_dict

            latency_ms = int((time.time() - start_time) * 1000)

            # Always persist whatever we collected — even partial responses
            # from a disconnected client are valuable history (and prevent
            # an orphan user message in the conversation).
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

            # Record the LLM call for cost/usage analytics. Skipped
            # silently when the LLM didn't surface usage_metadata
            # (Ollama, some self-hosted setups). usage_service swallows
            # write failures so a telemetry hiccup never breaks chat.
            event_row = None
            if usage_payload is not None:
                event_row = await usage_service.log_llm_call(
                    db,
                    model_id=usage_payload.get("model_id") or _agent.model_id,
                    prompt_tokens=usage_payload.get("prompt_tokens"),
                    completion_tokens=usage_payload.get("completion_tokens"),
                    latency_ms=latency_ms,
                    agent_id=_agent.id,
                    conversation_id=_conv_id,
                    workspace_id=_agent.workspace_id,
                    user_id=user_id,
                )
                await db.commit()

            # Mirror to the LLM-specific trace provider (Langfuse /
            # LangSmith / Phoenix) when configured. Provider's
            # ``emit`` swallows exceptions; this never blocks chat.
            if usage_payload is not None and full_response:
                from app.platform.observability.trace_provider import get_provider
                from app.platform.observability.trace_provider.base import LLMTrace

                await get_provider().emit(
                    LLMTrace(
                        name="agent.chat",
                        model_id=usage_payload.get("model_id") or _agent.model_id,
                        messages=[
                            {"role": m.role, "content": m.content}
                            for m in history
                        ],
                        output=full_response,
                        prompt_tokens=usage_payload.get("prompt_tokens"),
                        completion_tokens=usage_payload.get("completion_tokens"),
                        total_tokens=usage_payload.get("total_tokens"),
                        cost_usd=(
                            float(event_row.cost_usd)
                            if event_row is not None and event_row.cost_usd is not None
                            else None
                        ),
                        latency_ms=latency_ms,
                        workspace_id=_agent.workspace_id,
                        user_id=user_id,
                        agent_id=_agent.id,
                        conversation_id=_conv_id,
                    )
                )

            if not client_gone:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("chat_sse stream crashed")
            if not client_gone:
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
