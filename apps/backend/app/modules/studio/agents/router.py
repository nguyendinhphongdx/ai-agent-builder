import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_credential import AICredential
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.workspaces.permissions import require_active_permission
from app.modules.runtime.chat.share.schemas import ShareConfigResponse, ShareSettingsUpdate
from app.modules.runtime.chat.share.service import (
    disable_share,
    enable_share,
    update_share_settings,
)
from app.modules.studio.agents.schemas import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from app.modules.studio.agents.service import (
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
from app.platform.context import current_user_id
from app.platform.db.session import get_db
from app.platform.permissions import catalogue as P


async def _assert_credential_owned(
    db: AsyncSession, credential_id: uuid.UUID | None
) -> None:
    """Reject if `credential_id` references a credential the user doesn't own."""
    if credential_id is None:
        return
    result = await db.execute(
        select(AICredential.id).where(
            AICredential.id == credential_id,
            AICredential.user_id == current_user_id(),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="Invalid credential_id")


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[AgentListResponse])
async def list_agents_endpoint(  # Lấy danh sách agent của user hiện tại
    db: AsyncSession = Depends(get_db),
):
    agents = await list_agents(db)
    return [AgentListResponse.model_validate(a).release() for a in agents]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_endpoint(  # Tạo agent mới
    body: AgentCreate,
    _: object = Depends(require_active_permission(P.AGENT_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    await _assert_credential_owned(db, body.credential_id)
    agent = await create_agent(db, **body.model_dump())
    return AgentResponse.model_validate(agent).release()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(  # Lấy chi tiết agent theo ID
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent).release()


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent_endpoint(  # Cập nhật thông tin agent
    agent_id: uuid.UUID,
    body: AgentUpdate,
    _: object = Depends(require_active_permission(P.AGENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = body.model_dump(exclude_unset=True)
    if "credential_id" in updates:
        await _assert_credential_owned(db, updates["credential_id"])

    agent = await update_agent(db, agent, **updates)
    return AgentResponse.model_validate(agent).release()


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_endpoint(  # Xóa agent
    agent_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.AGENT_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await delete_agent(db, agent)


@router.post("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_201_CREATED)
async def attach_tool_endpoint(  # Gắn tool vào agent
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.AGENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await attach_tool(db, agent_id, tool_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": "Tool attached"}


@router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tool_endpoint(  # Gỡ tool khỏi agent
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.AGENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await detach_tool(db, agent_id, tool_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{agent_id}/knowledge-bases/{kb_id}", status_code=status.HTTP_201_CREATED
)
async def attach_kb_endpoint(  # Gắn knowledge base vào agent
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.AGENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await attach_knowledge_base(db, agent_id, kb_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": "Knowledge base attached"}


@router.delete(
    "/{agent_id}/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_kb_endpoint(  # Gỡ knowledge base khỏi agent
    agent_id: uuid.UUID,
    kb_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.AGENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        await detach_knowledge_base(db, agent_id, kb_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ─── Share / embed channel ───────────────────────────────────────────────
# Single endpoint covers all owner ops: enable, disable, rotate, settings.
# Frontend only needs one call per UI interaction.


def _share_config(agent) -> ShareConfigResponse:
    return ShareConfigResponse(
        enabled=agent.share_token is not None,
        share_token=agent.share_token,
        settings=agent.share_settings or {},
    )


@router.get("/{agent_id}/share", response_model=ShareConfigResponse)
async def get_share_config(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Read current share state — used by the embed integration page."""
    agent = await get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _share_config(agent)


@router.patch("/{agent_id}/share", response_model=ShareConfigResponse)
async def update_share_config(
    agent_id: uuid.UUID,
    body: ShareSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Toggle / rotate / customise the agent's share channel."""
    agent = await get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.settings is not None:
        agent = await update_share_settings(db, agent, body.settings)

    if body.rotate or body.enabled is True:
        agent = await enable_share(db, agent, rotate=body.rotate)
    elif body.enabled is False:
        agent = await disable_share(db, agent)

    return _share_config(agent)
