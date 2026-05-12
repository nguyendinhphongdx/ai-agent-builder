import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_credentials.schemas import (
    AICredentialCreate,
    AICredentialResponse,
    AICredentialUpdate,
)
from app.modules.ai_credentials.service import (
    create_ai_credential,
    delete_ai_credential,
    get_ai_credential,
    list_ai_credentials,
    update_ai_credential,
)
from app.modules.auth.dependencies import get_current_user
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/ai-credentials",
    tags=["ai-credentials"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[AICredentialResponse])
async def list_credentials(db: AsyncSession = Depends(get_db)):
    """List all AI credentials for the current user (keys are masked)."""
    return await list_ai_credentials(db)


@router.post("", response_model=AICredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: AICredentialCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new encrypted AI credential."""
    result = await create_ai_credential(db, body)
    await db.commit()
    return result


@router.get("/{cred_id}", response_model=AICredentialResponse)
async def get_credential(
    cred_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    cred = await get_ai_credential(db, cred_id)
    if not cred:
        raise HTTPException(status_code=404, detail="AI credential not found")
    return cred


@router.patch("/{cred_id}", response_model=AICredentialResponse)
async def update_credential(
    cred_id: uuid.UUID,
    body: AICredentialUpdate,
    db: AsyncSession = Depends(get_db),
):
    cred = await update_ai_credential(db, cred_id, body)
    if not cred:
        raise HTTPException(status_code=404, detail="AI credential not found")
    await db.commit()
    return cred


@router.delete("/{cred_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    cred_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_ai_credential(db, cred_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="AI credential not found")
    await db.commit()
