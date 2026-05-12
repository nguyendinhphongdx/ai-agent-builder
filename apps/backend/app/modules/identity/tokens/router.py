"""Personal access token CRUD — browser-facing (cookie auth).

Endpoints live under ``/api-tokens`` and are consumed by the Settings page in
the frontend. The plaintext token is returned ONCE on creation and never again.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.tokens.schemas import (
    TokenCreate,
    TokenCreatedResponse,
    TokenResponse,
)
from app.modules.identity.tokens.service import create_token, list_tokens, revoke_token
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/api-tokens",
    tags=["api-tokens"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[TokenResponse])
async def list_tokens_endpoint(db: AsyncSession = Depends(get_db)):
    """List all tokens owned by the current user (revoked included for audit)."""
    tokens = await list_tokens(db)
    return [TokenResponse.model_validate(t) for t in tokens]


@router.post(
    "",
    response_model=TokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_token_endpoint(
    body: TokenCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new token. Plaintext value is returned ONCE — frontend must
    surface it to the user immediately."""
    token, plaintext = await create_token(db, body)
    await db.commit()

    payload = TokenResponse.model_validate(token).model_dump()
    return TokenCreatedResponse(**payload, plaintext=plaintext)


@router.post("/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token_endpoint(
    token_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft-revoke a token. Future requests using it will be rejected."""
    ok = await revoke_token(db, token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    await db.commit()
