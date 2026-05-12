"""Notion KB connector.

Auth: integration token (``Internal Integration`` secret from
the Notion settings page). The admin pastes it into an
``ai_credential`` row; we Fernet-decrypt at fetch time and send
``Authorization: Bearer <token>``.

Discovery shape:
  config.database_id       optional — index a specific database's
                           rows as pages
  config.search_query      optional — pull pages matching a search
                           query (Notion search returns everything
                           the integration has access to)
  config.include_databases default true — when no database_id /
                           search_query, list every page the
                           integration can see via the /search
                           endpoint.

Incremental sync: keyed on Notion's ``last_edited_time``. The
search/database-query endpoint returns pages sorted descending by
edit time, so we can stop reading once we hit a page older than
the cursor watermark.

Content: each page's full block tree is fetched and flattened to
markdown-ish text. Block-by-block rendering keeps the parser
simple (no recursive Notion API client dependency).

Rate limits: Notion publishes "3 requests per second average".
The connector serialises requests; a workspace with thousands of
pages will finish over multiple ticks, paged via the cursor.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, AsyncIterator

import httpx

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_NOTION_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_TIMEOUT = 15.0
_LIST_BUDGET = 100


def _client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_NOTION_BASE,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        },
        timeout=_TIMEOUT,
    )


def _page_title(page: dict[str, Any]) -> str:
    """Notion's title is one of the properties (often "Name" or
    "Title" depending on the template). Walk properties; pick the
    first one of type ``title``."""
    props = page.get("properties") or {}
    for prop in props.values():
        if prop.get("type") == "title":
            spans = prop.get("title") or []
            return "".join(span.get("plain_text", "") for span in spans)
    return "(untitled)"


def _rich_text(spans: list[dict[str, Any]]) -> str:
    return "".join(s.get("plain_text", "") for s in spans or [])


def _render_block(block: dict[str, Any]) -> str:
    """Flatten one block to markdown-ish text.

    Notion's block schema is enormous; we cover the common types
    (paragraph, heading, list items, code, quote, todo, callout).
    Unknown types render as their type name in [brackets] so the
    output is never empty — useful for unsupported blocks like
    embeds and synced blocks.
    """
    btype = block.get("type") or ""
    data = block.get(btype) or {}
    text = _rich_text(data.get("rich_text") or [])

    if btype == "paragraph":
        return text
    if btype == "heading_1":
        return f"# {text}"
    if btype == "heading_2":
        return f"## {text}"
    if btype == "heading_3":
        return f"### {text}"
    if btype == "bulleted_list_item":
        return f"- {text}"
    if btype == "numbered_list_item":
        return f"1. {text}"
    if btype == "to_do":
        mark = "x" if data.get("checked") else " "
        return f"- [{mark}] {text}"
    if btype == "quote":
        return f"> {text}"
    if btype == "callout":
        return f"> {text}"
    if btype == "code":
        lang = data.get("language") or ""
        return f"```{lang}\n{text}\n```"
    if btype == "divider":
        return "---"
    return f"[{btype}]"


async def _walk_blocks(
    client: httpx.AsyncClient, block_id: str, depth: int = 0
) -> list[str]:
    """Recursively flatten a Notion page's block tree.

    ``depth`` caps recursion at 5 — Notion allows arbitrary nesting
    but block-tree spelunking past five levels is rare and the
    extra depth blows the time budget on big pages.
    """
    if depth > 5:
        return []
    out: list[str] = []
    start_cursor: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        resp = await client.get(f"/blocks/{block_id}/children", params=params)
        if resp.status_code != 200:
            logger.warning(
                "notion: blocks fetch failed for %s: %s", block_id, resp.status_code
            )
            return out
        data = resp.json()
        for block in data.get("results", []) or []:
            line = _render_block(block)
            if line:
                out.append("  " * depth + line)
            if block.get("has_children"):
                out.extend(await _walk_blocks(client, block["id"], depth + 1))
        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
    return out


class NotionConnector(KBConnector):
    name = "notion"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        token = (credentials or {}).get("integration_token", "").strip()
        if not token:
            logger.warning(
                "notion connector: missing credential integration_token"
            )
            return

        last_iso = cursor.get("last_edited_iso")
        last_edited = (
            datetime.fromisoformat(last_iso) if last_iso else None
        )

        database_id = (config.get("database_id") or "").strip()
        search_query = config.get("search_query")
        seen = 0

        async with _client(token) as client:
            if database_id:
                iterator = self._iter_database(client, database_id)
            else:
                iterator = self._iter_search(client, query=search_query)

            async for page in iterator:
                last_edited_str = page.get("last_edited_time")
                page_edited = None
                if isinstance(last_edited_str, str):
                    try:
                        page_edited = datetime.fromisoformat(
                            last_edited_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        page_edited = None

                # Sorted desc by last_edited_time — once we hit an
                # older page, every remaining one is older too.
                if (
                    last_edited is not None
                    and page_edited is not None
                    and page_edited <= last_edited
                ):
                    return

                page_id = page.get("id")
                if not page_id:
                    continue

                yield ConnectorResource(
                    resource_id=page_id,
                    filename=f"{_page_title(page)}.md",
                    mime_type="text/markdown",
                    size=None,
                    content_hash=None,
                    modified_at=page_edited,
                    metadata={
                        "notion_url": page.get("url"),
                        "object": page.get("object"),
                        "parent": page.get("parent"),
                    },
                )
                seen += 1
                if seen >= _LIST_BUDGET:
                    return

    async def _iter_database(
        self, client: httpx.AsyncClient, database_id: str
    ) -> AsyncIterator[dict[str, Any]]:
        start_cursor: str | None = None
        while True:
            body: dict[str, Any] = {
                "page_size": 100,
                "sorts": [
                    {"timestamp": "last_edited_time", "direction": "descending"}
                ],
            }
            if start_cursor:
                body["start_cursor"] = start_cursor
            resp = await client.post(f"/databases/{database_id}/query", json=body)
            if resp.status_code != 200:
                logger.warning(
                    "notion db query failed: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return
            data = resp.json()
            for page in data.get("results", []) or []:
                yield page
            if not data.get("has_more"):
                return
            start_cursor = data.get("next_cursor")

    async def _iter_search(
        self, client: httpx.AsyncClient, *, query: str | None
    ) -> AsyncIterator[dict[str, Any]]:
        start_cursor: str | None = None
        while True:
            body: dict[str, Any] = {
                "page_size": 100,
                "sort": {
                    "timestamp": "last_edited_time",
                    "direction": "descending",
                },
                "filter": {"value": "page", "property": "object"},
            }
            if query:
                body["query"] = query
            if start_cursor:
                body["start_cursor"] = start_cursor
            resp = await client.post("/search", json=body)
            if resp.status_code != 200:
                logger.warning(
                    "notion search failed: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return
            data = resp.json()
            for page in data.get("results", []) or []:
                yield page
            if not data.get("has_more"):
                return
            start_cursor = data.get("next_cursor")

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        token = (credentials or {}).get("integration_token", "").strip()
        if not token:
            raise PermissionError("notion: integration_token missing")

        async with _client(token) as client:
            # Title from metadata if cached, else refetch the page.
            title = resource.filename.rsplit(".", 1)[0]
            lines = await _walk_blocks(client, resource.resource_id)

        body = f"# {title}\n\n" + "\n\n".join(lines)
        data = body.encode("utf-8")
        resource.size = len(data)
        resource.content_hash = hashlib.sha256(data).hexdigest()
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
        prev_iso = current_cursor.get("last_edited_iso")
        if prev_iso is None or datetime.fromisoformat(prev_iso) < mtime:
            return {**current_cursor, "last_edited_iso": mtime.isoformat()}
        return current_cursor
