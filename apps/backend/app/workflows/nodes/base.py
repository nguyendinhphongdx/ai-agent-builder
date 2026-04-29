"""Base classes for workflow node executors.

Every node executor inherits NodeExecutor and implements execute().
Executors are pure: receive items, return items. No state mutation, no graph awareness.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


# ─── Execution Context ────────────────────────────────────────────

@dataclass
class ExecutionContext:
    """Context passed to every node executor."""

    node_id: str
    node_type: str
    label: str | None
    db: AsyncSession
    variables: dict[str, Any] = field(default_factory=dict)
    initial_input: dict[str, Any] = field(default_factory=dict)
    # Output items of upstream nodes, keyed by label (preferred) or node_id.
    # Lets executors render `{{ nodes["LLM"].text }}` without re-walking the graph.
    upstream_outputs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


# ─── Node Result ──────────────────────────────────────────────────

@dataclass
class NodeResult:
    """Result returned by a node executor.

    - items: output data items (default output)
    - route: for condition/switch — which output handle to follow (e.g. "true", "case_0")
    - outputs: for multi-output nodes (filter) — {handle: items} per branch
    - tokens_used: LLM token consumption
    """

    items: list[dict[str, Any]]
    route: str | None = None
    outputs: dict[str, list[dict[str, Any]]] | None = None
    tokens_used: int = 0


# ─── Node Executor (abstract base) ───────────────────────────────

class NodeExecutor(ABC):
    """Abstract base class for all node executors."""

    @abstractmethod
    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        """Execute the node logic.

        Args:
            items: Input data items from previous node(s)
            config: Node configuration from the editor (JSONB)
            ctx: Execution context (db session, variables, metadata)

        Returns:
            NodeResult with output items and optional routing info
        """
        ...


# ─── Node Execution Record ───────────────────────────────────────

@dataclass
class NodeExecution:
    """Complete execution record for one node (stored in WorkflowRun)."""

    node_id: str
    node_type: str
    label: str | None
    status: str  # "completed" | "failed" | "skipped"
    input_items: list[dict[str, Any]]
    output_items: list[dict[str, Any]]
    error: str | None = None
    tokens_used: int = 0
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "status": self.status,
            "input_items": self.input_items,
            "output_items": self.output_items,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ─── Run Result ───────────────────────────────────────────────────

@dataclass
class RunResult:
    """Final result of a workflow execution."""

    status: str  # "completed" | "failed"
    output: Any
    node_executions: list[NodeExecution]
    total_tokens: int = 0
    error: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)


# ─── Helpers ──────────────────────────────────────────────────────

def now_iso() -> str:
    """Current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()
