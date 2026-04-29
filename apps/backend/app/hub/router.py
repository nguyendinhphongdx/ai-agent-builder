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
    ReviewCreate,
    ReviewResponse,
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
from app.hub.reviews import (
    delete_review,
    list_reviews,
    upsert_review,
)
from app.hub.payment import (
    create_checkout_session,
    get_purchase_status,
    is_stripe_configured,
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


# ─── Authenticated: paid purchase via Stripe Checkout ────────────────


@auth_router.post("/{template_id}/purchase")
async def purchase_endpoint(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for a paid template.

    Returns ``{checkout_url}`` — caller redirects the browser to it. The
    session id is stored on the Purchase row so the webhook can find it
    when payment completes.

    503 when Stripe isn't configured (lets the FE show a clear message
    instead of a confusing 500).
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Paid templates are not available on this deployment",
        )
    try:
        url, purchase = await create_checkout_session(db, template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    await db.commit()
    return {"checkout_url": url, "purchase_id": str(purchase.id)}


@auth_router.get("/purchases/{session_id}/status")
async def purchase_status_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Poll endpoint for the FE return-from-Stripe page.

    Returns ``{status: 'pending'|'paid'|'refunded'|'failed', agent_id?: uuid}``
    once the agent is forked. 404 when the session doesn't belong to the caller.
    """
    result = await get_purchase_status(db, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return result


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


# ─── Reviews ──────────────────────────────────────────────────────────


@public_router.get("/{template_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews_endpoint(
    template_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Public — anyone can read reviews on a published template."""
    rows = await list_reviews(db, template_id, limit=limit, offset=offset)
    return [
        ReviewResponse(
            id=r.id,
            template_id=r.template_id,
            user_id=r.user_id,
            user_name=name,
            rating=r.rating,
            body=r.body,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r, name in rows
    ]


@auth_router.put("/{template_id}/reviews/me", response_model=ReviewResponse)
async def upsert_review_endpoint(
    template_id: uuid.UUID,
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update my review of this template. Must have forked it first."""
    try:
        review = await upsert_review(db, template_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return ReviewResponse(
        id=review.id,
        template_id=review.template_id,
        user_id=review.user_id,
        user_name=None,  # caller knows their own name
        rating=review.rating,
        body=review.body,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@auth_router.delete("/{template_id}/reviews/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review_endpoint(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_review(db, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No review to delete")
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
