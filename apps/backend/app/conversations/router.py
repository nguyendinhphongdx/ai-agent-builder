import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.conversations.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from app.conversations.service import (
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations,
)
from app.conversations.sse import chat_sse
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations_endpoint(  # Lấy danh sách cuộc hội thoại, có thể lọc theo agent_id
    agent_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convs = await list_conversations(db, current_user.id, agent_id)
    return [ConversationResponse.model_validate(c) for c in convs]


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation_endpoint(  # Tạo cuộc hội thoại mới với agent
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await create_conversation(db, current_user.id, body.agent_id, body.title)
    return ConversationResponse.model_validate(conv)


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation_endpoint(  # Lấy chi tiết cuộc hội thoại theo ID
    conv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.post("/{conv_id}/chat")
async def chat_stream_endpoint(  # Gửi tin nhắn và stream phản hồi agent qua SSE
    conv_id: uuid.UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_sse(conv_id, current_user.id, body.content, db)


@router.get("/{conv_id}/messages", response_model=list[MessageResponse])
async def get_messages_endpoint(  # Lấy danh sách tin nhắn với phân trang
    conv_id: uuid.UUID,
    limit: int = Query(100, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Kiểm tra quyền truy cập conversation trước khi lấy tin nhắn
    conv = await get_conversation(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await get_messages(db, conv_id, limit, offset)
    return [MessageResponse.model_validate(m) for m in messages]
