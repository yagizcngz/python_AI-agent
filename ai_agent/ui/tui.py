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
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.command import (
    CommandInput,
    CommandList,
    CommandPalette,
    SearchIcon,
)
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
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
from ..core.client import create_client, fetch_account_usage, validate_model_id
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
        width: 80%;
        max-width: 90;
        height: auto;
        max-height: 94%;
        border: solid $accent;
        background: $panel;
        padding: 0 1;
        overflow-y: auto;
    }

    #model-header {
        height: 1;
        layout: horizontal;
        margin-top: 1;
        margin-bottom: 0;
    }

    #model-dialog-title {
        width: 1fr;
        height: 1;
        text-style: bold;
        color: $accent;
    }

    #btn-close-model {
        width: 4;
        min-width: 4;
        height: 1;
        border: none;
        padding: 0;
        text-style: bold;
        content-align: center middle;
        background: #dc2626;
        color: #ffffff;
    }

    #btn-close-model:focus, #btn-close-model:hover {
        background: #ef4444;
        border: none;
    }

    #model-options {
        height: 7;
        border: solid #334155;
        margin-bottom: 1;
    }

    #custom-model-input {
        height: 3;
        margin-bottom: 1;
    }

    #model-error-msg {
        color: #ef4444;
        text-style: bold;
        display: none;
    }

    #model-btn-bar {
        height: 1;
        layout: horizontal;
        align: right middle;
        margin-top: 0;
        margin-bottom: 1;
    }

    .modal-btn {
        height: 1;
        min-height: 1;
        border: none;
        padding: 0 1;
        margin-left: 1;
        text-style: bold;
    }

    .modal-btn:focus, .modal-btn:hover {
        background: $accent;
        color: #02131f;
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
            with Horizontal(id="model-header"):
                yield Label("Select Active AI Model", id="model-dialog-title")
                yield Button("X", variant="error", id="btn-close-model")
            yield Label("Choose a recommended model or type a custom model ID below:")

            options = []
            for m in RECOMMENDED_FREE_MODELS:
                badge = "(Active)" if m == self.current_model else "(Free)"
                options.append(f"{m} {badge}")
            options.append("qwen2.5-coder:1.5b (Local Ollama)")
            options.append("llama3.2:1b (Local Ollama)")

            yield OptionList(*options, id="model-options")
            yield Input(
                placeholder="Or type custom model (e.g. openai/gpt-4o, deepseek/deepseek-chat)...",
                id="custom-model-input",
            )
            yield Label("", id="model-error-msg")
            with Horizontal(id="model-btn-bar"):
                yield Button("Select", variant="primary", id="btn-confirm-model", classes="modal-btn")
                yield Button("Cancel", variant="default", id="btn-cancel-model", classes="modal-btn")

    def on_mount(self) -> None:
        self._adjust_size(self.app.size.height)

    def on_resize(self, event) -> None:
        self._adjust_size(event.size.height)

    def _adjust_size(self, h: int) -> None:
        try:
            options = self.query_one("#model-options", OptionList)
            if h <= 15:
                options.styles.height = 3
            elif h <= 18:
                options.styles.height = 4
            elif h <= 21:
                options.styles.height = 5
            else:
                options.styles.height = 7
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-model":
            self.confirm_selection()
        elif event.button.id in ("btn-cancel-model", "btn-close-model"):
            self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.confirm_selection()

    def confirm_selection(self) -> None:
        custom_val = self.query_one("#custom-model-input", Input).value.strip()
        err_label = self.query_one("#model-error-msg", Label)

        if custom_val:
            is_local = custom_val.startswith("ollama/")
            model_name = custom_val[7:] if is_local else custom_val

            is_valid, resolved = validate_model_id(model_name, is_local=is_local)
            if not is_valid:
                err_label.update(f"[bold red]{resolved}[/bold red]")
                err_label.display = True
                return

            err_label.display = False
            res = {
                "model": resolved,
                "is_local": is_local,
                "base_url": DEFAULT_LOCAL_BASE_URL if is_local else None,
            }
            self.dismiss(res)
            return

        opt_list = self.query_one("#model-options", OptionList)
        if opt_list.highlighted is not None:
            err_label.display = False
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


class KeysModal(ModalScreen[None]):
    """Modal dialog displaying keyboard shortcuts with an [ X ] close button."""

    CSS = """
    KeysModal {
        align: center middle;
    }

    #keys-dialog {
        width: 76;
        max-width: 90%;
        height: auto;
        max-height: 85%;
        border: solid #38bdf8;
        background: #0b0f19;
        padding: 1;
    }

    #keys-header {
        height: 3;
        layout: horizontal;
        margin-bottom: 1;
    }

    #keys-title {
        width: 1fr;
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: #38bdf8;
    }

    #btn-close-keys {
        width: 5;
        min-width: 5;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: #dc2626;
        color: #ffffff;
    }

    #btn-close-keys:focus, #btn-close-keys:hover {
        background: #ef4444;
        text-style: bold;
        border: tall #ffffff;
    }

    #keys-log {
        height: auto;
        max-height: 18;
        border: solid #1e293b;
        background: #060911;
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="keys-dialog"):
            with Horizontal(id="keys-header"):
                yield Label("KEYBOARD SHORTCUTS", id="keys-title")
                yield Button("X", variant="error", id="btn-close-keys")
            yield RichLog(id="keys-log", highlight=True, markup=True, wrap=True)

    def on_mount(self) -> None:
        log = self.query_one("#keys-log", RichLog)
        shortcuts = [
            ("Alt+1", "Files", "Show Workspace file directory tree"),
            ("Alt+2", "Tools", "Show Tool Activity real-time log"),
            ("Alt+3", "Split", "Split view: Files + Tools stacked side-by-side"),
            ("Alt+C", "Chat", "Toggle full-screen chat / restore split"),
            ("Alt+R", "Refresh", "Refresh workspace directory files"),
            ("Alt+M", "Model", "Open interactive AI Model Switcher dialog"),
            ("Alt+P", "Palette", "Open Command Palette (search commands & themes)"),
            ("Ctrl+R", "Reset", "Reset conversation context & token usage"),
            ("Esc", "Quit", "Prompt confirmation before quitting application"),
            ("Enter", "Send", "Submit prompt or instruction to agent"),
        ]
        log.write("[bold #fbbf24]SHORTCUT[/bold #fbbf24]       [bold #38bdf8]ACTION[/bold #38bdf8]      [bold #94a3b8]DESCRIPTION[/bold #94a3b8]")
        log.write("[dim]─────────────────────────────────────────────────────────────────[/dim]")
        for key, act, desc in shortcuts:
            log.write(f"[bold #fbbf24]{key:<14}[/bold #fbbf24] [bold #38bdf8]{act:<10}[/bold #38bdf8] {desc}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-keys":
            self.dismiss()

    def action_dismiss_modal(self) -> None:
        self.dismiss()


class CustomCommandPalette(CommandPalette):
    """Command palette with an explicit red [ X ] close button in the header bar."""

    DEFAULT_CSS = """
    CustomCommandPalette #btn-close-palette {
        width: 5;
        min-width: 5;
        height: 3;
        text-style: bold;
        content-align: center middle;
        background: #dc2626;
        color: #ffffff;
        margin-right: 1;
    }

    CustomCommandPalette #btn-close-palette:hover,
    CustomCommandPalette #btn-close-palette:focus {
        background: #ef4444;
        border: tall #ffffff;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="--container"):
            with Horizontal(id="--input"):
                yield SearchIcon()
                yield CommandInput(placeholder=self._placeholder, select_on_focus=False)
                if not self.run_on_select:
                    yield Button("\u25b6")
                yield Button("X", variant="error", id="btn-close-palette")
            with Vertical(id="--results"):
                yield CommandList()
                yield LoadingIndicator()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-palette":
            event.stop()
            self._action_escape()


