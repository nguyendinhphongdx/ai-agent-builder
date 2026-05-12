"""REST endpoints cho Multi-Agent patterns."""


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.service import get_agent
from app.modules.auth.dependencies import get_current_user
from app.modules.multi_agent.schemas import (
    MultiAgentResponse,
    PeerRequest,
    SupervisorRequest,
)
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/multi-agent",
    tags=["multi-agent"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/supervisor", response_model=MultiAgentResponse)
async def run_supervisor_endpoint(  # Chạy supervisor pattern: agent đầu điều phối, các agent sau là worker
    body: SupervisorRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(body.agent_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Cần ít nhất 2 agent (1 supervisor + 1 worker)",
        )

    # Lấy tất cả agents và kiểm tra quyền sở hữu
    agents = []
    for agent_id in body.agent_ids:
        agent = await get_agent(db, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        agents.append(agent)

    supervisor_agent = agents[0]
    worker_agents = agents[1:]

    from app.modules.multi_agent.supervisor import run_supervisor

    result = await run_supervisor(
        supervisor_agent=supervisor_agent,
        worker_agents=worker_agents,
        user_message=body.message,
        db=db,
        max_iterations=body.max_iterations,
    )

    return MultiAgentResponse(
        response=result["response"],
        agent_outputs=result["worker_results"],
        pattern="supervisor",
        iterations=result["iterations"],
    )


@router.post("/peer", response_model=MultiAgentResponse)
async def run_peer_endpoint(  # Chạy peer collaboration: các agent xử lý tuần tự
    body: PeerRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(body.agent_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Cần ít nhất 2 agent cho peer collaboration",
        )

    # Lấy tất cả agents và kiểm tra quyền sở hữu
    agents = []
    for agent_id in body.agent_ids:
        agent = await get_agent(db, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        agents.append(agent)

    from app.modules.multi_agent.peer import run_peer_collaboration

    result = await run_peer_collaboration(
        agents=agents,
        user_message=body.message,
        db=db,
        rounds=body.rounds,
        synthesis_prompt=body.synthesis_prompt,
    )

    return MultiAgentResponse(
        response=result["response"],
        agent_outputs=result["agent_outputs"],
        pattern="peer",
    )

