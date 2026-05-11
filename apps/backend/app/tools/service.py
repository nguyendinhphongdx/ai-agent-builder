import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import current_user_id, current_workspace_id_or_none
from app.models.tool import Tool


def _scope_filter(stmt):
    """Phase 1.1 dual-filter on workspace_id (= current OR IS NULL)."""
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return stmt
    return stmt.where(
        (Tool.workspace_id == workspace_id) | (Tool.workspace_id.is_(None))
    )


async def list_tools(db: AsyncSession) -> list[Tool]:
    stmt = (
        select(Tool)
        .where(Tool.user_id == current_user_id())
        .order_by(Tool.updated_at.desc())
    )
    result = await db.execute(_scope_filter(stmt))
    return list(result.scalars().all())


async def get_tool(db: AsyncSession, tool_id: uuid.UUID) -> Tool | None:
    stmt = select(Tool).where(Tool.id == tool_id, Tool.user_id == current_user_id())
    result = await db.execute(_scope_filter(stmt))
    return result.scalar_one_or_none()


async def create_tool(db: AsyncSession, **kwargs) -> Tool:
    kwargs.setdefault("workspace_id", current_workspace_id_or_none())
    tool = Tool(user_id=current_user_id(), **kwargs)
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
