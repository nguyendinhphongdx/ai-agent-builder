"""3-legged OAuth router.

Routes:
  GET  /api/oauth-connectors/providers              list configured providers
  GET  /api/oauth-connectors/connections            list user's connections
  DELETE /api/oauth-connectors/connections/{id}     unlink
  POST /api/oauth-connectors/{provider}/start       mint state + return authorize URL
  GET  /api/oauth-connectors/{provider}/callback    provider redirects here
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth.dependencies import get_current_user
from app.modules.integrations.connectors.oauth import service
from app.modules.integrations.connectors.oauth.providers import PROVIDERS, get_provider
from app.platform.config import settings
from app.platform.db.session import get_db

logger = logging.getLogger("agentforge")

router = APIRouter(
    prefix="/oauth-connectors",
    tags=["oauth-connectors"],
)


class ProviderListItem(BaseModel):
    id: str
    label: str
    configured: bool


class StartRequest(BaseModel):
    return_to: str | None = None


class StartResponse(BaseModel):
    authorize_url: str


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    provider: str
    account_label: str | None
    external_account_id: str | None
    scope: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


@router.get("/providers", response_model=list[ProviderListItem])
async def list_providers(_user=Depends(get_current_user)):
    """Surfaces which providers are wired on this deployment so
    the FE can hide unconfigured Connect buttons."""
    return [
        ProviderListItem(id=p.id, label=p.label, configured=p.is_configured())
        for p in PROVIDERS.values()
    ]


@router.get("/connections", response_model=list[ConnectionResponse])
async def list_connections(
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_connections(db)
    return [
        ConnectionResponse(
            id=r.id,
            provider=r.provider,
            account_label=r.account_label,
            external_account_id=r.external_account_id,
            scope=r.scope,
            expires_at=r.expires_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.delete("/connections/{connection_id}", status_code=204)
async def unlink(
    connection_id: uuid.UUID,
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_connection(db, connection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="connection_not_found")
    await service.delete_connection(db, row)
    await db.commit()
    return None


@router.post("/{provider_id}/start", response_model=StartResponse)
async def start(
    provider_id: str,
    body: StartRequest,
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        url = await service.start_oauth(
            db,
            provider_id=provider_id,
            return_to=body.return_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return StartResponse(authorize_url=url)


@router.get("/{provider_id}/callback")
async def callback(
    provider_id: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Provider redirects the user's browser here. We complete the
    token exchange + redirect them back to the FE's ``return_to``.

    No auth dep — provider redirects can't carry our cookies
    reliably (the user IS arriving from a third-party site).
    State token + the workspace stamped on it during /start is
    what authenticates the callback.
    """
    if get_provider(provider_id) is None:
        raise HTTPException(status_code=404, detail="unknown_provider")
    if error:
        # User declined / provider rejected. Bounce them back to a
        # generic settings page with an error param.
        target = f"{settings.FRONTEND_URL}/settings/connections?error={error}"
        return RedirectResponse(target, status_code=302)
    if not code or not state:
        raise HTTPException(
            status_code=400, detail="missing_code_or_state"
        )

    try:
        connection, return_to = await service.complete_oauth(
            db, provider_id=provider_id, code=code, state=state
        )
    except ValueError as exc:
        logger.warning("oauth callback failed: %s", exc)
        target = (
            f"{settings.FRONTEND_URL}/settings/connections"
            f"?error={urlencode({'msg': str(exc)})}"
        )
        return RedirectResponse(target, status_code=302)
    await db.commit()

    # Build the final redirect — append success + connection id
    # so the FE knows what just got connected.
    base = (return_to or "/settings/connections").lstrip("/")
    sep = "&" if "?" in base else "?"
    target = (
        f"{settings.FRONTEND_URL}/{base}{sep}"
        f"oauth=success&connection_id={connection.id}&provider={provider_id}"
    )
    return RedirectResponse(target, status_code=302)
