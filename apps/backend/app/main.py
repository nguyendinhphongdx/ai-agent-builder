import logging
import time
import uuid

from fastapi import Cookie, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
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

from app.agents.router import router as agents_router
from app.auth.router import router as auth_router
from app.auth.oauth_router import router as oauth_router
from app.auth.service import decode_token
from app.config import settings
from app.conversations.router import router as conversations_router
from app.db.session import get_db
from app.knowledge.router import router as knowledge_router
from app.tools.router import router as tools_router
from app.workflows.router import router as workflows_router
from app.multi_agent.router import router as multi_agent_router
from app.ai_credentials.router import router as ai_credentials_router
from app.llm.router import router as llm_router
from app.internal.router import router as internal_router
from app.external.router import router as external_router
from app.integrations.router import router as integrations_router
from app.personal_tokens.router import router as personal_tokens_router
from app.share.router import router as share_router
from app.webhooks.router import router as webhooks_router


def create_app() -> FastAPI:
    """Khởi tạo ứng dụng FastAPI với middleware, router và các endpoint."""
    app = FastAPI(
        title=settings.APP_NAME,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Request/Response logging middleware
    # Paths to skip logging (static files)
    _SILENT_PREFIXES = ("/uploads/",)

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

    # CORS — split by route family:
    #   /api/external/*  → open to any origin (public API, no cookies)
    #   everything else  → restricted to the configured frontend origins (cookies)
    # Starlette's CORSMiddleware doesn't natively scope by path, so we mount it
    # twice via a tiny dispatcher that picks the right policy per request.
    class ScopedCORSMiddleware(BaseHTTPMiddleware):
        """Apply CORS-* response headers based on whether the path is public."""

        # Both families are origin-less by design: external uses Bearer tokens,
        # share uses opaque path tokens. Neither relies on cookies, so wildcard
        # CORS is safe — the embed widget lives on third-party sites.
        PUBLIC_PREFIXES = (
            f"{settings.API_PREFIX}/external/",
            f"{settings.API_PREFIX}/share/",
        )

        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            origin = request.headers.get("origin")
            if not origin:
                return response

            is_public = request.url.path.startswith(self.PUBLIC_PREFIXES)
            if is_public:
                # Public API — bearer/path-token auth, no cookies; any origin.
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
            elif origin in settings.CORS_ORIGINS:
                # Browser app — cookie-auth, must echo origin and allow creds.
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Vary"] = "Origin"
            return response

    # Built-in CORS for the cookie-auth app routes (handles preflight properly).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
    app.include_router(personal_tokens_router, prefix=settings.API_PREFIX)
    app.include_router(share_router, prefix=settings.API_PREFIX)

    from app.uploads.router import router as upload_router
    app.include_router(upload_router, prefix=settings.API_PREFIX)

    from app.notifications.router import router as notifications_router
    app.include_router(notifications_router, prefix=settings.API_PREFIX)

    # Log validation errors (422)
    from fastapi.exceptions import RequestValidationError
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"{request.method} {request.url.path} → ValidationError: {exc.errors()}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # Global exception handler (500)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"{request.method} {request.url.path} → {type(exc).__name__}: {exc}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # Endpoint kiểm tra trạng thái server
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
