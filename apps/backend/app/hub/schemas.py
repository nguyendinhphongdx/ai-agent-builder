"""Pydantic schemas for the Agent Hub."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ─── Snapshot shapes (frozen at publish time) ─────────────────────────


class ToolSnapshot(BaseModel):
    """Tool config as recorded inside a template version snapshot."""
    name: str
    description: str
    tool_type: str
    config: dict
    input_schema: dict
    output_schema: dict | None = None
    timeout_seconds: int = 30


class KnowledgeBaseSnapshot(BaseModel):
    """KB config — no documents, only the structure. Buyer uploads their own."""
    name: str
    description: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    chunk_strategy: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None


class AgentSnapshot(BaseModel):
    """Frozen agent config at publish time. No credential / share fields."""
    name: str
    description: str | None = None
    avatar_url: str | None = None
    system_prompt: str
    model_id: str
    llm_config: dict = Field(default_factory=dict)
    welcome_message: str | None = None
    max_turns: int = 50
    kb_retrieval_mode: str = "tool"


class TemplateSnapshot(BaseModel):
    """Top-level snapshot stored in ``agent_template_versions.snapshot``."""
    schema_version: int = 1
    agent: AgentSnapshot
    tools: list[ToolSnapshot] = Field(default_factory=list)
    knowledge_bases: list[KnowledgeBaseSnapshot] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


# ─── Publish / update ─────────────────────────────────────────────────


class TemplatePublishRequest(BaseModel):
    """Request body for ``POST /agents/{id}/publish``."""
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    author_name: str | None = Field(default=None, max_length=100)  # defaults to user.name
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] = Field(default_factory=list)
    cover_image_url: str | None = None
    price_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class TemplateUpdateRequest(BaseModel):
    """Patch metadata of an existing template (owner only). Snapshot stays frozen."""
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    author_name: str | None = Field(default=None, max_length=100)
    category: str | None = None
    tags: list[str] | None = None
    cover_image_url: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    status: str | None = None  # 'published' | 'archived'


# ─── Responses ────────────────────────────────────────────────────────


class TemplateSummary(BaseModel):
    """Card-shaped row for the Hub list view."""
    id: uuid.UUID
    slug: str
    title: str
    description: str | None
    author_name: str
    category: str | None
    tags: list[str]
    cover_image_url: str | None
    price_cents: int
    currency: str
    is_featured: bool
    fork_count: int
    rating_avg: Decimal | None
    rating_count: int
    published_at: datetime | None

    model_config = {"from_attributes": True}


class TemplateDetail(TemplateSummary):
    """Detail page — adds the current snapshot so buyers can preview."""
    user_id: uuid.UUID
    status: str
    snapshot: dict | None = None  # current version's snapshot
    current_version: str | None = None
    created_at: datetime
    updated_at: datetime


class TemplateVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version: str
    changelog: str | None
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishVersionRequest(BaseModel):
    """Author publishes a new version of an existing template.

    ``bump`` decides the semver step from the previous version. Pass an
    explicit ``version`` to override (e.g. for going from ``0.x`` to ``1.0``).
    """
    bump: str = Field(default="patch", pattern="^(patch|minor|major)$")
    version: str | None = None  # explicit override
    changelog: str | None = Field(default=None, max_length=5000)


class ForkResponse(BaseModel):
    """Returned to the buyer after a successful fork — points at the new agent."""
    agent_id: uuid.UUID
    template_id: uuid.UUID
    version_id: uuid.UUID
    purchase_id: uuid.UUID


# ─── Browse / search ──────────────────────────────────────────────────


class TemplateBrowseResponse(BaseModel):
    """Paginated browse results."""
    items: list[TemplateSummary]
    total: int
    has_more: bool


# ─── Reviews ──────────────────────────────────────────────────────────


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None = None  # populated server-side from join
    rating: int
    body: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
