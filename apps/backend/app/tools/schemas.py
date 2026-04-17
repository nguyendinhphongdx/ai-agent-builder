import uuid
from datetime import datetime

from pydantic import BaseModel


class ToolCreate(BaseModel):
    name: str
    description: str
    tool_type: str  # 'http_request', 'code_exec', 'db_query', 'web_scrape', 'custom_function'
    config: dict
    input_schema: dict
    output_schema: dict | None = None
    timeout_seconds: int = 30


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    is_active: bool | None = None
    timeout_seconds: int | None = None


class ToolResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    tool_type: str
    config: dict
    input_schema: dict
    output_schema: dict | None
    is_active: bool
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolTestRequest(BaseModel):
    input_data: dict


class ToolTestResponse(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None
    latency_ms: int
