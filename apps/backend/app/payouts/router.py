"""Author payout management — Stripe Connect onboarding + status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.payouts import service

router = APIRouter(
    prefix="/me/payouts",
    tags=["payouts"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/onboarding-link", response_model=dict)
async def start_onboarding(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Mint a fresh Stripe Connect onboarding URL for the current user.

    Frontend should open it in a new tab and poll ``/me/payouts/status``
    until ``charges_enabled`` flips true.
    """
    try:
        url = await service.start_onboarding(db)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return {"url": url}


@router.get("/status", response_model=dict)
async def status_endpoint(db: AsyncSession = Depends(get_db)) -> dict:
    """Cached onboarding status for the current user."""
    return await service.get_status(db)


@router.post("/dashboard-link", response_model=dict)
async def dashboard_link(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """One-time login URL for the author's Stripe Express dashboard."""
    try:
        url = await service.create_dashboard_link(db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return {"url": url}
