import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ApiKeyCreate(BaseModel):
    provider: str
    name: str
    plaintext_key: str
    is_default: bool = True

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"openai", "anthropic", "google", "ollama"}
        if v not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v

    @field_validator("plaintext_key")
    @classmethod
    def validate_key_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    provider: str
    name: str
    is_default: bool
    last_used_at: datetime | None
    created_at: datetime
    # Key value is never returned — only masked prefix
    masked_key: str

    model_config = {"from_attributes": True}
