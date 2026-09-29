"""
Interactive Terminal User Interface (TUI) for Python AI Agent using Textual.
Clean Chat stream on left; responsive Tool Activity & Workspace Files on right.
Includes on-the-fly Model Switcher (Alt+M), File Previewer with X close button,
Confirm Quit modal, full-screen Chat expand/restore toggling, and Command Palette (Alt+P).
"""

from pathlib import Path
from typing import Optional

from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.syntax import Syntax

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    RichLog,
    Tree,
)

from ..config import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_MODEL,
    RECOMMENDED_FREE_MODELS,
    WORKSPACE_DIR,
)
from ..core.agent import Agent, AgentEvent, AgentEventType
from ..core.client import create_client, fetch_account_usage
from ..core.memory import ConversationMemory
from ..tools.base import ToolRegistry
from ..tools.filesystem import EditTool, ListDirTool, ReadTool, WriteTool
from ..tools.shell import BashTool


def detect_language(path: Path) -> str:
    """Detect syntax highlighting language based on file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".md": "markdown",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".bat": "batch",
        ".ps1": "powershell",
        ".txt": "text",
        ".env": "text",
        ".gitignore": "text",
    }
    return ext_map.get(path.suffix.lower(), "text")


class ConfirmQuitModal(ModalScreen[bool]):
    """Modal dialog prompting user for confirmation before quitting."""

    CSS = """
    ConfirmQuitModal {
        align: center middle;
    }

    #confirm-quit-dialog {
        width: 52;
        height: auto;
        border: solid $error;
        background: $panel;
        padding: 1;
    }

    #confirm-quit-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #confirm-quit-btn-bar {
        height: auto;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
    }

    .confirm-btn {
        margin-left: 1;
        min-width: 12;
    }

    /* Prevent white background rectangle on focused buttons */
    .confirm-btn:focus {
        text-style: bold;
    }

    #btn-confirm-quit {
        background: #991b1b;
        color: #ffffff;
    }

    #btn-confirm-quit:focus {
        background: #dc2626;
        color: #ffffff;
        text-style: bold;
        border: tall #fca5a5;
    }

    #btn-cancel-quit {
        background: #374151;
        color: #ffffff;
    }

    #btn-cancel-quit:focus {
        background: #2563eb;
        color: #ffffff;
        text-style: bold;
        border: tall #93c5fd;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-quit-dialog"):
            yield Label("Confirm Exit", id="confirm-quit-title")
            yield Label("Are you sure you want to quit Python AI Agent?")
            with Horizontal(id="confirm-quit-btn-bar"):
                yield Button("Yes, Quit", variant="error", id="btn-confirm-quit", classes="confirm-btn")
                yield Button("Cancel", variant="default", id="btn-cancel-quit", classes="confirm-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-quit":
            self.dismiss(True)
        elif event.button.id == "btn-cancel-quit":
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ModelSelectModal(ModalScreen[Optional[dict]]):
    """Modal dialog allowing user to choose or input an AI model."""

    CSS = """
    ModelSelectModal {
        align: center middle;
    }

    #model-dialog {
        width: 76%;
        max-width: 86;
        height: auto;
        max-height: 85%;
        border: solid $accent;
        background: $panel;
        padding: 1;
    }

    #model-dialog-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #model-options {
        height: 8;
        border: solid $secondary;
        margin-bottom: 1;
    }

    #custom-model-input {
        margin-bottom: 1;
    }

    #model-btn-bar {
        height: auto;
        layout: horizontal;
        align: right middle;
    }

    .modal-btn {
        margin-left: 1;
    }

    .modal-btn:focus {
        text-style: bold;
        border: tall $accent;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_model: str, **kwargs):
        super().__init__(**kwargs)
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        with Vertical(id="model-dialog"):
            yield Label("Select Active AI Model", id="model-dialog-title")
            yield Label("Choose a recommended model or type a custom model ID below:")

            options = []
            for m in RECOMMENDED_FREE_MODELS:
                badge = "(Active)" if m == self.current_model else "(Free)"
                options.append(f"{m} {badge}")
            options.append("qwen2.5-coder:1.5b (Local Ollama)")
            options.append("llama3.2:1b (Local Ollama)")

            yield OptionList(*options, id="model-options")
            yield Input(
                placeholder="Or type custom model (e.g. meta-llama/llama-3.3-70b-instruct:free)...",
                id="custom-model-input",
            )
            with Horizontal(id="model-btn-bar"):
                yield Button("Select", variant="primary", id="btn-confirm-model", classes="modal-btn")
                yield Button("Cancel", variant="default", id="btn-cancel-model", classes="modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-model":
            self.confirm_selection()
        elif event.button.id == "btn-cancel-model":
            self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.confirm_selection()

    def confirm_selection(self) -> None:
        custom_val = self.query_one("#custom-model-input", Input).value.strip()
        if custom_val:
            if custom_val.startswith("ollama/"):
                res = {
                    "model": custom_val[7:],
                    "is_local": True,
                    "base_url": DEFAULT_LOCAL_BASE_URL,
                }
            else:
                res = {
                    "model": custom_val,
                    "is_local": False,
                    "base_url": None,
                }
            self.dismiss(res)
            return

        opt_list = self.query_one("#model-options", OptionList)
        if opt_list.highlighted is not None:
            prompt_opt = str(opt_list.get_option_at_index(opt_list.highlighted).prompt)
            model_id = prompt_opt.split(" ")[0]
            if "(Local Ollama)" in prompt_opt:
                res = {
                    "model": model_id,
                    "is_local": True,
                    "base_url": DEFAULT_LOCAL_BASE_URL,
                }
            else:
                res = {
                    "model": model_id,
                    "is_local": False,
                    "base_url": None,
                }
            self.dismiss(res)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class FilePreviewModal(ModalScreen[None]):
    """Modal dialog displaying syntax-highlighted code preview of a workspace file."""

    CSS = """
    FilePreviewModal {
        align: center middle;
    }

    #preview-dialog {
        width: 88%;
        height: 88%;
        border: solid $accent;
        background: $panel;
        padding: 1;
    }

    #preview-header {
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }

    #preview-title {
        width: 1fr;
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: $accent;
    }

    #btn-close-preview {
        width: 5;
        min-width: 5;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: #dc2626;
        color: #ffffff;
    }

    #btn-close-preview:focus {
        background: #ef4444;
        text-style: bold;
        border: tall #ffffff;
    }

    #preview-log {
        height: 1fr;
        border: solid $secondary;
        background: $background;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
    ]

    def __init__(self, file_path: Path, content: str, language: str, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.content = content
        self.language = language

    def compose(self) -> ComposeResult:
        with Vertical(id="preview-dialog"):
            with Horizontal(id="preview-header"):
                yield Label(
                    f"File Preview: {self.file_path.name} ({len(self.content):,} chars)",
                    id="preview-title",
                )
                yield Button("X", variant="error", id="btn-close-preview")
            yield RichLog(id="preview-log", highlight=True, markup=True, wrap=True)

    def on_mount(self) -> None:
        log = self.query_one("#preview-log", RichLog)
        syntax = Syntax(
            self.content,
            self.language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        log.write(syntax)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-preview":
            self.dismiss()

    def action_dismiss_modal(self) -> None:
        self.dismiss()


class AgentTUIApp(App):
    """Textual Terminal User Interface for Python AI Agent."""

    TITLE = "Python AI Agent"
    SUB_TITLE = "Autonomous Multi-Tool Agent"
    ENABLE_COMMAND_PALETTE = True
    COMMAND_PALETTE_BINDING = "alt+p"

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    /* Prevent white background rectangle on focused buttons globally */
    Button:focus {
        text-style: bold;
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
        overflow-x: auto;
        margin-bottom: 0;
    }

    .tab-btn {
        height: 1;
        min-height: 1;
        border: none;
        padding: 0 1;
        margin-right: 0;
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
        ("alt+1", "view_files", "Files"),
        ("alt+2", "view_tools", "Tools"),
        ("alt+3", "view_split", "Split"),
        ("alt+r", "refresh_files", "Refresh"),
        ("alt+m", "switch_model", "Model"),
        ("alt+c", "toggle_chat_expand", "Chat"),
        ("alt+p", "command_palette", "Palette"),
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
        self.is_chat_expanded = False

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
                    yield Button("Expand", variant="default", id="expand-chat-btn", classes="action-btn")
                    yield Button("Reset", variant="default", id="reset-btn", classes="action-btn")
                    yield Button("Quit", variant="error", id="quit-btn", classes="action-btn")

            # Right: Compact Toolbar + Resizable Panels
            with Vertical(id="sidebar"):
                with Horizontal(id="sidebar-toolbar"):
                    yield Button("Files (Alt+1)", id="btn-view-files", classes="tab-btn tab-btn-active")
                    yield Button("Tools (Alt+2)", id="btn-view-tools", classes="tab-btn")
                    yield Button("Split (Alt+3)", id="btn-view-split", classes="tab-btn")
                    yield Button("Refresh (Alt+R)", id="btn-refresh-files", classes="tab-btn")
                    yield Button("Model (Alt+M)", id="btn-switch-model", classes="tab-btn")

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
                f"• Press [bold]Alt+M[/bold] for Model Switcher, [bold]Alt+P[/bold] for Command Palette, or click files to preview code.",
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

    def action_toggle_chat_expand(self) -> None:
        """Toggle chat container between full width (100%) and split width (52%)."""
        chat_box = self.query_one("#chat-container", Vertical)
        sidebar = self.query_one("#sidebar", Vertical)
        btn_expand = self.query_one("#expand-chat-btn", Button)

        self.is_chat_expanded = not self.is_chat_expanded
        if self.is_chat_expanded:
            sidebar.display = False
            chat_box.styles.width = "100%"
            btn_expand.label = "Restore"
            self.notify("Chat expanded to full width", title="View")
        else:
            sidebar.display = True
            chat_box.styles.width = "52%"
            sidebar.styles.width = "48%"
            btn_expand.label = "Expand"
            self.notify("Restored side-by-side view", title="View")

    def action_view_files(self) -> None:
        """Switch to Workspace Files view."""
        if self.is_chat_expanded:
            self.action_toggle_chat_expand()
        self.set_view_mode("files")

    def action_view_tools(self) -> None:
        """Switch to Tool Activity view."""
        if self.is_chat_expanded:
            self.action_toggle_chat_expand()
        self.set_view_mode("tools")

    def action_view_split(self) -> None:
        """Switch to Split view."""
        if self.is_chat_expanded:
            self.action_toggle_chat_expand()
        self.set_view_mode("split")

    def action_refresh_files(self) -> None:
        """Manually trigger workspace file tree refresh."""
        self.populate_file_tree()
        self.notify("Workspace files refreshed", title="Files")

    def action_switch_model(self) -> None:
        """Open the model switcher modal."""
        def on_model_chosen(res: Optional[dict]) -> None:
            if res:
                self.switch_to_model(res)

        self.push_screen(ModelSelectModal(current_model=self.model), on_model_chosen)

    def switch_to_model(self, model_config: dict) -> None:
        """Switch active model and client configuration."""
        new_model = model_config["model"]
        is_local = model_config.get("is_local", False)
        base_url = model_config.get("base_url")

        self.model = new_model
        self.is_local = is_local
        self.base_url = base_url

        try:
            self.client = create_client(
                api_key=self.api_key,
                base_url=self.base_url,
                is_local=self.is_local,
            )
            self.agent.client = self.client
            self.agent.model = self.model
            self.update_telemetry()

            mode_desc = "Local Ollama" if self.is_local else "OpenRouter"
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(
                Panel(
                    f"Switched active model to [bold cyan]{self.model}[/bold cyan] ({mode_desc})",
                    title="Model Changed",
                    border_style="cyan",
                )
            )
            self.notify(f"Switched to {self.model}", title="Model Updated")
        except Exception as e:
            self.notify(f"Failed to switch model: {e}", title="Error", severity="error")

    def action_reset_chat(self) -> None:
        """Reset conversation context."""
        self.memory.reset()
        self.query_one("#chat-log", RichLog).write("[italic cyan]-- Conversation context reset --[/italic cyan]")
        self.query_one("#tool-log", RichLog).write("[italic cyan]-- Tool activity reset --[/italic cyan]")
        self.current_step = 0
        self.update_telemetry()

    def action_quit_app(self) -> None:
        """Prompt user with confirmation modal before quitting."""
        def on_confirm(should_quit: Optional[bool]) -> None:
            if should_quit:
                self.exit()

        self.push_screen(ConfirmQuitModal(), on_confirm)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Toggle directory expansion or open file preview for files."""
        node_data = event.node.data
        if isinstance(node_data, Path):
            if node_data.is_dir():
                event.node.toggle()
            elif node_data.is_file():
                self.open_file_preview(node_data)
        else:
            event.node.toggle()

    def open_file_preview(self, file_path: Path) -> None:
        """Read and open modal file preview."""
        try:
            if file_path.stat().st_size > 500_000:
                content = f"[File exceeds 500 KB limit ({file_path.stat().st_size:,} bytes)]"
                lang = "text"
            else:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                lang = detect_language(file_path)
        except Exception as e:
            content = f"Error reading file: {e}"
            lang = "text"

        self.push_screen(FilePreviewModal(file_path=file_path, content=content, language=lang))

    def populate_file_tree(self) -> None:
        """Populate the sidebar workspace file tree."""
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        tree.root.label = f"[{self.workspace_dir.name}]"
        tree.root.data = self.workspace_dir
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
                        branch = parent_node.add(f"[DIR] {entry.name}", expand=False, data=entry)
                        add_nodes(branch, entry, depth + 1)
                    else:
                        parent_node.add_leaf(entry.name, data=entry)
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
        elif event.button.id == "expand-chat-btn":
            self.action_toggle_chat_expand()
        elif event.button.id == "btn-view-files":
            self.action_view_files()
        elif event.button.id == "btn-view-tools":
            self.action_view_tools()
        elif event.button.id == "btn-view-split":
            self.action_view_split()
        elif event.button.id == "btn-refresh-files":
            self.action_refresh_files()
        elif event.button.id == "btn-switch-model":
            self.action_switch_model()

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
            if self.is_chat_expanded:
                self.action_toggle_chat_expand()
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
