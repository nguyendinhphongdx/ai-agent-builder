"""Unified trigger row — every flavour of "what makes a workflow fire"
in one polymorphic table.

The five legacy tables (slack_triggers, teams_triggers, discord_triggers,
email_triggers, scheduled_triggers) all had the same skeleton — workflow
+ workspace + name + is_active + a fistful of provider-specific
columns — so we collapse them into one row shape:

  type                    discriminator: 'slack' | 'teams' | 'discord'
                          | 'email' | 'scheduled'
  config (JSONB)          provider-specific user config (channel filter,
                          IMAP host, cron expression, …)
  credentials_encrypted   Fernet-encrypted secret blob, when the provider
                          needs one (email password, Teams HMAC secret)
  last_fired_at           operational state — when the trigger last
                          dispatched a workflow run
  last_error              free-text error from the most recent attempt
  next_run_at             populated for PollingTrigger.tick() planning
                          (scheduled). NULL for webhook-only types.
  last_polled_at          populated for poll-based types (email).
  poll_cursor (JSONB)     opaque provider cursor (email last_seen_uid,
                          future polling sources). NULL/{} for webhooks.

This matches the `kb_connectors` shape — one polymorphic row + a
provider-specific handler registered in
``app.modules.runtime.triggers._registry``. Adding a 6th trigger type
(WhatsApp, SMS, …) means writing a Pydantic config schema + a
TriggerHandler subclass — zero schema migrations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, TimestampMixin, UUIDMixin

# Discriminator values. Source of truth — the per-type Pydantic
# schemas in ``modules.runtime.triggers.schemas`` reference these.
TRIGGER_TYPE_SLACK = "slack"
TRIGGER_TYPE_TEAMS = "teams"
TRIGGER_TYPE_DISCORD = "discord"
TRIGGER_TYPE_EMAIL = "email"
TRIGGER_TYPE_SCHEDULED = "scheduled"


class Trigger(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "triggers"

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Fernet-encrypted secret blob. NULL when the provider has no
    # per-trigger secret (Slack uses a deployment-wide signing
    # secret; Discord stores its public key in config).
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    # ─── Operational state ───────────────────────────────────────
    last_fired_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Polling-type fields (NULL for webhook-only types) ───────
    next_run_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    poll_cursor: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        # Hot path: list triggers in a workspace, filtered by type.
        Index("ix_triggers_workspace_type", "workspace_id", "type"),
        # Hot path: list a workflow's triggers (Settings page).
        Index("ix_triggers_workflow", "workflow_id"),
        # Polling scheduler does ``WHERE next_run_at <= now()``.
        # Partial keeps the index tiny — webhook triggers don't
        # populate next_run_at and shouldn't bloat scans.
        Index(
            "ix_triggers_next_run",
            "next_run_at",
            postgresql_where=text("next_run_at IS NOT NULL"),
        ),
        # Slack event dispatch hot path. Expression index over
        # config so we don't unnest at query time.
        Index(
            "ix_triggers_slack_dispatch",
            text("(config->>'slack_team_id')"),
            text("(config->>'filter_event_type')"),
            postgresql_where=text("type = 'slack' AND is_active"),
        ),
        # Discord dispatch hot path.
        Index(
            "ix_triggers_discord_app",
            text("(config->>'discord_application_id')"),
            postgresql_where=text("type = 'discord' AND is_active"),
        ),
        # Preserve the (workflow_id, node_id) uniqueness scheduled_triggers
        # had — the workflow-save sync UPSERTs on this pair.
        Index(
            "uq_triggers_scheduled_node",
            "workflow_id",
            text("(config->>'node_id')"),
            unique=True,
            postgresql_where=text("type = 'scheduled'"),
        ),
    )


__all__ = [
    "Trigger",
    "TRIGGER_TYPE_SLACK",
    "TRIGGER_TYPE_TEAMS",
    "TRIGGER_TYPE_DISCORD",
    "TRIGGER_TYPE_EMAIL",
    "TRIGGER_TYPE_SCHEDULED",
]
