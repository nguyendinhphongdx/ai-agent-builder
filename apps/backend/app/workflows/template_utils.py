"""Template rendering for workflow node configs.

Supports {{key}} and {{key.nested.path}} substitution.
"""

from __future__ import annotations

import re
from typing import Any


def render_template(template: str, data: dict[str, Any]) -> str:
    """Replace {{key}} and {{key.nested}} with values from data dict.

    Examples:
        >>> render_template("Hello {{name}}", {"name": "Alice"})
        'Hello Alice'
        >>> render_template("{{user.email}}", {"user": {"email": "a@b.com"}})
        'a@b.com'
    """
    if "{{" not in template:
        return template

    def replacer(match: re.Match) -> str:
        path = match.group(1).strip()
        value: Any = data
        for key in path.split("."):
            if isinstance(value, dict):
                value = value.get(key, "")
            else:
                return ""
        return str(value)

    return re.sub(r"\{\{(.+?)\}\}", replacer, template)
