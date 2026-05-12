"""Seed (or re-seed) the 5 official starter templates into the Hub.

Usage:
    python -m app.platform.cli.seed_starter_templates --owner-email admin@example.com

Idempotent — looks up by slug. If a template exists, refreshes its
metadata + replaces the current snapshot version (preserving fork_count
/ rating aggregates). If not, creates both rows.

Starter templates are owned by the admin you point at — that's just the
DB's ``user_id`` foreign key. The displayed author is hard-coded
``AgentForge`` via ``author_name``.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_template import AgentTemplate
from app.models.agent_template_version import AgentTemplateVersion
from app.models.user import User
from app.platform.cli._starter_templates import DEFAULT_AUTHOR_NAME, STARTERS, build_snapshot
from app.platform.db.session import async_session_factory


async def _resolve_owner(session: AsyncSession, email: str) -> User:
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        raise SystemExit(f"No user with email {email!r}. Run seed_admin first.")
    if user.role not in ("admin", "moderator", "support"):
        raise SystemExit(
            f"User {email!r} has role={user.role!r}; only staff can own starter templates."
        )
    return user


async def _upsert_starter(
    session: AsyncSession,
    starter: dict,
    owner: User,
) -> tuple[str, AgentTemplate]:
    snapshot = build_snapshot(starter)

    existing = (
        await session.execute(
            select(AgentTemplate).where(AgentTemplate.slug == starter["slug"])
        )
    ).scalar_one_or_none()

    if existing is None:
        template = AgentTemplate(
            user_id=owner.id,
            slug=starter["slug"],
            title=starter["title"],
            description=starter["description"],
            author_name=DEFAULT_AUTHOR_NAME,
            category=starter.get("category"),
            tags=starter.get("tags", []),
            cover_image_url=None,
            price_cents=0,
            currency="USD",
            status="published",
            is_featured=True,
        )
        session.add(template)
        await session.flush()
        version = AgentTemplateVersion(
            template_id=template.id,
            version="1.0.0",
            snapshot=snapshot,
            changelog="Initial seed.",
            is_current=True,
        )
        session.add(version)
        return "created", template

    # Refresh metadata. Keep aggregates (fork_count, rating_*).
    existing.title = starter["title"]
    existing.description = starter["description"]
    existing.category = starter.get("category")
    existing.tags = starter.get("tags", [])
    existing.author_name = DEFAULT_AUTHOR_NAME
    existing.is_featured = True
    existing.status = "published"

    # Replace the "current" version's snapshot in place. We don't bump version
    # for a re-seed; the snapshot diff is what matters for live forks.
    current = (
        await session.execute(
            select(AgentTemplateVersion)
            .where(AgentTemplateVersion.template_id == existing.id)
            .where(AgentTemplateVersion.is_current.is_(True))
        )
    ).scalar_one_or_none()
    if current is None:
        # Recover from a half-broken seed.
        version = AgentTemplateVersion(
            template_id=existing.id,
            version="1.0.0",
            snapshot=snapshot,
            changelog="Re-seed (recovery — no prior version found).",
            is_current=True,
        )
        session.add(version)
    else:
        await session.execute(
            update(AgentTemplateVersion)
            .where(AgentTemplateVersion.id == current.id)
            .values(snapshot=snapshot)
        )
    return "updated", existing


async def _seed(owner_email: str) -> int:
    async with async_session_factory() as session:
        owner = await _resolve_owner(session, owner_email)
        for starter in STARTERS:
            action, template = await _upsert_starter(session, starter, owner)
            print(f"  {action:>7}  {template.slug:<30} {template.title}")
        await session.commit()
    print(f"✓ {len(STARTERS)} starter templates ready.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="seed_starter_templates",
        description="Create or refresh the 5 official Hub starter templates.",
    )
    parser.add_argument(
        "--owner-email",
        required=True,
        help="Email of the staff user that owns the seeded rows (admin/moderator/support).",
    )
    args = parser.parse_args()
    return asyncio.run(_seed(args.owner_email))


if __name__ == "__main__":
    sys.exit(main())
