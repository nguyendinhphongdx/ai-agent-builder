"""Review service for agent templates.

Only buyers (users who have a paid Purchase row for the template) can
review. Aggregates rating_avg + rating_count are recomputed on every
write so the cache on `agent_templates` stays correct without triggers.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import current_user_id
from app.hub.schemas import ReviewCreate
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_review import AgentTemplateReview
from app.models.user import User


async def _user_has_forked(
    db: AsyncSession, user_id: uuid.UUID, template_id: uuid.UUID
) -> bool:
    """A purchase row (free or paid, status=paid) is the proof you used the template."""
    result = await db.execute(
        select(AgentTemplatePurchase.id).where(
            AgentTemplatePurchase.buyer_id == user_id,
            AgentTemplatePurchase.template_id == template_id,
            AgentTemplatePurchase.status == "paid",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def upsert_review(
    db: AsyncSession, template_id: uuid.UUID, body: ReviewCreate
) -> AgentTemplateReview:
    """Create or replace the caller's review for a template.

    Raises:
        ValueError — caller hasn't forked the template (so can't review it)
        ValueError — template doesn't exist / isn't published
    """
    user_id = current_user_id()

    template = await db.get(AgentTemplate, template_id)
    if template is None or template.status != "published":
        raise ValueError("Template not found or not published")

    if not await _user_has_forked(db, user_id, template_id):
        raise ValueError("Only users who forked the template can review it")

    existing = await db.execute(
        select(AgentTemplateReview).where(
            AgentTemplateReview.template_id == template_id,
            AgentTemplateReview.user_id == user_id,
        )
    )
    review = existing.scalar_one_or_none()
    if review is None:
        review = AgentTemplateReview(
            template_id=template_id,
            user_id=user_id,
            rating=body.rating,
            body=body.body,
        )
        db.add(review)
    else:
        review.rating = body.rating
        review.body = body.body

    await db.flush()
    await _refresh_aggregate(db, template_id)
    await db.refresh(review)
    return review


async def list_reviews(
    db: AsyncSession, template_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[tuple[AgentTemplateReview, str | None]]:
    """Return (review, reviewer_name) tuples — the FE shows a real name on each card."""
    result = await db.execute(
        select(AgentTemplateReview, User.name)
        .join(User, AgentTemplateReview.user_id == User.id)
        .where(AgentTemplateReview.template_id == template_id)
        .order_by(AgentTemplateReview.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [(r, name) for r, name in result.all()]


async def delete_review(
    db: AsyncSession, template_id: uuid.UUID
) -> bool:
    """Delete the caller's review. Returns True if a row was deleted."""
    user_id = current_user_id()
    result = await db.execute(
        select(AgentTemplateReview).where(
            AgentTemplateReview.template_id == template_id,
            AgentTemplateReview.user_id == user_id,
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        return False
    await db.delete(review)
    await db.flush()
    await _refresh_aggregate(db, template_id)
    return True


async def _refresh_aggregate(db: AsyncSession, template_id: uuid.UUID) -> None:
    """Recompute rating_avg + rating_count on the parent template.

    Cheap query (single GROUP BY on indexed FK). Recomputed on every write
    instead of incrementally so we can't drift if a row is deleted out-of-band.
    """
    from sqlalchemy import func

    row = await db.execute(
        select(
            func.avg(AgentTemplateReview.rating),
            func.count(AgentTemplateReview.id),
        ).where(AgentTemplateReview.template_id == template_id)
    )
    avg, count = row.one()
    await db.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == template_id)
        .values(rating_avg=avg, rating_count=int(count or 0))
    )
