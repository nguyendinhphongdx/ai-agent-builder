"""Public external API — mounted at ``/api/external/*``.

Auth: ``Authorization: Bearer afpt_...`` (personal access token). Cookie auth
also works (since :func:`get_current_user` accepts both), but external clients
should always use a token so per-request scope/quota tracking applies.

Add new sub-routers here to keep ``main.py`` clean.
"""
from fastapi import APIRouter, Depends

from app.modules.external.agents import router as agents_router
from app.modules.external.conversations import router as conversations_router
from app.platform.rate_limit import enforce_external_rate_limit

# Rate limit applies to every endpoint mounted on this router. Cookie sessions
# bypass automatically (the dependency checks ``request.state.api_token``).
router = APIRouter(
    prefix="/external",
    dependencies=[Depends(enforce_external_rate_limit)],
)
router.include_router(agents_router)
router.include_router(conversations_router)
