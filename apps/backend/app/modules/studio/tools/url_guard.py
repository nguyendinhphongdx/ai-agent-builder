"""SSRF guard cho user-controlled URLs (HTTP/web scrape tools).

Resolve hostname rồi reject nếu rơi vào private/loopback/link-local/multicast
hoặc cloud metadata. Dùng `getaddrinfo` thay vì `gethostbyname` để hỗ trợ IPv6.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

_BLOCKED_HOSTS = {"metadata.google.internal", "metadata.goog"}


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _is_trusted_internal_url(url: str) -> bool:
    """Whitelist for the backend's own ``BASE_URL`` — the ingestion
    extractor downloads files from the local storage endpoint
    (``{BASE_URL}/uploads/...``) which would otherwise be blocked
    because ``localhost`` resolves to a loopback address.

    Empty BASE_URL → no whitelist (production safe-default)."""
    from app.platform.config import settings

    base = (settings.BASE_URL or "").rstrip("/")
    return bool(base) and url.startswith(base + "/")


def assert_safe_url(url: str) -> str:
    """Validate URL. Raise ValueError if scheme/host is unsafe."""
    if _is_trusted_internal_url(url):
        return url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme not allowed: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")

    if host.lower() in _BLOCKED_HOSTS:
        raise ValueError(f"Hostname not allowed: {host}")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host: {host}") from exc

    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise ValueError(f"Host resolves to blocked address: {host} → {ip}")

    return url


# ─── Safe redirect-following client ─────────────────────────────────


async def safe_get(
    url: str,
    *,
    max_redirects: int = 5,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET ``url``, manually following redirects with SSRF re-validation per hop.

    Why not ``httpx.AsyncClient(follow_redirects=True)``: a 302 to a private IP
    bypasses the initial ``assert_safe_url`` check. By disabling auto-follow
    and re-validating each ``Location`` header, we keep the guarantee that
    no hop reaches an internal address.

    Returns the final ``httpx.Response`` (already-read content). Raises
    ``ValueError`` if any hop fails the URL guard, or after ``max_redirects``.
    """
    import httpx

    assert_safe_url(url)
    current = url

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, headers=headers
    ) as client:
        for _ in range(max_redirects + 1):
            response = await client.get(current)
            if not response.is_redirect:
                return response

            location = response.headers.get("location")
            if not location:
                return response  # 3xx without Location — let caller see it

            # Resolve relative redirects against the URL we just hit.
            current = urljoin(str(response.url), location)
            assert_safe_url(current)

        raise ValueError(f"Too many redirects (>{max_redirects}) for {url}")
