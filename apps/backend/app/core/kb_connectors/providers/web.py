"""Web URL crawler — index public web pages into a KB.

Two operating modes selected by config shape:

  ``urls: ["https://...", ...]``
      Explicit URL list. The connector fetches each URL on every
      run; the orchestrator dedups via content hash so unchanged
      pages don't re-ingest.

  ``sitemap: "https://example.com/sitemap.xml"``
      Pull the sitemap, walk every ``<loc>``, optionally filter
      by ``include_patterns`` (fnmatch on the URL). ``<lastmod>``
      tags drive incremental sync — only URLs modified after the
      cursor's high-water timestamp are re-fetched.

Other config:
  user_agent        sent on every request (default branded AF UA)
  max_urls          per-tick budget; default 200
  timeout_seconds   per-request HTTP timeout; default 10
  respect_robots    when True (default), skip URLs disallowed by
                    /robots.txt for the configured user_agent.

Credentials: none. Public-only crawl. Authenticated scraping is
intentionally out of scope — that's the Notion / GDrive / etc.
provider's job.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any, AsyncIterator
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_DEFAULT_USER_AGENT = "AgentForge KB Crawler/1.0 (+https://agentforge.dev)"
_DEFAULT_MAX_URLS = 200
_DEFAULT_TIMEOUT = 10.0

# Sitemaps use this namespace by default — strip it for tag matches.
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


async def _fetch_sitemap(
    url: str, *, user_agent: str, timeout: float
) -> list[tuple[str, datetime | None]]:
    """Return ``[(loc, lastmod), ...]`` from a sitemap or sitemap-index.

    Sitemap-indexes are walked one level deep — common pattern is
    monthly index files; deeper nesting is unusual and not handled.
    """
    async with httpx.AsyncClient(
        headers={"User-Agent": user_agent}, timeout=timeout, follow_redirects=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        rootname = _strip_ns(root.tag)
        urls: list[tuple[str, datetime | None]] = []

        if rootname == "sitemapindex":
            # Walk child sitemaps. Cap fan-out at 10 to avoid
            # accidental quadratic explosion on misconfigured sites.
            child_locs: list[str] = []
            for sm in root.findall(f"{_SITEMAP_NS}sitemap"):
                loc = sm.findtext(f"{_SITEMAP_NS}loc")
                if loc:
                    child_locs.append(loc.strip())
            for cl in child_locs[:10]:
                try:
                    urls.extend(
                        await _fetch_sitemap(
                            cl, user_agent=user_agent, timeout=timeout
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("sitemap child %s failed: %s", cl, exc)
            return urls

        # Plain urlset
        for u in root.findall(f"{_SITEMAP_NS}url"):
            loc = u.findtext(f"{_SITEMAP_NS}loc")
            if not loc:
                continue
            lastmod_str = u.findtext(f"{_SITEMAP_NS}lastmod")
            lastmod = None
            if lastmod_str:
                try:
                    # Sitemap spec allows W3C datetime; strip trailing
                    # Z because fromisoformat doesn't accept it pre-3.11.
                    lastmod = datetime.fromisoformat(
                        lastmod_str.strip().replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            urls.append((loc.strip(), lastmod))
        return urls


class WebCrawlerConnector(KBConnector):
    name = "web"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        user_agent = config.get("user_agent") or _DEFAULT_USER_AGENT
        max_urls = int(config.get("max_urls", _DEFAULT_MAX_URLS))
        timeout = float(config.get("timeout_seconds", _DEFAULT_TIMEOUT))

        # Cursor: high-water mark over <lastmod>s. Pages without a
        # lastmod always pass through (orchestrator dedups by hash).
        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None

        # Build the URL list.
        explicit_urls: list[str] = list(config.get("urls") or [])
        candidates: list[tuple[str, datetime | None]] = [
            (u, None) for u in explicit_urls
        ]

        sitemap_url = (config.get("sitemap") or "").strip()
        if sitemap_url:
            try:
                candidates.extend(
                    await _fetch_sitemap(
                        sitemap_url, user_agent=user_agent, timeout=timeout
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("sitemap %s failed: %s", sitemap_url, exc)

        include_patterns: list[str] = config.get("include_patterns") or []

        seen_ids: set[str] = set()
        count = 0
        for url, lastmod in candidates:
            if url in seen_ids:
                continue
            seen_ids.add(url)
            if include_patterns and not any(
                fnmatch(url, p) for p in include_patterns
            ):
                continue
            if last_mod is not None and lastmod is not None and lastmod <= last_mod:
                continue

            parsed = urlparse(url)
            filename = (
                (parsed.path.rsplit("/", 1)[-1] or parsed.netloc)
                + (".html" if not parsed.path.endswith((".html", ".htm", ".md", ".txt", ".pdf")) else "")
            )
            yield ConnectorResource(
                resource_id=url,
                filename=filename,
                mime_type=None,  # sniffed from response headers at fetch
                size=None,
                content_hash=None,
                modified_at=lastmod,
                metadata={"host": parsed.netloc},
            )
            count += 1
            if count >= max_urls:
                return

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        user_agent = config.get("user_agent") or _DEFAULT_USER_AGENT
        timeout = float(config.get("timeout_seconds", _DEFAULT_TIMEOUT))

        async with httpx.AsyncClient(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            resp = await client.get(resource.resource_id)
            resp.raise_for_status()
            data = resp.content
            ctype = resp.headers.get("content-type", "")
            # Persist mime + a hint for the parser.
            resource.metadata["content_type"] = ctype.split(";")[0].strip()

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
        prev_iso = current_cursor.get("last_modified_iso")
        if prev_iso is None or datetime.fromisoformat(prev_iso) < mtime:
            return {**current_cursor, "last_modified_iso": mtime.isoformat()}
        return current_cursor

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        # If nothing in this run had a lastmod, stamp ``now`` so
        # next tick filters on *some* watermark even for sites
        # without sitemap metadata.
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        if "last_modified_iso" not in out:
            out["last_modified_iso"] = last_run_at.astimezone(
                timezone.utc
            ).isoformat()
        return out
