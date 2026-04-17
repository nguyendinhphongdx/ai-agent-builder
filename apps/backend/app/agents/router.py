import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from app.agents.service import (
    attach_knowledge_base,
    attach_tool,
    create_agent,
    delete_agent,
    detach_knowledge_base,
    detach_tool,
    get_agent,
    list_agents,
    update_agent,
)
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentListResponse])
async def list_agents_endpoint(  # Lấy danh sách agent của user hiện tại
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agents = await list_agents(db, current_user.id)
    return [AgentListResponse.model_validate(a).release() for a in agents]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_endpoint(  # Tạo agent mới
    body: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await create_agent(db, current_user.id, **body.model_dump())
    return AgentResponse.model_validate(agent).release()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(  # Lấy chi tiết agent theo ID
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent).release()


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent_endpoint(  # Cập nhật thông tin agent
    agent_id: uuid.UUID,
    body: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await update_agent(db, agent, **body.model_dump(exclude_unset=True))
    return AgentResponse.model_validate(agent).release()


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_endpoint(  # Xóa agent
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await delete_agent(db, agent)


@router.post("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_201_CREATED)
async def attach_tool_endpoint(  # Gắn tool vào agent
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await attach_tool(db, agent_id, tool_id)
    return {"message": "Tool attached"}


@router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tool_endpoint(  # Gỡ tool khỏi agent
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await detach_tool(db, agent_id, tool_id)


@router.post(
    "/{agent_id}/knowledge-bases/{kb_id}", status_code=status.HTTP_201_CREATED
)
async def attach_kb_endpoint(  # Gắn knowledge base vào agent
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id, current_user.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await attach_knowledge_base(db, agent_id, kb_id)
    return {"message": "Knowledge base attached"}


@router.delete(
    "/{agent_id}/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_kb_endpoint(  # Gỡ knowledge base khỏi agent
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await detach_knowledge_base(db, agent_id, kb_id)
