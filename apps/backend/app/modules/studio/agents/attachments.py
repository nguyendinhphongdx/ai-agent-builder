"""Build LLM content parts from user-uploaded ``File`` attachments.

Two paths, depending on MIME type:

- **Image** (``image/*``): fetch bytes, base64-inline as an ``image_url`` part.
  The LLM provider decides whether it can consume the image; if not, the
  request will surface an error at invocation time. (OCR fallback is a
  future enhancement slot.)

- **Document** (pdf / docx / xlsx / pptx / txt / md / csv / html):
  :class:`app.platform.extractors.Extractor` converts to plain text, which is emitted
  as a ``text`` content part tagged with the filename so the LLM knows where
  it came from.

The shape of returned ``content_parts`` matches LangChain's multi-modal input
convention; ``HumanMessage(content=parts)`` translates to each provider's
native format (OpenAI, Anthropic, Gemini, …) transparently.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Iterable

from app.models.file import File as FileModel
from app.modules.studio.tools.url_guard import safe_get
from app.platform.extractors import (
    ExtractionError,
    Extractor,
    UnsupportedFormatError,
)
from app.platform.storage import get_storage

logger = logging.getLogger("agentforge")


async def _fetch_bytes(url: str) -> bytes:
    """Download ``url`` with redirect-aware SSRF guard.

    The URL comes from our storage backend (S3 presigned, GCS, local FS),
    but we still re-validate each redirect hop so a misconfigured backend
    can't be steered into the metadata API.
    """
    resp = await safe_get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


async def _image_part(file: FileModel) -> dict[str, Any]:
    """Return an ``image_url`` content block with the image inlined as base64."""
    url = get_storage().get_url(file.storage_key, access=file.access)
    data = await _fetch_bytes(url)
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{file.mime_type};base64,{b64}"},
    }


async def _doc_text_part(file: FileModel) -> dict[str, Any]:
    """Extract text from a document attachment and wrap it as a ``text`` block."""
    url = get_storage().get_url(file.storage_key, access=file.access)
    file_ext = file.original_name.rsplit(".", 1)[-1] if "." in file.original_name else ""
    try:
        result = await Extractor(url, file_ext).parse_async()
        text = result.text.strip()
    except UnsupportedFormatError:
        text = f"[Unsupported file type: {file.original_name}]"
    except ExtractionError as e:
        logger.warning("Attachment extract failed for %s: %s", file.original_name, e)
        text = f"[Failed to read file: {file.original_name}]"

    if not text:
        text = f"[{file.original_name} contained no extractable text — may be a scanned image.]"

    return {
        "type": "text",
        "text": f"[Attached file: {file.original_name}]\n{text}",
    }


async def build_content_parts(
    user_text: str,
    attachments: Iterable[FileModel],
) -> list[dict[str, Any]] | str:
    """Assemble the multimodal content list for this turn's user message.

    Returns a plain ``str`` when there are no attachments — keeps small paths
    readable and compatible with providers that don't expect block lists.
    """
    files = list(attachments)
    if not files:
        return user_text

    parts: list[dict[str, Any]] = []

    # Doc text blocks first so the LLM has context before it sees the question.
    for f in files:
        if not (f.mime_type or "").startswith("image/"):
            parts.append(await _doc_text_part(f))

    # Then images (LLM reads them alongside the question).
    for f in files:
        if (f.mime_type or "").startswith("image/"):
            parts.append(await _image_part(f))

    # Finally the user's actual text.
    if user_text:
        parts.append({"type": "text", "text": user_text})

    return parts
