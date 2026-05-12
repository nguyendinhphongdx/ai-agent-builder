"""Unified upload service - validation, storage, DB record."""

import os
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.modules.runtime.uploads.config import get_upload_config
from app.platform.storage import generate_storage_key, get_storage


async def upload_file(
    db: AsyncSession,
    file: UploadFile,
    file_type: str,
    owner_id: uuid.UUID,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> File:
    config = get_upload_config(file_type)

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lstrip(".").lower()
    if ext not in config.allowed_extensions:
        allowed = ", ".join(config.allowed_extensions)
        raise ValueError(f"File type .{ext} not allowed. Allowed: {allowed}")

    # Validate entity_type
    if entity_type and entity_type not in config.entity_types:
        raise ValueError(f"entity_type '{entity_type}' not valid for '{file_type}'")

    # Read + validate size
    content = await file.read()
    if len(content) > config.max_size:
        max_mb = config.max_size / (1024 * 1024)
        raise ValueError(f"File too large. Max: {max_mb:.0f}MB")

    # Upload via storage backend
    storage = get_storage()
    key = generate_storage_key(config.path, owner_id, file.filename or "file")
    await storage.upload(key, content, file.content_type or "application/octet-stream")

    # DB record
    db_file = File(
        owner_id=owner_id,
        type=file_type,
        original_name=file.filename or "unknown",
        storage_key=key,
        mime_type=file.content_type or "application/octet-stream",
        size=len(content),
        access=config.access,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(db_file)
    await db.flush()
    await db.refresh(db_file)
    return db_file


async def delete_file(db: AsyncSession, file: File) -> None:
    storage = get_storage()
    await storage.delete(file.storage_key)
    await db.delete(file)
    await db.flush()
