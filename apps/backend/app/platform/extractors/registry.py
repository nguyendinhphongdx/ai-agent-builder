"""Registry + public dispatcher for format-specific extractors."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .base import ExtractResult, FormatExtractor, UnsupportedFormatError
from .docx import DocxExtractor
from .pdf import PdfExtractor
from .plain import HtmlExtractor, PlainTextExtractor
from .pptx import PptxExtractor
from .xlsx import XlsxExtractor


def _build_registry() -> dict[str, FormatExtractor]:
    """Build a {lowercase_ext: extractor} table by expanding each extractor."""
    registry: dict[str, FormatExtractor] = {}
    for extractor in (
        PdfExtractor(),
        DocxExtractor(),
        XlsxExtractor(),
        PptxExtractor(),
        PlainTextExtractor(),
        HtmlExtractor(),
    ):
        for ext in extractor.extensions:
            registry[ext.lower()] = extractor
    return registry


_REGISTRY = _build_registry()


def supported_extensions() -> tuple[str, ...]:
    """Extensions the system can parse right now. Useful for FE ``accept``."""
    return tuple(sorted(_REGISTRY.keys()))


def get_extractor(file_type: str) -> FormatExtractor | None:
    """Look up the extractor for a file extension / type string.

    Accepts ``"pdf"``, ``".pdf"`` or ``"PDF"``. Returns ``None`` if no match.
    """
    return _REGISTRY.get(file_type.lower().lstrip("."))


def extract_text(path: str | Path, file_type: str | None = None) -> ExtractResult:
    """Synchronous extraction entry point.

    ``file_type`` overrides the file's extension. Raises
    :class:`UnsupportedFormatError` when no extractor handles the type.
    """
    p = Path(path)
    ext = (file_type or p.suffix).lower().lstrip(".")
    extractor = get_extractor(ext)
    if extractor is None:
        raise UnsupportedFormatError(
            f"No extractor for file type '{ext}' (file: {p.name})"
        )
    return extractor.extract(p)


async def extract_text_async(
    path: str | Path, file_type: str | None = None
) -> ExtractResult:
    """Async wrapper around :func:`extract_text`.

    Parsing libraries are CPU-bound + blocking; ``asyncio.to_thread`` keeps the
    event loop responsive so other requests / SSE streams keep flowing.
    """
    return await asyncio.to_thread(extract_text, path, file_type)
