"""Build + restore template snapshots.

Publishing walks an Agent + its tools + KB shells into a frozen
``TemplateSnapshot`` (Pydantic). Forking reads the snapshot and clones
each piece into the buyer's namespace.

Explicitly NOT included in the snapshot:
- ``credential_id`` — buyer must connect their own AI credential.
- ``share_token`` / ``share_settings`` — different concept from publishing.
- KB documents — would balloon storage and may contain private data.
- Tool ``user_id`` — re-stamped as buyer on fork.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.context import current_user_id
from app.hub.schemas import (
    AgentSnapshot,
    KnowledgeBaseSnapshot,
    TemplateSnapshot,
    ToolSnapshot,
)
from app.models.agent import Agent, AgentKnowledgeBase, AgentTool
from app.models.knowledge_base import KnowledgeBase
from app.models.tool import Tool


# ─── Build snapshot from a live agent ─────────────────────────────────


async def build_snapshot_from_agent(db: AsyncSession, agent: Agent) -> TemplateSnapshot:
    """Serialise an Agent + its attached tools + KB shells into a frozen snapshot.

    Caller must ensure the agent belongs to the publishing user (router does
    this via ``get_agent`` before calling).
    """
    # Tools — eager loaded by Agent.tools relationship (lazy='selectin')
    tool_snapshots = [
        ToolSnapshot(
            name=t.name,
            description=t.description,
            tool_type=t.tool_type,
            config=t.config or {},
            input_schema=t.input_schema or {"type": "object", "properties": {}},
            output_schema=t.output_schema,
            timeout_seconds=t.timeout_seconds or 30,
        )
        for t in (agent.tools or [])
    ]

    # KBs — snapshot config only, NOT documents
    kb_snapshots = [
        KnowledgeBaseSnapshot(
            name=kb.name,
            description=kb.description,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            chunk_strategy=kb.chunk_strategy,
            embedding_provider=kb.embedding_provider,
            embedding_model=kb.embedding_model,
            embedding_dimensions=kb.embedding_dimensions,
        )
        for kb in (agent.knowledge_bases or [])
    ]

    return TemplateSnapshot(
        schema_version=1,
        agent=AgentSnapshot(
            name=agent.name,
            description=agent.description,
            avatar_url=agent.avatar_url,
            system_prompt=agent.system_prompt,
            model_id=agent.model_id,
            llm_config=agent.llm_config or {},
            welcome_message=agent.welcome_message,
            max_turns=agent.max_turns or 50,
            kb_retrieval_mode=agent.kb_retrieval_mode or "tool",
        ),
        tools=tool_snapshots,
        knowledge_bases=kb_snapshots,
        metadata={
            "tool_count": len(tool_snapshots),
            "kb_count": len(kb_snapshots),
            "required_credentials": _detect_required_credentials(agent),
        },
    )


def _detect_required_credentials(agent: Agent) -> list[str]:
    """Best-effort: derive provider name from model_id ('openai/gpt-4o' → 'openai')."""
    if not agent.model_id or "/" not in agent.model_id:
        return []
    return [agent.model_id.split("/", 1)[0]]


# ─── Restore snapshot into a new agent (fork) ─────────────────────────


async def fork_snapshot_into_agent(
    db: AsyncSession,
    snapshot: dict,
    *,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
) -> Agent:
    """Create a new Agent + clone tools + clone KB shells from a snapshot.

    The new resources are owned by the current user (read from context).
    Buyer must connect their own credential before chatting — agent created
    with ``credential_id=None``.
    """
    user_id = current_user_id()
    snap = TemplateSnapshot.model_validate(snapshot)

    # 1. Agent
    agent = Agent(
        user_id=user_id,
        name=snap.agent.name,
        description=snap.agent.description,
        avatar_url=snap.agent.avatar_url,
        system_prompt=snap.agent.system_prompt,
        model_id=snap.agent.model_id,
        credential_id=None,  # buyer connects their own
        llm_config=snap.agent.llm_config,
        welcome_message=snap.agent.welcome_message,
        max_turns=snap.agent.max_turns,
        kb_retrieval_mode=snap.agent.kb_retrieval_mode,
        is_published=False,
        status="draft",
        template_id=template_id,
        template_version_id=version_id,
    )
    db.add(agent)
    await db.flush()

    # 2. Tools — clone each into buyer's namespace, link via AgentTool
    for tool_snap in snap.tools:
        tool = Tool(
            user_id=user_id,
            name=tool_snap.name,
            description=tool_snap.description,
            tool_type=tool_snap.tool_type,
            config=tool_snap.config,
            input_schema=tool_snap.input_schema,
            output_schema=tool_snap.output_schema,
            timeout_seconds=tool_snap.timeout_seconds,
        )
        db.add(tool)
        await db.flush()
        db.add(AgentTool(agent_id=agent.id, tool_id=tool.id))

    # 3. KBs — empty shells; buyer uploads their own documents post-fork
    for kb_snap in snap.knowledge_bases:
        kb = KnowledgeBase(
            user_id=user_id,
            name=kb_snap.name,
            description=kb_snap.description,
            chunk_size=kb_snap.chunk_size,
            chunk_overlap=kb_snap.chunk_overlap,
            chunk_strategy=kb_snap.chunk_strategy,
            embedding_provider=kb_snap.embedding_provider,
            embedding_model=kb_snap.embedding_model,
            embedding_dimensions=kb_snap.embedding_dimensions,
        )
        db.add(kb)
        await db.flush()
        db.add(AgentKnowledgeBase(agent_id=agent.id, knowledge_base_id=kb.id))

    await db.flush()
    await db.refresh(agent)
    await db.refresh(agent, ["tools", "knowledge_bases"])
    return agent


# ─── Helpers ──────────────────────────────────────────────────────────


async def load_agent_for_snapshot(
    db: AsyncSession, agent_id: uuid.UUID
) -> Agent | None:
    """Fetch an agent with tools + KBs eagerly loaded for snapshot building.

    Scoped to current user via context.
    """
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools), selectinload(Agent.knowledge_bases))
        .where(Agent.id == agent_id, Agent.user_id == current_user_id())
    )
    return result.scalar_one_or_none()
