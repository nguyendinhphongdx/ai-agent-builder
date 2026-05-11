"""Phase 1.1 step-2 Group A rollout — workspace isolation for
ai_credentials + personal_access_tokens.

Mirrors test_agent_workspace_isolation.py: confirm auto-fill on
create, dual-filter on list (legacy NULL rows still visible),
cross-tenant rows hidden.
"""
from __future__ import annotations

import pytest

from app.ai_credentials.schemas import AICredentialCreate
from app.ai_credentials.service import (
    create_ai_credential,
    get_ai_credential,
    list_ai_credentials,
)
from app.context import (
    reset_current_user_id,
    reset_current_workspace_id,
    set_current_user_id,
    set_current_workspace_id,
)
from app.models.ai_credential import AICredential
from app.personal_tokens.schemas import TokenCreate
from app.personal_tokens.service import create_token, list_tokens, revoke_token
from app.workspaces.service import ensure_personal_workspace
from tests.factories import UserFactory, create


@pytest.fixture
def user_context():
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


# ─── ai_credentials ────────────────────────────────────────────────


async def test_create_credential_auto_fills_workspace_id(
    db_session, user_context, monkeypatch
) -> None:
    # Avoid real Fernet on test data — replace encryption with identity.
    from app.ai_credentials import service as svc

    monkeypatch.setattr(svc, "_encrypt", lambda s: s)
    monkeypatch.setattr(svc, "_decrypt", lambda s: s)

    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)
    user_context(user.id, workspace.id)

    await create_ai_credential(
        db_session,
        AICredentialCreate(
            provider="openai", name="prod", plaintext_key="sk-test-aaa"
        ),
    )

    # Fetch raw row to confirm the column got stamped.
    from sqlalchemy import select

    cred = await db_session.scalar(
        select(AICredential).where(AICredential.user_id == user.id)
    )
    assert cred is not None
    assert cred.workspace_id == workspace.id


async def test_list_credentials_isolated_per_workspace(
    db_session, user_context, monkeypatch
) -> None:
    from app.ai_credentials import service as svc

    monkeypatch.setattr(svc, "_encrypt", lambda s: s)
    monkeypatch.setattr(svc, "_decrypt", lambda s: s)

    alice = await create(db_session, UserFactory, email="alice@example.com")
    bob = await create(db_session, UserFactory, email="bob@example.com")
    ws_a = await ensure_personal_workspace(db_session, alice)
    ws_b = await ensure_personal_workspace(db_session, bob)

    user_context(alice.id, ws_a.id)
    await create_ai_credential(
        db_session,
        AICredentialCreate(provider="openai", name="Alice's", plaintext_key="k"),
    )

    user_context(bob.id, ws_b.id)
    await create_ai_credential(
        db_session,
        AICredentialCreate(provider="openai", name="Bob's", plaintext_key="k"),
    )

    bob_creds = await list_ai_credentials(db_session)
    assert {c.name for c in bob_creds} == {"Bob's"}


async def test_list_credentials_hides_null_rows_after_lock(
    db_session, user_context, monkeypatch
) -> None:
    """Post-step-4 the dual-filter is gone — NULL rows would have been
    caught by the lock migration's verification scan. This test
    pins the new strict-filter behavior: any NULL row that somehow
    persists is invisible in workspace-scoped listings."""
    from app.ai_credentials import service as svc

    monkeypatch.setattr(svc, "_encrypt", lambda s: s)
    monkeypatch.setattr(svc, "_decrypt", lambda s: s)

    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)
    legacy = AICredential(
        user_id=user.id,
        workspace_id=None,
        provider="openai",
        name="legacy",
        encrypted_key="legacy-key",
    )
    db_session.add(legacy)
    await db_session.flush()

    user_context(user.id, workspace.id)
    creds = await list_ai_credentials(db_session)
    assert not any(c.name == "legacy" for c in creds)


async def test_get_credential_cross_workspace_returns_none(
    db_session, user_context, monkeypatch
) -> None:
    from app.ai_credentials import service as svc

    monkeypatch.setattr(svc, "_encrypt", lambda s: s)
    monkeypatch.setattr(svc, "_decrypt", lambda s: s)

    user = await create(db_session, UserFactory)
    ws_a = await ensure_personal_workspace(db_session, user)
    # Make a second team workspace for the same user.
    from app.workspaces.service import create_team_workspace

    ws_b = await create_team_workspace(db_session, creator=user, name="Other")

    user_context(user.id, ws_a.id)
    created = await create_ai_credential(
        db_session,
        AICredentialCreate(provider="openai", name="in-A", plaintext_key="k"),
    )

    # Switch to workspace B — same user, but should not see ws_a's row.
    user_context(user.id, ws_b.id)
    fetched = await get_ai_credential(db_session, created.id)
    assert fetched is None


# ─── personal_access_tokens ────────────────────────────────────────


async def test_create_token_auto_fills_workspace_id(db_session, user_context) -> None:
    user = await create(db_session, UserFactory)
    workspace = await ensure_personal_workspace(db_session, user)
    user_context(user.id, workspace.id)

    token, _plaintext = await create_token(
        db_session, TokenCreate(name="ci", scopes=["agents:read"])
    )
    assert token.workspace_id == workspace.id


async def test_list_tokens_isolated_per_workspace(db_session, user_context) -> None:
    """User has 2 workspaces; tokens stamped in each are not cross-visible."""
    user = await create(db_session, UserFactory)
    ws_a = await ensure_personal_workspace(db_session, user)
    from app.workspaces.service import create_team_workspace

    ws_b = await create_team_workspace(db_session, creator=user, name="Other")

    user_context(user.id, ws_a.id)
    await create_token(db_session, TokenCreate(name="in-A", scopes=[]))

    user_context(user.id, ws_b.id)
    await create_token(db_session, TokenCreate(name="in-B", scopes=[]))

    tokens_in_b = await list_tokens(db_session)
    assert {t.name for t in tokens_in_b} == {"in-B"}


async def test_revoke_token_blocked_across_workspaces(
    db_session, user_context
) -> None:
    """A token minted in ws_a cannot be revoked while in ws_b context —
    dual-filter hides it from get()."""
    user = await create(db_session, UserFactory)
    ws_a = await ensure_personal_workspace(db_session, user)
    from app.workspaces.service import create_team_workspace

    ws_b = await create_team_workspace(db_session, creator=user, name="Other")

    user_context(user.id, ws_a.id)
    token, _ = await create_token(db_session, TokenCreate(name="a", scopes=[]))

    user_context(user.id, ws_b.id)
    ok = await revoke_token(db_session, token.id)
    assert ok is False

    user_context(user.id, ws_a.id)
    ok = await revoke_token(db_session, token.id)
    assert ok is True
