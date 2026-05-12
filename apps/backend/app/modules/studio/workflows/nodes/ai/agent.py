from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from sqlalchemy import select

from app.models.agent import Agent as AgentModel
from app.modules.integrations.llm.credentials.service import get_plaintext_key_by_id
from app.modules.integrations.llm.provider import build_llm_from_agent
from app.modules.studio.agents.executor import (
    _auto_retrieve_context,
    _build_system_prompt,
    build_agent_tools,
)

from ..base import ExecutionContext, NodeExecutor, NodeResult


def _extract_tokens(response: Any) -> int:
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        return response.usage_metadata.get("total_tokens", 0)
    return 0


class AgentExecutor(NodeExecutor):
    """Run a persisted Agent (ReAct loop) for each incoming item.

    This is the ONLY node that uses LangGraph internally.
    """

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        agent_id = config.get("agent_id")
        if not agent_id:
            raise ValueError("agent_id is required in agent node config")

        result = await ctx.db.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        api_key = await get_plaintext_key_by_id(ctx.db, agent.credential_id) if agent.credential_id else None
        llm = build_llm_from_agent(agent, api_key=api_key)
        tools = await build_agent_tools(agent, ctx.db)

        output_var = config.get("output_variable", "response")
        output_mode = config.get("output_mode", "text")

        results: list[dict[str, Any]] = []
        total_tokens = 0

        for item in items:
            user_content = str(item.get("input", item))

            kb_context = None
            if agent.kb_retrieval_mode == "auto":
                class _Msg:
                    def __init__(self, role: str, content: str) -> None:
                        self.role = role
                        self.content = content
                kb_context = await _auto_retrieve_context(agent, [_Msg("user", user_content)], ctx.db)

            system_prompt = _build_system_prompt(agent.system_prompt, kb_context)
            messages: list[Any] = [HumanMessage(content=user_content)]

            response_text = ""
            tool_results: list[dict[str, Any]] = []

            if tools:
                graph = create_react_agent(llm, tools, prompt=system_prompt)
                result_state = await graph.ainvoke({"messages": messages})
                for msg in reversed(result_state.get("messages", [])):
                    if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                        response_text = msg.content
                        break
                for msg in result_state.get("messages", []):
                    if isinstance(msg, ToolMessage):
                        tool_results.append({"tool_call_id": msg.tool_call_id, "content": str(msg.content)[:500]})
            else:
                pre_messages: list[Any] = []
                if system_prompt:
                    pre_messages.append(SystemMessage(content=system_prompt))
                pre_messages.extend(messages)
                raw_response = await llm.ainvoke(pre_messages)
                response_text = raw_response.content
                total_tokens += _extract_tokens(raw_response)

            output_value: Any = (
                {"response": response_text, "tool_results": tool_results, "sources": []}
                if output_mode == "structured"
                else response_text
            )
            results.append({**item, output_var: output_value})

        return NodeResult(items=results, tokens_used=total_tokens)
