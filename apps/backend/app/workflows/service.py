"""Service layer cho Workflow CRUD - thao tác database."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Workflow
from app.models.workflow_node import WorkflowNode
from app.models.workflow_edge import WorkflowEdge
from app.models.workflow_run import WorkflowRun


async def list_workflows(db: AsyncSession, user_id: uuid.UUID) -> list[Workflow]:
    """Lấy danh sách workflow của user, sắp xếp theo thời gian cập nhật."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.user_id == user_id)
        .order_by(Workflow.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, user_id: uuid.UUID
) -> Workflow | None:
    """Lấy chi tiết workflow kèm nodes và edges (eager loading)."""
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id, Workflow.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_workflow(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Workflow:
    """Tạo workflow mới."""
    workflow = Workflow(user_id=user_id, **kwargs)
    db.add(workflow)
    await db.flush()
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

    # Tạo nodes mới với UUID từ frontend
    for node_data in nodes_data:
        node = WorkflowNode(
            id=node_data["id"],
            workflow_id=workflow.id,
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
    return workflow


# ─── Workflow Run ──────────────────────────────────────────────────

async def create_workflow_run(
    db: AsyncSession,
    workflow_id: uuid.UUID,
    user_id: uuid.UUID,
    input_data: dict,
    conversation_id: uuid.UUID | None = None,
) -> WorkflowRun:
    """Tạo bản ghi chạy workflow mới với trạng thái 'running'."""
    run = WorkflowRun(
        workflow_id=workflow_id,
        user_id=user_id,
        input_data=input_data,
        conversation_id=conversation_id,
        status="running",
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
