from __future__ import annotations
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
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
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required in LLM node config")

        llm = build_llm(
            provider=config.get("llm_provider", "openai"),
            model=config.get("llm_model"),
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
