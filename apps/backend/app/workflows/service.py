"""Service layer cho Workflow CRUD - thao tác database."""

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.context import current_user_id, current_workspace_id_or_none
from app.models.workflow import Workflow
from app.models.workflow_edge import WorkflowEdge
from app.models.workflow_node import WorkflowNode
from app.models.workflow_run import WorkflowRun


def _scope_filter(stmt):
    """Restrict to workflows in the current workspace."""
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return stmt
    return stmt.where(Workflow.workspace_id == workspace_id)


def generate_webhook_token() -> str:
    """URL-safe random token for embedding in webhook URLs.

    32 random bytes → ~43 ASCII chars; column allows 64 to leave headroom for
    future format changes (e.g. adding a versioned prefix like ``whsec_``).
    """
    return secrets.token_urlsafe(32)


async def list_workflows(db: AsyncSession) -> list[Workflow]:
    """Lấy danh sách workflow của user, sắp xếp theo thời gian cập nhật."""
    stmt = (
        select(Workflow)
        .where(Workflow.user_id == current_user_id())
        .order_by(Workflow.updated_at.desc())
    )
    result = await db.execute(_scope_filter(stmt))
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession, workflow_id: uuid.UUID
) -> Workflow | None:
    """Lấy chi tiết workflow kèm nodes và edges (eager loading)."""
    stmt = (
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id, Workflow.user_id == current_user_id())
    )
    result = await db.execute(_scope_filter(stmt))
    return result.scalar_one_or_none()


async def create_workflow(db: AsyncSession, **kwargs) -> Workflow:
    """Tạo workflow mới — auto-generate webhook_token if not provided."""
    kwargs.setdefault("webhook_token", generate_webhook_token())
    kwargs.setdefault("workspace_id", current_workspace_id_or_none())
    workflow = Workflow(user_id=current_user_id(), **kwargs)
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow, ["nodes", "edges"])
    return workflow


async def rotate_webhook_token(db: AsyncSession, workflow: Workflow) -> Workflow:
    """Generate a new webhook token. Old URLs stop working immediately."""
    workflow.webhook_token = generate_webhook_token()
    await db.flush()
    await db.refresh(workflow)
    await db.refresh(workflow, ["nodes", "edges"])
    return workflow


async def update_workflow(db: AsyncSession, workflow: Workflow, **kwargs) -> Workflow:
    """Cập nhật thông tin workflow (không bao gồm nodes/edges)."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(workflow, key, value)
    await db.flush()
    await db.refresh(workflow, ["nodes", "edges"])
    return workflow


async def delete_workflow(db: AsyncSession, workflow: Workflow) -> None:
    """Xóa workflow (cascade xóa nodes, edges, runs)."""
    await db.delete(workflow)
    await db.flush()


async def save_graph(
    db: AsyncSession,
    workflow: Workflow,
    nodes_data: list[dict],
    edges_data: list[dict],
) -> Workflow:
    """Lưu toàn bộ graph (nodes + edges) cho workflow.

    Xóa nodes/edges cũ và tạo lại từ dữ liệu mới.
    Tăng version mỗi lần lưu.
    """
    # Xóa edges trước (do FK tới nodes)
    for edge in list(workflow.edges):
        await db.delete(edge)
    for node in list(workflow.nodes):
        await db.delete(node)
    await db.flush()

    # Inherit workspace_id from the parent workflow so the graph stays
    # tenant-tagged even when the workflow was just freshly stamped.
    ws_id = workflow.workspace_id

    # Tạo nodes mới với UUID từ frontend
    for node_data in nodes_data:
        node = WorkflowNode(
            id=node_data["id"],
            workflow_id=workflow.id,
            workspace_id=ws_id,
            node_type=node_data["node_type"],
            label=node_data.get("label"),
            config=node_data.get("config", {}),
            position_x=node_data.get("position_x", 0),
            position_y=node_data.get("position_y", 0),
            width=node_data.get("width"),
            height=node_data.get("height"),
        )
        db.add(node)
    await db.flush()

    # Tạo edges mới
    for edge_data in edges_data:
        edge = WorkflowEdge(
            id=edge_data["id"],
            workflow_id=workflow.id,
            workspace_id=ws_id,
            source_node_id=edge_data["source_node_id"],
            target_node_id=edge_data["target_node_id"],
            source_handle=edge_data.get("source_handle"),
            target_handle=edge_data.get("target_handle"),
            label=edge_data.get("label"),
            style=edge_data.get("style", {}),
        )
        db.add(edge)

    # Tăng version
    workflow.version = (workflow.version or 0) + 1
    await db.flush()
    await db.refresh(workflow, ["nodes", "edges"])

    # Reconcile scheduled_triggers — pick up new cron_trigger nodes,
    # drop deleted ones. Done in the same transaction as the graph
    # save so the schedule never out-of-sync with the workflow.
    from app.scheduled_triggers.service import sync_from_workflow

    await sync_from_workflow(db, workflow, created_by=workflow.user_id)
    return workflow


# ─── Workflow Run ──────────────────────────────────────────────────

async def create_workflow_run(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
    input_data: dict,
    conversation_id: uuid.UUID | None = None,
    is_partial: bool = False,
) -> WorkflowRun:
    """Tạo bản ghi chạy workflow mới với trạng thái 'running'.

    ``workspace_id`` inherits from the parent workflow so per-tenant
    cost dashboards can filter runs without a JOIN to workflows.
    """
    workspace_id = await db.scalar(
        select(Workflow.workspace_id).where(Workflow.id == workflow_id)
    )
    run = WorkflowRun(
        workflow_id=workflow_id,
        user_id=user_id,
        workspace_id=workspace_id,
        input_data=input_data,
        conversation_id=conversation_id,
        status="running",
        is_partial=is_partial,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def update_workflow_run(db: AsyncSession, run: WorkflowRun, **kwargs) -> WorkflowRun:
    """Cập nhật bản ghi chạy workflow (status, output, tokens, ...)."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(run, key, value)
    await db.flush()
    await db.refresh(run)
    return run


async def get_workflow_run(
    db: AsyncSession, run_id: uuid.UUID, workflow_id: uuid.UUID
) -> WorkflowRun | None:
    """Lấy chi tiết một lần chạy workflow."""
    result = await db.execute(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id,
            WorkflowRun.workflow_id == workflow_id,
        )
    )
    return result.scalar_one_or_none()


async def list_workflow_runs(
    db: AsyncSession, workflow_id: uuid.UUID, limit: int = 20
) -> list[WorkflowRun]:
    """Lấy danh sách lịch sử chạy workflow, mới nhất trước."""
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
