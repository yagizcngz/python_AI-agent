"""
Sandboxed shell command execution with execution timeouts and safety bounds.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from ..config import DEFAULT_SHELL_TIMEOUT
from .base import BaseTool


def normalize_python_command(command: str) -> str:
    """
    Replace calls to python/python3/py with the active sys.executable,
    respecting command start or chaining operators (&&, ||, ;, |).
    """
    python_exe = f'"{sys.executable}"'
    pattern = r'(^|[;&|]\s*)(?:python3?|py)(?=\s|$)'
    return re.sub(pattern, lambda m: f'{m.group(1)}{python_exe}', command)


class BashTool(BaseTool):
    """Execute shell commands strictly anchored in the workspace directory."""

    name = "Bash"
    description = (
        "Execute a shell command within the workspace sandbox. "
        "Commands are executed using the local system shell with a strict timeout."
    )
    parameters = {
        "type": "object",
        "required": ["command"],
        "properties": {
            "command": {
                "type": "string",
                "description": "The command string to execute in the terminal.",
            }
        },
    }

    def __init__(self, workspace_dir: Path, timeout: int = DEFAULT_SHELL_TIMEOUT):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.timeout = timeout

    def execute(self, **kwargs) -> str:
        command = kwargs.get("command") or kwargs.get("cmd")
        if not command and kwargs:
            # Fallback if argument was passed as a single unnamed value
            command = list(kwargs.values())[0]

        if not command or not isinstance(command, str):
            return "Error: No command provided to execute."

        command = command.strip()
        command = normalize_python_command(command)

        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.workspace_dir),
                timeout=self.timeout,
                errors="replace",
            )
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            result_parts = []
            if process.returncode != 0:
                result_parts.append(f"[Exit code: {process.returncode}]")
            if stdout:
                result_parts.append(f"STDOUT:\n{stdout}")
            if stderr:
                result_parts.append(f"STDERR:\n{stderr}")
            if not stdout and not stderr:
                result_parts.append("Command completed with no output.")

            return "\n".join(result_parts)
        except subprocess.TimeoutExpired:
            return (
                f"Error: Command timed out after {self.timeout} seconds and was terminated. "
                "Ensure commands do not start interactive prompts or long-running daemons."
            )
        except Exception as e:
            return f"Error executing command: {type(e).__name__}: {e}"
