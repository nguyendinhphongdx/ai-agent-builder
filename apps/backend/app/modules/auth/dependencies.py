"""Auth dependencies — resolve current user from cookie OR API token header.

Single ``get_current_user`` accepts both:
  - ``Authorization: Bearer afpt_...`` header (external API clients)
  - ``access_token`` cookie (browser sessions)

Header takes precedence when both are present. The resolved
:class:`PersonalAccessToken` is stashed on ``request.state.api_token`` so
downstream dependencies (``require_scope``, rate-limit middleware) can
distinguish API requests from cookie requests without re-decoding.
"""
from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace
from app.modules.auth.service import decode_token, get_user_by_id
from app.modules.personal_tokens.service import verify_plaintext
from app.platform.context import set_current_user_id, set_current_workspace_id
from app.platform.db.session import get_db

# Paths exempt from the ``force_mfa`` workspace gate. The user has to
# be able to reach these even without MFA enrolled, otherwise the
# only way to satisfy the gate (enrolling TOTP) would be blocked by
# the gate itself.
_MFA_EXEMPT_PREFIXES = (
    "/api/auth/mfa/",       # enrolment + verify endpoints
    "/api/auth/logout",     # always allow sign-out
    "/api/auth/refresh",    # session refresh
    "/api/users/me",        # whoami — used by the FE to detect mfa_enabled
)


def _bearer_token(authorization: str | None) -> str | None:
    """Extract the token portion of an ``Authorization: Bearer <value>`` header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current user from API token (header) or cookie session.

    Also seeds the ``current_workspace_id`` ContextVar from
    ``X-Workspace-Id`` header when present, falling back to
    ``user.default_workspace_id``. Membership enforcement happens
    later in workspace-scoped routers — this dependency just plumbs
    the value through so service queries can read it.
    """
    # ── 1. Bearer API token ──────────────────────────────────────────
    bearer = _bearer_token(authorization)
    if bearer:
        result = await verify_plaintext(db, bearer)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API token",
            )
        token, user = result
        # Stash for require_scope + rate-limit middleware downstream.
        request.state.api_token = token
        set_current_user_id(user.id)
        # API tokens carry their OWN workspace binding (set at mint
        # time). Ignore the header — the token is the source of truth
        # for which tenant this request can see. Legacy tokens with
        # workspace_id IS NULL fall back to the user's default
        # workspace, matching pre-Phase-1.1 behavior.
        set_current_workspace_id(token.workspace_id or user.default_workspace_id)
        return user

    # ── 2. Cookie session ────────────────────────────────────────────
    request.state.api_token = None  # explicit: marker for "not API auth"

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(access_token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    set_current_user_id(user.id)
    _seed_workspace_context(user, x_workspace_id)
    await _enforce_workspace_mfa(request, user, db)
    await _enforce_workspace_ip_allowlist(request, db)
    return user


async def _enforce_workspace_mfa(
    request: Request, user: User, db: AsyncSession
) -> None:
    """Block requests when the active workspace has ``force_mfa=True``
    and the user hasn't enrolled MFA.

    Skips:
      - exempt paths (enrol + sign-out + whoami)
      - API-token auth (tokens carry their own scope; MFA gate would
        break programmatic clients that legitimately can't TOTP)
      - users who've already enrolled
    """
    # API-token requests bypass — header-only programmatic auth.
    if getattr(request.state, "api_token", None) is not None:
        return
    if user.mfa_enabled:
        return

    path = request.url.path
    if any(path.startswith(p) for p in _MFA_EXEMPT_PREFIXES):
        return

    # Read the active workspace's force_mfa flag.
    from app.platform.context import current_workspace_id_or_none

    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return  # no workspace context = no enforcement

    force_mfa = await db.scalar(
        select(Workspace.force_mfa).where(Workspace.id == workspace_id)
    )
    if force_mfa:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="mfa_required",
        )


async def _enforce_workspace_ip_allowlist(
    request: Request, db: AsyncSession
) -> None:
    """Block requests whose client IP isn't in the active workspace's
    CIDR allowlist.

    Empty allowlist → no restriction (the common case). Non-empty
    list + no match → 403 ``ip_not_allowed``. API-token requests
    bypass — those are typically programmatic clients from CI
    runners where IP allowlisting is enforced at the network layer."""
    if getattr(request.state, "api_token", None) is not None:
        return

    from app.modules.sso.service import ip_matches_any, list_ip_rules
    from app.platform.context import current_workspace_id_or_none

    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return

    rules = await list_ip_rules(db, workspace_id)
    if not rules:
        return  # no restriction configured

    client_ip = _client_ip(request)
    if not ip_matches_any(client_ip, rules):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ip_not_allowed",
        )


def _client_ip(request: Request) -> str:
    """Resolve caller IP — first hop of X-Forwarded-For, else
    request.client.host. Same heuristic as the share-channel rate
    limiter."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


def _seed_workspace_context(user: User, header_value: str | None) -> None:
    """Pick the active workspace for this request and stash it in the
    ContextVar.

    Resolution order:
      1. ``X-Workspace-Id`` header — explicit override from the client.
         Membership/permission enforcement is the responsibility of
         workspace-scoped routers; this dep just propagates the value.
      2. ``user.default_workspace_id`` — set during ``ensure_personal_
         workspace`` at signup / first login.
      3. ``None`` — pre-multi-tenancy users that haven't been backfilled
         yet. Service queries during the transition treat this as
         "no workspace scope".

    Bad header values silently fall back to the default rather than
    erroring — same forgiveness model as Accept-Language.
    """
    import uuid as _uuid  # local import keeps the module's public surface tight

    chosen: _uuid.UUID | None = None
    if header_value:
        try:
            chosen = _uuid.UUID(header_value)
        except ValueError:
            chosen = None
    if chosen is None:
        chosen = user.default_workspace_id
    set_current_workspace_id(chosen)


def require_scope(scope: str):
    """Dependency factory — enforce a scope when the request is API-key auth.

    Cookie sessions bypass scope checks entirely: a logged-in browser session
    is the resource owner with full permission. API tokens are explicitly
    constrained — token must list ``scope`` in its ``scopes`` array.

    Note: callers must declare ``Depends(get_current_user)`` BEFORE this
    dependency in the endpoint signature so ``request.state.api_token`` is set.
    """

    async def _check(request: Request) -> None:
        token = getattr(request.state, "api_token", None)
        if token is None:
            return  # cookie session — owner, allow
        if scope not in (token.scopes or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token missing required scope: {scope}",
            )

    return _check
