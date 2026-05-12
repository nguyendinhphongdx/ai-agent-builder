"""Author payout management — Stripe Connect + MoMo connect + payment history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user
from app.modules.payouts import service
from app.platform.db.session import get_db


class MoMoConnectRequest(BaseModel):
    """Body for ``PATCH /me/payouts/momo`` — author's MoMo Business creds."""

    partner_code: str = Field(min_length=1, max_length=64)
    access_key: str = Field(min_length=1, max_length=128)
    secret_key: str = Field(min_length=1, max_length=256)

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


@router.get("/history", response_model=dict)
async def history_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    purchase_status: str | None = Query(default=None, alias="status"),
    provider: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Paginated paid-purchase history for templates the user owns.

    Query params:
      - ``limit``, ``offset`` — paging.
      - ``status=paid|refunded`` — filter by payment state.
      - ``provider=stripe|momo`` — filter by gateway.
    """
    items, total = await service.list_history(
        db,
        limit=limit,
        offset=offset,
        status=purchase_status,
        provider=provider,
    )
    return {
        "items": items,
        "total": total,
        "has_more": offset + len(items) < total,
    }


@router.get("/summary", response_model=dict)
async def summary_endpoint(db: AsyncSession = Depends(get_db)) -> dict:
    """Monthly + total revenue aggregates for the current user."""
    return await service.get_summary(db)


@router.patch("/momo", response_model=dict)
async def connect_momo_endpoint(
    body: MoMoConnectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save author's MoMo Business merchant credentials.

    The author registers with MoMo Business out-of-band first
    (Vietnamese business documents required); this endpoint just
    encrypts + stores the resulting ``(partnerCode, accessKey, secretKey)``
    so VND checkouts on their templates route to *their* MoMo balance.
    """
    try:
        result = await service.connect_momo(
            db,
            partner_code=body.partner_code,
            access_key=body.access_key,
            secret_key=body.secret_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return result


@router.delete("/momo", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_momo_endpoint(db: AsyncSession = Depends(get_db)):
    """Forget the author's MoMo credentials. Future VND checkouts fall
    back to platform-collects (manual settlement)."""
    await service.disconnect_momo(db)
    await db.commit()
