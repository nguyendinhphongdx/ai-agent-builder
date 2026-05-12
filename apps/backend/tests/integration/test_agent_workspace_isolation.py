"""Tests for the Phase 1.1 step-2 ``agents.workspace_id`` rollout.

Covers:
  - ``create_agent`` auto-fills workspace_id from the ContextVar.
  - ``list_agents`` / ``get_agent`` only return rows scoped to the
    caller's active workspace (legacy NULL rows still surface during
    transition — assertion documents that behavior).
  - User A in workspace X never sees user B in workspace Y, even if
    they share the same DB.
"""
from __future__ import annotations

import pytest

from app.modules.agents.service import create_agent, get_agent, list_agents
from app.platform.context import (
    reset_current_user_id,
    reset_current_workspace_id,
    set_current_user_id,
    set_current_workspace_id,
)
from app.modules.workspaces.service import ensure_personal_workspace
from tests.factories import UserFactory, create


def _make_payload(name: str) -> dict:
    """Minimum required fields for an Agent row."""
    return {
        "name": name,
        "system_prompt": f"You are {name}.",
        "model_id": "openai/gpt-4o",
    }


@pytest.fixture
def user_context():
    """Helper that sets+resets both ContextVars in one shot."""
    tokens: list = []

    def _set(user_id, workspace_id):
        u = set_current_user_id(user_id)
        w = set_current_workspace_id(workspace_id)
        tokens.append((u, w))

    yield _set

    while tokens:
        u, w = tokens.pop()
        reset_current_workspace_id(w)
        reset_current_user_id(u)


async def test_create_agent_auto_fills_workspace_id(db_session, user_context) -> None:
    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)
    user_context(user.id, workspace.id)

    agent = await create_agent(db_session, **_make_payload("MyAgent"))

    assert agent.workspace_id == workspace.id
    assert agent.user_id == user.id


async def test_list_agents_isolated_per_workspace(db_session, user_context) -> None:
    """Two users with two personal workspaces. Each one only sees
    their own agent — the cross-tenant row stays hidden."""
    alice = await create(db_session, UserFactory, email="alice@example.com")
    bob = await create(db_session, UserFactory, email="bob@example.com")
    ws_a = await ensure_personal_workspace(db_session, alice)
    ws_b = await ensure_personal_workspace(db_session, bob)

    user_context(alice.id, ws_a.id)
    await create_agent(db_session, **_make_payload("Alice's Agent"))

    user_context(bob.id, ws_b.id)
    await create_agent(db_session, **_make_payload("Bob's Agent"))

    # Bob's session
    bob_agents = await list_agents(db_session)
    bob_names = {a.name for a in bob_agents}
    assert bob_names == {"Bob's Agent"}, (
        f"Bob saw cross-tenant rows: {bob_names}"
    )

    # Switch back to Alice
    user_context(alice.id, ws_a.id)
    alice_agents = await list_agents(db_session)
    alice_names = {a.name for a in alice_agents}
    assert alice_names == {"Alice's Agent"}


async def test_get_agent_blocks_cross_workspace_lookup(db_session, user_context) -> None:
    """Even when Bob knows Alice's agent UUID, fetching it from his
    own workspace context returns ``None`` — workspace filter wins."""
    alice = await create(db_session, UserFactory, email="alice@example.com")
    bob = await create(db_session, UserFactory, email="bob@example.com")
    ws_a = await ensure_personal_workspace(db_session, alice)
    ws_b = await ensure_personal_workspace(db_session, bob)

    user_context(alice.id, ws_a.id)
    alice_agent = await create_agent(db_session, **_make_payload("Alice's Agent"))

    user_context(bob.id, ws_b.id)
    sneaky_lookup = await get_agent(db_session, alice_agent.id)
    assert sneaky_lookup is None


async def test_legacy_null_rows_are_invisible_after_lock(
    db_session, user_context
) -> None:
    """Post-step-4 the dual-filter is gone — rows with ``workspace_id
    IS NULL`` should NOT surface when a workspace context is set.

    This was the documented transition behavior in step 2/3; step 4
    locked the column NOT NULL, so a freshly-listed workspace cannot
    contain legacy rows. The migration would have failed to apply
    if any NULL row existed. Test enforces the new contract.
    """
    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)

    # Insert a NULL-workspace row directly, bypassing the service
    # auto-fill (simulates an unscoped insert pre-lock).
    from app.models.agent import Agent

    legacy = Agent(
        user_id=user.id,
        workspace_id=None,
        name="Legacy Agent",
        system_prompt="x",
        model_id="openai/gpt-4o",
    )
    db_session.add(legacy)
    await db_session.flush()

    user_context(user.id, workspace.id)
    fresh = await create_agent(db_session, **_make_payload("Fresh Agent"))
    assert fresh.workspace_id == workspace.id

    # Listing must now hide the NULL row — strict filter.
    agents = await list_agents(db_session)
    names = {a.name for a in agents}
    assert names == {"Fresh Agent"}


async def test_no_workspace_context_falls_back_to_user_only(
    db_session, user_context
) -> None:
    """Callers without a workspace ContextVar (CLI scripts, background
    tasks) get the legacy ``WHERE user_id`` query — no implicit
    cross-tenant leak because a workspace_id of NULL means 'unscoped'
    and we don't shadow other tenants' rows."""
    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)

    user_context(user.id, workspace.id)
    await create_agent(db_session, **_make_payload("Scoped Agent"))

    # Drop the workspace context — simulates a CLI / cron job.
    user_context(user.id, None)
    agents = await list_agents(db_session)
    # Without workspace scope we still filter by user_id — and since
    # user only owns the one we just made, that's what we see.
    assert {a.name for a in agents} == {"Scoped Agent"}
