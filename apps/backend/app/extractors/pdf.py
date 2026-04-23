"""PDF extraction via LangChain's ``PyPDFLoader`` (wraps pypdf).

Same loader the knowledge-base ingestion uses, so upgrading loader quality
later (e.g. ``PyMuPDFLoader`` for better layout) happens in one place.
Empty-text output indicates an image-only / scanned PDF — callers decide
whether to fall back to OCR.
"""

from __future__ import annotations

from pathlib import Path

from .base import ExtractionError, ExtractResult


class PdfExtractor:
    extensions = ("pdf",)

    def extract(self, path: Path) -> ExtractResult:
        try:
            from langchain_community.document_loaders import PyPDFLoader  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ExtractionError("langchain-community / pypdf is not installed") from e

        try:
            loader = PyPDFLoader(str(path))
            pages = loader.load()
        except Exception as e:
            raise ExtractionError(f"Failed to read PDF {path.name}: {e}") from e

        return ExtractResult(
            text="\n\n".join(page.page_content for page in pages),
            metadata={"pages": len(pages)},
        )
