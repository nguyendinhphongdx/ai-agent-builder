import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.modules.llm.catalog import allowed_providers


class AICredentialCreate(BaseModel):
    provider: str
    name: str
    plaintext_key: str

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = allowed_providers()
        if v not in allowed:
            raise ValueError(f"Provider must be one of {sorted(allowed)}")
        return v

    @field_validator("plaintext_key")
    @classmethod
    def validate_key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class AICredentialUpdate(BaseModel):
    name: str | None = None


class AICredentialResponse(BaseModel):
    id: uuid.UUID
    provider: str
    name: str
    last_used_at: datetime | None
    created_at: datetime
    masked_key: str

    model_config = {"from_attributes": True}
