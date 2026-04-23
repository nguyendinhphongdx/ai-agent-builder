import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import AppBaseModel


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str
    model_id: str = "openai/gpt-4o"
    credential_id: uuid.UUID | None = None
    llm_config: dict = {}
    welcome_message: str | None = None
    max_turns: int = 50
    kb_retrieval_mode: str = "tool"


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model_id: str | None = None
    credential_id: uuid.UUID | None = None
    llm_config: dict | None = None
    welcome_message: str | None = None
    max_turns: int | None = None
    status: str | None = None
    is_published: bool | None = None
    avatar_url: str | None = None
    kb_retrieval_mode: str | None = None


class ToolBrief(AppBaseModel):
    id: uuid.UUID
    name: str
    description: str
    tool_type: str


class KnowledgeBaseBrief(AppBaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    embedding_provider: str
    embedding_model: str
    total_documents: int
    total_chunks: int


class AgentResponse(AppBaseModel):
    __storage_fields__ = ("avatar_url",)

    id: uuid.UUID
    name: str
    description: str | None
    avatar_url: str | None
    system_prompt: str
    model_id: str
    credential_id: uuid.UUID | None
    llm_config: dict
    welcome_message: str | None
    max_turns: int
    kb_retrieval_mode: str
    is_published: bool
    status: str
    tools: list[ToolBrief] = []
    knowledge_bases: list[KnowledgeBaseBrief] = []
    created_at: datetime
    updated_at: datetime


class AgentListResponse(AppBaseModel):
    __storage_fields__ = ("avatar_url",)

    id: uuid.UUID
    name: str
    description: str | None
    avatar_url: str | None
    model_id: str
    credential_id: uuid.UUID | None
    status: str
    is_published: bool
    created_at: datetime
