"""
Base tool interfaces and registry for agent function calling.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ..config import MAX_TOOL_OUTPUT_CHARS


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with keyword arguments and return string result."""
        pass

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert the tool into OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def truncate_output(text: str, max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    """Truncate tool output if it exceeds max_chars to preserve context window."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    omitted = len(text) - max_chars
    return (
        f"{text[:half]}\n\n"
        f"[... {omitted} characters truncated to preserve context ...]\n\n"
        f"{text[-half:]}"
    )


class ToolRegistry:
    """Registry that holds tools and handles dispatching and argument parsing."""

    def __init__(self, tools: Optional[List[BaseTool]] = None):
        self._tools: Dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Return all registered tools formatted for OpenAI API."""
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def dispatch(self, name: str, arguments_str: str) -> str:
        """
        Safely parse JSON arguments and execute the matching tool.
        Returns error messages if tool not found or JSON parsing fails.
        """
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available tools: {list(self._tools.keys())}"

        # Safe JSON decoding
        try:
            if isinstance(arguments_str, dict):
                args = arguments_str
            elif isinstance(arguments_str, str) and arguments_str.strip():
                args = json.loads(arguments_str)
            else:
                args = {}
        except json.JSONDecodeError as e:
            return (
                f"Error: Malformed JSON arguments in call to '{name}': {e}. "
                "Please retry with valid JSON parameters."
            )

        try:
            result = tool.execute(**args)
            return truncate_output(str(result))
        except Exception as e:
            return f"Error executing {name}: {type(e).__name__}: {str(e)}"
