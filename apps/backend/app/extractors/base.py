"""Core types + the main ``Extractor`` facade class.

Two levels of API:

- **Class facade** :class:`Extractor` — point-and-shoot. Construct with a
  local path or a URL; call :meth:`parse_async`. Type is auto-detected from
  the suffix.

- **Functional API** :func:`extract_text` / :func:`extract_text_async` from
  ``registry.py`` — used internally, still public for callers that prefer
  functions.

Per-format plugins implement :class:`FormatExtractor`; the registry wires
extensions to the matching plugin.

Source shapes accepted by :class:`Extractor`:
    - local filesystem path (``str`` or :class:`pathlib.Path`)
    - ``http://`` / ``https://`` URL — downloaded to a temp file, parsed, then
      cleaned up. Keeps the extractor storage-agnostic: callers just ask the
      storage backend for a URL and pass it in.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse


# ─── Result + errors ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractResult:
    """What every extractor returns."""

    text: str
    #: Free-form parser metadata: ``{"pages": 12}``, ``{"sheets": ["Data"]}``…
    metadata: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.text or not self.text.strip()


class ExtractionError(Exception):
    """Raised when an extractor fails for a supported format (bad file, wrong
    encoding, password-protected, etc). Callers should surface this to users."""


class UnsupportedFormatError(Exception):
    """Raised when no extractor is registered for the given extension / MIME."""


# ─── Per-format plugin protocol ──────────────────────────────────────────

class FormatExtractor(Protocol):
    """Contract each concrete extractor satisfies structurally.

    Implementations declare their handled extensions via :attr:`extensions`
    (lowercase, no leading dot) and do the real work in :meth:`extract`.
    """

    extensions: tuple[str, ...]

    def extract(self, path: Path) -> ExtractResult: ...


# ─── Facade ──────────────────────────────────────────────────────────────

class Extractor:
    """Turn any file — local or remote — into :class:`ExtractResult`.

    Typical usage::

        # Local path
        result = Extractor("/uploads/deck.pptx").parse()

        # URL from the storage backend (S3, GCS, local HTTP mount — anything)
        url = storage.get_url(file.storage_key, access=file.access)
        result = await Extractor(url, file_type=file.file_type).parse_async()

    ``file_type`` is auto-detected from the suffix of path or URL. Pass it
    explicitly when the source has no extension (hashed keys, query strings,
    etc).
    """

    def __init__(self, source: str | Path, file_type: str | None = None) -> None:
        self.source = str(source)
        self.file_type = self._detect_type(self.source, file_type)

    # ── Factory-style helpers keep call-sites readable ─────────────

    @classmethod
    def from_url(cls, url: str, file_type: str | None = None) -> "Extractor":
        """Explicit spelling — matches the storage layer's ``get_url`` output."""
        return cls(url, file_type=file_type)

    # ── Public methods ──────────────────────────────────────────────

    @property
    def is_url(self) -> bool:
        return self.source.startswith(("http://", "https://"))

    @property
    def supported(self) -> bool:
        """True if an extractor is registered for this file type."""
        from .registry import get_extractor
        return get_extractor(self.file_type) is not None

    def parse(self) -> ExtractResult:
        """Synchronous parse. Only works for local paths — URL sources require
        :meth:`parse_async` because downloading is inherently async."""
        if self.is_url:
            raise ValueError(
                "Use parse_async() for URL sources — the sync variant "
                "cannot download files."
            )
        from .registry import extract_text
        return extract_text(self.source, self.file_type)

    async def parse_async(self) -> ExtractResult:
        """Parse the file, handling URL download transparently.

        For URL sources the file is fetched to a temp file, parsed, and the
        temp file is deleted when :class:`ExtractResult` is returned — even
        if parsing raised.
        """
        if self.is_url:
            tmp_path = await self._download_to_temp(self.source, self.file_type)
            try:
                return await asyncio.to_thread(self._extract_path, tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        return await asyncio.to_thread(self.parse)

    # ── Internals ───────────────────────────────────────────────────

    def _extract_path(self, path: str | Path) -> ExtractResult:
        from .registry import extract_text
        return extract_text(path, self.file_type)

    @staticmethod
    def _detect_type(source: str, explicit: str | None) -> str:
        if explicit:
            return explicit.lower().lstrip(".")
        # Strip query string / fragment before reading suffix
        parsed = urlparse(source) if source.startswith(("http://", "https://")) else None
        name = parsed.path if parsed else source
        return Path(name).suffix.lower().lstrip(".")

    @staticmethod
    async def _download_to_temp(url: str, file_type: str) -> str:
        """Fetch ``url`` and write the bytes to a NamedTemporaryFile. Returns
        the temp file path. Caller is responsible for unlinking.

        Uses ``safe_get`` so each redirect hop is re-validated against the
        SSRF blocklist — important when the URL ultimately came from
        user-supplied storage config.
        """
        from app.tools.url_guard import safe_get

        suffix = f".{file_type}" if file_type else ""
        try:
            resp = await safe_get(url, timeout=30)
            resp.raise_for_status()
            data = resp.content
        except Exception as e:
            raise ExtractionError(f"Failed to download {url}: {e}") from e

        # delete=False so we can close the handle and still read it on Windows
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            return tmp.name

    def __repr__(self) -> str:
        return f"Extractor(source={self.source!r}, file_type={self.file_type!r})"
