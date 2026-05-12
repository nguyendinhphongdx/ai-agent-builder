"""Base Pydantic schema with release() pattern for response transformation."""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from app.platform.storage.url import resolve_url


class AppBaseModel(BaseModel):
    """Base schema providing release() for response transformation.

    - __storage_fields__: tuple of field names that hold storage keys.
      release() will resolve them to full URLs automatically.
    - Override release() for custom transform logic (call super().release() first).
    """

    __storage_fields__: ClassVar[tuple[str, ...]] = ()

    # `protected_namespaces=()` opts out of Pydantic's `model_*` reservation
    # so we can keep field names like `model_id` that mirror the LLM domain
    # (Anthropic / OpenAI / Ollama all use "model" as the user-facing term).
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    def release(self) -> dict:
        data = self.model_dump()
        for field in self.__storage_fields__:
            val = data.get(field)
            if val is not None:
                data[field] = resolve_url(val)
        return data
