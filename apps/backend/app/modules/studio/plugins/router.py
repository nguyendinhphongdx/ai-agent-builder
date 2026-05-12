"""Plugin registry API.

  GET    /api/plugins                  list installed plugins
  POST   /api/plugins/install          install from YAML / JSON
  PATCH  /api/plugins/{id}/status      enable/disable
  DELETE /api/plugins/{id}             uninstall
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.studio.plugins import service
from app.platform.db.session import get_db

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginResponse(BaseModel):
    id: uuid.UUID
    slug: str
    version: str
    name: str
    description: str | None
    runtime: str
    status: str
    manifest: dict[str, Any]
    installed_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InstallRequest(BaseModel):
    # One of the two must be set. ``manifest_yaml`` is the raw
    # plugin.yaml string; ``manifest`` is a pre-parsed dict for
    # callers that already have it (e.g. marketplace import flow).
    manifest_yaml: str | None = None
    manifest: dict[str, Any] | None = None


class StatusPatch(BaseModel):
    enabled: bool


@router.get("", response_model=list[PluginResponse])
async def list_endpoint(db: AsyncSession = Depends(get_db)):
    rows = await service.list_plugins(db)
    return [PluginResponse.model_validate(r) for r in rows]


@router.post("/install", response_model=PluginResponse, status_code=201)
async def install_endpoint(
    payload: InstallRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    raw = payload.manifest_yaml or payload.manifest
    if raw is None:
        raise HTTPException(
            status_code=400,
            detail="provide manifest_yaml or manifest",
        )
    try:
        row = await service.install_plugin(db, raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return PluginResponse.model_validate(row)


@router.patch("/{plugin_id}/status", response_model=PluginResponse)
async def patch_status(
    plugin_id: uuid.UUID,
    payload: StatusPatch,
    db: AsyncSession = Depends(get_db),
):
    plugin = await service.get_plugin(db, plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    plugin = await service.set_status(db, plugin, enabled=payload.enabled)
    await db.commit()
    return PluginResponse.model_validate(plugin)


@router.delete("/{plugin_id}", status_code=204)
async def uninstall_endpoint(
    plugin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    plugin = await service.get_plugin(db, plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="plugin_not_found")
    await service.uninstall_plugin(db, plugin)
    await db.commit()
    return None
