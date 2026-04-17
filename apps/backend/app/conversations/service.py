import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def list_conversations(
    db: AsyncSession, user_id: uuid.UUID, agent_id: uuid.UUID | None = None
) -> list[Conversation]:
    """Lấy danh sách cuộc hội thoại chưa lưu trữ, sắp xếp theo tin nhắn mới nhất.

    Có thể lọc theo agent_id nếu được cung cấp.
    """
    q = select(Conversation).where(
        Conversation.user_id == user_id, Conversation.is_archived == False  # noqa: E712
    )
    if agent_id:
        q = q.where(Conversation.agent_id == agent_id)
    q = q.order_by(Conversation.last_message_at.desc().nullslast())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, conv_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    """Lấy cuộc hội thoại theo ID, chỉ trả về nếu thuộc về user hiện tại."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_conversation(
    db: AsyncSession, user_id: uuid.UUID, agent_id: uuid.UUID, title: str | None = None
) -> Conversation:
    """Tạo cuộc hội thoại mới giữa user và agent."""
    conv = Conversation(user_id=user_id, agent_id=agent_id, title=title)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def get_messages(
    db: AsyncSession, conv_id: uuid.UUID, limit: int = 100, offset: int = 0
) -> list[Message]:
    """Lấy danh sách tin nhắn theo thứ tự thời gian, hỗ trợ phân trang."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def save_message(
    db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str, **kwargs
) -> Message:
    """Lưu tin nhắn mới và cập nhật bộ đếm trên conversation.

    Tự động tăng total_messages, cập nhật last_message_at,
    và cộng dồn total_tokens nếu có thông tin token_usage.
    """
    msg = Message(conversation_id=conversation_id, role=role, content=content, **kwargs)
    db.add(msg)

    # Cập nhật bộ đếm trên conversation (số tin nhắn, thời gian, token)
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        conv.total_messages = (conv.total_messages or 0) + 1
        conv.last_message_at = datetime.now(timezone.utc)
        if kwargs.get("token_usage"):
            usage = kwargs["token_usage"]
            conv.total_tokens = (conv.total_tokens or 0) + usage.get("total_tokens", 0)

    await db.flush()
    await db.refresh(msg)
    return msg
