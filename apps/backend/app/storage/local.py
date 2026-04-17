"""Local filesystem storage."""

import os

from app.config import settings
from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self):
        self.root = settings.UPLOAD_DIR
        os.makedirs(self.root, exist_ok=True)

    async def upload(self, key: str, content: bytes, content_type: str) -> str:
        path = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return key

    async def delete(self, key: str) -> None:
        path = os.path.join(self.root, key)
        if os.path.exists(path):
            os.remove(path)

    def get_url(self, key: str, access: str) -> str:
        base = f"{settings.BASE_URL.rstrip('/')}/uploads"
        return f"{base}/{key}"