# Disallow maximizing buttons and input fields to prevent single-button full-screen blowout
Button.ALLOW_MAXIMIZE = False
Input.ALLOW_MAXIMIZE = False


class StaticHeader(Header):
    """Header widget that stays fixed at 1 line and does not expand on click."""

    def toggle_class(self, *class_names: str):
        filtered = [c for c in class_names if c != "-tall"]
        if filtered:
            return super().toggle_class(*filtered)
        return self

    def set_class(self, value: bool, class_name: str):
        if class_name == "-tall":
            return self
        return super().set_class(value, class_name)

    def add_class(self, *class_names: str):
        filtered = [c for c in class_names if c != "-tall"]
        if filtered:
            return super().add_class(*filtered)
        return self

    def on_click(self, event) -> None:
        event.stop()
        event.prevent_default()

    def _on_click(self) -> None:
        pass


class AgentTUIApp(App):
    """Textual Terminal User Interface for Python AI Agent."""

    TITLE = "Python AI Agent"
    SUB_TITLE = "Autonomous Multi-Tool Agent"
    ENABLE_COMMAND_PALETTE = True
    COMMAND_PALETTE_BINDING = "alt+p"

    CSS = """
    Screen {
        layout: vertical;
        background: #0b0f19;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    Header, Header.-tall, StaticHeader, StaticHeader.-tall {
        height: 1;
        min-height: 1;
        max-height: 1;
    }

    HeaderIcon {
        display: none;
    }

    Button:focus {
        text-style: bold;
    }

    #status-bar {
        height: 1;
        width: 100%;
        background: #1e293b;
        color: #f8fafc;
        padding: 0 1;
        text-style: bold;
    }

    #main-container {
        height: 1fr;
        min-height: 0;
        layout: horizontal;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #chat-container {
        width: 52%;
        height: 100%;
        min-height: 0;
        padding: 0 1;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #chat-log {
        height: 1fr;
        min-height: 0;
        border: heavy #38bdf8;
        background: #060911;
        padding: 1;
        scrollbar-size: 1 1;
    }

    #input-bar {
        height: 3;
        min-height: 3;
        layout: horizontal;
        margin-top: 0;
        margin-bottom: 0;
    }

    #user-input {
        width: 1fr;
        height: 3;
        border: heavy #38bdf8;
        background: #0f172a;
        color: #f8fafc;
    }

    #user-input:focus {
        border: heavy #7dd3fc;
    }

    .action-btn {
        margin-left: 1;
        min-width: 6;
        width: 8;
        height: 3;
        border: heavy #0284c7;
        text-style: bold;
    }

    #send-btn {
        background: #38bdf8;
        color: #032b43;
        border: heavy #0284c7;
        padding: 0;
    }
    #send-btn:focus, #send-btn:hover {
        background: #7dd3fc;
        border: heavy #ffffff;
    }

    #sidebar {
        width: 48%;
        height: 100%;
        min-height: 0;
        padding: 0 1;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #files-box {
        height: 1fr;
        min-height: 0;
        border: heavy #c084fc;
        background: #060911;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #tool-box {
        height: 1fr;
        min-height: 0;
        border: heavy #fbbf24;
        background: #060911;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #tool-log {
        height: 1fr;
        min-height: 0;
        border: none;
        padding: 0 1;
        scrollbar-size: 1 1;
    }

    #file-tree {
        height: 1fr;
        min-height: 0;
        border: none;
        padding: 0 1;
        scrollbar-size: 1 1;
    }

    #bottom-bar {
        dock: bottom;
        height: 1;
        width: 100%;
        background: #0f172a;
        layout: horizontal;
        padding: 0 1;
        overflow: hidden hidden;
        scrollbar-size: 0 0;
    }

    #bottom-right {
        width: 100%;
        height: 1;
        layout: horizontal;
        align: right middle;
    }

    .bottom-btn {
        height: 1;
        min-height: 1;
        min-width: 5;
        border: none;
        padding: 0 1;
        margin-left: 1;
        background: #1e293b;
        color: #94a3b8;
        text-style: bold;
    }

    .bottom-btn:hover, .bottom-btn:focus {
        background: #0284c7;
        color: #ffffff;
        text-style: bold;
    }

    .bottom-btn-active {
        background: #38bdf8;
        color: #02131f;
        text-style: bold;
    }

    #expand-chat-btn {
        min-width: 9;
        text-align: center;
    }

    .quit-btn:hover, .quit-btn:focus {
        background: #dc2626;
        color: #ffffff;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "quit_app", "Quit application", show=False),
        Binding("ctrl+c", "quit_app", "Quit application", show=False),
        Binding("f1", "show_help_panel", "Keyboard shortcuts", show=False),
        Binding("question_mark", "show_help_panel", "Keyboard shortcuts", show=False),
        Binding("alt+1", "view_files", "Files (Workspace tree)"),
        Binding("alt+2", "view_tools", "Tools (Tool activity)"),
        Binding("alt+3", "view_split", "Split (Files + Tools)"),
        Binding("alt+c", "toggle_chat_expand", "Chat (Toggle full screen)"),
        Binding("alt+r", "refresh_files", "Refresh workspace files"),
        Binding("alt+m", "switch_model", "Model switcher dialog"),
        Binding("ctrl+r", "reset_chat", "Reset conversation & tokens"),
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
        self.cached_remaining_requests: Optional[int] = None
        self.cached_limit_requests: Optional[int] = None
        self.cached_used_requests: Optional[int] = None
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

    def action_maximize(self) -> None:
        """Maximize main content panels, never individual small buttons."""
        if self.screen.maximized is not None:
            self.screen.minimize()
            return
        focused = self.screen.focused
        if focused is not None and getattr(focused, "allow_maximize", False):
            self.screen.maximize(focused)
        else:
            chat_log = self.query_one("#chat-log", RichLog)
            self.screen.maximize(chat_log)

    def compose(self) -> ComposeResult:
        yield StaticHeader(show_clock=True)
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
                    yield Button("SEND", variant="primary", id="send-btn", classes="action-btn")

            # Right: Resizable Panels
            with Vertical(id="sidebar"):
                with Vertical(id="files-box") as fb:
                    fb.border_title = f"Workspace: {self.workspace_dir.name}"
                    yield Tree("Root", id="file-tree")
                with Vertical(id="tool-box") as tb:
                    tb.border_title = "Tool Activity"
                    yield RichLog(id="tool-log", highlight=True, markup=True, wrap=True)

        with Horizontal(id="bottom-bar"):
            with Horizontal(id="bottom-right"):
                yield Button("FILES", id="btn-view-files", classes="bottom-btn bottom-btn-active", tooltip="Show Workspace Files (Alt+1)")
                yield Button("TOOLS", id="btn-view-tools", classes="bottom-btn", tooltip="Show Tool Activity (Alt+2)")
                yield Button("SPLIT", id="btn-view-split", classes="bottom-btn", tooltip="Show Split View (Alt+3)")
                yield Button("CHAT", id="expand-chat-btn", classes="bottom-btn", tooltip="Toggle Full Screen Chat (Alt+C)")
                yield Button("REFRESH", id="btn-refresh-files", classes="bottom-btn", tooltip="Refresh Workspace Files (Alt+R)")
                yield Button("MODEL", id="btn-switch-model", classes="bottom-btn", tooltip="Switch AI Model (Alt+M)")
                yield Button("RESET", id="reset-btn", classes="bottom-btn", tooltip="Reset Context & Logs (Ctrl+R)")
                yield Button("PALETTE", id="btn-palette", classes="bottom-btn", tooltip="Open Command Palette (Alt+P)")
                yield Button("QUIT", id="quit-btn", classes="bottom-btn quit-btn", tooltip="Quit Application (Esc)")

    def get_system_commands(self, screen):
        """Custom command palette actions replacing default HelpPanel with KeysModal."""
        yield SystemCommand(
            "Keys",
            "Show available keyboard shortcuts",
            self.action_show_help_panel,
        )
        yield SystemCommand(
            "Theme",
            "Change the current theme",
            self.action_change_theme,
        )
        yield SystemCommand(
            "Screenshot",
            "Save an SVG screenshot of the current screen",
            self.action_screenshot,
        )
        yield SystemCommand(
            "Quit",
            "Quit application with confirmation",
            self.action_quit_app,
        )

    def action_command_palette(self) -> None:
        """Show custom Command Palette with close button."""
        if self.use_command_palette and not CommandPalette.is_open(self):
            self.push_screen(CustomCommandPalette(id="--command-palette"))

    def action_show_help_panel(self) -> None:
        """Display custom Keyboard Shortcuts modal with [ X ] button instead of default HelpPanel."""
        try:
            from textual.widgets import HelpPanel
            for p in self.screen.query(HelpPanel):
                p.remove()
        except Exception:
            pass
        self.push_screen(KeysModal())

    def action_hide_help_panel(self) -> None:
        """Close keys modal or remove any lingering help panel."""
        if isinstance(self.screen, KeysModal):
            self.screen.dismiss()
        try:
            from textual.widgets import HelpPanel
            for p in self.screen.query(HelpPanel):
                p.remove()
        except Exception:
            pass

    def action_help(self) -> None:
        """Display custom Keyboard Shortcuts modal with [ X ] button instead of default HelpPanel."""
        self.action_show_help_panel()

    def on_resize(self, event) -> None:
        """Dynamically adjust panel display on terminal resize."""
        if not self.is_chat_expanded:
            if event.size.height < 18 and self.current_view_mode == "split":
                self.set_view_mode("files")

    def on_mount(self) -> None:
        """Called when UI starts up."""
        # Ensure any residual HelpPanel is removed
        try:
            from textual.widgets import HelpPanel
            for p in self.screen.query(HelpPanel):
                p.remove()
        except Exception:
            pass

        chat_log = self.query_one("#chat-log", RichLog)
        tool_log = self.query_one("#tool-log", RichLog)

        chat_log.write(
            Panel(
                f"[bold #38bdf8]P Y T H O N   A I   A G E N T   [ O N L I N E ][/bold #38bdf8]\n"
                f"WORKSPACE : [bold #fbbf24]{self.workspace_dir.name}[/bold #fbbf24] ({self.workspace_dir})\n"
                f"STATUS    : [bold #34d399]READY FOR INSTRUCTIONS[/bold #34d399]",
                title="[ S T A T U S ]",
                border_style="#38bdf8",
            )
        )
        tool_log.write(
            Panel(
                "Tool invocations (Bash, Read, Write, Edit, ListDir) stream here in real-time.",
                title="[ T O O L   A C T I V I T Y ]",
                border_style="#fbbf24",
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

        btn_files.remove_class("bottom-btn-active")
        btn_tools.remove_class("bottom-btn-active")
        btn_split.remove_class("bottom-btn-active")

        if mode == "files":
            files_box.display = True
            tool_box.display = False
            btn_files.add_class("bottom-btn-active")
        elif mode == "tools":
            files_box.display = False
            tool_box.display = True
            btn_tools.add_class("bottom-btn-active")
        elif mode == "split":
            files_box.display = True
            tool_box.display = True
            btn_split.add_class("bottom-btn-active")

    def action_toggle_chat_expand(self) -> None:
        """Toggle chat container between full width (100%) and split width (52%)."""
        chat_box = self.query_one("#chat-container", Vertical)
        sidebar = self.query_one("#sidebar", Vertical)
        btn_expand = self.query_one("#expand-chat-btn", Button)

        self.is_chat_expanded = not self.is_chat_expanded
        if self.is_chat_expanded:
            sidebar.display = False
            chat_box.styles.width = "100%"
            btn_expand.label = "RESTORE"
            btn_expand.add_class("bottom-btn-active")
        else:
            sidebar.display = True
            chat_box.styles.width = "52%"
            sidebar.styles.width = "48%"
            btn_expand.label = "CHAT"
            btn_expand.remove_class("bottom-btn-active")

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
        """Prompt user with confirmation modal before quitting, or restore maximized widget / help panel."""
        if self.screen.maximized is not None:
            self.screen.minimize()
            return

        if isinstance(self.screen, KeysModal):
            self.screen.dismiss()
            return

        try:
            from textual.widgets import HelpPanel
            help_panels = self.screen.query(HelpPanel)
            if help_panels:
                help_panels.remove()
                return
        except Exception:
            pass

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
        elif event.button.id == "btn-palette":
            self.action_command_palette()

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
                title="[bold #38bdf8][ U S E R ][/bold #38bdf8]",
                border_style="#38bdf8",
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

        # Optimistically decrement remaining requests count immediately
        if self.cached_remaining_requests is not None and self.cached_remaining_requests > 0:
            self.cached_remaining_requests -= 1
            self.cached_used_requests = (self.cached_used_requests or 0) + 1
            lim = self.cached_limit_requests or 50
            self.daily_limits_text = f"Requests: [bold green]{self.cached_remaining_requests}/{lim} left[/bold green] ({self.cached_used_requests} used)"

        self.update_telemetry()
        # Fetch authoritative count from OpenRouter after 2-second backend ingestion delay
        self.refresh_account_limits(delay=2.0)
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
    def refresh_account_limits(self, delay: float = 0.0) -> None:
        """Fetch live remaining limits in background thread with optional delay."""
        import time
        if delay > 0:
            time.sleep(delay)
        usage = fetch_account_usage(self.api_key)
        if not usage:
            return
        daily = usage.get("free_model_daily_requests")
        if daily:
            self.cached_remaining_requests = daily.get("remaining", 0)
            self.cached_limit_requests = daily.get("limit", 0)
            self.cached_used_requests = daily.get("used", 0)
            self.daily_limits_text = f"Requests: [bold green]{self.cached_remaining_requests}/{self.cached_limit_requests} left[/bold green] ({self.cached_used_requests} used)"
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
            chat_log.write(f"[dim #fbbf24]► [ T H I N K I N G ] {event.data} [ █ ][/dim #fbbf24]")
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

            chat_log.write(f"[dim #38bdf8]► [ E X E C U T I N G ] {fn_name} [ █ ][/dim #38bdf8]")

            # Route tool calls exclusively to the dedicated Tool Activity panel
            tool_log.write(
                Panel(
                    Syntax(fn_args, "json", theme="monokai", word_wrap=True),
                    title=f"[bold #fbbf24][ T O O L : {fn_name} ][/bold #fbbf24]",
                    border_style="#fbbf24",
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
                    title=f"[bold #38bdf8][ R E S U L T : {fn_name} ][/bold #38bdf8]",
                    border_style="#38bdf8",
                )
            )

        elif event.event_type == AgentEventType.ANSWER:
            # Pure assistant final response appears cleanly in the chat log on the left
            chat_log.write(
                Panel(
                    RichMarkdown(event.data),
                    title="[bold #c084fc][ A G E N T   A N S W E R ][/bold #c084fc]",
                    border_style="#c084fc",
                )
            )
            self.update_telemetry()

        elif event.event_type == AgentEventType.ERROR:
            err_data = event.data
            err_msg = err_data.get("error") if isinstance(err_data, dict) else str(err_data)
            chat_log.write(
                Panel(
                    f"[bold red]{err_msg}[/bold red]",
                    title="[bold red][ E R R O R ][/bold red]",
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
