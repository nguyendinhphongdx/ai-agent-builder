import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    """Schema tạo cuộc hội thoại mới."""
    agent_id: uuid.UUID
    title: str | None = None


class ConversationResponse(BaseModel):
    """Schema trả về thông tin cuộc hội thoại kèm thống kê."""
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None
    is_pinned: bool
    is_archived: bool
    total_messages: int
    total_tokens: int
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    """Schema gửi tin nhắn mới."""
    content: str


class ChatRequest(BaseModel):
    """Schema gửi tin nhắn tới agent qua SSE."""
    content: str
    #: Storage ``file.id`` đã upload trước đó. BE sẽ:
    #: - Doc types → extract text, inject vào prompt (current turn).
    #: - Image types → fetch bytes, build base64 image block (current turn).
    attachment_ids: list[uuid.UUID] = []


class MessageAttachment(BaseModel):
    """Metadata lưu trong ``messages.attachments`` (JSONB) + trả về cho FE."""
    id: uuid.UUID
    file_name: str
    mime_type: str | None = None
    size: int | None = None


class MessageResponse(BaseModel):
    """Schema trả về tin nhắn kèm metadata (token usage, latency, tool calls, ...)."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str  # "user", "assistant", hoặc "tool"
    content: str
    content_type: str  # "text", "image", ...
    tool_calls: dict | None = None
    tool_name: str | None = None
    attachments: list[MessageAttachment] = []
    token_usage: dict | None = None  # {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
    latency_ms: int | None = None  # Thời gian phản hồi từ LLM (ms)
    llm_model: str | None = None
    feedback: str | None = None  # "up" hoặc "down" từ user
    created_at: datetime

    model_config = {"from_attributes": True}
