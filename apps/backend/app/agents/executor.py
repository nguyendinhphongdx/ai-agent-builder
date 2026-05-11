"""LangGraph-based agent executor with tool support and streaming."""
from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.attachments import build_content_parts
from app.knowledge.retriever import KnowledgeRetriever
from app.llm.provider import build_llm_from_agent
from app.models.agent import Agent
from app.models.file import File as FileModel
from app.tools.registry import tool_registry


async def _build_history(
    messages: list,
    current_attachments: list["FileModel"] | None = None,
) -> list:
    """Convert DB messages to LangChain message objects.

    System prompt is NOT included here — it is passed via state_modifier.

    ``current_attachments`` (if any) are attached to the LATEST user message —
    doc text is inlined, images get base64 ``image_url`` blocks. Past
    user-turn attachments are NOT re-hydrated: they already had extracted text
    persisted into their ``content`` at save time, and re-uploading images on
    every turn would blow up tokens.
    """
    lc_messages: list = []

    # Index of the last user message — only that one gets attachment blocks.
    last_user_idx = -1
    for i, msg in enumerate(messages):
        if msg.role == "user":
            last_user_idx = i

    for i, msg in enumerate(messages):
        if msg.role == "user":
            if i == last_user_idx and current_attachments:
                content = await build_content_parts(msg.content, current_attachments)
            else:
                content = msg.content
            lc_messages.append(HumanMessage(content=content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == "tool":
            lc_messages.append(
                ToolMessage(content=msg.content, tool_call_id=msg.tool_call_id or "")
            )

    return lc_messages


async def _auto_retrieve_context(
    agent: Agent, messages: list, db: AsyncSession
) -> str | None:
    """Auto-retrieve relevant KB chunks for the latest user message.

    Returns formatted context string or None if no results.
    """
    if not agent.knowledge_bases:
        return None

    # Find latest user message
    latest_user_msg = None
    for msg in reversed(messages):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    if not latest_user_msg:
        return None

    retriever = KnowledgeRetriever(db)
    kb_ids = [kb.id for kb in agent.knowledge_bases]
    chunks = await retriever.retrieve(latest_user_msg, kb_ids)

    if not chunks:
        return None

    formatted_chunks = []
    for c in chunks:
        source = f" (source: {c.source_document})" if c.source_document else ""
        formatted_chunks.append(f"{c.content}{source}")

    return "\n\n---\n\n".join(formatted_chunks)


def _build_system_prompt(base_prompt: str | None, kb_context: str | None) -> str | None:
    """Combine system prompt with auto-retrieved KB context."""
    parts = []
    if base_prompt:
        parts.append(base_prompt)
    if kb_context:
        parts.append(f"## Relevant Knowledge:\n{kb_context}")
    return "\n\n".join(parts) if parts else None


async def build_agent_tools(
    agent: Agent, db: AsyncSession
) -> list[StructuredTool]:
    """Build all tools for an agent: custom tools + RAG retrieval tool (if mode=tool)."""
    tools: list[StructuredTool] = []

    # Custom tools attached to the agent
    if agent.tools:
        tools.extend(tool_registry.build_many(agent.tools))

    # Knowledge base retrieval tool — only in "tool" mode
    if agent.knowledge_bases and agent.kb_retrieval_mode == "tool":
        retriever = KnowledgeRetriever(db)
        kb_ids = [kb.id for kb in agent.knowledge_bases]
        kb_names = ", ".join(kb.name for kb in agent.knowledge_bases)

        async def search_knowledge(query: str) -> str:
            """Search the agent's knowledge base for relevant information."""
            chunks = await retriever.retrieve(query, kb_ids)
            if not chunks:
                return "No relevant information found."
            results = []
            for c in chunks:
                source = f" (source: {c.source_document})" if c.source_document else ""
                results.append(f"{c.content}{source}")
            return "\n\n---\n\n".join(results)

        from langchain_core.tools import tool as tool_decorator

        @tool_decorator(description=f"Search knowledge bases ({kb_names}) for relevant information about the query.")
        async def search_knowledge_base(query: str) -> str:
            """Search knowledge bases for relevant information."""
            return await search_knowledge(query)

        tools.append(search_knowledge_base)

    return tools


class AgentStreamEvent:
    """Events emitted during agent execution."""

    def __init__(self, event_type: str, **kwargs):
        self.type = event_type
        self.data = kwargs

    def to_dict(self) -> dict:
        return {"type": self.type, **self.data}


async def execute_agent_stream(
    agent: Agent,
    messages: list,
    db: AsyncSession,
    api_key: str | None = None,
    current_attachments: list[FileModel] | None = None,
) -> AsyncGenerator[AgentStreamEvent, None]:
    """Execute agent with LangGraph and yield streaming events."""
    llm = build_llm_from_agent(agent, api_key=api_key)
    tools = await build_agent_tools(agent, db)
    lc_messages = await _build_history(messages, current_attachments)

    # Build system prompt (with auto KB context if mode=auto)
    kb_context = None
    if agent.kb_retrieval_mode == "auto":
        kb_context = await _auto_retrieve_context(agent, messages, db)

    system_prompt = "Your name is " + agent.name + ". " if agent.name else ""
    # _build_system_prompt returns None when both base prompt and KB context are
    # empty (KB-only mode with no retrieved context). Coerce to "" to avoid
    # `str + None` TypeError.
    system_prompt += _build_system_prompt(agent.system_prompt, kb_context) or ""

    if tools:
        # Use LangGraph ReAct agent with tools
        # Pass system prompt via state_modifier for correct placement
        graph = create_react_agent(llm, tools, prompt=system_prompt)

        async for event in graph.astream_events(
            {"messages": lc_messages},
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    # Anthropic models return content as list of dicts
                    if isinstance(content, list):
                        content = "".join(
                            c.get("text", "") for c in content if isinstance(c, dict)
                        )
                    if content:
                        yield AgentStreamEvent("token", content=content)

            elif kind == "on_chat_model_end":
                # Token usage lives on the final AIMessage's
                # usage_metadata (LangChain normalises this across
                # providers — keys: input_tokens, output_tokens,
                # total_tokens). Yield a usage event so the SSE
                # handler can write a usage_events row.
                usage = _extract_usage(event.get("data"))
                if usage is not None:
                    yield AgentStreamEvent(
                        "usage",
                        prompt_tokens=usage.get("input_tokens"),
                        completion_tokens=usage.get("output_tokens"),
                        total_tokens=usage.get("total_tokens"),
                        model_id=agent.model_id,
                    )

            elif kind == "on_tool_start":
                yield AgentStreamEvent(
                    "tool_start",
                    name=event["name"],
                    input=str(event["data"].get("input", ""))[:500],
                )

            elif kind == "on_tool_end":
                yield AgentStreamEvent(
                    "tool_end",
                    name=event["name"],
                    result=str(event["data"].get("output", ""))[:500],
                )
    else:
        # Simple streaming without tools
        pre_messages = []
        if system_prompt:
            pre_messages.append(SystemMessage(content=system_prompt))
        pre_messages.extend(lc_messages)

        # Track the final chunk so we can pull usage_metadata after
        # the stream completes (LangChain attaches it to the last
        # AIMessage chunk in the stream).
        final_chunk = None
        async for chunk in llm.astream(pre_messages):
            final_chunk = chunk
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    content = "".join(
                        c.get("text", "") for c in content if isinstance(c, dict)
                    )
                if content:
                    yield AgentStreamEvent("token", content=content)

        if final_chunk is not None:
            usage = _extract_usage({"output": final_chunk})
            if usage is not None:
                yield AgentStreamEvent(
                    "usage",
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    model_id=agent.model_id,
                )

    yield AgentStreamEvent("done")


def _extract_usage(data: object) -> dict | None:
    """Pull ``usage_metadata`` off the chat model's final output.

    LangChain stashes the dict on ``AIMessage.usage_metadata`` for
    every modern provider (OpenAI, Anthropic, Google, Mistral). The
    shape is normalised to ``{input_tokens, output_tokens, total_tokens}``
    regardless of provider — same keys we forward to usage_events.

    Some streaming providers also include it on the last chunk
    (.usage_metadata) — we accept both shapes.
    """
    if not isinstance(data, dict):
        return None
    candidate = data.get("output") or data.get("chunk")
    if candidate is None:
        return None
    usage = getattr(candidate, "usage_metadata", None)
    if isinstance(usage, dict) and (usage.get("input_tokens") or usage.get("output_tokens")):
        return usage
    return None
