"""AWS S3 / MinIO storage."""

import boto3
from botocore.config import Config

from app.config import settings
from app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(self):
        self.bucket = settings.S3_BUCKET
        self.region = settings.S3_REGION
        self.client = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            **({"endpoint_url": settings.S3_ENDPOINT_URL} if settings.S3_ENDPOINT_URL else {}),
        )

    async def upload(self, key: str, content: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return key

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get_url(self, key: str, access: str) -> str:
        if access == "public":
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

        # Private: presigned URL, 15 min
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=900,
        )
