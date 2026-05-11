"""Connector contract.

A connector's job is "give me documents from this external source".
The orchestrator (``app.knowledge.connectors.sync``) handles the
plumbing: cursor management, document deduplication via content
hash, persisting Document rows + handing them off to the
ingestion job.

Implementations should:
  - Tolerate ``cursor={}`` as "do a full sync from the start".
  - Stamp the new cursor on the returned result so the next call
    is delta-only.
  - Stream content as bytes (not str) — the parsers downstream
    handle decoding + format detection.
  - Treat fetch failures as per-resource warnings, not whole-run
    aborts. Aggregate into ``result.errors`` so partial progress
    survives a flaky network.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator


@dataclass
class ConnectorResource:
    """One discoverable document.

    ``content_hash`` is what dedups across runs — a connector should
    surface its provider-native ETag/checksum when available, else
    a SHA-256 over the bytes after fetch.
    """

    resource_id: str
    """Provider-stable id (S3 key, GDrive file id, …)."""
    filename: str
    mime_type: str | None
    size: int | None
    content_hash: str | None
    modified_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KBConnectorRunResult:
    discovered: int = 0
    fetched: int = 0
    failed: int = 0
    new_cursor: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class KBConnector(ABC):
    """One subclass per external source. Stateless — config +
    credentials arrive at each call so the same instance can serve
    many KBs."""

    name: str

    @abstractmethod
    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        """Yield resources visible to the configured credentials.

        Implementations should respect the ``cursor`` for delta
        sync — empty cursor means full sync. Async generator so we
        don't hold every-resource-in-source in memory for huge
        buckets.
        """
        ...
        # Subclasses must be ``async def`` generators (yield) — the
        # ``...`` placeholder satisfies the abstract contract; real
        # implementations override.

    @abstractmethod
    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        """Download the bytes for one resource. Raises on failure —
        the orchestrator catches + records the error against the
        resource id."""

    @abstractmethod
    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        """Compute the cursor *after* the given resource was seen.

        Called for every resource in monotonic-order providers (S3
        by LastModified; Notion by last_edited_time). Out-of-order
        providers can no-op until ``finalize_cursor``.
        """
        ...

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        """Stamp end-of-run cursor. Default implementation just
        records the run timestamp — providers with custom resume
        tokens override."""
        return {**current_cursor, "last_run_at": last_run_at.isoformat()}
