"""Plugin install / list / uninstall — registry layer.

Doesn't *run* plugin code — that's the future plugin daemon's
job. This module is the source-of-truth list of installed
plugins per workspace, used by the FE to render the marketplace
"installed" view and by the daemon (when shipped) to know what
to spawn.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import (
    PLUGIN_STATUS_ACTIVE,
    PLUGIN_STATUS_DISABLED,
    Plugin,
)
from app.modules.studio.plugins.manifest import PluginManifest, parse_manifest
from app.platform.context import current_workspace_id_or_none


async def install_plugin(
    db: AsyncSession, raw_manifest: str | dict
) -> Plugin:
    """Validate the manifest, upsert the registry row.

    Same (slug, version) under the active workspace is idempotent:
    second install overwrites the row's manifest in place. Bumping
    ``version`` in plugin.yaml creates a new row alongside the old
    one — operator can then disable the older version.
    """
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise ValueError("no_active_workspace")

    manifest: PluginManifest = parse_manifest(raw_manifest)

    existing = await db.scalar(
        select(Plugin).where(
            Plugin.workspace_id == workspace_id,
            Plugin.slug == manifest.id,
            Plugin.version == manifest.version,
        )
    )
    payload = manifest.model_dump()
    if existing is not None:
        existing.name = manifest.name
        existing.description = manifest.description
        existing.runtime = manifest.runtime
        existing.manifest = payload
        existing.status = PLUGIN_STATUS_ACTIVE
        await db.flush()
        return existing

    row = Plugin(
        workspace_id=workspace_id,
        slug=manifest.id,
        version=manifest.version,
        name=manifest.name,
        description=manifest.description,
        runtime=manifest.runtime,
        manifest=payload,
        status=PLUGIN_STATUS_ACTIVE,
    )
    db.add(row)
    await db.flush()
    return row


async def list_plugins(db: AsyncSession) -> Sequence[Plugin]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(Plugin).order_by(Plugin.installed_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(Plugin.workspace_id == workspace_id)
    return (await db.execute(stmt)).scalars().all()


async def get_plugin(db: AsyncSession, plugin_id: uuid.UUID) -> Plugin | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(Plugin).where(Plugin.id == plugin_id)
    if workspace_id is not None:
        stmt = stmt.where(Plugin.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def set_status(
    db: AsyncSession, plugin: Plugin, *, enabled: bool
) -> Plugin:
    plugin.status = PLUGIN_STATUS_ACTIVE if enabled else PLUGIN_STATUS_DISABLED
    await db.flush()
    return plugin


async def uninstall_plugin(db: AsyncSession, plugin: Plugin) -> None:
    await db.delete(plugin)
    await db.flush()
