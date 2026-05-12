"""Browser-facing /api/integrations/* — status + preview endpoints used by
the Settings → Integrations UI to verify a channel is wired up correctly.

External clients should use ``/api/external/*`` instead — these routes are
cookie-auth only and tied to the dashboard."""

from fastapi import APIRouter

from app.modules.integrations.mcp import router as mcp_router

router = APIRouter(prefix="/integrations")
router.include_router(mcp_router)
