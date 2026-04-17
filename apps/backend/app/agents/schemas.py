import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import AppBaseModel


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_config: dict = {}
    welcome_message: str | None = None
    max_turns: int = 50
    kb_retrieval_mode: str = "tool"


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
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
    total_documents: int


class AgentResponse(AppBaseModel):
    __storage_fields__ = ("avatar_url",)

    id: uuid.UUID
    name: str
    description: str | None
    avatar_url: str | None
    system_prompt: str
    llm_provider: str
    llm_model: str
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
    llm_provider: str
    llm_model: str
    status: str
    is_published: bool
    created_at: datetime
