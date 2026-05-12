"""Atlassian Confluence KB connector.

Auth: API token + email pair (Basic auth: ``email:api_token``).
Most teams already mint these for CI; full 3-legged OAuth lands
when the public marketplace UI ships.

Config:
  base_url           https://your-org.atlassian.net (no trailing /)
  space_key          optional — restrict to one space
                     (CQL "space = SPACEKEY")
  cql                optional — power-user override; when set,
                     ignored: space_key + the default page filter
  include_blogposts  default false — pages only

Credentials (per-KB ai_credential row, Fernet-decrypted):
  email              the Atlassian account email
  api_token          token minted at id.atlassian.com/manage/api-tokens

Incremental sync: Confluence's CQL ``lastModified > "iso8601"``
gives server-side filter. Combined with ``order by lastModified
desc`` we get cursor-stop semantics.

Content: ``body.storage`` is XHTML (Confluence's intermediate
format) — we use BeautifulSoup to strip tags. ``body.export_view``
is also an option but adds an extra round-trip per page.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime
from typing import Any, AsyncIterator

import httpx

from app.knowledge.connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_TIMEOUT = 15.0
_LIST_BUDGET = 100
_PAGE_SIZE = 25  # Confluence caps content/search at 25 per page


def _auth_header(email: str, api_token: str) -> str:
    basic = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return f"Basic {basic}"


def _client(base_url: str, email: str, api_token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        headers={
            "Authorization": _auth_header(email, api_token),
            "Accept": "application/json",
        },
        timeout=_TIMEOUT,
    )


def _build_cql(
    *,
    space_key: str | None,
    include_blogposts: bool,
    last_modified: datetime | None,
    custom: str | None,
) -> str:
    if custom:
        return custom
    parts: list[str] = []
    if include_blogposts:
        parts.append('(type = "page" OR type = "blogpost")')
    else:
        parts.append('type = "page"')
    if space_key:
        parts.append(f'space = "{space_key}"')
    if last_modified is not None:
        iso = last_modified.strftime("%Y-%m-%d %H:%M")
        parts.append(f'lastModified > "{iso}"')
    return " AND ".join(parts) + " ORDER BY lastModified DESC"


def _strip_xhtml(xhtml: str) -> str:
    """Flatten Confluence storage-format XHTML to plain text-ish.

    BeautifulSoup is already in the dep tree (used by extractors).
    Confluence macros (``<ac:structured-macro/>``) render as their
    macro name in brackets so empty placeholders don't blank-out
    the page.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # Fallback — minimal regex strip. Worse output but
        # connector still works.
        import re

        return re.sub(r"<[^>]+>", " ", xhtml).strip()

    soup = BeautifulSoup(xhtml, "html.parser")
    # Replace macros with a brief marker before tag-strip.
    for macro in soup.select("[ac\\:name]"):
        macro.replace_with(f"[{macro.get('ac:name', 'macro')}]")
    return soup.get_text("\n", strip=True)


class ConfluenceConnector(KBConnector):
    name = "confluence"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        base_url = (config.get("base_url") or "").strip()
        if not base_url:
            logger.warning("confluence: missing config.base_url")
            return
        creds = credentials or {}
        email = (creds.get("email") or "").strip()
        api_token = (creds.get("api_token") or "").strip()
        if not (email and api_token):
            logger.warning("confluence: missing email + api_token credentials")
            return

        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None

        cql = _build_cql(
            space_key=(config.get("space_key") or "").strip() or None,
            include_blogposts=bool(config.get("include_blogposts")),
            last_modified=last_mod,
            custom=config.get("cql"),
        )

        seen = 0
        start = 0
        async with _client(base_url, email, api_token) as client:
            while seen < _LIST_BUDGET:
                resp = await client.get(
                    "/wiki/rest/api/content/search",
                    params={
                        "cql": cql,
                        "start": start,
                        "limit": _PAGE_SIZE,
                        "expand": "version",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(
                        "confluence search failed: %s %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return
                data = resp.json()
                results = data.get("results", []) or []
                if not results:
                    return

                for page in results:
                    when_str = (page.get("version") or {}).get("when")
                    when = None
                    if isinstance(when_str, str):
                        try:
                            when = datetime.fromisoformat(
                                when_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            when = None
                    yield ConnectorResource(
                        resource_id=page["id"],
                        filename=(page.get("title") or page["id"]) + ".html",
                        mime_type="text/html",
                        size=None,
                        content_hash=None,
                        modified_at=when,
                        metadata={
                            "space_key": (page.get("space") or {}).get("key"),
                            "url": (page.get("_links") or {}).get("webui"),
                            "type": page.get("type"),
                        },
                    )
                    seen += 1
                    if seen >= _LIST_BUDGET:
                        return

                if data.get("size", 0) < _PAGE_SIZE:
                    return
                start += _PAGE_SIZE

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        base_url = (config.get("base_url") or "").strip()
        creds = credentials or {}
        email = (creds.get("email") or "").strip()
        api_token = (creds.get("api_token") or "").strip()

        async with _client(base_url, email, api_token) as client:
            resp = await client.get(
                f"/wiki/rest/api/content/{resource.resource_id}",
                params={"expand": "body.storage,version,space"},
            )
            resp.raise_for_status()
            page = resp.json()

        title = page.get("title") or resource.resource_id
        xhtml = ((page.get("body") or {}).get("storage") or {}).get("value", "")
        text = _strip_xhtml(xhtml)

        body = f"# {title}\n\n{text}"
        data = body.encode("utf-8")
        resource.size = len(data)
        resource.content_hash = hashlib.sha256(data).hexdigest()
        # Promote the rendered shape so the downstream parser
        # uses the markdown extractor instead of HTML parser.
        resource.mime_type = "text/markdown"
        resource.filename = (title or resource.resource_id) + ".md"
        return data

    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        mtime = resource.modified_at
        if mtime is None:
            return current_cursor
        prev_iso = current_cursor.get("last_modified_iso")
        if prev_iso is None or datetime.fromisoformat(prev_iso) < mtime:
            return {**current_cursor, "last_modified_iso": mtime.isoformat()}
        return current_cursor
