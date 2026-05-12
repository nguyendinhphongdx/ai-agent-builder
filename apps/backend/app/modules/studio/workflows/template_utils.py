"""Legacy template renderer — preserved as a thin shim over `expression.py`.

New code should call ``evaluate_template`` directly with a richer context
(items, vars, upstream). This shim only knows about the current item, which
matches the original ``render_template(template, data)`` contract.
"""

from __future__ import annotations

from typing import Any

from app.modules.studio.workflows.expression import evaluate_template


def render_template(template: str, data: dict[str, Any]) -> str:
    """Backward-compatible single-dict template render.

    Equivalent to ``evaluate_template(template, item=data)`` but always
    coerces the result to ``str`` (the legacy callers expected strings).
    """
    result = evaluate_template(template, item=data, items=[data] if data else [])
    if result is None:
        return ""
    return result if isinstance(result, str) else str(result)
