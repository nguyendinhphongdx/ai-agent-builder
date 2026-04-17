import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool


async def list_tools(db: AsyncSession, user_id: uuid.UUID) -> list[Tool]:
    result = await db.execute(
        select(Tool).where(Tool.user_id == user_id).order_by(Tool.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_tool(db: AsyncSession, tool_id: uuid.UUID, user_id: uuid.UUID) -> Tool | None:
    result = await db.execute(
        select(Tool).where(Tool.id == tool_id, Tool.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_tool(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Tool:
    tool = Tool(user_id=user_id, **kwargs)
    db.add(tool)
    await db.flush()
    await db.refresh(tool)
    return tool


async def update_tool(db: AsyncSession, tool: Tool, **kwargs) -> Tool:
    for key, value in kwargs.items():
        if value is not None:
            setattr(tool, key, value)
    await db.flush()
    await db.refresh(tool)
    return tool


async def delete_tool(db: AsyncSession, tool: Tool) -> None:
    await db.delete(tool)
    await db.flush()
