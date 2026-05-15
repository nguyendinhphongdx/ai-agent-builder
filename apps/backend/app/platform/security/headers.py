"""Response security headers middleware.

Adds the standard browser-side defense-in-depth headers to every
response — none of these prevent a 0-day, but they raise the cost of
known attack patterns (clickjacking, MIME sniffing, mixed-content,
referrer leaks, framing).

Tuned for an *API* server (this app is purely JSON/SSE — HTML is only
served at ``/api/docs`` via Swagger UI). The frontend (Next.js) sets
its own CSP at the edge; if you ever serve user-facing HTML from this
app, tighten ``Content-Security-Policy`` accordingly.

HSTS:
  Set unconditionally because browsers ignore the header when received
  over plain HTTP — so dev traffic isn't affected, and a reverse-proxy
  terminating TLS in production gets the header transparently.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Docs/redoc UI inlines scripts + styles + CDN assets. Keep its CSP
# permissive so the page actually renders; everything else gets the
# strict default. (Browsers index ``/api/openapi.json`` directly so
# the JSON endpoint doesn't need a relaxed policy.)
_DOCS_PATHS = ("/api/docs", "/api/redoc")

# Strict default — pure API responses have no need for *any* sub-resource.
_STRICT_CSP = "default-src 'none'; frame-ancestors 'none'"

# Swagger/Redoc need 'unsafe-inline' for their bootstrap script + style.
# This is acceptable because the docs route is internal/admin-only in
# production (or should be — gate /api/docs behind auth or kill it).
_DOCS_CSP = (
    "default-src 'self' https:; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "frame-ancestors 'none'"
)

# 1 year, applies to subdomains. Preload-eligible. Safe to send over
# HTTP because the spec mandates browsers ignore it then.
_HSTS = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set defense-in-depth response headers.

    Header rationale:
      * ``Strict-Transport-Security`` — force HTTPS for the lifetime of
        the cookie. 1y matches the preload-list requirement.
      * ``X-Content-Type-Options: nosniff`` — stop the browser from
        re-guessing ``Content-Type`` based on response bytes; without
        it a JSON endpoint that accidentally returns HTML can be
        weaponised as XSS on the API origin.
      * ``X-Frame-Options: DENY`` — API responses should never be
        framed. Belt-and-suspenders with the CSP ``frame-ancestors``.
      * ``Referrer-Policy: strict-origin-when-cross-origin`` — modern
        default; prevents path/query leakage to third parties.
      * ``Content-Security-Policy`` — strict for API JSON, relaxed only
        for the Swagger/Redoc HTML.
      * ``Permissions-Policy`` — deny the long tail of browser features
        the API has no reason to use.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        path = request.url.path
        csp = _DOCS_CSP if path.startswith(_DOCS_PATHS) else _STRICT_CSP

        # ``setdefault`` so a route handler that already set a stricter
        # header (e.g. a download endpoint with its own CSP) wins.
        headers = response.headers
        headers.setdefault("Strict-Transport-Security", _HSTS)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Content-Security-Policy", csp)
        headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()",
        )
        # Legacy XSS filter — modern browsers ignore it, but old IE/Edge
        # still respect it. Cheap to send.
        headers.setdefault("X-XSS-Protection", "0")
        return response


__all__ = ["SecurityHeadersMiddleware"]
