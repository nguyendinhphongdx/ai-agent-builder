"""Email-in trigger configuration.

One row binds a workflow to one IMAP mailbox. The polling worker
walks every active row at its configured cadence, fetches new
messages by UID, and enqueues a workflow run per message.

Decision: do NOT store message bodies here. The trigger is
stateless past the cursor — each message becomes a workflow run
whose ``input_data`` carries the email payload. Replays / audits
live in workflow_runs alongside every other run.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class EmailTrigger(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "email_triggers"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    imap_use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    imap_username: Mapped[str] = mapped_column(String(255), nullable=False)
    # Fernet-encrypted IMAP password. Accessor helpers in the
    # service decrypt on the fly; never returned to the FE.
    imap_password_enc: Mapped[str] = mapped_column(Text, nullable=False)
    imap_folder: Mapped[str] = mapped_column(String(255), nullable=False, default="INBOX")
    poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300
    )
    mark_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_uid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workflow: Mapped["Workflow"] = relationship()
