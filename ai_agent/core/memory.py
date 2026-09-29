"""
Conversation memory and context management for the AI Agent.
"""

import platform
from typing import Any, Dict, List, Optional


def build_default_system_prompt() -> str:
    """Dynamically build system instructions aware of current host OS and available tools."""
    os_name = platform.system()
    if os_name == "Windows":
        os_guidance = (
            "The host machine runs Windows. When using the Bash tool, use Windows-compatible commands "
            "(e.g., use 'dir' instead of 'ls', and 'mkdir' without '-p')."
        )
    elif os_name == "Darwin":
        os_guidance = "The host machine runs macOS (Darwin). Standard Unix/POSIX commands are supported."
    else:
        os_guidance = "The host machine runs Linux. Standard Unix/POSIX commands are supported."

    return (
        "You are an autonomous AI programming and task assistant.\n"
        f"{os_guidance}\n"
        "Guidelines:\n"
        "1. Prefer native tools (Read, Write, Edit, ListDir) over shell commands whenever possible for file operations.\n"
        "2. When modifying existing files, prefer the Edit tool to change specific blocks rather than rewriting entire files.\n"
        "3. Provide clean, concise answers and confirm when tasks have been completed.\n"
        "4. Work iteratively: inspect files first, plan changes, apply them, and verify results.\n"
        "5. Do NOT use any emojis in your responses or outputs. Keep all text plain, clear, and professional."
    )


class ConversationMemory:
    """Manages chat messages history and token metrics."""

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt or build_default_system_prompt()
        self.messages: List[Dict[str, Any]] = []
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.reset()

    def reset(self, new_system_prompt: Optional[str] = None) -> None:
        """Reset conversation history while retaining or updating system prompt."""
        if new_system_prompt:
            self.system_prompt = new_system_prompt
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def add_user_message(self, content: str) -> None:
        """Add a user message to history."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Any]] = None,
    ) -> None:
        """Add assistant response or tool call request to history."""
        msg: Dict[str, Any] = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ]
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Add a tool execution result to history."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def record_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        """Record token usage metrics from an API response."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

    def get_messages(self) -> List[Dict[str, Any]]:
        """Return full conversation message history."""
        return list(self.messages)
