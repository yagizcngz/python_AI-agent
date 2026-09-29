"""
Entry point for Autonomous Python AI Agent.
Preserves full backward compatibility while delegating to the modular ai_agent package.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding across Windows locales
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_agent.cli import main

if __name__ == "__main__":
    main()