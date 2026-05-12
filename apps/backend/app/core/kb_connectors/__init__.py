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

from app.core.kb_connectors.base import (
    ConnectorResource,
    KBConnector,
    KBConnectorRunResult,
)
from app.core.kb_connectors.providers.local_fs import LocalFilesystemConnector


def build_connector(connector_type: str) -> KBConnector | None:
    """Resolve a connector_type string to a provider instance."""
    provider = (connector_type or "").lower().strip()
    if provider == "local_fs":
        return LocalFilesystemConnector()
    if provider == "s3":
        # Lazy import keeps boto3 out of cold-start for tenants
        # who never use S3.
        from app.core.kb_connectors.providers.s3 import S3Connector

        return S3Connector()
    if provider == "web":
        from app.core.kb_connectors.providers.web import WebCrawlerConnector

        return WebCrawlerConnector()
    if provider == "notion":
        from app.core.kb_connectors.providers.notion import NotionConnector

        return NotionConnector()
    if provider == "gcs":
        from app.core.kb_connectors.providers.gcs import GCSConnector

        return GCSConnector()
    if provider == "azure_blob":
        from app.core.kb_connectors.providers.azure_blob import (
            AzureBlobConnector,
        )

        return AzureBlobConnector()
    if provider == "gdrive":
        from app.core.kb_connectors.providers.gdrive import (
            GoogleDriveConnector,
        )

        return GoogleDriveConnector()
    if provider == "confluence":
        from app.core.kb_connectors.providers.confluence import (
            ConfluenceConnector,
        )

        return ConfluenceConnector()
    if provider == "msgraph":
        # Single connector serves SharePoint document libraries +
        # OneDrive — both expose Drive in Graph.
        from app.core.kb_connectors.providers.msgraph import (
            MSGraphConnector,
        )

        return MSGraphConnector()
    if provider == "dropbox":
        from app.core.kb_connectors.providers.dropbox import (
            DropboxConnector,
        )

        return DropboxConnector()
    if provider == "slack":
        # OAuth-backed — the access token is resolved in sync.py
        # from ``config.oauth_connection_id`` before this connector
        # runs.
        from app.core.kb_connectors.providers.slack import (
            SlackFilesConnector,
        )

        return SlackFilesConnector()
    return None


__all__ = [
    "KBConnector",
    "ConnectorResource",
    "KBConnectorRunResult",
    "build_connector",
]
