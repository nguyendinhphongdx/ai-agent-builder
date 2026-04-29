import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.tools.schemas import (
    ToolCreate,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)
from app.tools.service import create_tool, delete_tool, get_tool, list_tools, update_tool

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ToolResponse])
async def list_tools_endpoint(db: AsyncSession = Depends(get_db)):
    tools = await list_tools(db)
    return [ToolResponse.model_validate(t) for t in tools]


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_endpoint(
    body: ToolCreate,
    db: AsyncSession = Depends(get_db),
):
    tool = await create_tool(db, **body.model_dump())
    return ToolResponse.model_validate(tool)


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool_endpoint(
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    tool = await get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolResponse.model_validate(tool)


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool_endpoint(
    tool_id: uuid.UUID,
    body: ToolUpdate,
    db: AsyncSession = Depends(get_db),
):
    tool = await get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool = await update_tool(db, tool, **body.model_dump(exclude_unset=True))
    return ToolResponse.model_validate(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_endpoint(
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    tool = await get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    await delete_tool(db, tool)


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool_endpoint(
    tool_id: uuid.UUID,
    body: ToolTestRequest,
    db: AsyncSession = Depends(get_db),
):
    tool = await get_tool(db, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    from app.tools.registry import tool_registry

    start = time.time()
    try:
        lc_tool = tool_registry.build(tool)
        result = await lc_tool.ainvoke(body.input_data)
        latency_ms = int((time.time() - start) * 1000)
        return ToolTestResponse(success=True, result=str(result), latency_ms=latency_ms)
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return ToolTestResponse(success=False, error=str(e), latency_ms=latency_ms)
