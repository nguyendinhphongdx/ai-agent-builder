from __future__ import annotations

from typing import Any

from ..base import ExecutionContext, NodeExecutor, NodeResult


class KnowledgeRetrievalExecutor(NodeExecutor):
    """Stub executor for vector-store knowledge base search.

    TODO: implement pgvector similarity search via knowledge_bases/documents tables.
    """

    async def execute(self, items: list[dict[str, Any]], config: dict[str, Any], ctx: ExecutionContext) -> NodeResult:
        return NodeResult(items=items)
