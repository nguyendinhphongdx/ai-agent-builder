"""Email delivery for auth flows.

All email goes through the dispatcher → mail service (template: `general`).
Backend composes the `content` HTML and hands off to the mail service which
wraps it with AgentForge-branded header/footer.

Sends are fire-and-forget: failures are logged but never raised into the
caller. Losing a verification email is annoying; crashing the request is worse.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.dispatcher_client import dispatcher

logger = logging.getLogger("agentforge")


# ─── Content builders ────────────────────────────────────────────────────

def _verify_content(code: str, full_name: str | None) -> dict[str, str]:
    greeting = f"Hi {full_name}," if full_name else "Hi there,"
    code_block = (
        "<p style=\"margin:24px 0;font-family:ui-monospace,SFMono-Regular,monospace;"
        "font-size:38px;letter-spacing:0.35em;font-weight:700;text-align:center;"
        "color:#111827;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;"
        f"padding:18px 24px;\">{code}</p>"
    )
    content = (
        f"<p>{greeting}</p>"
        "<p>Enter this verification code on the page waiting for you:</p>"
        f"{code_block}"
        "<p style=\"font-size:13px;color:#64748b;\">The code expires in 15 minutes. "
        "If you didn't try to sign up, you can safely ignore this email.</p>"
    )
    return {
        "title": "Your AgentForge verification code",
        "previewText": "Your AgentForge verification code",
        "greeting": "Welcome to AgentForge",
        "content": content,
    }


def _reset_content(reset_url: str, full_name: str | None) -> dict[str, str]:
    greeting = f"Hi {full_name}," if full_name else "Hi there,"
    content = (
        f"<p>{greeting}</p>"
        "<p>Someone — hopefully you — asked to reset your password. "
        "Click the button below to choose a new one.</p>"
        "<p style=\"font-size:13px;color:#64748b;margin-top:24px;\">"
        "Or copy this link into your browser:<br>"
        f"<a href=\"{reset_url}\" style=\"color:#6366f1;word-break:break-all;\">"
        f"{reset_url}</a></p>"
        "<p style=\"font-size:13px;color:#64748b;\">"
        "The link expires in 30 minutes. If you didn't request this, nothing will change.</p>"
    )
    return {
        "title": "Reset your AgentForge password",
        "previewText": "Reset your AgentForge password",
        "greeting": "Reset your password",
        "content": content,
        "buttonText": "Choose a new password",
        "buttonUrl": reset_url,
    }


# ─── Public API ──────────────────────────────────────────────────────────

def send_verification_email(to: str, full_name: str | None, code: str) -> None:
    """Fire-and-forget: dispatch a verification-code email."""
    dispatcher.sync_bg(
        "mail",
        "/mail/send",
        body={
            "to": to,
            "subject": "Your AgentForge verification code",
            "template": "general",
            "data": _verify_content(code, full_name),
        },
    )


def send_password_reset_email(to: str, full_name: str | None, token: str) -> None:
    """Fire-and-forget: dispatch a password-reset email."""
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    dispatcher.sync_bg(
        "mail",
        "/mail/send",
        body={
            "to": to,
            "subject": "Reset your AgentForge password",
            "template": "general",
            "data": _reset_content(reset_url, full_name),
        },
    )
