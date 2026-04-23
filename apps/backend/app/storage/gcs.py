"""Google Cloud Storage backend.

Credential resolution order:
  1. ``settings.GCS_SA_JSON`` — inline service account JSON (tiện cho env-only deploy).
  2. ``settings.GCS_SA_FILE`` — path tới file service account JSON (đã mount vào container).
  3. Application Default Credentials fallback — ``~/.config/gcloud/...`` hoặc metadata server
     khi chạy trên GCE / Cloud Run / GKE với SA gắn instance.

Signed URL yêu cầu credential có thể ký: SA JSON (inline hoặc file) hoạt động
mặc định; ADC qua metadata server cần SA có quyền ``iam.serviceAccountTokenCreator``.
"""

from __future__ import annotations

import json
from datetime import timedelta

from app.config import settings
from app.storage.base import StorageBackend


class GCSStorage(StorageBackend):
    def __init__(self) -> None:
        from google.cloud import storage as gcs

        if settings.GCS_SA_JSON:
            from google.oauth2 import service_account

            info = json.loads(settings.GCS_SA_JSON)
            creds = service_account.Credentials.from_service_account_info(info)
            self.client = gcs.Client(credentials=creds, project=info.get("project_id"))
        elif settings.GCS_SA_FILE:
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(settings.GCS_SA_FILE)
            self.client = gcs.Client(credentials=creds, project=creds.project_id)
        else:
            # ADC fallback: ~/.config/gcloud/... hoặc metadata server
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
