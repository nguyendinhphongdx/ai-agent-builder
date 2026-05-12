"""Per-provider OAuth configuration.

Each provider declares:
  - the authorize + token endpoints
  - default scopes
  - the env-var names where client id / secret live
  - a ``parse_token_response`` hook that picks out the
    provider-specific fields (Slack's response shape ≠ Notion's
    ≠ Dropbox's) and returns a normalised dict.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.platform.config import settings


@dataclass
class ParsedToken:
    """Normalised token-response shape used by the service layer."""

    access_token: str
    refresh_token: str | None
    expires_in: int | None
    scope: str | None
    account_label: str | None
    external_account_id: str | None
    raw: dict[str, Any]


@dataclass
class OAuthProvider:
    id: str
    label: str
    authorize_url: str
    token_url: str
    default_scope: str
    # Names of the env vars holding client id / secret. Read via
    # ``settings.<name>`` so we never hardcode secrets here.
    client_id_setting: str
    client_secret_setting: str
    # Provider-specific token response parser.
    parse: Callable[[dict[str, Any]], ParsedToken]
    # Some providers want extra fields on the authorize URL —
    # Dropbox needs ``token_access_type=offline`` for refresh
    # tokens; Slack needs ``user_scope`` or none.
    extra_authorize_params: dict[str, str] | None = None
    # Some providers expect form-urlencoded token requests with
    # client_id+client_secret as form fields (Slack); others want
    # Basic auth header (Notion, Dropbox).
    token_auth_style: str = "basic"  # "basic" | "form"

    def is_configured(self) -> bool:
        return bool(self.client_id()) and bool(self.client_secret())

    def client_id(self) -> str:
        return getattr(settings, self.client_id_setting, "") or ""

    def client_secret(self) -> str:
        return getattr(settings, self.client_secret_setting, "") or ""


# ─── Provider-specific token parsers ──────────────────────────────


def _parse_slack(data: dict[str, Any]) -> ParsedToken:
    """Slack OAuth v2 response.

    Slack always returns ``ok`` — fail fast if false. Tokens are
    long-lived unless rotation is enabled (out of scope).
    """
    if not data.get("ok"):
        raise ValueError(
            f"slack oauth failure: {data.get('error') or 'unknown'}"
        )
    team = data.get("team") or {}
    return ParsedToken(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        scope=data.get("scope"),
        account_label=team.get("name"),
        external_account_id=team.get("id"),
        raw=data,
    )


def _parse_notion(data: dict[str, Any]) -> ParsedToken:
    """Notion OAuth response — long-lived bot token."""
    return ParsedToken(
        access_token=data["access_token"],
        refresh_token=None,
        expires_in=None,
        scope=None,
        account_label=data.get("workspace_name"),
        external_account_id=data.get("workspace_id"),
        raw=data,
    )


def _parse_dropbox(data: dict[str, Any]) -> ParsedToken:
    """Dropbox OAuth — short-lived access + long-lived refresh."""
    return ParsedToken(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        scope=data.get("scope"),
        account_label=data.get("uid") or data.get("account_id"),
        external_account_id=data.get("account_id"),
        raw=data,
    )


# ─── Registry ──────────────────────────────────────────────────────


PROVIDERS: dict[str, OAuthProvider] = {
    "slack": OAuthProvider(
        id="slack",
        label="Slack",
        authorize_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        # ``files:read`` for the files connector; ``channels:read``
        # so we can resolve channel names; ``users:read`` for
        # uploader attribution.
        default_scope="files:read,channels:history,channels:read,users:read",
        client_id_setting="SLACK_CONNECTOR_CLIENT_ID",
        client_secret_setting="SLACK_CONNECTOR_CLIENT_SECRET",
        parse=_parse_slack,
        token_auth_style="form",
    ),
    "notion": OAuthProvider(
        id="notion",
        label="Notion",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        default_scope="",  # Notion doesn't use scope strings
        client_id_setting="NOTION_CONNECTOR_CLIENT_ID",
        client_secret_setting="NOTION_CONNECTOR_CLIENT_SECRET",
        parse=_parse_notion,
        token_auth_style="basic",
        # Notion requires response_type=code + owner=user to be
        # set on the authorize URL.
        extra_authorize_params={"owner": "user"},
    ),
    "dropbox": OAuthProvider(
        id="dropbox",
        label="Dropbox",
        authorize_url="https://www.dropbox.com/oauth2/authorize",
        token_url="https://api.dropboxapi.com/oauth2/token",
        default_scope="files.metadata.read files.content.read",
        client_id_setting="DROPBOX_CONNECTOR_CLIENT_ID",
        client_secret_setting="DROPBOX_CONNECTOR_CLIENT_SECRET",
        parse=_parse_dropbox,
        token_auth_style="basic",
        # ``offline`` => issue a refresh token alongside.
        extra_authorize_params={"token_access_type": "offline"},
    ),
}


def get_provider(slug: str) -> OAuthProvider | None:
    return PROVIDERS.get(slug)
