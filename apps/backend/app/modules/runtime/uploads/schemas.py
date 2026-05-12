import uuid
from datetime import datetime

from pydantic import BaseModel

from app.platform.schemas.base import AppBaseModel
from app.platform.storage.url import resolve_url


class FileResponse(AppBaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    type: str
    original_name: str
    storage_key: str
    mime_type: str
    size: int
    access: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    url: str | None = None
    created_at: datetime

    def release(self) -> dict:
        data = super().release()
        if data.get("url") is None:
            data["url"] = resolve_url(self.storage_key, self.access)
        return data


class FileUrlResponse(BaseModel):
    url: str
    expires_in: int  # seconds
