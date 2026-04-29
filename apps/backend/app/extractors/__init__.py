"""Text extraction from user-uploaded files.

Single point of truth for "turn this file into text". Reused by:
- Knowledge base ingestion (chunk -> embed -> store)
- Chat attachments (inline into LLM prompt)

Quick start::

    from app.extractors import Extractor

    # Sync
    result = Extractor("/uploads/deck.pptx").parse()

    # Async — recommended inside request handlers
    result = await Extractor(path).parse_async()

    print(result.text)         # "=== Slide 1 ===\\n..."
    print(result.metadata)     # {"slides": 12}

Functional API is also exported (``extract_text`` / ``extract_text_async``)
for call-sites that already pass paths around as strings.
"""

from .base import (
    ExtractionError,
    Extractor,
    ExtractResult,
    FormatExtractor,
    UnsupportedFormatError,
)
from .registry import (
    extract_text,
    extract_text_async,
    get_extractor,
    supported_extensions,
)

__all__ = [
    # Facade
    "Extractor",
    # Types
    "ExtractResult",
    "ExtractionError",
    "UnsupportedFormatError",
    "FormatExtractor",
    # Functional
    "extract_text",
    "extract_text_async",
    "get_extractor",
    "supported_extensions",
]
