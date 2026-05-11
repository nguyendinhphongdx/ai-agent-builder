import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agentforge")

# Suppress noisy loggers
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Init Sentry before app construction so its integrations can hook the
# Starlette ASGI app + asyncio event loop. No-op when SENTRY_DSN is unset.
from app.config import settings as _settings  # noqa: E402
from app.observability import init_sentry, install_json_formatter  # noqa: E402

init_sentry()

# Switch root logger handlers to JSON formatting in production. Done after
# basicConfig so we replace the freshly-installed StreamHandler's formatter.
if _settings.LOG_FORMAT == "json":
    install_json_formatter()

from app.admin.router import router as admin_router
from app.agents.router import router as agents_router
from app.ai_credentials.router import router as ai_credentials_router
from app.auth.oauth_router import router as oauth_router
from app.auth.router import router as auth_router
from app.config import settings
from app.conversations.router import router as conversations_router
from app.dashboard.router import router as dashboard_router
from app.external.router import router as external_router
from app.hub.router import auth_router as hub_auth_router
from app.hub.router import public_router as hub_public_router
from app.integrations.router import router as integrations_router
from app.internal.router import router as internal_router
from app.jobs.router import router as jobs_router
from app.knowledge.router import router as knowledge_router
from app.mfa.router import router as mfa_router
from app.llm.router import router as llm_router
from app.multi_agent.router import router as multi_agent_router
from app.payments.webhooks import momo_router as momo_webhook_router
from app.payments.webhooks import stripe_router as stripe_webhook_router
from app.payouts.router import router as payouts_router
from app.permissions.router import router as permissions_router
from app.personal_tokens.router import router as personal_tokens_router
from app.audit.router import org_router as org_audit_router
from app.scim.router import router as scim_router
from app.share.router import router as share_router
from app.sso.oidc_router import router as sso_oidc_router
from app.sso.router import router as sso_admin_router
from app.tools.router import router as tools_router
from app.webhooks.router import router as webhooks_router
from app.workflows.router import router as workflows_router
from app.workspaces.router import router as workspaces_router


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """App-wide startup/shutdown hooks. Boots background services
    that share the API process; add new ones here as they land."""
    from app.audit import purge as audit_purge
    from app.scheduled_triggers import scheduler

    scheduler.start()
    audit_purge.start()
    try:
        yield
    finally:
        await audit_purge.stop()
        await scheduler.stop()


