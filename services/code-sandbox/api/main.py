"""Code Sandbox Service — lightweight HTTP API for sandboxed code execution."""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import FastAPI

from api.executor import execute_code, SUPPORTED_LANGUAGES

app = FastAPI(title="Code Sandbox", version="1.0.0")


class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = Field(default=30, ge=1, le=120)


class ExecuteResponse(BaseModel):
    output: str
    exit_code: int
    error: str | None
    execution_time_ms: int


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest) -> ExecuteResponse:
    result = await execute_code(
        code=req.code,
        language=req.language,
        timeout=req.timeout,
    )
    return ExecuteResponse(**result)


@app.get("/health")
async def health():
    return {"status": "ok", "languages": list(SUPPORTED_LANGUAGES)}
