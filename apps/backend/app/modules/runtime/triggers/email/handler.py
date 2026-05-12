"""Email handler — :class:`PollingTrigger` implementation.

Wraps the IMAP fetch + parse + dispatch loop that previously lived
in ``email/service.py``. The poll cursor (``last_seen_uid``) lives
under ``Trigger.poll_cursor`` instead of a dedicated column.
"""
from __future__ import annotations

import asyncio
import email as email_lib
import json
import logging
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import TRIGGER_TYPE_EMAIL, Trigger
from app.modules.runtime.triggers._base import PollingTrigger
from app.modules.runtime.triggers._dispatch import enqueue_workflow_run
from app.modules.runtime.triggers.schemas import EmailConfig, EmailCredentials
from app.platform.security.crypto import decrypt_secret

logger = logging.getLogger("agentforge")

# IMAP fetch budget per poll — big enough to catch backlog after
# downtime, small enough that one slow mailbox doesn't stall the
# whole sweep.
_FETCH_LIMIT = 50
_IMAP_TIMEOUT_SECONDS = 6


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    out: list[str] = []
    for chunk, charset in decode_header(raw):
        if isinstance(chunk, bytes):
            out.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _message_text(msg: Message) -> str:
    """Extract a best-effort plain-text body. Naive on purpose —
    LLM nodes can do real parsing if more fidelity matters."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        return ""
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return str(payload or "")


def _build_message_payload(msg: Message, uid: int) -> dict:
    return {
        "uid": uid,
        "from": _decode_header(msg.get("From")),
        "to": _decode_header(msg.get("To")),
        "cc": _decode_header(msg.get("Cc")),
        "subject": _decode_header(msg.get("Subject")),
        "message_id": msg.get("Message-ID"),
        "date": msg.get("Date"),
        "body": _message_text(msg),
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
    """Blocking IMAP fetch — call via ``asyncio.to_thread``."""
    import imaplib

    cls = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
    imap = cls(host=host, port=port, timeout=_IMAP_TIMEOUT_SECONDS)
    try:
        imap.login(username, password)
        imap.select(folder, readonly=not mark_seen)
        if since_uid is not None:
            typ, data = imap.uid("search", None, f"UID {since_uid + 1}:*")
        else:
            typ, data = imap.uid("search", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return []
        uids = sorted(data[0].split(), key=int)
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
            msg = email_lib.message_from_bytes(raw)
            results.append((uid, msg))
        return results
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


class EmailHandler(PollingTrigger):
    type = TRIGGER_TYPE_EMAIL
    label = "Email (IMAP)"
    config_schema = EmailConfig
    credentials_schema = EmailCredentials

    async def tick(self, db: AsyncSession, trigger: Trigger) -> int:
        """One IMAP poll pass for one trigger row. Stamps the cursor,
        last_polled_at + last_error before returning."""
        cfg = trigger.config or {}
        cursor = trigger.poll_cursor or {}
        last_seen_uid = cursor.get("last_seen_uid")

        try:
            blob = decrypt_secret(trigger.credentials_encrypted) if trigger.credentials_encrypted else None
            password = (
                json.loads(blob).get("imap_password")
                if blob and blob.startswith("{")
                else blob
            )
        except Exception:
            logger.exception("email trigger %s: decryption failed", trigger.id)
            trigger.last_error = "Failed to decrypt IMAP password"
            trigger.last_polled_at = datetime.now(timezone.utc)
            await db.flush()
            return 0

        try:
            messages = await asyncio.to_thread(
                _sync_fetch,
                host=cfg["imap_host"],
                port=cfg.get("imap_port", 993),
                use_ssl=cfg.get("imap_use_ssl", True),
                username=cfg["imap_username"],
                password=password,
                folder=cfg.get("imap_folder", "INBOX"),
                since_uid=last_seen_uid,
                limit=_FETCH_LIMIT,
                mark_seen=cfg.get("mark_seen", True),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("email trigger %s: fetch failed: %s", trigger.id, exc)
            trigger.last_error = str(exc)[:500]
            trigger.last_polled_at = datetime.now(timezone.utc)
            await db.flush()
            return 0

        dispatched = 0
        new_cursor = dict(cursor)
        if last_seen_uid is None and messages:
            # First poll — anchor cursor at latest UID, skip backlog.
            new_cursor["last_seen_uid"] = max(uid for uid, _ in messages)
        else:
            for uid, msg in messages:
                payload = _build_message_payload(msg, uid)
                ok = await enqueue_workflow_run(
                    db, trigger, source_payload=payload
                )
                if ok:
                    dispatched += 1
                if uid > (new_cursor.get("last_seen_uid") or 0):
                    new_cursor["last_seen_uid"] = uid

        trigger.poll_cursor = new_cursor
        trigger.last_polled_at = datetime.now(timezone.utc)
        if dispatched > 0:
            trigger.last_fired_at = trigger.last_polled_at
        trigger.last_error = None
        await db.flush()
        return dispatched


__all__ = ["EmailHandler"]
