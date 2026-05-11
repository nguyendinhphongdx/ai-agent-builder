"""KB connector registry.

Adding a connector:
  1. Subclass :class:`KBConnector` (see ``base.py``).
  2. Register it here keyed on ``connector_type``.
  3. Document required ``config`` + ``credentials`` shapes in the
     subclass docstring — admins see those at create time.

The registry stays a plain dict so wiring is obvious. Lazy imports
keep optional native dependencies (boto3, gdrive SDKs, …) out of
the main-app import path.
"""
from __future__ import annotations

from app.knowledge.connectors.base import (
    ConnectorResource,
    KBConnector,
    KBConnectorRunResult,
)
from app.knowledge.connectors.providers.local_fs import LocalFilesystemConnector


def build_connector(connector_type: str) -> KBConnector | None:
    """Resolve a connector_type string to a provider instance."""
    provider = (connector_type or "").lower().strip()
    if provider == "local_fs":
        return LocalFilesystemConnector()
    # S3 / GCS / GDrive / Notion implementations land in follow-ups —
    # adding them is a registry entry + provider module.
    return None


__all__ = [
    "KBConnector",
    "ConnectorResource",
    "KBConnectorRunResult",
    "build_connector",
]
