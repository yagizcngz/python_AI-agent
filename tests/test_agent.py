"""
Test suite for Agent ReAct reasoning loop with mocked API completions.
"""

from pathlib import Path
from unittest.mock import MagicMock

from ai_agent.core.agent import Agent, AgentEvent, AgentEventType
from ai_agent.core.memory import ConversationMemory
from ai_agent.tools.base import ToolRegistry
from ai_agent.tools.filesystem import ReadTool, WriteTool


def make_mock_choice(content=None, tool_calls=None):
    choice = MagicMock()
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice.message = msg
    return choice


def test_agent_direct_answer(tmp_path: Path):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [make_mock_choice(content="Hello! How can I help you?")]
    mock_response.usage = MagicMock(prompt_tokens=15, completion_tokens=10)
    mock_client.chat.completions.create.return_value = mock_response

    tools = ToolRegistry([ReadTool(tmp_path), WriteTool(tmp_path)])
    agent = Agent(client=mock_client, model="test-model", tools=tools)

    events = []
    agent.event_handler = lambda e: events.append(e)

    answer = agent.run("Hello")
    assert answer == "Hello! How can I help you?"
    assert agent.memory.total_prompt_tokens == 15
    assert agent.memory.total_completion_tokens == 10

    # Ensure answer event was emitted
    answer_events = [e for e in events if e.event_type == AgentEventType.ANSWER]
    assert len(answer_events) == 1
    assert answer_events[0].data == "Hello! How can I help you?"


def test_agent_tool_calling_loop(tmp_path: Path):
    mock_client = MagicMock()

    # Step 1: Model calls Write tool
    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function.name = "Write"
    tool_call.function.arguments = '{"file_path": "greeting.txt", "content": "Hello file!"}'

    response_1 = MagicMock()
    response_1.choices = [make_mock_choice(content=None, tool_calls=[tool_call])]
    response_1.usage = MagicMock(prompt_tokens=20, completion_tokens=15)

    # Step 2: Model returns synthesized answer
    response_2 = MagicMock()
    response_2.choices = [make_mock_choice(content="I have created greeting.txt for you.")]
    response_2.usage = MagicMock(prompt_tokens=30, completion_tokens=10)

    mock_client.chat.completions.create.side_effect = [response_1, response_2]

    tools = ToolRegistry([ReadTool(tmp_path), WriteTool(tmp_path)])
    agent = Agent(client=mock_client, model="test-model", tools=tools)

    events = []
    agent.event_handler = lambda e: events.append(e)

    result = agent.run("Create greeting.txt with 'Hello file!'")
    assert result == "I have created greeting.txt for you."

    # Check file on disk
    created_file = tmp_path / "greeting.txt"
    assert created_file.exists()
    assert created_file.read_text(encoding="utf-8") == "Hello file!"

    # Verify event stream
    tool_calls = [e for e in events if e.event_type == AgentEventType.TOOL_CALL]
    assert len(tool_calls) == 1
    assert tool_calls[0].data["name"] == "Write"


def test_agent_max_steps_guard(tmp_path: Path):
    mock_client = MagicMock()

    # Model continuously requests tool calls
    tool_call = MagicMock()
    tool_call.id = "call_infinite"
    tool_call.function.name = "Read"
    tool_call.function.arguments = '{"file_path": "missing.txt"}'

    response = MagicMock()
    response.choices = [make_mock_choice(content=None, tool_calls=[tool_call])]
    response.usage = None
    mock_client.chat.completions.create.return_value = response

    tools = ToolRegistry([ReadTool(tmp_path)])
    agent = Agent(client=mock_client, model="test-model", tools=tools, max_steps=3)

    result = agent.run("Do infinite work")
    assert "Limit reached: Agent reached maximum steps (3)" in result
