"""Hub service layer — publish, browse, fork."""
from __future__ import annotations

import re
import secrets
import uuid
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.context import current_user_id
from app.hub.schemas import TemplatePublishRequest
from app.hub.snapshot import (
    build_snapshot_from_agent,
    fork_snapshot_into_agent,
    load_agent_for_snapshot,
)
from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_version import AgentTemplateVersion
from app.models.user import User


# ─── Publish ──────────────────────────────────────────────────────────


def _slugify(title: str) -> str:
    """URL-safe slug from a title. Suffix added later for uniqueness."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:100] or "agent"


async def _unique_slug(db: AsyncSession, title: str) -> str:
    """Slugify + append a short random suffix until the slug is free.

    We always append a suffix so SEO URLs don't collide silently when two
    users publish "customer-support-bot" minutes apart.
    """
    base = _slugify(title)
    for _ in range(5):
        candidate = f"{base}-{secrets.token_hex(3)}"
        exists = await db.scalar(
            select(AgentTemplate.id).where(AgentTemplate.slug == candidate)
        )
        if not exists:
            return candidate
    # Astronomically unlikely — fall back to longer random.
    return f"{base}-{secrets.token_hex(8)}"


async def publish_agent(
    db: AsyncSession, agent_id: uuid.UUID, body: TemplatePublishRequest
) -> AgentTemplate:
    """Publish an agent the caller owns as a Hub template.

    Creates ``AgentTemplate`` (status=published) + initial ``AgentTemplateVersion``
    with a frozen snapshot. Subsequent edits to the source agent don't affect
    the published version — author must explicitly publish a new version.
    """
    user_id = current_user_id()
    agent = await load_agent_for_snapshot(db, agent_id)
    if agent is None:
        raise PermissionError("Agent not found or not owned by user")

    snapshot = await build_snapshot_from_agent(db, agent)

    # Fall back to user's display name if author_name not provided.
    author_name = body.author_name
    if not author_name:
        user = await db.get(User, user_id)
        author_name = user.name if user and user.name else "Anonymous"

    template = AgentTemplate(
        user_id=user_id,
        source_agent_id=agent.id,
        slug=await _unique_slug(db, body.title),
        title=body.title,
        description=body.description,
        author_name=author_name,
        category=body.category,
        tags=body.tags,
        cover_image_url=body.cover_image_url,
        price_cents=body.price_cents,
        currency=body.currency,
        status="published",
        published_at=func.now(),
    )
    db.add(template)
    await db.flush()

    version = AgentTemplateVersion(
        template_id=template.id,
        version="1.0.0",
        snapshot=snapshot.model_dump(),
        is_current=True,
        changelog="Initial release",
    )
    db.add(version)
    await db.flush()
    await db.refresh(template)
    return template


# ─── Browse + search ──────────────────────────────────────────────────


async def list_published(
    db: AsyncSession,
    *,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    pricing: str | None = None,  # 'free' | 'paid' | None
    sort: str = "popular",
    limit: int = 24,
    offset: int = 0,
) -> tuple[list[AgentTemplate], int]:
    """Paginated browse over published templates. Public — no auth required."""
    base = select(AgentTemplate).where(AgentTemplate.status == "published")

    if query:
        # Postgres FTS via the generated `search_vector` column.
        base = base.where(
            func.to_tsvector("simple", AgentTemplate.title + " " + func.coalesce(AgentTemplate.description, "")).op(
                "@@"
            )(func.plainto_tsquery("simple", query))
        )
    if category:
        base = base.where(AgentTemplate.category == category)
    if tag:
        # JSONB array contains: tags @> '["foo"]'::jsonb
        base = base.where(AgentTemplate.tags.op("@>")([tag]))
    if pricing == "free":
        base = base.where(AgentTemplate.price_cents == 0)
    elif pricing == "paid":
        base = base.where(AgentTemplate.price_cents > 0)

    # Total before pagination.
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    # Sort.
    if sort == "newest":
        base = base.order_by(AgentTemplate.published_at.desc().nullslast())
    elif sort == "top-rated":
        base = base.order_by(
            AgentTemplate.rating_avg.desc().nullslast(),
            AgentTemplate.fork_count.desc(),
        )
    elif sort == "cheapest":
        base = base.order_by(AgentTemplate.price_cents.asc(), AgentTemplate.fork_count.desc())
    else:  # popular (default) — featured first, then forks
        base = base.order_by(
            AgentTemplate.is_featured.desc(),
            AgentTemplate.fork_count.desc(),
            AgentTemplate.published_at.desc().nullslast(),
        )

    result = await db.execute(base.limit(limit).offset(offset))
    return list(result.scalars().all()), int(total)


async def get_by_slug_or_id(
    db: AsyncSession, slug_or_id: str
) -> AgentTemplate | None:
    """Detail lookup by slug (preferred) or UUID."""
    # Try UUID first (cheap), fall back to slug.
    try:
        tid = uuid.UUID(slug_or_id)
        clause = AgentTemplate.id == tid
    except ValueError:
        clause = AgentTemplate.slug == slug_or_id

    result = await db.execute(
        select(AgentTemplate)
        .options(selectinload(AgentTemplate.versions))
        .where(clause)
    )
    return result.scalar_one_or_none()


async def list_my_templates(db: AsyncSession) -> list[AgentTemplate]:
    """Templates the current user has published — seller side dashboard."""
    result = await db.execute(
        select(AgentTemplate)
        .where(AgentTemplate.user_id == current_user_id())
        .order_by(AgentTemplate.created_at.desc())
    )
    return list(result.scalars().all())


# ─── Owner edits ──────────────────────────────────────────────────────


async def update_template(
    db: AsyncSession, template_id: uuid.UUID, **updates: Any
) -> AgentTemplate:
    """Patch a template's metadata. Only the owner can edit; snapshot stays frozen."""
    user_id = current_user_id()
    template = await db.get(AgentTemplate, template_id)
    if template is None or template.user_id != user_id:
        raise PermissionError("Template not found or not owned by user")

    for key, value in updates.items():
        if value is not None:
            setattr(template, key, value)
    await db.flush()
    await db.refresh(template)
    return template


