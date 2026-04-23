"""Internal API — endpoints consumed only by the dispatcher.

Everything under `/api/internal/*` is guarded by :func:`require_dispatcher`.
Add new sub-modules as sub-routers below — one guard, one place to monitor.
"""

from fastapi import APIRouter, Depends

from app.internal.guard import require_dispatcher
from app.internal.knowledge import router as knowledge_router

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_dispatcher)],
)

router.include_router(knowledge_router)
