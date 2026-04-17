"""Sandboxed code execution with resource limits."""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

LANGUAGE_CONFIG = {
    "python": {"command": ["python3"], "ext": ".py"},
    "javascript": {"command": ["node"], "ext": ".js"},
    "bash": {"command": ["bash"], "ext": ".sh"},
}

SUPPORTED_LANGUAGES = set(LANGUAGE_CONFIG.keys())


async def execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30,
) -> dict:
    """Execute code in a subprocess with resource limits."""
    if language not in LANGUAGE_CONFIG:
        return {
            "output": "",
            "exit_code": 1,
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
            "execution_time_ms": 0,
        }

    lang_config = LANGUAGE_CONFIG[language]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=lang_config["ext"], delete=False, dir="/tmp"
    ) as f:
        f.write(code)
        tmp_path = f.name

    # Make readable by sandbox user
    os.chmod(tmp_path, 0o644)

    try:
        start = time.monotonic()

        cmd = [
            "su", "-s", "/bin/bash", "sandbox", "-c",
            f"ulimit -v 131072 -t {timeout} && {' '.join(lang_config['command'])} {tmp_path}"
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "output": "",
                "exit_code": -1,
                "error": f"Execution timed out after {timeout}s",
                "execution_time_ms": elapsed,
            }

        elapsed = int((time.monotonic() - start) * 1000)
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        return {
            "output": output[:10000],
            "exit_code": proc.returncode,
            "error": error[:5000] if error else None,
            "execution_time_ms": elapsed,
        }

    finally:
        os.unlink(tmp_path)
