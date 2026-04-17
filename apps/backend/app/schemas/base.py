"""Base Pydantic schema with release() pattern for response transformation."""
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from app.storage.url import resolve_url


class AppBaseModel(BaseModel):
    """Base schema providing release() for response transformation.

    - __storage_fields__: tuple of field names that hold storage keys.
      release() will resolve them to full URLs automatically.
    - Override release() for custom transform logic (call super().release() first).
    """

    __storage_fields__: ClassVar[tuple[str, ...]] = ()

    model_config = {"from_attributes": True}

    def release(self) -> dict:
        data = self.model_dump()
        for field in self.__storage_fields__:
            val = data.get(field)
            if val is not None:
                data[field] = resolve_url(val)
        return data
