"""Annotation API + dashboard endpoints.

Two route families:
  /messages/{id}/annotation      message-scoped CRUD (cookie auth)
  /annotations/*                 workspace-scoped dashboard reads
                                 (billing.manage permission)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.workspaces.permissions import require_active_permission
from app.modules.runtime.chat.annotations import service
from app.platform.context import current_workspace_id_or_none
from app.platform.db.session import get_db
from app.platform.permissions import catalogue as P

router = APIRouter(tags=["annotations"])


# ─── Message-scoped ────────────────────────────────────────────────


class AnnotationRequest(BaseModel):
    rating: int = Field(description="-1 = thumbs down, +1 = thumbs up")
    feedback: str | None = None
    expected_response: str | None = None
    tags: list[str] | None = None


class AnnotationResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    feedback: str | None
    expected_response: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.put(
    "/messages/{message_id}/annotation", response_model=AnnotationResponse
)
async def put_annotation(
    message_id: uuid.UUID,
    payload: AnnotationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await service.upsert_annotation(
            db,
            message_id=message_id,
            rating=payload.rating,
            feedback=payload.feedback,
            expected_response=payload.expected_response,
            tags=payload.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return AnnotationResponse.model_validate(row)


@router.get(
    "/messages/{message_id}/annotation",
    response_model=AnnotationResponse | None,
)
async def get_annotation(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_for_message(db, message_id)
    return AnnotationResponse.model_validate(row) if row else None


@router.delete("/messages/{message_id}/annotation", status_code=204)
async def delete_annotation(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_annotation(db, message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="annotation_not_found")
    await db.commit()
    return None


# ─── Workspace dashboard ───────────────────────────────────────────


class AnnotationTotals(BaseModel):
    up: int
    down: int
    total: int
    up_rate: float
    since: str


class AnnotationTagRow(BaseModel):
    tag: str
    count: int


def _active_workspace_or_403() -> uuid.UUID:
    ws = current_workspace_id_or_none()
    if ws is None:
        raise HTTPException(status_code=403, detail="no_active_workspace")
    return ws


@router.get("/annotations/totals", response_model=AnnotationTotals)
async def get_totals(
    since: datetime | None = Query(default=None),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = _active_workspace_or_403()
    data = await service.workspace_totals(db, ws, since=since)
    return AnnotationTotals(**data)


@router.get("/annotations/tags", response_model=list[AnnotationTagRow])
async def get_tags(
    since: datetime | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = _active_workspace_or_403()
    return [AnnotationTagRow(**r) for r in await service.top_tags(db, ws, since=since, limit=limit)]


@router.get("/annotations/recent-negative", response_model=list[AnnotationResponse])
async def get_recent_negative(
    limit: int = Query(default=50, ge=1, le=200),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = _active_workspace_or_403()
    rows = await service.recent_negative(db, ws, limit=limit)
    return [AnnotationResponse.model_validate(r) for r in rows]


@router.get("/annotations/export.jsonl")
async def export_jsonl(
    only_negative: bool = Query(default=False),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Stream the workspace's annotated turns as JSONL.

    Default exports every annotated turn; ``only_negative=true``
    narrows to thumbs-down rows where the user supplied
    ``expected_response`` — the gold fine-tuning corpus.
    """
    ws = _active_workspace_or_403()
    rows = await service.export_jsonl_rows(db, ws, only_negative=only_negative)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    return PlainTextResponse(
        body,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": (
                f"attachment; filename=annotations-{ws}.jsonl"
            )
        },
    )
