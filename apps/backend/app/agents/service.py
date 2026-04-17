import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, AgentTool, AgentKnowledgeBase


async def list_agents(db: AsyncSession, user_id: uuid.UUID) -> list[Agent]:
    """Lấy danh sách agent của user, sắp xếp theo thời gian cập nhật mới nhất."""
    result = await db.execute(
        select(Agent)
        .where(Agent.user_id == user_id)
        .order_by(Agent.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_agent(db: AsyncSession, agent_id: uuid.UUID, user_id: uuid.UUID) -> Agent | None:
    """Lấy chi tiết agent kèm danh sách tools và knowledge bases đã gắn."""
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools), selectinload(Agent.knowledge_bases))
        .where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_agent(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Agent:
    """Tạo agent mới và tải sẵn quan hệ tools, knowledge_bases."""
    agent = Agent(user_id=user_id, **kwargs)
    db.add(agent)
    await db.flush()
    # Full refresh ensures DB-generated fields (e.g. timestamps) are loaded.
    await db.refresh(agent)
    await db.refresh(agent, ["tools", "knowledge_bases"])
    return agent


async def update_agent(db: AsyncSession, agent: Agent, **kwargs) -> Agent:
    """Cập nhật các trường của agent, bỏ qua giá trị None."""
    for key, value in kwargs.items():
        if value is not None:
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


async def attach_tool(db: AsyncSession, agent_id: uuid.UUID, tool_id: uuid.UUID) -> None:
    """Gắn tool vào agent thông qua bảng trung gian agent_tools."""
    link = AgentTool(agent_id=agent_id, tool_id=tool_id)
    db.add(link)
    await db.flush()


async def detach_tool(db: AsyncSession, agent_id: uuid.UUID, tool_id: uuid.UUID) -> None:
    """Gỡ tool khỏi agent, bỏ qua nếu liên kết không tồn tại."""
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
    db: AsyncSession, agent_id: uuid.UUID, kb_id: uuid.UUID
) -> None:
    """Gắn knowledge base vào agent thông qua bảng trung gian."""
    link = AgentKnowledgeBase(agent_id=agent_id, knowledge_base_id=kb_id)
    db.add(link)
    await db.flush()


async def detach_knowledge_base(
    db: AsyncSession, agent_id: uuid.UUID, kb_id: uuid.UUID
) -> None:
    """Gỡ knowledge base khỏi agent, bỏ qua nếu liên kết không tồn tại."""
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
