"""Smoke test for the Phase 1.1 step-3 backfill CLI.

Covers the high-value end-to-end path: legacy rows with
``workspace_id IS NULL`` get stamped after running the script's
two phases. Doesn't exhaustively re-test every table — that's the
job of each resource table's isolation test suite.
"""
from __future__ import annotations

from sqlalchemy import select

from app.platform.cli.backfill_tenancy import _phase_a_users, _phase_b_resources
from app.models.agent import Agent
from app.models.knowledge_base import KnowledgeBase
from tests.factories import UserFactory, create


async def test_phase_a_provisions_personal_workspaces(db_session) -> None:
    """Users without default_workspace_id get a personal Org+Workspace+
    owner-Member tuple materialised."""
    u1 = await create(db_session, UserFactory, email="legacy1@example.com")
    u2 = await create(db_session, UserFactory, email="legacy2@example.com")
    # Neither user has default_workspace_id set — that's the legacy state.
    assert u1.default_workspace_id is None
    assert u2.default_workspace_id is None

    count = await _phase_a_users(db_session, dry_run=False, batch_size=100)
    assert count == 2

    await db_session.refresh(u1)
    await db_session.refresh(u2)
    assert u1.default_workspace_id is not None
    assert u2.default_workspace_id is not None
    assert u1.default_workspace_id != u2.default_workspace_id


async def test_phase_a_dry_run_does_not_persist(db_session) -> None:
    user = await create(db_session, UserFactory)
    count = await _phase_a_users(db_session, dry_run=True, batch_size=100)
    assert count == 1
    await db_session.refresh(user)
    # Dry-run must leave the pointer untouched.
    assert user.default_workspace_id is None


async def test_phase_b_stamps_resource_rows(db_session) -> None:
    """Insert legacy rows (workspace_id NULL) then run backfill —
    every row should end up tagged with the owner's personal workspace."""
    user = await create(db_session, UserFactory)
    # Phase A first to provision the workspace pointer.
    await _phase_a_users(db_session, dry_run=False, batch_size=100)
    await db_session.refresh(user)
    target_ws_id = user.default_workspace_id
    assert target_ws_id is not None

    # Insert legacy resources with workspace_id=NULL.
    agent = Agent(
        user_id=user.id,
        workspace_id=None,
        name="legacy-agent",
        system_prompt="x",
        model_id="openai/gpt-4o",
    )
    kb = KnowledgeBase(
        user_id=user.id,
        workspace_id=None,
        name="legacy-kb",
    )
    db_session.add_all([agent, kb])
    await db_session.flush()

    counts = await _phase_b_resources(db_session, dry_run=False, batch_size=100)
    assert counts["agents"] >= 1
    assert counts["knowledge_bases"] >= 1

    # Round-trip via SELECT so we see what's actually on disk.
    fetched_agent = await db_session.scalar(select(Agent).where(Agent.id == agent.id))
    fetched_kb = await db_session.scalar(
        select(KnowledgeBase).where(KnowledgeBase.id == kb.id)
    )
    assert fetched_agent.workspace_id == target_ws_id
    assert fetched_kb.workspace_id == target_ws_id


async def test_phase_b_idempotent(db_session) -> None:
    """Re-running on a clean DB should report zero updates — the
    table-level NULL count is the loop's exit condition."""
    await create(db_session, UserFactory)
    await _phase_a_users(db_session, dry_run=False, batch_size=100)

    # First pass — nothing to backfill since no legacy resources exist.
    first = await _phase_b_resources(db_session, dry_run=False, batch_size=100)
    assert all(n == 0 for n in first.values())

    # Second pass — same result. The script is safe to re-run on green.
    second = await _phase_b_resources(db_session, dry_run=False, batch_size=100)
    assert all(n == 0 for n in second.values())
