"""Loop node — array fan-out (P3.6.2 first slice).

Semantics: each input item that contains an array at
``config.items_path`` (default ``"items"``) is exploded into N
output items — one per array element — with the chosen path
replaced by the single element plus a ``_loop`` envelope:

    { ..., "_loop": { "index": 0, "total": 3, "truncated": false } }

Downstream nodes then execute once per element. This gives users
the fan-out behaviour without the runner-level "loop body
subgraph" feature (which is a larger refactor; future iteration).

Inputs that don't contain the path or whose path isn't an array
pass through unchanged. ``max_items`` caps the explosion so a
runaway array can't blow up the run.
"""
from __future__ import annotations

from typing import Any

from ..base import ExecutionContext, NodeExecutor, NodeResult


def _resolve(obj: Any, path: str) -> Any:
    """Dot-path lookup tolerating dict + list-by-index."""
    cursor = obj
    for part in path.split("."):
        if cursor is None:
            return None
        if isinstance(cursor, dict):
            cursor = cursor.get(part)
        elif isinstance(cursor, list):
            try:
                cursor = cursor[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cursor


def _set_path(obj: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor: Any = obj
    for p in parts[:-1]:
        nxt = cursor.get(p) if isinstance(cursor, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[p] = nxt
        cursor = nxt
    if isinstance(cursor, dict):
        cursor[parts[-1]] = value


class LoopExecutor(NodeExecutor):
    """Array fan-out: explode one input into N outputs."""

    async def execute(
        self,
        items: list[dict[str, Any]],
        config: dict[str, Any],
        ctx: ExecutionContext,
    ) -> NodeResult:
        items_path = str(config.get("items_path", "items"))
        max_items = int(config.get("max_items", 1000))
        keep_parent = bool(config.get("keep_parent", True))

        out: list[dict[str, Any]] = []
        for parent in items:
            collection = _resolve(parent, items_path)
            if not isinstance(collection, list):
                out.append(parent)
                continue
            total = len(collection)
            for idx, element in enumerate(collection[:max_items]):
                base = dict(parent) if keep_parent else {}
                _set_path(base, items_path, element)
                base["_loop"] = {
                    "index": idx,
                    "total": min(total, max_items),
                    "truncated": total > max_items,
                }
                out.append(base)
        return NodeResult(items=out)
