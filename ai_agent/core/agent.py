"""
Agent reasoning loop (ReAct pattern) with step guards and event emission.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from openai import OpenAI

from ..config import DEFAULT_MAX_STEPS
from ..tools.base import ToolRegistry
from .client import get_model_suggestions
from .memory import ConversationMemory


class AgentEventType(str, Enum):
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ANSWER = "answer"
    ERROR = "error"
    STEP = "step"


@dataclass
class AgentEvent:
    event_type: AgentEventType
    step: int
    data: Any


class Agent:
    """Autonomous agent engine executing the ReAct (Reason-Act-Observe) loop."""

    def __init__(
        self,
        client: OpenAI,
        model: str,
        tools: ToolRegistry,
        memory: Optional[ConversationMemory] = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        event_handler: Optional[Callable[[AgentEvent], None]] = None,
    ):
        self.client = client
        self.model = model
        self.tools = tools
        self.memory = memory or ConversationMemory()
        self.max_steps = max_steps
        self.event_handler = event_handler
        self.current_step = 0

    def _emit(self, event_type: AgentEventType, data: Any) -> None:
        """Emit an event if a handler is registered."""
        if self.event_handler:
            try:
                self.event_handler(AgentEvent(event_type=event_type, step=self.current_step, data=data))
            except Exception:
                pass

    def run(self, prompt: str) -> str:
        """
        Execute an autonomous task to completion.
        Maintains memory across multiple turns if run repeatedly.
        """
        self.memory.add_user_message(prompt)
        self.current_step = 0
        openai_tools = self.tools.get_openai_tools()

        while True:
            self.current_step += 1
            if self.current_step > self.max_steps:
                msg = f"Limit reached: Agent reached maximum steps ({self.max_steps}). Stopping loop."
                self._emit(AgentEventType.ERROR, msg)
                return msg

            self._emit(AgentEventType.STEP, self.current_step)
            self._emit(AgentEventType.THINKING, f"Consulting model '{self.model}'...")

            try:
                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.memory.get_messages(),
                    tools=openai_tools if openai_tools else None,
                )
            except Exception as e:
                err_msg = f"API Connection error with model '{self.model}': {e}"
                self._emit(AgentEventType.ERROR, {
                    "error": err_msg,
                    "suggestions": get_model_suggestions(self.model),
                })
                return err_msg

            if not chat.choices:
                err_msg = f"Error: Received empty response from model '{self.model}'."
                self._emit(AgentEventType.ERROR, {
                    "error": err_msg,
                    "suggestions": get_model_suggestions(self.model),
                })
                return err_msg

            # Record token usage
            if hasattr(chat, "usage") and chat.usage:
                self.memory.record_usage(
                    prompt_tokens=getattr(chat.usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(chat.usage, "completion_tokens", 0) or 0,
                )

            choice = chat.choices[0]
            message = choice.message

            # Save assistant message to memory
            self.memory.add_assistant_message(
                content=message.content,
                tool_calls=message.tool_calls,
            )

            # Check for tool execution requests
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = tool_call.function.arguments

                    self._emit(AgentEventType.TOOL_CALL, {
                        "id": tool_call.id,
                        "name": fn_name,
                        "arguments": fn_args,
                    })

                    # Dispatch through tool registry
                    result = self.tools.dispatch(fn_name, fn_args)

                    self._emit(AgentEventType.TOOL_RESULT, {
                        "id": tool_call.id,
                        "name": fn_name,
                        "result": result,
                    })

                    self.memory.add_tool_result(tool_call.id, result)
            else:
                # Agent completed reasoning and returned final text response
                final_answer = message.content or ""
                self._emit(AgentEventType.ANSWER, final_answer)
                return final_answer
