import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_keys.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.api_keys.service import (
    create_api_key,
    delete_api_key,
    get_api_key,
    list_api_keys,
    update_api_key,
)
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user (keys are masked)."""
    return await list_api_keys(db, current_user.id)


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a new encrypted API key."""
    result = await create_api_key(db, current_user.id, body)
    await db.commit()
    return result


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await get_api_key(db, key_id, current_user.id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_key(
    key_id: uuid.UUID,
    body: ApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = await update_api_key(db, key_id, current_user.id, body)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_api_key(db, key_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.commit()
