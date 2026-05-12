"""Local filesystem connector — useful in dev + as the template for
cloud-storage providers (S3 / GCS / Azure Blob, all of which follow
the same list+fetch shape).

Config:
  ``root``      absolute path on the backend filesystem to scan.
  ``include``   optional list of glob patterns to match (default:
                everything not starting with '.').
  ``recursive`` bool (default True). False = top-level only.

Credentials: none. The backend process must already have read
access to ``root``.

Security: the orchestrator should restrict ``root`` to a configured
allowlist (per-org sandbox root) before creating a connector pointing
at it — otherwise a workspace admin could read any file the backend
user can. Out of scope for v1 (this connector is dev-only).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, AsyncIterator

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")


class LocalFilesystemConnector(KBConnector):
    name = "local_fs"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        root_str = (config.get("root") or "").strip()
        if not root_str:
            return
        root = Path(root_str).resolve()
        if not root.exists() or not root.is_dir():
            logger.warning("local_fs: root %s does not exist or is not a dir", root)
            return

        patterns: list[str] = config.get("include") or []
        recursive: bool = bool(config.get("recursive", True))
        # Delta sync uses ``cursor['last_modified_iso']`` if present —
        # only yield files modified strictly after that timestamp.
        last_mod_str = cursor.get("last_modified_iso")
        last_mod = (
            datetime.fromisoformat(last_mod_str)
            if last_mod_str
            else None
        )

        # os.walk is sync — wrap in to_thread so we don't block the
        # event loop on huge trees. For small dev directories this is
        # overkill but the cost is microseconds.
        def _walk() -> list[tuple[Path, os.stat_result]]:
            seen: list[tuple[Path, os.stat_result]] = []
            if not recursive:
                for entry in root.iterdir():
                    if entry.is_file():
                        seen.append((entry, entry.stat()))
                return seen
            for dirpath, _, files in os.walk(root):
                for name in files:
                    p = Path(dirpath) / name
                    try:
                        seen.append((p, p.stat()))
                    except OSError:
                        # File vanished mid-walk; skip.
                        continue
            return seen

        entries = await asyncio.to_thread(_walk)
        for path, st in entries:
            rel = path.relative_to(root).as_posix()
            if rel.startswith("."):
                continue
            if patterns and not any(fnmatch(rel, p) for p in patterns):
                continue
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            if last_mod is not None and mtime <= last_mod:
                continue
            yield ConnectorResource(
                resource_id=str(path),
                filename=path.name,
                mime_type=None,  # parser sniffs from filename + bytes
                size=st.st_size,
                content_hash=None,  # filled after fetch
                modified_at=mtime,
                metadata={"relative_path": rel},
            )

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        path = Path(resource.resource_id)
        # Sanity check — the path must still live under the configured
        # root. Defends against in-memory path tampering between list
        # and fetch (concurrent sync runs).
        root = Path((config.get("root") or "").strip()).resolve()
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise PermissionError(
                f"refusing to read {path}: escapes configured root"
            ) from exc

        def _read() -> bytes:
            return path.read_bytes()

        data = await asyncio.to_thread(_read)
        # Patch the content_hash now that we have the bytes — lets the
        # orchestrator dedupe across runs even when the FS doesn't
        # expose one natively.
        resource.content_hash = hashlib.sha256(data).hexdigest()
        return data

    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        # Stamp the high-water-mark mtime. ``list_resources`` walks in
        # whatever order ``os.walk`` returns (not strictly monotonic),
        # so we take max over what we've seen.
        mtime = resource.modified_at
        if mtime is None:
            return current_cursor
        prev_iso = current_cursor.get("last_modified_iso")
        if prev_iso is None or datetime.fromisoformat(prev_iso) < mtime:
            return {**current_cursor, "last_modified_iso": mtime.isoformat()}
        return current_cursor
