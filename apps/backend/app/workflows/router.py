"""REST endpoints cho Workflow CRUD và execution."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.context import current_user_id
from app.db.session import get_db
from app.permissions import catalogue as P
from app.rate_limit import make_limit
from app.workspaces.permissions import require_active_permission
from app.workflows.schemas import (
    NodeExecuteRequest,
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from app.workflows.service import (
    create_workflow,
    delete_workflow,
    get_workflow,
    get_workflow_run,
    list_workflow_runs,
    list_workflows,
    rotate_webhook_token,
    save_graph,
    update_workflow,
)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[WorkflowListResponse])
async def list_workflows_endpoint(  # Lấy danh sách workflow của user
    db: AsyncSession = Depends(get_db),
):
    workflows = await list_workflows(db)
    return [WorkflowListResponse.model_validate(w) for w in workflows]


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_endpoint(  # Tạo workflow mới
    body: WorkflowCreate,
    _: object = Depends(require_active_permission(P.WORKFLOW_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await create_workflow(db, **body.model_dump())
    return WorkflowResponse.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_endpoint(  # Lấy chi tiết workflow kèm nodes + edges
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow_endpoint(  # Cập nhật workflow, có thể lưu toàn bộ graph
    workflow_id: uuid.UUID,
    body: WorkflowUpdate,
    _: object = Depends(require_active_permission(P.WORKFLOW_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Nếu có nodes/edges thì lưu toàn bộ graph
    if body.nodes is not None and body.edges is not None:
        workflow = await save_graph(
            db,
            workflow,
            [n.model_dump() for n in body.nodes],
            [e.model_dump() for e in body.edges],
        )

    # Cập nhật metadata workflow
    update_fields = body.model_dump(exclude={"nodes", "edges"}, exclude_unset=True)
    if update_fields:
        workflow = await update_workflow(db, workflow, **update_fields)

    await db.commit()
    await db.refresh(workflow)
    return WorkflowResponse.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow_endpoint(  # Xóa workflow
    workflow_id: uuid.UUID,
    _: object = Depends(require_active_permission(P.WORKFLOW_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await delete_workflow(db, workflow)


# ─── Execution ─────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/execute",
    response_model=WorkflowRunResponse,
    dependencies=[
        Depends(make_limit("workflow-exec", 30)),
        Depends(require_active_permission(P.WORKFLOW_EXECUTE)),
    ],
)
async def execute_workflow_endpoint(  # Chạy workflow và trả về kết quả
    workflow_id: uuid.UUID,
    body: WorkflowExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not workflow.nodes:
        raise HTTPException(status_code=400, detail="Workflow has no nodes")

    # Runner is reachable from background tasks (webhook _run_detached) so it
    # keeps user_id explicit — read from context here at the boundary.
    from app.workflows.runner import WorkflowRunner

    runner = WorkflowRunner(db)
    run = await runner.run(
        workflow=workflow,
        user_id=current_user_id(),
        input_data=body.input_data,
        conversation_id=body.conversation_id,
    )
    return WorkflowRunResponse.model_validate(run)


@router.post(
    "/{workflow_id}/nodes/{node_id}/execute",
    response_model=WorkflowRunResponse,
    dependencies=[Depends(make_limit("workflow-step-exec", 60))],
)
async def execute_node_endpoint(  # NDV "Execute step" — chạy đơn lẻ một node
    workflow_id: uuid.UUID,
    node_id: str,
    body: NodeExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from app.workflows.runner import WorkflowRunner

    runner = WorkflowRunner(db)
    try:
        run = await runner.run_single_node(
            workflow=workflow,
            user_id=current_user_id(),
            node_id=node_id,
            input_items=body.input_items,
            config_overrides=body.config_overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return WorkflowRunResponse.model_validate(run)


# ─── Run history ───────────────────────────────────────────────────

@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunResponse])
async def list_runs_endpoint(  # Lấy lịch sử chạy workflow
    workflow_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    # Kiểm tra quyền truy cập workflow
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    runs = await list_workflow_runs(db, workflow_id, limit)
    return [WorkflowRunResponse.model_validate(r) for r in runs]


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_run_endpoint(  # Lấy chi tiết một lần chạy
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    run = await get_workflow_run(db, run_id, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return WorkflowRunResponse.model_validate(run)


# ─── Webhook token ────────────────────────────────────────────────

@router.post("/{workflow_id}/webhook-token/rotate", response_model=WorkflowResponse)
async def rotate_webhook_token_endpoint(  # Tạo lại token webhook (URL cũ ngừng hoạt động)
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = await rotate_webhook_token(db, workflow)
    await db.commit()
    return WorkflowResponse.model_validate(workflow)


# ─── NDV: Per-node execution data ─────────────────────────────────

@router.get("/{workflow_id}/runs/{run_id}/nodes/{node_id}")
async def get_node_execution_endpoint(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get per-node input/output data for NDV panels (Schema/Table/JSON views)."""
    workflow = await get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    run = await get_workflow_run(db, run_id, workflow_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    node_executions = run.node_executions or []
    node_exec = next(
        (n for n in node_executions if n.get("node_id") == node_id),
        None,
    )
    if not node_exec:
        raise HTTPException(status_code=404, detail="Node execution not found")

    return {
        "node_id": node_exec.get("node_id"),
        "node_type": node_exec.get("node_type"),
        "label": node_exec.get("label"),
        "status": node_exec.get("status"),
        "input_items": node_exec.get("input_items", []),
        "output_items": node_exec.get("output_items", []),
        "tokens_used": node_exec.get("tokens_used", 0),
        "error": node_exec.get("error"),
        "started_at": node_exec.get("started_at"),
        "completed_at": node_exec.get("completed_at"),
    }
