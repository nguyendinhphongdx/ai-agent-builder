"""Sample plugin entrypoint — Echo tool.

Reference shape for plugin authors. The actual loader/runner is
the future plugin daemon; for now this file is documentation in
executable form.

When the daemon ships, it will:
  1. Spawn a Python subprocess with ``main.py`` on argv.
  2. Communicate over stdio JSON-RPC: each ``tool.call`` request
     is dispatched to the matching ``handle_<tool_name>`` function.
  3. Enforce permissions (http_outbound, secrets) by sandboxing
     the subprocess via the existing code-sandbox service.
"""
from __future__ import annotations

from typing import Any


def handle_echo(params: dict[str, Any]) -> dict[str, Any]:
    """Return the input unchanged. Plugin tools are pure functions
    of their inputs — no global state, no async unless declared."""
    message = params.get("message", "")
    return {"message": message}


# Optional: a __main__ entry so authors can quickly test locally
# with ``python main.py``. The daemon will import the module,
# not exec it, so this block is only for manual smoke tests.
if __name__ == "__main__":
    import json
    import sys

    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    print(json.dumps(handle_echo(payload)))
