"""Email-trigger CRUD + IMAP fetch loop.

Two layers:
  - CRUD functions, used by the router. Always set workspace_id
    from the request ContextVar so multi-tenancy is preserved.
  - ``poll_once(db, trigger)`` — single IMAP fetch + dispatch
    cycle for one row. Called by the poll worker and exposed for
    "trigger now" tests.
"""
from __future__ import annotations

import asyncio
import email
import logging
import uuid
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id, current_workspace_id_or_none
from app.email_triggers.schemas import EmailTriggerCreate, EmailTriggerUpdate
from app.jobs import types as job_types
from app.jobs.producer import enqueue as enqueue_job
from app.models.email_trigger import EmailTrigger
from app.models.workflow import Workflow
from app.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger("agentforge")

# IMAP fetch budget per poll. Big enough to catch a backlog after
# downtime, small enough that one slow mailbox doesn't stall the
# whole sweep. Newer messages always fetched first (UID descending
# behaviour of IMAP UID SEARCH).
_FETCH_LIMIT = 50

# IMAP connect timeout. Six seconds keeps a misbehaving server from
# tying up the worker indefinitely.
_IMAP_TIMEOUT_SECONDS = 6


# ─── CRUD ──────────────────────────────────────────────────────────


async def list_triggers(
    db: AsyncSession, workflow_id: uuid.UUID | None = None
) -> Sequence[EmailTrigger]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(EmailTrigger).order_by(EmailTrigger.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(EmailTrigger.workspace_id == workspace_id)
    if workflow_id is not None:
        stmt = stmt.where(EmailTrigger.workflow_id == workflow_id)
    return (await db.execute(stmt)).scalars().all()


async def get_trigger(
    db: AsyncSession, trigger_id: uuid.UUID
) -> EmailTrigger | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(EmailTrigger).where(EmailTrigger.id == trigger_id)
    if workspace_id is not None:
        stmt = stmt.where(EmailTrigger.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def create_trigger(
    db: AsyncSession, payload: EmailTriggerCreate
) -> EmailTrigger:
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise ValueError("no_active_workspace")

    # Verify the workflow belongs to the active workspace before
    # binding. Cross-workspace trigger creation would be a privilege
    # escalation vector.
    wf = await db.scalar(
        select(Workflow).where(
            Workflow.id == payload.workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )
    if wf is None:
        raise ValueError("workflow_not_found")

    row = EmailTrigger(
        workflow_id=payload.workflow_id,
        workspace_id=workspace_id,
        name=payload.name,
        imap_host=payload.imap_host,
        imap_port=payload.imap_port,
        imap_use_ssl=payload.imap_use_ssl,
        imap_username=payload.imap_username,
        imap_password_enc=encrypt_secret(payload.imap_password),
        imap_folder=payload.imap_folder,
        poll_interval_seconds=payload.poll_interval_seconds,
        mark_seen=payload.mark_seen,
        is_active=payload.is_active,
    )
    db.add(row)
    await db.flush()
    return row


async def update_trigger(
    db: AsyncSession, trigger: EmailTrigger, payload: EmailTriggerUpdate
) -> EmailTrigger:
    data = payload.model_dump(exclude_unset=True)
    # Password field is special — only rotate when explicitly sent.
    if "imap_password" in data:
        pw = data.pop("imap_password")
        if pw:
            trigger.imap_password_enc = encrypt_secret(pw)
    for k, v in data.items():
        setattr(trigger, k, v)
    await db.flush()
    return trigger


async def delete_trigger(db: AsyncSession, trigger: EmailTrigger) -> None:
    await db.delete(trigger)
    await db.flush()


# ─── IMAP fetch ────────────────────────────────────────────────────


def _decode_header(raw: str | None) -> str:
    """Decode an RFC 2047 encoded-word header. Returns "" on None."""
    if not raw:
        return ""
    parts = decode_header(raw)
    out: list[str] = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _message_text(msg: Message) -> str:
    """Extract the plain-text body, falling back to HTML stripped of
    tags. Naive on purpose — workflow LLM nodes can do real parsing
    if more fidelity matters."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        return ""
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(
            msg.get_content_charset() or "utf-8", errors="replace"
        )
    return str(payload or "")


def _build_message_payload(msg: Message, uid: int) -> dict:
    """Shape one IMAP message into the workflow's ``input_data`` dict.

    Matches the webhook input shape ({ body, headers, … }) so a
    workflow can switch trigger types without reshaping every node.
    """
    return {
        "uid": uid,
        "from": _decode_header(msg.get("From")),
        "to": _decode_header(msg.get("To")),
        "cc": _decode_header(msg.get("Cc")),
        "subject": _decode_header(msg.get("Subject")),
        "message_id": msg.get("Message-ID"),
        "date": msg.get("Date"),
        "body": _message_text(msg),
        # Whole RFC 822 header dump for the rare workflow that
        # needs DKIM/auth info. Keys lower-cased to match the
        # webhook trigger.
        "headers": {k.lower(): v for k, v in msg.items()},
    }


def _sync_fetch(
    *,
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
    folder: str,
    since_uid: int | None,
    limit: int,
    mark_seen: bool,
) -> list[tuple[int, Message]]:
    """Blocking IMAP fetch — call via ``asyncio.to_thread``.

    Returns a list of (uid, message) tuples newest-first. Caller is
    responsible for ordering / cursor update.
    """
    import imaplib

    cls = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
    imap = cls(host=host, port=port, timeout=_IMAP_TIMEOUT_SECONDS)
    try:
        imap.login(username, password)
        imap.select(folder, readonly=not mark_seen)
        # UID SEARCH supports "UID since:*" — fetch uids strictly
        # greater than the cursor.
        if since_uid is not None:
            typ, data = imap.uid("search", None, f"UID {since_uid + 1}:*")
        else:
            typ, data = imap.uid("search", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()
        # IMAP doesn't strictly order; sort then trim to budget.
        uids = sorted(uids, key=int)
        if len(uids) > limit:
            uids = uids[-limit:]

        results: list[tuple[int, Message]] = []
        for raw_uid in uids:
            uid = int(raw_uid)
            typ, msg_data = imap.uid("fetch", raw_uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            results.append((uid, msg))
        return results
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001 — cleanup best-effort
            pass


async def _dispatch_message(
    db: AsyncSession,
    trigger: EmailTrigger,
    uid: int,
    msg: Message,
) -> None:
    """Enqueue one workflow run for one message."""
    payload = _build_message_payload(msg, uid)
    workflow = await db.get(Workflow, trigger.workflow_id)
    if workflow is None or not workflow.is_active:
        return
    await enqueue_job(
        db,
        job_type=job_types.JOB_WORKFLOW_RUN,
        target="backend",
        path=f"{settings.API_PREFIX}/internal/workflows/run",
        payload={
            "workflow_id": str(workflow.id),
            "user_id": str(workflow.user_id),
            "input_data": {
                "trigger": "email",
                "trigger_id": str(trigger.id),
                "email": payload,
            },
        },
        workspace_id=workflow.workspace_id,
        user_id=workflow.user_id,
        priority="normal",
        retry={"maxAttempts": 3, "backoffMs": 5_000, "backoffMultiplier": 2},
        timeout_ms=300_000,
    )


async def poll_once(db: AsyncSession, trigger: EmailTrigger) -> int:
    """Fetch new messages for one trigger + enqueue runs.

    Returns the number of messages dispatched. Stamps the cursor +
    last_polled_at on success; stamps last_error on failure.
    """
    try:
        password = decrypt_secret(trigger.imap_password_enc)
    except Exception:
        # Encryption key rotated and we never re-encrypted? Surface
        # the error in the UI rather than silently failing.
        logger.exception(
            "email_trigger %s: decryption failed", trigger.id
        )
        trigger.last_error = "Failed to decrypt IMAP password"
        trigger.last_error_at = datetime.now(timezone.utc)
        await db.flush()
        return 0

    try:
        messages = await asyncio.to_thread(
            _sync_fetch,
            host=trigger.imap_host,
            port=trigger.imap_port,
            use_ssl=trigger.imap_use_ssl,
            username=trigger.imap_username,
            password=password,
            folder=trigger.imap_folder,
            since_uid=trigger.last_seen_uid,
            limit=_FETCH_LIMIT,
            mark_seen=trigger.mark_seen,
        )
    except Exception as exc:  # noqa: BLE001 — IMAP libs raise broadly
        logger.warning(
            "email_trigger %s: fetch failed: %s", trigger.id, exc
        )
        trigger.last_error = str(exc)[:500]
        trigger.last_error_at = datetime.now(timezone.utc)
        trigger.last_polled_at = datetime.now(timezone.utc)
        await db.flush()
        return 0

    dispatched = 0
    if trigger.last_seen_uid is None and messages:
        # First poll — establish cursor at the latest UID and skip
        # backlog. Without this a freshly-bound mailbox would
        # replay every existing message.
        trigger.last_seen_uid = max(uid for uid, _ in messages)
    else:
        for uid, msg in messages:
            await _dispatch_message(db, trigger, uid, msg)
            dispatched += 1
            if uid > (trigger.last_seen_uid or 0):
                trigger.last_seen_uid = uid

    trigger.last_polled_at = datetime.now(timezone.utc)
    trigger.last_error = None
    trigger.last_error_at = None
    await db.flush()
    return dispatched
