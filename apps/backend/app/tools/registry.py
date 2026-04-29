from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.tool import Tool
from app.tools.url_guard import assert_safe_url


def _render_template(template: str, kwargs: dict) -> str:
    """Substitute `{name}` placeholders with stringified values."""
    out = template
    for key, val in kwargs.items():
        out = out.replace(f"{{{key}}}", str(val))
    return out


def _render_json_body(template: str, kwargs: dict) -> Any:
    """Render a JSON body template by substituting placeholders inside JSON values
    (not string concatenation), so quotes/special chars don't break the JSON.
    """
    body = json.loads(template) if template else None
    if body is None:
        return None

    def _walk(node):
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, str):
            return _render_template(node, kwargs)
        return node

    return _walk(body)


def json_schema_to_pydantic(schema: dict) -> type[BaseModel]:
    """Convert a JSON Schema dict to a Pydantic model at runtime."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions: dict[str, Any] = {}
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for name, prop in properties.items():
        field_type = type_map.get(prop.get("type", "string"), str)
        description = prop.get("description", "")
        default = prop.get("default", ...)

        if name not in required and default is ...:
            default = None
            field_type = field_type | None

        field_definitions[name] = (field_type, default if default is not ... else ...)

    return create_model("DynamicToolInput", **field_definitions)


class ToolBuilder:
    """Base class for tool builders per tool_type."""

    def build(self, tool_def: Tool) -> StructuredTool:
        raise NotImplementedError


class HTTPRequestToolBuilder(ToolBuilder):
    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            url = _render_template(config["url"], kwargs)
            try:
                assert_safe_url(url)
            except ValueError as exc:
                return f"Error: {exc}"

            headers = config.get("headers", {})
            method = config.get("method", "GET").upper()
            body = _render_json_body(config.get("body_template"), kwargs)

            async with httpx.AsyncClient(timeout=tool_def.timeout_seconds) as client:
                resp = await client.request(method, url, headers=headers, json=body)
                resp.raise_for_status()
                return resp.text[:4000]

        args_schema = json_schema_to_pydantic(tool_def.input_schema)

        return StructuredTool.from_function(
            coroutine=execute,
            name=tool_def.name.replace(" ", "_").lower(),
            description=tool_def.description,
            args_schema=args_schema,
        )


class CodeExecToolBuilder(ToolBuilder):
    """Builder cho tool code execution - gọi sandbox service qua HTTP."""

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            code = _render_template(config.get("code_template", ""), kwargs)
            language = config.get("language", "python")

            headers = {}
            if settings.SANDBOX_SECRET:
                headers["x-internal-token"] = settings.SANDBOX_SECRET

            async with httpx.AsyncClient(timeout=tool_def.timeout_seconds + 5) as client:
                try:
                    resp = await client.post(
                        f"{settings.SANDBOX_URL}/execute",
                        json={
                            "code": code,
                            "language": language,
                            "timeout": tool_def.timeout_seconds,
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if result.get("error"):
                        return f"Output:\n{result['output']}\n\nError:\n{result['error']}"
                    return result["output"][:4000]

                except httpx.ConnectError:
                    return "Error: Code sandbox service is not available."

        args_schema = json_schema_to_pydantic(tool_def.input_schema)

        return StructuredTool.from_function(
            coroutine=execute,
            name=tool_def.name.replace(" ", "_").lower(),
            description=tool_def.description,
            args_schema=args_schema,
        )


class WebScrapeToolBuilder(ToolBuilder):
    """Builder cho tool web scrape - GET URL và trả về nội dung text."""

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            url = _render_template(config.get("url_template", ""), kwargs)
            try:
                assert_safe_url(url)
            except ValueError as exc:
                return f"Error: {exc}"

            async with httpx.AsyncClient(timeout=tool_def.timeout_seconds) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text

            max_length = config.get("max_length", 5000)
            return text[:max_length]

        args_schema = json_schema_to_pydantic(tool_def.input_schema)

        return StructuredTool.from_function(
            coroutine=execute,
            name=tool_def.name.replace(" ", "_").lower(),
            description=tool_def.description,
            args_schema=args_schema,
        )


class DBQueryToolBuilder(ToolBuilder):
    """Builder cho tool DB query - thực thi SELECT query trên database.

    Config:
    - connection_string: URL Postgres (asyncpg). Khuyến nghị dùng role read-only.
    - max_rows: số dòng tối đa trả về (mặc định 50).

    Bảo mật:
    - connection set ``default_transaction_read_only=on`` ở server level →
      Postgres reject mọi statement ghi (INSERT/UPDATE/DELETE/DDL).
    - host trong connection_string phải là public IP — chặn private/loopback/
      link-local + cloud metadata để LLM không gọi tới Postgres internal của
      platform hoặc nội mạng VPC.
    """

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            query = kwargs.get("query", "")
            if not query.strip():
                return "Error: Empty query."

            connection_string = config.get("connection_string", "")
            if not connection_string:
                return "Error: Thiếu connection_string trong config."

            # SSRF guard: parse the host out of the URL and validate it.
            # ``urlparse`` handles postgres://… URIs the same way it handles
            # http; we feed the resulting hostname through assert_safe_url
            # by reconstructing as an http URL so the existing guard applies.
            from urllib.parse import urlparse

            try:
                parsed = urlparse(connection_string)
                if not parsed.hostname:
                    return "Error: connection_string thiếu hostname."
                # Reuse the HTTP guard's hostname resolver — it doesn't care
                # about scheme as long as we feed something it parses.
                assert_safe_url(f"http://{parsed.hostname}:{parsed.port or 5432}/")
            except ValueError as exc:
                return f"Error: {exc}"

            max_rows = config.get("max_rows", 50)

            try:
                import asyncpg

                conn = await asyncpg.connect(
                    connection_string,
                    server_settings={"default_transaction_read_only": "on"},
                )
                try:
                    rows = await conn.fetch(query)
                    result = [dict(row) for row in rows[:max_rows]]
                    for row in result:
                        for key, value in row.items():
                            if not isinstance(value, (str, int, float, bool, type(None))):
                                row[key] = str(value)
                    return json.dumps(result, ensure_ascii=False, indent=2)
                finally:
                    await conn.close()

            except Exception as e:
                return f"Error: {str(e)}"

        args_schema = json_schema_to_pydantic(tool_def.input_schema)

        return StructuredTool.from_function(
            coroutine=execute,
            name=tool_def.name.replace(" ", "_").lower(),
            description=tool_def.description,
            args_schema=args_schema,
        )


class ToolRegistry:
    """Converts persisted tool definitions into callable LangChain tools."""

    _builders: dict[str, ToolBuilder] = {}

    def __init__(self):
        self._builders = {
            "http_request": HTTPRequestToolBuilder(),
            "code_exec": CodeExecToolBuilder(),
            "web_scrape": WebScrapeToolBuilder(),
            "db_query": DBQueryToolBuilder(),
        }

    def register_builder(self, tool_type: str, builder: ToolBuilder):
        self._builders[tool_type] = builder

    def build(self, tool_def: Tool) -> StructuredTool:
        builder = self._builders.get(tool_def.tool_type)
        if not builder:
            raise ValueError(f"Unknown tool type: {tool_def.tool_type}")
        return builder.build(tool_def)

    def build_many(self, tool_defs: list[Tool]) -> list[StructuredTool]:
        return [self.build(t) for t in tool_defs if t.is_active]


# Singleton
tool_registry = ToolRegistry()
