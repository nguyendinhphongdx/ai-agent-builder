"""Storage interface and shared utilities."""

import os
import uuid
from abc import ABC, abstractmethod


def generate_storage_key(prefix: str, owner_id: uuid.UUID | str, filename: str) -> str:
    """Generate a unique storage key. Single source of truth for key format.

    Format: {prefix}/{owner_id}/{random12}.{ext}
    Example: avatars/550e8400.../a1b2c3d4e5f6.png
    """
    ext = os.path.splitext(filename)[1].lstrip(".").lower() or "bin"
    unique = uuid.uuid4().hex[:12]
    return f"{prefix}/{owner_id}/{unique}.{ext}"


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, key: str, content: bytes, content_type: str) -> str:
        """Upload file content. Returns storage key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete file by storage key."""
        ...

    @abstractmethod
    def get_url(self, key: str, access: str) -> str:
        """Get URL for a file.
        - access="public" → direct URL (CDN/static)
        - access="private" → presigned/time-limited URL
        """
        ...
