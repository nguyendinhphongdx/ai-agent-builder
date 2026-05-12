"""OIDC discovery + token exchange helpers.

We deliberately avoid pulling in ``authlib``'s full client machinery
here — the existing ``app.modules.identity.auth.oauth`` module already speaks HTTP/JSON
directly and that pattern keeps the surface area small. OIDC just adds
discovery (``.well-known/openid-configuration``) and a userinfo call.

When SAML lands in Block 6 it will live in a parallel ``app/sso/saml.py``.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("agentforge")


# Discovery results are static for the lifetime of an IdP config —
# cache by issuer to avoid hitting the well-known endpoint on every
# login. Keyed by issuer URL (already normalized by the caller).
_DISCOVERY_CACHE: dict[str, dict[str, Any]] = {}


class OIDCDiscoveryError(RuntimeError):
    """Raised when the IdP's well-known doc is unreachable or malformed.
    Callers translate this to a 503 with operator-friendly detail."""


async def discover(issuer: str) -> dict[str, Any]:
    """Fetch and cache the OIDC well-known document.

    Returns the parsed JSON — callers index into ``authorization_endpoint``,
    ``token_endpoint``, ``userinfo_endpoint``, ``jwks_uri`` etc.
    """
    issuer = issuer.rstrip("/")
    if issuer in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[issuer]
    url = f"{issuer}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            doc = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise OIDCDiscoveryError(
            f"OIDC discovery failed for {issuer}: {exc}"
        ) from exc
    if not isinstance(doc, dict) or "authorization_endpoint" not in doc:
        raise OIDCDiscoveryError(
            f"OIDC discovery response from {issuer} is missing required fields"
        )
    _DISCOVERY_CACHE[issuer] = doc
    return doc


async def exchange_code(
    *,
    token_endpoint: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """OAuth 2 authorization-code grant → token response.

    Standard application/x-www-form-urlencoded body, HTTP-Basic auth
    on the client credentials. Most IdPs accept either Basic or form-
    encoded client auth — we use Basic since it's the most consistently
    supported.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    if resp.status_code >= 400:
        raise OIDCDiscoveryError(
            f"OIDC token exchange failed: {resp.status_code} {resp.text[:200]}"
        )
    return resp.json()


async def fetch_userinfo(
    *, userinfo_endpoint: str, access_token: str
) -> dict[str, Any]:
    """GET the userinfo endpoint with the bearer access token.

    OIDC userinfo always returns JSON. Different IdPs put the same data
    under different claim names; the SSO config's ``attribute_mapping``
    tells us how to find email/name in this payload.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code >= 400:
        raise OIDCDiscoveryError(
            f"OIDC userinfo failed: {resp.status_code} {resp.text[:200]}"
        )
    return resp.json()


def map_claims(
    userinfo: dict[str, Any],
    attribute_mapping: dict[str, str],
) -> dict[str, Any]:
    """Apply the org's claim → field mapping.

    ``attribute_mapping`` is shaped like ``{"email": "mail", "full_name": "displayName"}``.
    Missing entries fall back to OIDC standard names (``email``, ``name``).

    Returns ``{"email": str | None, "full_name": str | None, "sub": str}``.
    Empty/None returned for fields not present in either the map or
    the userinfo payload — caller decides whether to reject.
    """
    email_claim = attribute_mapping.get("email", "email")
    name_claim = attribute_mapping.get("full_name", "name")
    sub = userinfo.get("sub", "")

    return {
        "sub": str(sub) if sub else "",
        "email": (userinfo.get(email_claim) or userinfo.get("email") or None),
        "full_name": (
            userinfo.get(name_claim)
            or userinfo.get("name")
            or userinfo.get("displayName")
            or None
        ),
        # OIDC ``email_verified`` is a standard claim — IdPs usually
        # populate it. Treat absence as ``True`` since the IdP wouldn't
        # have authenticated the user if they couldn't prove identity.
        "email_verified": bool(userinfo.get("email_verified", True)),
    }
