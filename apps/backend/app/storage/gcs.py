"""Google Cloud Storage."""

from datetime import timedelta

from app.config import settings
from app.storage.base import StorageBackend


class GCSStorage(StorageBackend):
    def __init__(self):
        from google.cloud import storage as gcs
        self.client = gcs.Client()
        self.bucket = self.client.bucket(settings.GCS_BUCKET)

    async def upload(self, key: str, content: bytes, content_type: str) -> str:
        blob = self.bucket.blob(key)
        blob.upload_from_string(content, content_type=content_type)
        return key

    async def delete(self, key: str) -> None:
        blob = self.bucket.blob(key)
        blob.delete()

    def get_url(self, key: str, access: str) -> str:
        if access == "public":
            return f"https://storage.googleapis.com/{settings.GCS_BUCKET}/{key}"

        # Private: signed URL, 15 min
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(expiration=timedelta(minutes=15))
