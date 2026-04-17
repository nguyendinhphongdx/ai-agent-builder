from __future__ import annotations

import uuid
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tool import Tool


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
            import httpx

            url = config["url"]
            for key, val in kwargs.items():
                url = url.replace(f"{{{key}}}", str(val))

            headers = config.get("headers", {})
            method = config.get("method", "GET").upper()

            body = None
            if config.get("body_template"):
                import json
                body_str = config["body_template"]
                for key, val in kwargs.items():
                    body_str = body_str.replace(f"{{{key}}}", str(val))
                body = json.loads(body_str)

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

    SANDBOX_URL = "http://code-sandbox:8000/execute"

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            import httpx

            code = config.get("code_template", "")
            for key, val in kwargs.items():
                code = code.replace(f"{{{key}}}", str(val))

            language = config.get("language", "python")

            async with httpx.AsyncClient(timeout=tool_def.timeout_seconds + 5) as client:
                try:
                    resp = await client.post(
                        CodeExecToolBuilder.SANDBOX_URL,
                        json={
                            "code": code,
                            "language": language,
                            "timeout": tool_def.timeout_seconds,
                        },
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
            import httpx

            url = config.get("url_template", "")
            for key, val in kwargs.items():
                url = url.replace(f"{{{key}}}", str(val))

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

    Config cần có:
    - connection_string: URL kết nối database (chỉ hỗ trợ SELECT)
    - max_rows: số dòng tối đa trả về (mặc định: 50)

    Bảo mật: chỉ cho phép câu lệnh SELECT, chặn INSERT/UPDATE/DELETE/DROP/ALTER.
    """

    # Danh sách từ khóa nguy hiểm bị chặn
    BLOCKED_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"}

    def build(self, tool_def: Tool) -> StructuredTool:
        config = tool_def.config

        async def execute(**kwargs) -> str:
            import json

            query = kwargs.get("query", "")

            # Kiểm tra bảo mật: chỉ cho phép SELECT
            query_lower = query.strip().lower()
            first_word = query_lower.split()[0] if query_lower.split() else ""
            if first_word != "select":
                return "Error: Chỉ cho phép câu lệnh SELECT."

            for keyword in DBQueryToolBuilder.BLOCKED_KEYWORDS:
                if keyword in query_lower:
                    return f"Error: Từ khóa '{keyword}' không được phép."

            connection_string = config.get("connection_string", "")
            if not connection_string:
                return "Error: Thiếu connection_string trong config."

            max_rows = config.get("max_rows", 50)

            try:
                import asyncpg

                conn = await asyncpg.connect(connection_string)
                try:
                    rows = await conn.fetch(query)
                    # Chuyển kết quả thành list of dict
                    result = [dict(row) for row in rows[:max_rows]]

                    # Serialize các giá trị đặc biệt (UUID, datetime, ...)
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
