"""Fire-and-forget socket event emitter for workflow execution tracking.

Sends events via dispatcher → socket service. Non-blocking: failures are silently
ignored so workflow execution is never affected.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.platform.dispatcher_client import dispatcher

# Serialize emits so events arrive at the socket server in the order they were
# queued. Fire-and-forget tasks running concurrently can otherwise complete out
# of order, causing visual glitches (e.g. two nodes appearing "running" at once
# if the "completed" event for node A is overtaken by the "running" event for
# node B).
_emit_lock = asyncio.Lock()


async def _emit(room: str, event: str, payload: dict[str, Any]) -> None:
    """Internal: emit event via dispatcher. Swallows all errors."""
    async with _emit_lock:
        try:
            await dispatcher.call(
                "socket",
                "/emit/room",
                body={"room": room, "event": event, "payload": payload},
                timeout=5.0,
            )
        except Exception:
            pass  # Non-critical — never break workflow execution


def emit_to_room(room: str, event: str, payload: dict[str, Any]) -> None:
    """Fire-and-forget: emit event to a socket room.

    Creates a background task — does NOT block the caller. A module-level lock
    inside ``_emit`` serializes the actual dispatcher calls so delivery order
    matches enqueue order.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_emit(room, event, payload))
    except RuntimeError:
        pass  # No running loop — skip silently


# ─── Convenience helpers for workflow events ─────────────────────

def emit_node_running(
    workflow_id: str, node_id: str, node_type: str, label: str | None
) -> None:
    emit_to_room(
        room=f"workflow:{workflow_id}",
        event="node:running",
        payload={"nodeId": node_id, "nodeType": node_type, "label": label or ""},
    )


def emit_node_completed(
    workflow_id: str,
    node_id: str,
    node_type: str,
    label: str | None,
    output_items_count: int = 0,
    tokens_used: int = 0,
) -> None:
    emit_to_room(
        room=f"workflow:{workflow_id}",
        event="node:completed",
        payload={
            "nodeId": node_id,
            "nodeType": node_type,
            "label": label or "",
            "outputItemsCount": output_items_count,
            "tokensUsed": tokens_used,
        },
    )


def emit_node_failed(
    workflow_id: str, node_id: str, node_type: str, label: str | None, error: str
) -> None:
    emit_to_room(
        room=f"workflow:{workflow_id}",
        event="node:failed",
        payload={
            "nodeId": node_id,
            "nodeType": node_type,
            "label": label or "",
            "error": error,
        },
    )


def emit_workflow_completed(
    workflow_id: str, run_id: str, total_tokens: int = 0, output_items_count: int = 0
) -> None:
    emit_to_room(
        room=f"workflow:{workflow_id}",
        event="workflow:completed",
        payload={
            "runId": run_id,
            "totalTokens": total_tokens,
            "outputItemsCount": output_items_count,
        },
    )


def emit_workflow_failed(workflow_id: str, run_id: str, error: str) -> None:
    emit_to_room(
        room=f"workflow:{workflow_id}",
        event="workflow:failed",
        payload={"runId": run_id, "error": error},
    )
