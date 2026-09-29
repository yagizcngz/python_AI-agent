"""
Interactive Terminal User Interface (TUI) for Python AI Agent using Textual.
Clean Chat stream on left; responsive Tool Activity & Workspace Files on right.
"""

from pathlib import Path
from typing import Optional

from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.syntax import Syntax

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Tree,
)

from ..config import DEFAULT_MODEL, WORKSPACE_DIR
from ..core.agent import Agent, AgentEvent, AgentEventType
from ..core.client import create_client, fetch_account_usage
from ..core.memory import ConversationMemory
from ..tools.base import ToolRegistry
from ..tools.filesystem import EditTool, ListDirTool, ReadTool, WriteTool
from ..tools.shell import BashTool


class AgentTUIApp(App):
    """Textual Terminal User Interface for Python AI Agent."""

    TITLE = "Python AI Agent"
    SUB_TITLE = "Autonomous Multi-Tool Agent"
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #status-bar {
        height: 1;
        width: 100%;
        background: $panel;
        color: $text;
        padding: 0 1;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #chat-container {
        width: 52%;
        height: 100%;
        padding: 0 1;
    }

    #chat-log {
        height: 1fr;
        border: solid $accent;
        background: $background;
        padding: 1;
    }

    #input-bar {
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }

    #user-input {
        width: 1fr;
    }

    .action-btn {
        margin-left: 1;
        min-width: 8;
    }

    #sidebar {
        width: 48%;
        height: 100%;
        padding: 0 1;
    }

    #sidebar-toolbar {
        height: 1;
        layout: horizontal;
        margin-bottom: 0;
    }

    .tab-btn {
        height: 1;
        min-height: 1;
        border: none;
        padding: 0 1;
        margin-right: 1;
        background: $panel;
        color: $text-muted;
    }

    .tab-btn:hover {
        background: $accent;
        color: $text;
    }

    .tab-btn-active {
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #sidebar-content {
        height: 1fr;
    }

    #tool-box {
        height: 1fr;
        border: solid $accent;
        background: $background;
    }

    #files-box {
        height: 1fr;
        border: solid $secondary;
        background: $background;
    }

    #tool-log {
        height: 1fr;
        border: none;
        padding: 0 1;
    }

    #file-tree {
        height: 1fr;
        border: none;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "quit_app", "Quit"),
        ("ctrl+c", "quit_app", "Quit"),
        ("f2", "view_files", "Files"),
        ("f3", "view_tools", "Tools"),
        ("f4", "view_split", "Split"),
        ("f5", "refresh_files", "Refresh"),
        ("ctrl+r", "reset_chat", "Reset"),
    ]

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        workspace_dir: Optional[Path] = None,
        is_local: bool = False,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.workspace_dir = (workspace_dir or WORKSPACE_DIR).resolve()
        self.is_local = is_local
        self.base_url = base_url
        self.api_key = api_key

        self.current_step = 0
        self.current_status = "IDLE"
        self.daily_limits_text = "Requests: Loading..."
        self.current_view_mode = "files"

        # Initialize Agent components
        self.client = create_client(
            api_key=self.api_key,
            base_url=self.base_url,
            is_local=self.is_local,
        )
        self.memory = ConversationMemory()
        self.tools = ToolRegistry([
            ReadTool(self.workspace_dir),
            WriteTool(self.workspace_dir),
            EditTool(self.workspace_dir),
            ListDirTool(self.workspace_dir),
            BashTool(self.workspace_dir),
        ])
        self.agent = Agent(
            client=self.client,
            model=self.model,
            tools=self.tools,
            memory=self.memory,
            event_handler=self.on_agent_event,
        )
        self.is_busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("", id="status-bar")
        with Horizontal(id="main-container"):
            # Left: Clean Conversation Screen & Input Bar
            with Vertical(id="chat-container"):
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Type a goal or prompt (e.g. 'Create a script calculate.py')...",
                        id="user-input",
                    )
                    yield Button("Send", variant="primary", id="send-btn", classes="action-btn")
                    yield Button("Reset", variant="default", id="reset-btn", classes="action-btn")
                    yield Button("Quit", variant="error", id="quit-btn", classes="action-btn")

            # Right: Compact Toolbar + Resizable Panels
            with Vertical(id="sidebar"):
                with Horizontal(id="sidebar-toolbar"):
                    yield Button("Files (F2)", id="btn-view-files", classes="tab-btn tab-btn-active")
                    yield Button("Tools (F3)", id="btn-view-tools", classes="tab-btn")
                    yield Button("Split (F4)", id="btn-view-split", classes="tab-btn")
                    yield Button("Refresh (F5)", id="btn-refresh-files", classes="tab-btn")

                with Vertical(id="sidebar-content"):
                    with Vertical(id="files-box") as fb:
                        fb.border_title = f"Workspace: {self.workspace_dir.name}"
                        yield Tree("Root", id="file-tree")
                    with Vertical(id="tool-box") as tb:
                        tb.border_title = "Tool Activity"
                        yield RichLog(id="tool-log", highlight=True, markup=True, wrap=True)

        yield Footer()

    def on_mount(self) -> None:
        """Called when UI starts up."""
        chat_log = self.query_one("#chat-log", RichLog)
        tool_log = self.query_one("#tool-log", RichLog)

        chat_log.write(
            Panel(
                f"[bold cyan]Welcome to Python AI Agent[/bold cyan]\n"
                f"• Workspace: [bold]{self.workspace_dir}[/bold]\n"
                f"• Active Model: [bold green]{self.model}[/bold green]\n"
                f"• Type your task below and click [bold]Send[/bold].\n"
                f"• Tool executions and shell logs will display on the right panel.",
                title="Agent Ready",
                border_style="cyan",
            )
        )
        tool_log.write(
            Panel(
                "Tool invocations (Bash commands, file reads/writes, edits) will appear here in real-time.",
                title="Tool Activity Log",
                border_style="dim",
            )
        )

        self.populate_file_tree()
        self.update_telemetry()
        self.refresh_account_limits()

        # In small terminal mode, start in files mode so files are 100% visible
        if self.size.height < 18:
            self.set_view_mode("files")
        else:
            self.set_view_mode("split")

        self.query_one("#user-input", Input).focus()

    def set_view_mode(self, mode: str) -> None:
        """Switch right panel view between 'files', 'tools', and 'split'."""
        self.current_view_mode = mode
        files_box = self.query_one("#files-box", Vertical)
        tool_box = self.query_one("#tool-box", Vertical)

        btn_files = self.query_one("#btn-view-files", Button)
        btn_tools = self.query_one("#btn-view-tools", Button)
        btn_split = self.query_one("#btn-view-split", Button)

        btn_files.remove_class("tab-btn-active")
        btn_tools.remove_class("tab-btn-active")
        btn_split.remove_class("tab-btn-active")

        if mode == "files":
            files_box.display = True
            tool_box.display = False
            btn_files.add_class("tab-btn-active")
        elif mode == "tools":
            files_box.display = False
            tool_box.display = True
            btn_tools.add_class("tab-btn-active")
        elif mode == "split":
            files_box.display = True
            tool_box.display = True
            btn_split.add_class("tab-btn-active")

    def action_view_files(self) -> None:
        """Switch to Workspace Files view."""
        self.set_view_mode("files")

    def action_view_tools(self) -> None:
        """Switch to Tool Activity view."""
        self.set_view_mode("tools")

    def action_view_split(self) -> None:
        """Switch to Split view."""
        self.set_view_mode("split")

    def action_refresh_files(self) -> None:
        """Manually trigger workspace file tree refresh."""
        self.populate_file_tree()
        self.notify("Workspace files refreshed", title="Files")

    def action_reset_chat(self) -> None:
        """Reset conversation context."""
        self.memory.reset()
        self.query_one("#chat-log", RichLog).write("[italic cyan]-- Conversation context reset --[/italic cyan]")
        self.query_one("#tool-log", RichLog).write("[italic cyan]-- Tool activity reset --[/italic cyan]")
        self.current_step = 0
        self.update_telemetry()

    def action_quit_app(self) -> None:
        """Exit the application."""
        self.exit()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Toggle directory expansion on click or selection."""
        event.node.toggle()

    def populate_file_tree(self) -> None:
        """Populate the sidebar workspace file tree."""
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        tree.root.label = f"[{self.workspace_dir.name}]"
        tree.root.expand()

        ignore_names = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".idea", ".vscode"}

        def add_nodes(parent_node, directory: Path, depth: int = 0):
            if depth > 2:
                return
            try:
                entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for entry in entries:
                    if entry.name in ignore_names:
                        continue
                    if entry.is_dir():
                        branch = parent_node.add(f"[DIR] {entry.name}", expand=False)
                        add_nodes(branch, entry, depth + 1)
                    else:
                        parent_node.add_leaf(entry.name)
            except Exception:
                pass

        add_nodes(tree.root, self.workspace_dir)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            self.submit_prompt()
        elif event.button.id == "reset-btn":
            self.action_reset_chat()
        elif event.button.id == "quit-btn":
            self.action_quit_app()
        elif event.button.id == "btn-view-files":
            self.action_view_files()
        elif event.button.id == "btn-view-tools":
            self.action_view_tools()
        elif event.button.id == "btn-view-split":
            self.action_view_split()
        elif event.button.id == "btn-refresh-files":
            self.action_refresh_files()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "user-input":
            self.submit_prompt()

    def submit_prompt(self) -> None:
        """Read input and trigger asynchronous agent worker."""
        if self.is_busy:
            return

        input_widget = self.query_one("#user-input", Input)
        prompt = input_widget.value.strip()
        if not prompt:
            return

        input_widget.value = ""
        chat_log = self.query_one("#chat-log", RichLog)

        # Log User prompt in the clean chat area
        chat_log.write(
            Panel(
                prompt,
                title="[bold yellow]User[/bold yellow]",
                border_style="yellow",
            )
        )

        self.is_busy = True
        self.current_step = 0
        self.current_status = "THINKING"
        self.update_telemetry()
        self.run_agent_task(prompt)

    @work(thread=True)
    def run_agent_task(self, prompt: str) -> None:
        """Execute agent task in worker thread."""
        try:
            self.agent.run(prompt)
        except Exception as e:
            self.call_from_thread(self._handle_error, str(e))
        finally:
            self.call_from_thread(self._finish_task)

    def _handle_error(self, err_text: str) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[bold red]Error: {err_text}[/bold red]")

    def _finish_task(self) -> None:
        self.is_busy = False
        self.current_status = "IDLE"
        self.populate_file_tree()
        self.update_telemetry()
        self.refresh_account_limits()
        self.query_one("#user-input", Input).focus()

    def update_telemetry(self, status_text: Optional[str] = None) -> None:
        """Refresh single-line top status bar."""
        try:
            status = status_text or self.current_status
            if "RUNNING" in status:
                st_color = "cyan"
            elif "THINKING" in status:
                st_color = "yellow"
            else:
                st_color = "green"

            tokens_str = f"{self.memory.total_prompt_tokens:,}p / {self.memory.total_completion_tokens:,}c"
            bar_text = (
                f"Status: [bold {st_color}]{status}[/bold {st_color}] | "
                f"Model: [bold cyan]{self.model}[/bold cyan] | "
                f"{self.daily_limits_text} | "
                f"Tokens: {tokens_str} | "
                f"Step: {self.current_step}/{self.agent.max_steps}"
            )
            self.query_one("#status-bar", Label).update(bar_text)
        except Exception:
            pass

    @work(thread=True)
    def refresh_account_limits(self) -> None:
        """Fetch live remaining limits in background thread."""
        usage = fetch_account_usage(self.api_key)
        if not usage:
            return
        daily = usage.get("free_model_daily_requests")
        if daily:
            rem = daily.get("remaining", 0)
            lim = daily.get("limit", 0)
            used = daily.get("used", 0)
            self.daily_limits_text = f"Requests: [bold green]{rem}/{lim} left[/bold green] ({used} used)"
        elif usage.get("limit_remaining") is not None:
            self.daily_limits_text = f"Credits: [bold green]${usage.get('limit_remaining'):.4f}[/bold green]"
        else:
            self.daily_limits_text = "Plan: [bold green]Free Tier[/bold green]"
        self.call_from_thread(self.update_telemetry)

    def on_agent_event(self, event: AgentEvent) -> None:
        """Thread-safe event dispatcher from Agent."""
        self.call_from_thread(self._render_agent_event, event)

    def _render_agent_event(self, event: AgentEvent) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        tool_log = self.query_one("#tool-log", RichLog)

        if event.event_type == AgentEventType.STEP:
            self.current_step = event.step
            self.update_telemetry()

        elif event.event_type == AgentEventType.THINKING:
            self.current_status = "THINKING"
            self.update_telemetry()
            tool_log.write(f"[dim italic]--- Step {event.step}: Thinking... ---[/dim italic]")

        elif event.event_type == AgentEventType.TOOL_CALL:
            data = event.data
            fn_name = data.get("name", "Tool")
            fn_args = data.get("arguments", "{}")

            self.current_status = f"RUNNING: {fn_name}"
            self.update_telemetry()

            # Ensure tool activity is visible while tool is running
            if self.current_view_mode == "files" and self.size.height >= 18:
                self.set_view_mode("split")
            elif self.current_view_mode == "files":
                self.set_view_mode("tools")

            # Route tool calls exclusively to the dedicated Tool Activity panel
            tool_log.write(
                Panel(
                    Syntax(fn_args, "json", theme="monokai", word_wrap=True),
                    title=f"[bold green][Tool Call] {fn_name}[/bold green]",
                    border_style="green",
                )
            )

        elif event.event_type == AgentEventType.TOOL_RESULT:
            data = event.data
            fn_name = data.get("name", "Tool")
            res = data.get("result", "")
            preview = res if len(res) < 2000 else res[:2000] + "\n... [preview clipped]"

            # Route tool outputs exclusively to the dedicated Tool Activity panel
            tool_log.write(
                Panel(
                    preview,
                    title=f"[bold blue][Tool Output] {fn_name}[/bold blue]",
                    border_style="blue",
                )
            )

        elif event.event_type == AgentEventType.ANSWER:
            # Pure assistant final response appears cleanly in the chat log on the left
            chat_log.write(
                Panel(
                    RichMarkdown(event.data),
                    title="[bold magenta]Agent Answer[/bold magenta]",
                    border_style="magenta",
                )
            )
            self.update_telemetry()

        elif event.event_type == AgentEventType.ERROR:
            err_data = event.data
            err_msg = err_data.get("error") if isinstance(err_data, dict) else str(err_data)
            chat_log.write(
                Panel(
                    f"[bold red]{err_msg}[/bold red]",
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                )
            )


def run_tui(
    model: str = DEFAULT_MODEL,
    workspace_dir: Optional[Path] = None,
    is_local: bool = False,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> None:
    """Launch the Textual TUI Application."""
    app = AgentTUIApp(
        model=model,
        workspace_dir=workspace_dir,
        is_local=is_local,
        base_url=base_url,
        api_key=api_key,
    )
    app.run()