def create_app() -> FastAPI:
    """Khởi tạo ứng dụng FastAPI với middleware, router và các endpoint."""
    app = FastAPI(
        title=settings.APP_NAME,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    # Request id + structured access log. Order matters: RequestId runs first
    # so the access log line (and any deeper logger.* calls) carries the id.
    from app.observability import (
        RequestIdMiddleware,
        StructuredAccessLogMiddleware,
    )

    if settings.LOG_FORMAT == "json":
        app.add_middleware(StructuredAccessLogMiddleware)
        app.add_middleware(RequestIdMiddleware)
    else:
        # Dev: keep the human-readable text logger.
        _SILENT_PREFIXES = ("/uploads/", "/healthz", "/readyz")

        class LoggingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                path = request.url.path
                if path.startswith(_SILENT_PREFIXES):
                    return await call_next(request)
                start = time.time()
                logger.info(f"→ {request.method} {path}")
                response = await call_next(request)
                ms = int((time.time() - start) * 1000)
                logger.info(f"← {request.method} {path} {response.status_code} ({ms}ms)")
                return response

        app.add_middleware(LoggingMiddleware)
        app.add_middleware(RequestIdMiddleware)

    # CSRF guard — for cookie-authenticated mutating requests, require Origin to
    # match an allow-listed CORS origin. Bearer-token / no-cookie callers are
    # exempt: they aren't subject to CSRF (no ambient credentials in the browser).
    _MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    _CSRF_PUBLIC_PREFIXES = (
        f"{settings.API_PREFIX}/external/",
        f"{settings.API_PREFIX}/share/",
        f"{settings.API_PREFIX}/internal/",
        f"{settings.API_PREFIX}/auth/oauth/",
    )

    class CSRFOriginMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.method in _MUTATING_METHODS and not request.url.path.startswith(_CSRF_PUBLIC_PREFIXES):
                # Only enforce when the caller is using cookie auth.
                if "access_token" in request.cookies or "refresh_token" in request.cookies:
                    origin = request.headers.get("origin") or request.headers.get("referer")
                    if origin:
                        # Compare origin (scheme://host[:port]) prefix against allowlist.
                        if not any(origin.startswith(o) for o in settings.CORS_ORIGINS):
                            return JSONResponse(
                                status_code=403,
                                content={"detail": "Origin not allowed"},
                            )
            return await call_next(request)

    app.add_middleware(CSRFOriginMiddleware)

    # CORS — split by route family. One middleware now handles both regular
    # responses and OPTIONS preflight, so we don't stack Starlette's built-in
    # CORSMiddleware on top (the two used to fight over the same headers).
    #   /api/external/*  → open to any origin (public API, no cookies)
    #   /api/share/*     → open to any origin (path-token auth, no cookies)
    #   everything else  → restricted to settings.CORS_ORIGINS (cookies)
    class ScopedCORSMiddleware(BaseHTTPMiddleware):
        """Apply CORS-* response headers based on whether the path is public.

        Single source of truth for CORS: also short-circuits OPTIONS preflight
        so Starlette doesn't reach a route handler that may not allow OPTIONS.
        """

        PUBLIC_PREFIXES = (
            f"{settings.API_PREFIX}/external/",
            f"{settings.API_PREFIX}/share/",
        )

        async def dispatch(self, request: Request, call_next):
            origin = request.headers.get("origin")
            is_public = request.url.path.startswith(self.PUBLIC_PREFIXES)
            is_preflight = (
                request.method == "OPTIONS"
                and "access-control-request-method" in request.headers
            )

            if is_preflight and origin:
                response = Response(status_code=204)
                self._apply_headers(response, origin, is_public, request)
                return response

            response = await call_next(request)
            if origin:
                self._apply_headers(response, origin, is_public, request)
            return response

        @staticmethod
        def _apply_headers(
            response: Response,
            origin: str,
            is_public: bool,
            request: Request,
        ) -> None:
            requested_headers = request.headers.get(
                "access-control-request-headers", "*"
            )
            requested_method = request.headers.get(
                "access-control-request-method", "*"
            )
            if is_public:
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = requested_method
                response.headers["Access-Control-Allow-Headers"] = requested_headers
                response.headers["Access-Control-Max-Age"] = "86400"
            elif origin in settings.CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = requested_method
                response.headers["Access-Control-Allow-Headers"] = requested_headers
                response.headers["Access-Control-Max-Age"] = "86400"
                response.headers["Vary"] = "Origin"

    app.add_middleware(ScopedCORSMiddleware)

    # Serve uploaded files (avatars, documents)
    import os

    from fastapi.staticfiles import StaticFiles
    uploads_dir = settings.UPLOAD_DIR
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # REST routers
    app.include_router(auth_router, prefix=settings.API_PREFIX)
    app.include_router(oauth_router, prefix=settings.API_PREFIX)
    app.include_router(agents_router, prefix=settings.API_PREFIX)
    app.include_router(ai_credentials_router, prefix=settings.API_PREFIX)
    app.include_router(llm_router, prefix=settings.API_PREFIX)
    app.include_router(tools_router, prefix=settings.API_PREFIX)
    app.include_router(knowledge_router, prefix=settings.API_PREFIX)
    app.include_router(conversations_router, prefix=settings.API_PREFIX)
    app.include_router(workflows_router, prefix=settings.API_PREFIX)
    app.include_router(multi_agent_router, prefix=settings.API_PREFIX)
    app.include_router(webhooks_router, prefix=settings.API_PREFIX)
    app.include_router(internal_router, prefix=settings.API_PREFIX)
    app.include_router(external_router, prefix=settings.API_PREFIX)
    app.include_router(integrations_router, prefix=settings.API_PREFIX)
    app.include_router(jobs_router, prefix=settings.API_PREFIX)
    app.include_router(permissions_router, prefix=settings.API_PREFIX)
    app.include_router(personal_tokens_router, prefix=settings.API_PREFIX)
    app.include_router(share_router, prefix=settings.API_PREFIX)
    app.include_router(sso_oidc_router, prefix=settings.API_PREFIX)
    app.include_router(sso_admin_router, prefix=settings.API_PREFIX)
    app.include_router(scim_router, prefix=settings.API_PREFIX)
    app.include_router(mfa_router, prefix=settings.API_PREFIX)
    app.include_router(org_audit_router, prefix=settings.API_PREFIX)
    app.include_router(workspaces_router, prefix=settings.API_PREFIX)
    # Hub: public browse + detail, then authenticated fork/publish/edit on the
    # same /templates prefix. Order matters — public routes are defined before
    # the auth-gated ones in routers, but FastAPI matches by path so order of
    # include here doesn't affect routing.
    app.include_router(hub_public_router, prefix=settings.API_PREFIX)
    app.include_router(hub_auth_router, prefix=settings.API_PREFIX)
    # Stripe webhook — public, signature-verified. Mounted at
    # /api/webhooks/stripe (separate from /api/webhooks/{wf}/... which is
    # the workflow-trigger webhook with its own URL token scheme).
    app.include_router(stripe_webhook_router, prefix=settings.API_PREFIX)
    app.include_router(momo_webhook_router, prefix=settings.API_PREFIX)
    # Platform admin — gated by user.role hierarchy (moderator/support/admin).
    app.include_router(admin_router, prefix=settings.API_PREFIX)
    # Author payouts — Stripe Connect onboarding + status + payment history.
    app.include_router(payouts_router, prefix=settings.API_PREFIX)
    # Personal dashboard — combined stats endpoint.
    app.include_router(dashboard_router, prefix=settings.API_PREFIX)

    # File uploads are handled by the knowledge router (document upload) and
    # the static `/uploads/` mount above. The dedicated upload router was
    # never written — re-add this import only if/when `app/uploads/` exists.

    from app.notifications.router import router as notifications_router
    app.include_router(notifications_router, prefix=settings.API_PREFIX)

    # Log validation errors (422)
    from fastapi.exceptions import RequestValidationError
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"{request.method} {request.url.path} → ValidationError: {exc.errors()}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # Global exception handler (500). Never echo raw exception text to clients —
    # provider/SDK errors can carry API keys, SQL fragments, or filesystem paths.
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"{request.method} {request.url.path} → {type(exc).__name__}: {exc}")
        detail = f"{type(exc).__name__}: {exc}" if settings.DEBUG else "Internal server error"
        return JSONResponse(status_code=500, content={"detail": detail})

    # Liveness + readiness at the root (not under /api/) so infra probes hit
    # them directly. Legacy `/api/health` kept for backwards compat.
    from app.observability import health_router

    app.include_router(health_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
