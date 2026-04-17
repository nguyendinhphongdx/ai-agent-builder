"""Factory - returns the correct storage backend based on config."""

from functools import lru_cache

from app.config import settings
from app.storage.base import StorageBackend


@lru_cache
def get_storage() -> StorageBackend:
    match settings.STORAGE_TYPE:
        case "s3" | "minio":
            from app.storage.s3 import S3Storage
            return S3Storage()
        case "gcs":
            from app.storage.gcs import GCSStorage
            return GCSStorage()
        case _:
            from app.storage.local import LocalStorage
            return LocalStorage()
