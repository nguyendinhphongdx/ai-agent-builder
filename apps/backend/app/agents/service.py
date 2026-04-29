import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.context import current_user_id
from app.models.agent import Agent, AgentTool, AgentKnowledgeBase
from app.models.tool import Tool
from app.models.knowledge_base import KnowledgeBase


async def list_agents(db: AsyncSession) -> list[Agent]:
    """Lấy danh sách agent của user, sắp xếp theo thời gian cập nhật mới nhất."""
    result = await db.execute(
        select(Agent)
        .where(Agent.user_id == current_user_id())
        .order_by(Agent.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Agent | None:
    """Lấy chi tiết agent kèm danh sách tools và knowledge bases đã gắn."""
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools), selectinload(Agent.knowledge_bases))
        .where(Agent.id == agent_id, Agent.user_id == current_user_id())
    )
    return result.scalar_one_or_none()


async def create_agent(db: AsyncSession, **kwargs) -> Agent:
    """Tạo agent mới và tải sẵn quan hệ tools, knowledge_bases."""
    agent = Agent(user_id=current_user_id(), **kwargs)
    db.add(agent)
    await db.flush()
    # Full refresh ensures DB-generated fields (e.g. timestamps) are loaded.
    await db.refresh(agent)
    await db.refresh(agent, ["tools", "knowledge_bases"])
    return agent


async def update_agent(db: AsyncSession, agent: Agent, **kwargs) -> Agent:
    """Cập nhật các trường của agent. Caller phải pass schema với
    `model_dump(exclude_unset=True)` — null là giá trị hợp lệ (clear field)."""
    for key, value in kwargs.items():
        setattr(agent, key, value)
    await db.flush()
    # Full refresh avoids lazy-load on updated_at during response serialization.
    await db.refresh(agent)
    await db.refresh(agent, ["tools", "knowledge_bases"])
    return agent


async def delete_agent(db: AsyncSession, agent: Agent) -> None:
    """Xóa agent (cascade xóa luôn conversations liên quan)."""
    await db.delete(agent)
    await db.flush()


async def attach_tool(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
) -> None:
    """Attach a tool to an agent. Caller must be the owner of both.

    Reads the user from request context — see :mod:`app.context`. Raises
    ``PermissionError`` if either resource isn't owned by the current user
    (closes IDOR via the bridge table — knowing another user's tool UUID was
    previously enough to attach it).
    """
    user_id = current_user_id()
    agent = await db.execute(
        select(Agent.id).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    if agent.scalar_one_or_none() is None:
        raise PermissionError("Agent not found or not owned by user")

    tool = await db.execute(
        select(Tool.id).where(Tool.id == tool_id, Tool.user_id == user_id)
    )
    if tool.scalar_one_or_none() is None:
        raise PermissionError("Tool not found or not owned by user")

    link = AgentTool(agent_id=agent_id, tool_id=tool_id)
    db.add(link)
    await db.flush()


async def detach_tool(
    db: AsyncSession,
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
) -> None:
    """Detach a tool from an agent the caller owns. No-op if no link exists."""
    user_id = current_user_id()
    agent = await db.execute(
        select(Agent.id).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    if agent.scalar_one_or_none() is None:
        raise PermissionError("Agent not found or not owned by user")

    result = await db.execute(
        select(AgentTool).where(
            AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id
        )
    )
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.flush()


async def attach_knowledge_base(
    db: AsyncSession,
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
) -> None:
    """Attach a knowledge base to an agent. Both must belong to current user."""
    user_id = current_user_id()
    agent = await db.execute(
        select(Agent.id).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    if agent.scalar_one_or_none() is None:
        raise PermissionError("Agent not found or not owned by user")

    kb = await db.execute(
        select(KnowledgeBase.id).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id
        )
    )
    if kb.scalar_one_or_none() is None:
        raise PermissionError("Knowledge base not found or not owned by user")

    link = AgentKnowledgeBase(agent_id=agent_id, knowledge_base_id=kb_id)
    db.add(link)
    await db.flush()


async def detach_knowledge_base(
    db: AsyncSession,
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
) -> None:
    """Detach a knowledge base from an agent the caller owns."""
    user_id = current_user_id()
    agent = await db.execute(
        select(Agent.id).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    if agent.scalar_one_or_none() is None:
        raise PermissionError("Agent not found or not owned by user")

    result = await db.execute(
        select(AgentKnowledgeBase).where(
            AgentKnowledgeBase.agent_id == agent_id,
            AgentKnowledgeBase.knowledge_base_id == kb_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.flush()
