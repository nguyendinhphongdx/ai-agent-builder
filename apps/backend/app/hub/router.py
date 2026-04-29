"""Hub HTTP endpoints.

Browse + detail are public (no auth) — anyone can preview templates without
signing in. Publish, fork, edit, list-mine require authentication.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.hub.schemas import (
    ForkResponse,
    TemplateBrowseResponse,
    TemplateDetail,
    TemplatePublishRequest,
    TemplateSummary,
    TemplateUpdateRequest,
)
from app.hub.service import (
    archive_template,
    fork_template,
    get_by_slug_or_id,
    list_my_forks,
    list_my_templates,
    list_published,
    publish_agent,
    update_template,
)

# Public router — browse + detail. No auth dep at router level.
public_router = APIRouter(prefix="/templates", tags=["hub"])

# Authenticated router — fork, publish, edit, list-mine.
auth_router = APIRouter(
    prefix="/templates",
    tags=["hub"],
    dependencies=[Depends(get_current_user)],
)


# ─── Public: browse + detail ──────────────────────────────────────────


@public_router.get("", response_model=TemplateBrowseResponse)
async def browse_endpoint(
    q: str | None = Query(None, description="Full-text search"),
    category: str | None = Query(None),
    tag: str | None = Query(None),
    pricing: str | None = Query(None, regex="^(free|paid)$"),
    sort: str = Query("popular", regex="^(popular|newest|top-rated|cheapest)$"),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    items, total = await list_published(
        db,
        query=q,
        category=category,
        tag=tag,
        pricing=pricing,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return TemplateBrowseResponse(
        items=[TemplateSummary.model_validate(t) for t in items],
        total=total,
        has_more=(offset + len(items)) < total,
    )


@public_router.get("/{slug_or_id}", response_model=TemplateDetail)
async def detail_endpoint(
    slug_or_id: str,
    db: AsyncSession = Depends(get_db),
):
    template = await get_by_slug_or_id(db, slug_or_id)
    if template is None or template.status != "published":
        raise HTTPException(404, "Template not found")

    # Pick current version for snapshot preview.
    current = next((v for v in template.versions if v.is_current), None)
    return TemplateDetail(
        **TemplateSummary.model_validate(template).model_dump(),
        user_id=template.user_id,
        status=template.status,
        snapshot=current.snapshot if current else None,
        current_version=current.version if current else None,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ─── Authenticated: fork ──────────────────────────────────────────────


@auth_router.post("/{template_id}/fork", response_model=ForkResponse, status_code=status.HTTP_201_CREATED)
async def fork_endpoint(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fork a free template into the caller's agent list. Returns the new agent id."""
    try:
        agent, purchase, version = await fork_template(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return ForkResponse(
        agent_id=agent.id,
        template_id=template_id,
        version_id=version.id,
        purchase_id=purchase.id,
    )


# ─── Authenticated: owner edits ───────────────────────────────────────


@auth_router.patch("/{template_id}", response_model=TemplateSummary)
async def update_endpoint(
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        template = await update_template(
            db, template_id, **body.model_dump(exclude_unset=True)
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return TemplateSummary.model_validate(template)


@auth_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_endpoint(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        await archive_template(db, template_id)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()


# ─── Authenticated: lists ─────────────────────────────────────────────


@auth_router.get("/me/published", response_model=list[TemplateSummary])
async def my_templates_endpoint(db: AsyncSession = Depends(get_db)):
    """Templates I've published — seller dashboard."""
    templates = await list_my_templates(db)
    return [TemplateSummary.model_validate(t) for t in templates]


@auth_router.get("/me/forks", response_model=list[uuid.UUID])
async def my_forks_endpoint(db: AsyncSession = Depends(get_db)):
    """Agent ids in my list that came from the Hub. UI can fetch full agent rows."""
    agents = await list_my_forks(db)
    return [a.id for a in agents]


# ─── Publish from agents router (separate endpoint to keep agents router clean) ──


# This lives on the auth router so it inherits get_current_user.
@auth_router.post(
    "/publish-agent/{agent_id}",
    response_model=TemplateSummary,
    status_code=status.HTTP_201_CREATED,
)
async def publish_agent_endpoint(
    agent_id: uuid.UUID,
    body: TemplatePublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """Publish an agent the caller owns as a Hub template."""
    try:
        template = await publish_agent(db, agent_id, body)
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return TemplateSummary.model_validate(template)
