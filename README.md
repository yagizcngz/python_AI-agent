# Autonomous Python AI Agent

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter_API-6366F1?logoColor=white)](https://openrouter.ai/)
[![Local: Ollama](https://img.shields.io/badge/Local_LLM-Ollama_Ready-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An autonomous, multi-modal interface AI agent built in Python leveraging native LLM function calling via **OpenRouter** and **local offline runtimes (Ollama, LM Studio)**. The agent implements an iterative reasoning loop (**ReAct pattern**) capable of multi-step problem solving, sandboxed file operations (`Read`, `Write`, `Edit`, `ListDir`), and local terminal execution (`Bash`) across CLI, interactive REPL, and visual Textual Terminal UI.

---

## Key Features

* **Autonomous Reasoning Loop:** Runs an iterative ReAct decision loop with configurable step limits (`--max-steps`), preventing infinite loops and runaway token consumption.
* **Interactive Terminal UI (TUI):** A visual, keyboard-driven dashboard launched by default with live chat streams, syntax-highlighted tool cards, collapsible file tree explorer, model information, and token telemetry.
* **Conversational REPL Mode:** Run with `--repl` to engage in multi-turn back-and-forth tasks in the terminal with persistent conversation context and helper commands (`/reset`, `/usage`, `/exit`).
* **Native Tool Execution (Function Calling):**
  * `Read`: Safely reads files within the isolated application workspace.
  * `Write`: Creates and updates files with automatic directory provisioning.
  * `Edit`: Fast in-place search-and-replace text editing without rewriting entire files.
  * `ListDir`: Native tree/directory inspection without spawning shell sub-processes.
  * `Bash`: Sandboxed terminal commands with strict timeout guards (`--timeout`) and dynamic Python runtime detection.
* **Strict Sandbox & Traversal Protection:** All file operations are validated against the workspace root using `pathlib.Path.resolve().is_relative_to(sandbox_root)`, strictly forbidding directory traversal escapes (`../`).
* **Cloud + Local LLM Support:** Toggle between cloud models via OpenRouter or local zero-cost models on Ollama/LM Studio using `--local` or `--base-url`.
* **Fault-Tolerant & Safe:**
  * Timeout protection on API calls (`--api-timeout`) and subprocess executions.
  * Gracefully catches and repairs malformed JSON from small models.
  * Automatic UTF-8 stream reconfiguring to prevent Windows locale encoding errors.
  * Live model discovery (`--list-models`) and smart fallback suggestions when endpoints hit rate limits.

---

## Architecture & Execution Flow

```
                      User Prompt / Interaction
               (Default: TUI | REPL: --repl | CLI: -p)
                                  │
                                  ▼
                      ┌───────────────────────┐
                      │      Agent Brain      │ <─── OpenRouter or Local Ollama
                      └───────────┬───────────┘
                                  │
                          Tool Call Requested?
                          ├── YES ──> ┌────────────────────────────────────────┐
                          │           │        Sandboxed Tool Execution        │
                          │           │  • Read: Inspect local files           │
                          │           │  • Write: Create files & directories   │
                          │           │  • Edit: In-place text modifications   │
                          │           │  • ListDir: Inspect workspace tree     │
                          │           │  • Bash: Shell execution with timeout  │
                          │           └───────────────────┬────────────────────┘
                          │                               │
                          │        Tool Observation Fed Back to Context
                          │                               │
                          │                               ▼
                          │                 (Loop back to Agent Brain)
                          │
                          └── NO  ──> Render Final Response & Telemetry Table
```

---

## Built-in Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `Read` | `file_path` (string) | Reads file contents within the workspace sandbox. |
| `Write` | `file_path` (string), `content` (string) | Creates/overwrites files, provisioning any required parent directories. |
| `Edit` | `file_path` (string), `old_content` (string), `new_content` (string) | Performs surgical in-place text replacement in an existing file. |
| `ListDir` | `directory_path` (string, optional), `recursive` (bool, optional) | Inspects files and directories inside the sandbox without shell overhead. |
| `Bash` | `command` (string) | Runs shell commands anchored to the workspace with timeout protection. |

---

## Getting Started

### Prerequisites
* Python 3.9 or higher
* An [OpenRouter](https://openrouter.ai/) account and API Key **OR** a local [Ollama](https://ollama.com/) instance.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yagizcngz/python_AI-agent.git
   cd python_AI-agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and insert your key:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your_key_here
   ```

---

## Usage Modes

### 1. Visual Terminal UI (TUI) Dashboard (Default)
Simply run the application without arguments, or run `run.bat`:
```powershell
python app/main.py
# or double-click run.bat
```
* **UI Controls & Shortcuts:**
  * **Files (Alt+1):** Display workspace file tree. Click any file to open the syntax-highlighted File Preview modal (with close button [ X ]).
  * **Tools (Alt+2):** Display full tool activity and execution logs.
  * **Split (Alt+3):** Display both tool activity and workspace files in stacked split view.
  * **Chat (Alt+C):** Toggle full-width chat focus or restore side-by-side workspace split.
  * **Refresh (Alt+R):** Refresh the workspace file tree.
  * **Model (Alt+M):** Open the interactive Model Switcher dialog to select from recommended free models, local Ollama, or custom model IDs.
  * **Send (Enter):** Submit current prompt.
  * **Reset (Ctrl+R):** Clear conversation context and reset token telemetry.
  * **Palette (Alt+P):** Open Textual's command palette for theme switching and screenshot capture.
  * **Keys (F1 / ?):** Open the dedicated Keyboard Shortcuts modal with clean list and [ X ] close button.
  * **Quit (Esc):** Bottom-bar button or Esc prompts with a Confirm Exit modal before quitting.

---

### 2. Interactive Console REPL
Launch the multi-turn conversational REPL by passing `--repl`:
```powershell
python app/main.py --repl
```
```text
Python AI Agent -- Interactive REPL
Type your prompt and press Enter. Commands: /reset, /usage, /exit

User > Create a python file called calculate.py that calculates factorials.
...
User > Now run calculate.py using Bash and verify it works.
```

---

### 3. Single-Shot Command Line (CLI)
Pass a direct task with `-p`:
```powershell
python app/main.py -p "Inspect the workspace files and write a summary in summary.txt"
```

---

### 4. Running Local Offline Models (Ollama)
Run models locally with zero API keys and zero cost:
```powershell
# 1. In another terminal, pull and start your local model in Ollama:
ollama run qwen2.5-coder:1.5b

# 2. Run the agent with the --local flag:
python app/main.py --local -m "qwen2.5-coder:1.5b" -p "Write a hello world script"
```

---

## CLI Reference & Flags

| Flag | Long Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| | | Launch the visual Textual Terminal UI dashboard | Default behavior |
| `-p` | `--prompt` | Direct task prompt for single-shot execution | None |
| | `--repl`, `--cli` | Launch interactive text console REPL | `False` |
| `-m` | `--model` | OpenRouter or local model identifier | `inclusionai/ling-3.0-flash-sante:free` |
| | `--local` | Connect to local Ollama server at `http://localhost:11434/v1` | `False` |
| | `--base-url` | Custom OpenAI-compatible server base URL | OpenRouter API / Ollama |
| `-l` | `--list-models` | List active models from the endpoint and exit | `False` |
| `-w` | `--workspace` | Root directory for sandboxed file operations | Current directory |
| | `--max-steps` | Maximum reasoning iterations before halting | `25` |
| | `--timeout` | Shell command timeout in seconds | `30` |
| | `--api-timeout`| Timeout for API LLM calls in seconds | `30.0` |
| `-q` | `--quiet` | Output clean plaintext answer without Rich panels | `False` |
| `-h` | `--help` | Show help and exit | |

---

## Running Automated Tests

Run the full `pytest` test suite:
```powershell
pytest -v
```
Tests cover:
* Path sandboxing & directory traversal prevention (`tests/test_sandbox.py`)
* Tool operations (`Read`, `Write`, `Edit`, `ListDir`, `Bash`, timeouts) (`tests/test_tools.py`)
* ReAct reasoning loop, step limits, and mocked API responses (`tests/test_agent.py`)
* Responsive TUI layout, modal screens, and small/tall terminal rendering (`tests/test_tui_layout.py`)

---

## Security & Containment

* **Path Sandbox:** All operations are resolved against the workspace root and strictly checked using `Path.is_relative_to()`. Traversal attempts (`../` or external absolute paths) immediately raise a `PermissionError`.
* **Execution Timeout:** All shell commands are enforced with a strict execution timeout (default: 30s) to prevent frozen processes from blocking the agent.
* **Secrets Security:** Keys are loaded via `.env` files and environment variables, keeping plaintext credentials out of version control.

---

## License

This project is licensed under the MIT License -- see the [LICENSE](LICENSE) file for details.

---

## Author

**Yagiz Cengiz**
* GitHub: [@yagizcngz](https://github.com/yagizcngz)
* Email: [yagizcengiz55@gmail.com](mailto:yagizcengiz55@gmail.com)
