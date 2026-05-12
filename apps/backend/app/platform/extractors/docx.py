"""DOCX extraction via LangChain's ``Docx2txtLoader`` (wraps docx2txt).

Kept aligned with knowledge ingestion so upgrading the loader (e.g.
``UnstructuredWordDocumentLoader`` for richer layout) is a one-line change.
"""

from __future__ import annotations

from pathlib import Path

from .base import ExtractionError, ExtractResult


class DocxExtractor:
    extensions = ("docx",)

    def extract(self, path: Path) -> ExtractResult:
        try:
            from langchain_community.document_loaders import Docx2txtLoader  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ExtractionError(
                "langchain-community / docx2txt is not installed"
            ) from e

        try:
            loader = Docx2txtLoader(str(path))
            docs = loader.load()
        except Exception as e:
            raise ExtractionError(f"Failed to read DOCX {path.name}: {e}") from e

        return ExtractResult(text="\n\n".join(d.page_content for d in docs))
