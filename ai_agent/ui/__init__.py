"""
User Interface module: Rich console formatting and Textual TUI dashboard.
"""

from .console import RichAgentConsole
from .tui import run_tui

__all__ = ["RichAgentConsole", "run_tui"]
