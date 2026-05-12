"""3-legged OAuth for KB / data-source connectors.

Distinct from ``app.modules.identity.auth.oauth_router`` (login flow). This module:
  - holds the per-provider OAuth configuration
  - mints state tokens, persists them
  - completes the code → token exchange
  - stores the result encrypted in ``oauth_connections``
  - serves a get-token helper that auto-refreshes when needed.

Connectors consume tokens via ``service.get_access_token(connection_id)``
— they never touch the raw provider client config or stored secrets.
"""
