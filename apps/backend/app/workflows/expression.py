"""Expression evaluator for workflow node templates.

Replaces the legacy ``render_template`` (single-dict ``{{key.path}}`` lookup)
with a sandboxed Python expression evaluator.

Available names inside ``{{ ... }}``:

- ``json`` / ``item``  — current input item (dict; supports ``.attr`` access)
- ``items``            — full list of input items
- ``nodes``            — dict mapping upstream node label/id → list of output items
- ``vars``             — workflow variables dict

For backward compatibility, the *top-level keys* of the current item are also
exposed as bare names — so ``{{ name }}`` keeps resolving as ``{{ json.name }}``
on existing workflows. Newer workflows should prefer the explicit form.

A template made up of *exactly one* ``{{ expr }}`` block returns the raw value
(preserving int/list/dict types). Mixed templates return a string.
"""

from __future__ import annotations

import re
from typing import Any

from simpleeval import (
    AttributeDoesNotExist,
    EvalWithCompoundTypes,
    InvalidExpression,
    NameNotDefined,
)


_EXPR_RE = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)
# Pure expression = exactly one {{ ... }} block with only whitespace around it.
# The negative lookahead inside prevents matching across multiple blocks
# (regex lazy backtracking would otherwise expand to span them).
_PURE_EXPR_RE = re.compile(r"^\s*\{\{((?:(?!\}\}).)+?)\}\}\s*$", re.DOTALL)


# Functions exposed to expressions. simpleeval's defaults are conservative;
# add only safe stdlib helpers that template authors actually need.
_SAFE_FUNCTIONS: dict[str, Any] = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "sorted": sorted,
}


class _AttrDict(dict):
    """Dict subclass that allows ``obj.key`` in addition to ``obj["key"]``.

    Required because simpleeval evaluates Python expressions, and Python dicts
    don't natively support attribute access. We wrap every dict before exposing
    it to the evaluator so templates can use the JS-flavor dot syntax users
    expect from n8n.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _wrap(value: Any) -> Any:
    """Recursively wrap dicts so their values support ``.attr`` access."""
    if isinstance(value, dict):
        return _AttrDict({k: _wrap(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_wrap(v) for v in value]
    return value


def _build_names(
    item: dict[str, Any] | None,
    items: list[dict[str, Any]],
    variables: dict[str, Any],
    upstream: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    item = item or {}
    wrapped_item = _wrap(item)
    backcompat: dict[str, Any] = {}
    for key, value in item.items():
        if isinstance(key, str) and key.isidentifier():
            backcompat[key] = _wrap(value)

    # Legacy bare-key access first, then canonical names — so an item with a
    # field literally called `nodes` or `json` doesn't shadow the new API.
    return {
        **backcompat,
        "json": wrapped_item,
        "item": wrapped_item,
        "items": [_wrap(i) for i in items],
        "nodes": {k: [_wrap(i) for i in v] for k, v in upstream.items()},
        "vars": _wrap(variables),
    }


def evaluate_expression(
    expr: str,
    *,
    item: dict[str, Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    variables: dict[str, Any] | None = None,
    upstream: dict[str, list[dict[str, Any]]] | None = None,
) -> Any:
    """Evaluate a single expression (no ``{{ }}`` wrapping) and return raw value.

    Returns ``None`` for missing names/attributes so templates degrade
    gracefully instead of raising. Syntax errors still propagate.
    """
    names = _build_names(item, items or [], variables or {}, upstream or {})
    evaluator = EvalWithCompoundTypes(names=names, functions=_SAFE_FUNCTIONS)
    try:
        return evaluator.eval(expr.strip())
    except (NameNotDefined, AttributeDoesNotExist, KeyError, IndexError):
        return None


def evaluate_template(
    template: str,
    *,
    item: dict[str, Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    variables: dict[str, Any] | None = None,
    upstream: dict[str, list[dict[str, Any]]] | None = None,
) -> Any:
    """Render a template containing zero or more ``{{ expr }}`` blocks.

    - No ``{{`` in the template → return as-is (cheap path).
    - Single ``{{ expr }}`` and nothing else → return raw value (preserves type).
    - Multiple blocks or mixed text → return rendered string.
    """
    if not template or "{{" not in template:
        return template

    items = items or ([item] if item else [])

    pure = _PURE_EXPR_RE.match(template)
    if pure:
        return evaluate_expression(
            pure.group(1),
            item=item,
            items=items,
            variables=variables,
            upstream=upstream,
        )

    def _replace(match: re.Match[str]) -> str:
        result = evaluate_expression(
            match.group(1),
            item=item,
            items=items,
            variables=variables,
            upstream=upstream,
        )
        return "" if result is None else str(result)

    return _EXPR_RE.sub(_replace, template)


__all__ = ["evaluate_expression", "evaluate_template", "InvalidExpression"]
