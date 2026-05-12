"""Plain-text-ish formats: TXT, Markdown, CSV, HTML."""

from __future__ import annotations

from pathlib import Path

from .base import ExtractionError, ExtractResult


class PlainTextExtractor:
    """No parsing needed — just decode as UTF-8 and hand the bytes back."""

    extensions = ("txt", "md", "csv", "log")

    def extract(self, path: Path) -> ExtractResult:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ExtractionError(f"Failed to read {path.name}: {e}") from e
        return ExtractResult(text=text)


class HtmlExtractor:
    """HTML via LangChain's ``BSHTMLLoader`` (wraps BeautifulSoup).

    Same loader knowledge ingestion uses — also surfaces ``<title>`` as
    ``metadata["title"]`` for future citation UX. Falls back to raw text if
    BeautifulSoup / langchain-community isn't installed.
    """

    extensions = ("html", "htm")

    def extract(self, path: Path) -> ExtractResult:
        try:
            from langchain_community.document_loaders import BSHTMLLoader  # type: ignore
        except ImportError:
            # Fallback: raw bytes, best effort
            return ExtractResult(
                text=path.read_text(encoding="utf-8", errors="replace")
            )

        try:
            loader = BSHTMLLoader(str(path))
            docs = loader.load()
        except Exception as e:
            raise ExtractionError(f"Failed to read HTML {path.name}: {e}") from e

        title = docs[0].metadata.get("title") if docs else None
        return ExtractResult(
            text="\n\n".join(d.page_content for d in docs),
            metadata={"title": title} if title else {},
        )
