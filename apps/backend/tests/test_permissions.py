"""Unit tests for the platform role hierarchy.

Pure — no DB. ``require_role`` itself is a FastAPI dep that needs a
request scope; we test the inner ``has_role`` helper which is the source
of truth.
"""
from __future__ import annotations

from app.modules.auth.permissions import UserRole, has_role


def test_admin_is_superset_of_all():
    assert has_role("admin", UserRole.USER)
    assert has_role("admin", UserRole.MODERATOR)
    assert has_role("admin", UserRole.SUPPORT)
    assert has_role("admin", UserRole.ADMIN)


def test_user_has_no_staff_privileges():
    assert has_role("user", UserRole.USER) is True
    assert has_role("user", UserRole.MODERATOR) is False
    assert has_role("user", UserRole.SUPPORT) is False
    assert has_role("user", UserRole.ADMIN) is False


def test_support_inherits_moderator():
    """Support tier is meant to do everything mod can plus refunds/bans."""
    assert has_role("support", UserRole.MODERATOR) is True
    assert has_role("support", UserRole.SUPPORT) is True
    assert has_role("support", UserRole.ADMIN) is False


def test_moderator_does_not_get_support_powers():
    """Mod can suspend templates but should NOT be able to refund money."""
    assert has_role("moderator", UserRole.MODERATOR) is True
    assert has_role("moderator", UserRole.SUPPORT) is False


def test_unknown_role_denied():
    """Defence in depth: a row with a corrupted role fails closed."""
    assert has_role("god-mode", UserRole.USER) is False
    assert has_role("", UserRole.USER) is False
    assert has_role(None, UserRole.USER) is False  # type: ignore[arg-type]