async def archive_template(db: AsyncSession, template_id: uuid.UUID) -> None:
    """Soft delete — sets status=archived. Existing forks still work."""
    user_id = current_user_id()
    template = await db.get(AgentTemplate, template_id)
    if template is None or template.user_id != user_id:
        raise PermissionError("Template not found or not owned by user")
    template.status = "archived"
    await db.flush()


# ─── Fork (free path) ─────────────────────────────────────────────────


async def fork_template(
    db: AsyncSession, template_id: uuid.UUID
) -> tuple[Agent, AgentTemplatePurchase, AgentTemplateVersion]:
    """Fork a published template into the current user's agent list.

    V1 only handles free templates. Paid templates raise — V2 routes them
    through Stripe before reaching here.
    """
    user_id = current_user_id()

    template = await db.get(AgentTemplate, template_id)
    if template is None or template.status != "published":
        raise ValueError("Template not found or not published")

    if template.price_cents > 0:
        # V2 will gate this behind a Stripe payment intent confirmation.
        raise ValueError("Paid templates require purchase — V2 feature")

    # Use the current version (denormalised flag avoids ORDER BY at fork time).
    version_result = await db.execute(
        select(AgentTemplateVersion)
        .where(
            AgentTemplateVersion.template_id == template.id,
            AgentTemplateVersion.is_current == True,  # noqa: E712
        )
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    if version is None:
        raise RuntimeError(f"Template {template.id} has no current version")

    # 1. Clone the agent + tools + KB shells
    agent = await fork_snapshot_into_agent(
        db, version.snapshot, template_id=template.id, version_id=version.id
    )

    # 2. Audit row — same shape for free and paid
    purchase = AgentTemplatePurchase(
        buyer_id=user_id,
        template_id=template.id,
        version_id=version.id,
        price_paid_cents=0,
        currency=template.currency,
        status="paid",
    )
    db.add(purchase)

    # 3. Bump the denormalised counter
    await db.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == template.id)
        .values(fork_count=AgentTemplate.fork_count + 1)
    )

    await db.flush()
    await db.refresh(purchase)
    return agent, purchase, version


# ─── Buyer library ────────────────────────────────────────────────────


async def list_my_forks(db: AsyncSession) -> list[Agent]:
    """Agents the current user has forked from the Hub."""
    result = await db.execute(
        select(Agent)
        .where(
            Agent.user_id == current_user_id(),
            Agent.template_id.is_not(None),
        )
        .order_by(Agent.created_at.desc())
    )
    return list(result.scalars().all())
