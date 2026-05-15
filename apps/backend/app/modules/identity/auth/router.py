"""Auth feature router — aggregates the subrouters under ``/auth``.

Each subrouter under :mod:`.routers` owns one slice of the auth
surface (lifecycle, profile, email management, password recovery,
MFA-during-login). Adding a new auth-adjacent endpoint =
drop it into the right subrouter rather than expanding a monolith
here.

This file used to hold all 16 endpoints inline (726 LOC). The
behaviour-preserving split is documented in
``docs/backend/module-template.md``.
"""

from fastapi import APIRouter

from app.modules.identity.auth.routers import (
    basic,
    email,
    gdpr,
    mfa_login,
    password_reset,
    profile,
    session,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Order is presentation-only (FastAPI iterates by inclusion order for
# the OpenAPI spec). Logical grouping: lifecycle first, then MFA
# follow-up, then everything tied to "/me", then public recovery, then
# the data-rights surface (export/delete), then session state +
# workspace enter/exit (Phase 0 of the Hub refactor).
router.include_router(basic.router)
router.include_router(mfa_login.router)
router.include_router(profile.router)
router.include_router(email.router)
router.include_router(password_reset.router)
router.include_router(gdpr.router)
router.include_router(session.router)
