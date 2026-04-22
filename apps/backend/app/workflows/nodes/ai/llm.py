from __future__ import annotations
from typing import Any
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai_credentials.service import get_plaintext_key_by_id
from app.llm.provider import build_llm
from app.workflows.template_utils import render_template
from ..base import ExecutionContext, NodeExecutor, NodeResult


def _extract_tokens(response: Any) -> int:
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        return response.usage_metadata.get("total_tokens", 0)
    return 0


class LLMExecutor(NodeExecutor):
    """Call a chat LLM for each incoming item and append the response."""

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        model_id = config.get("model_id")
        if not model_id:
            raise ValueError("model_id is required in LLM node config")

        credential_id = config.get("credential_id")
        api_key: str | None = None
        if credential_id:
            api_key = await get_plaintext_key_by_id(ctx.db, uuid.UUID(str(credential_id)))
        if not api_key:
            raise ValueError("credential_id is required and must point to a valid AI credential")

        llm = build_llm(
            model_id=model_id,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            base_url=config.get("base_url"),
            api_key=api_key,
        )

        output_var = config.get("output_variable", "response")
        prompt_template = config.get("user_prompt_template", "{{input}}")
        system_prompt = config.get("system_prompt", "")

        results: list[dict[str, Any]] = []
        total_tokens = 0

        for item in items:
            messages: list[Any] = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=render_template(prompt_template, item)))

            response = await llm.ainvoke(messages)
            total_tokens += _extract_tokens(response)
            results.append({**item, output_var: response.content})

        return NodeResult(items=results, tokens_used=total_tokens)
