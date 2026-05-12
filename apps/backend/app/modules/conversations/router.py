import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user
from app.modules.conversations.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from app.modules.conversations.service import (
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations,
)
from app.modules.conversations.sse import chat_sse
from app.platform.context import current_user_id
from app.platform.db.session import get_db
from app.platform.rate_limit import make_limit

# Auth gate runs once per request via router-level dependency: it resolves the
# user (cookie or Bearer token) and stamps `app.platform.context.current_user_id` for
# the rest of the request's coroutines. Endpoints don't need to repeat it.
router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations_endpoint(  # Lấy danh sách cuộc hội thoại, có thể lọc theo agent_id
    agent_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    convs = await list_conversations(db, agent_id)
    return [ConversationResponse.model_validate(c) for c in convs]


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation_endpoint(  # Tạo cuộc hội thoại mới với agent
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    conv = await create_conversation(db, body.agent_id, body.title)
    return ConversationResponse.model_validate(conv)


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation_endpoint(  # Lấy chi tiết cuộc hội thoại theo ID
    conv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.post("/{conv_id}/chat", dependencies=[Depends(make_limit("chat", 60))])
async def chat_stream_endpoint(  # Gửi tin nhắn và stream phản hồi agent qua SSE
    conv_id: uuid.UUID,
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # SSE is long-running and may outlive the calling task — pass user_id
    # explicitly so the stream doesn't depend on contextvars during streaming.
    # Pass `request` so the generator can detect client disconnect and stop
    # pulling tokens (otherwise we'd keep paying the LLM after browser closed).
    return await chat_sse(
        conv_id, current_user_id(), body.content, db, body.attachment_ids,
        request=request,
    )


@router.get("/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages_endpoint(  # Lấy danh sách tin nhắn với phân trang
    conv_id: uuid.UUID,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Ownership check still happens via get_conversation (reads context).
    conv = await get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_messages(db, conv_id, limit, offset)
    return [MessageResponse.model_validate(m) for m in messages]
