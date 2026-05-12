import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.platform.context import current_user_id, current_workspace_id_or_none


def _scope_filter(stmt):
    """Restrict to conversations in the current workspace."""
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return stmt
    return stmt.where(Conversation.workspace_id == workspace_id)


async def list_conversations(
    db: AsyncSession, agent_id: uuid.UUID | None = None
) -> list[Conversation]:
    """Lấy danh sách cuộc hội thoại chưa lưu trữ, sắp xếp theo tin nhắn mới nhất.

    Có thể lọc theo agent_id nếu được cung cấp.
    """
    q = select(Conversation).where(
        Conversation.user_id == current_user_id(),
        Conversation.is_archived == False,  # noqa: E712
    )
    if agent_id:
        q = q.where(Conversation.agent_id == agent_id)
    q = q.order_by(Conversation.last_message_at.desc().nullslast())
    result = await db.execute(_scope_filter(q))
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, conv_id: uuid.UUID
) -> Conversation | None:
    """Lấy cuộc hội thoại theo ID, chỉ trả về nếu thuộc về user hiện tại."""
    stmt = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == current_user_id(),
    )
    result = await db.execute(_scope_filter(stmt))
    return result.scalar_one_or_none()


async def create_conversation(
    db: AsyncSession, agent_id: uuid.UUID, title: str | None = None
) -> Conversation:
    """Tạo cuộc hội thoại mới giữa user hiện tại và agent.

    ``workspace_id`` is pinned from the agent's workspace — keeps the
    conversation tagged with the agent's tenant even when the caller's
    active workspace differs (matters for share/embed channel where
    the agent owner may not be the request's authenticated user).
    """
    agent_workspace_id = await db.scalar(
        select(Agent.workspace_id).where(Agent.id == agent_id)
    )
    conv = Conversation(
        user_id=current_user_id(),
        agent_id=agent_id,
        workspace_id=agent_workspace_id,
        title=title,
    )
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

    Denormalises ``workspace_id`` from the parent conversation so
    message-level cost/usage queries don't need a JOIN to filter
    by tenant.
    """
    # Pull the parent's workspace_id in the same query that drives
    # the counter bump — saves a round-trip.
    parent_workspace_id = await db.scalar(
        select(Conversation.workspace_id).where(Conversation.id == conversation_id)
    )
    kwargs.setdefault("workspace_id", parent_workspace_id)
    msg = Message(conversation_id=conversation_id, role=role, content=content, **kwargs)
    db.add(msg)

    # Atomic counter bump — concurrent SSE/WS streams won't lose updates.
    values = {
        "total_messages": Conversation.total_messages + 1,
        "last_message_at": datetime.now(timezone.utc),
    }
    if kwargs.get("token_usage"):
        added = kwargs["token_usage"].get("total_tokens", 0) or 0
        if added:
            values["total_tokens"] = Conversation.total_tokens + added

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(**values)
    )

    await db.flush()
    await db.refresh(msg)
    return msg
