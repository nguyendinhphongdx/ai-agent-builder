"""Unified upload endpoint - single endpoint, config-driven validation."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File as FileModel
from app.models.user import User
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.runtime.uploads.config import UPLOAD_CONFIGS
from app.modules.runtime.uploads.schemas import FileResponse, FileUrlResponse
from app.modules.runtime.uploads.service import delete_file, upload_file
from app.platform.db.session import get_db
from app.platform.storage import get_storage

router = APIRouter(prefix="/upload", tags=["upload"])


def _to_response(f: FileModel) -> dict:
    return FileResponse.model_validate(f).release()


@router.post("", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_endpoint(
    file: UploadFile = File(...),
    type: str = Form(...),
    entity_type: str | None = Form(None),
    entity_id: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file. Type determines validation rules (max size, allowed extensions, access level)."""
    try:
        parsed_entity_id = uuid.UUID(entity_id) if entity_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_id format")

    try:
        db_file = await upload_file(
            db=db,
            file=file,
            file_type=type,
            owner_id=current_user.id,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _to_response(db_file)


@router.get("/types")
async def list_upload_types():
    """List available upload types and their constraints."""
    return {
        name: {
            "max_size": cfg.max_size,
            "max_size_mb": cfg.max_size / (1024 * 1024),
            "allowed_extensions": cfg.allowed_extensions,
            "access": cfg.access,
            "entity_types": cfg.entity_types,
        }
        for name, cfg in UPLOAD_CONFIGS.items()
    }


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_endpoint(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.owner_id == current_user.id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return _to_response(f)


@router.get("/{file_id}/url", response_model=FileUrlResponse)
async def get_file_url_endpoint(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get URL for a file. Public files return direct URL. Private files return time-limited URL."""
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.owner_id == current_user.id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    storage = get_storage()
    url = storage.get_url(f.storage_key, f.access)
    expires_in = 0 if f.access == "public" else 900
    return FileUrlResponse(url=url, expires_in=expires_in)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_endpoint(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.owner_id == current_user.id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    await delete_file(db, f)
