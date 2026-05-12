"""Unified trigger CRUD service.

One module replaces five legacy services (slack/teams/discord/email/
scheduled service.py files) — each had identical workspace-scoped
list/get/create/update/delete shapes wrapped around a different
model. The handler registry now picks the per-type config validator
and credential serialiser, so CRUD is generic.

Type-specific dispatch + signature verification still lives on each
handler — those need the request envelope which the per-type event
receiver routers feed in.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Sequence

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import Trigger
from app.models.workflow import Workflow
from app.modules.runtime.triggers._registry import (
    UnknownTriggerType,
    get_handler,
)
from app.platform.context import current_user_id, current_workspace_id_or_none
from app.platform.security.crypto import encrypt_secret

logger = logging.getLogger("agentforge")


class TriggerValidationError(ValueError):
    """User-input shape didn't match the handler's config / credentials
    schema. Router converts to 422."""


# ─── Reads ─────────────────────────────────────────────────────────


async def list_triggers(
    db: AsyncSession,
    *,
    trigger_type: str | None = None,
    workflow_id: uuid.UUID | None = None,
) -> Sequence[Trigger]:
    """List triggers in the current workspace. Optional type +
    workflow filters."""
    workspace_id = current_workspace_id_or_none()
    stmt = select(Trigger).order_by(Trigger.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(Trigger.workspace_id == workspace_id)
    if trigger_type is not None:
        stmt = stmt.where(Trigger.type == trigger_type)
    if workflow_id is not None:
        stmt = stmt.where(Trigger.workflow_id == workflow_id)
    return (await db.execute(stmt)).scalars().all()


async def get_trigger(
    db: AsyncSession, trigger_id: uuid.UUID
) -> Trigger | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(Trigger).where(Trigger.id == trigger_id)
    if workspace_id is not None:
        stmt = stmt.where(Trigger.workspace_id == workspace_id)
    return await db.scalar(stmt)


# ─── Writes ────────────────────────────────────────────────────────


def _validate_and_serialise(
    trigger_type: str,
    *,
    config: dict[str, Any],
    credentials: dict[str, Any] | None,
) -> tuple[dict[str, Any], str | None]:
    """Run handler's Pydantic validators + serialise credentials to a
    Fernet-encrypt-ready blob.

    Returns ``(validated_config_dict, encrypted_secret_or_None)``.
    """
    handler = get_handler(trigger_type)
    try:
        cfg_model = handler.config_schema.model_validate(config or {})
    except ValidationError as exc:
        raise TriggerValidationError(f"invalid config: {exc}") from exc

    cred_blob: str | None = None
    if handler.credentials_schema is not None:
        if credentials is None:
            raise TriggerValidationError(
                f"{handler.label} requires credentials"
            )
        try:
            cred_model = handler.credentials_schema.model_validate(credentials)
        except ValidationError as exc:
            raise TriggerValidationError(f"invalid credentials: {exc}") from exc
        blob = handler.secret_to_blob(cred_model)
        cred_blob = encrypt_secret(blob) if blob else None
    return cfg_model.model_dump(mode="json"), cred_blob


async def _resolve_workflow(
    db: AsyncSession, *, workspace_id: uuid.UUID, workflow_id: uuid.UUID
) -> Workflow:
    wf = await db.scalar(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )
    if wf is None:
        raise TriggerValidationError("workflow_not_found")
    return wf


async def create_trigger(
    db: AsyncSession,
    *,
    trigger_type: str,
    workflow_id: uuid.UUID,
    name: str,
    config: dict[str, Any],
    credentials: dict[str, Any] | None = None,
    is_active: bool = True,
) -> Trigger:
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise TriggerValidationError("no_active_workspace")

    # Cross-workspace binding would be privilege escalation — block.
    await _resolve_workflow(db, workspace_id=workspace_id, workflow_id=workflow_id)

    try:
        validated_config, cred_blob = _validate_and_serialise(
            trigger_type, config=config, credentials=credentials
        )
    except UnknownTriggerType as exc:
        raise TriggerValidationError(str(exc)) from exc

    row = Trigger(
        type=trigger_type,
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        name=name,
        config=validated_config,
        credentials_encrypted=cred_blob,
        is_active=is_active,
        created_by=current_user_id(),
    )
    db.add(row)
    await db.flush()
    return row


async def update_trigger(
    db: AsyncSession,
    trigger: Trigger,
    *,
    name: str | None = None,
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
    is_active: bool | None = None,
) -> Trigger:
    """Patch one trigger. Only fields explicitly supplied are touched;
    credentials default-stay unless a new dict is provided."""
    if name is not None:
        trigger.name = name
    if is_active is not None:
        trigger.is_active = is_active

    if config is not None:
        handler = get_handler(trigger.type)
        # Merge the patch onto the existing config so partial updates
        # don't drop unchanged keys.
        new_config = {**(trigger.config or {}), **config}
        try:
            cfg_model = handler.config_schema.model_validate(new_config)
        except ValidationError as exc:
            raise TriggerValidationError(f"invalid config: {exc}") from exc
        trigger.config = cfg_model.model_dump(mode="json")

    if credentials is not None:
        handler = get_handler(trigger.type)
        if handler.credentials_schema is None:
            raise TriggerValidationError(
                f"{handler.label} does not accept credentials"
            )
        try:
            cred_model = handler.credentials_schema.model_validate(credentials)
        except ValidationError as exc:
            raise TriggerValidationError(f"invalid credentials: {exc}") from exc
        blob = handler.secret_to_blob(cred_model)
        trigger.credentials_encrypted = encrypt_secret(blob) if blob else None

    await db.flush()
    return trigger


async def delete_trigger(db: AsyncSession, trigger: Trigger) -> None:
    await db.delete(trigger)
    await db.flush()


__all__ = [
    "TriggerValidationError",
    "list_triggers",
    "get_trigger",
    "create_trigger",
    "update_trigger",
    "delete_trigger",
]
