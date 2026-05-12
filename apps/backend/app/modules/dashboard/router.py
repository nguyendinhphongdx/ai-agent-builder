"""Personal dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.service import get_dashboard
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/me/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=DashboardResponse)
async def dashboard_endpoint(db: AsyncSession = Depends(get_db)) -> DashboardResponse:
    """Combined personal stats — agents, conversations, tokens, revenue."""
    return await get_dashboard(db)
