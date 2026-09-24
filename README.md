# 🤖 Autonomous Python AI Agent

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter_API-6366F1?logoColor=white)](https://openrouter.ai/)
[![Tools: Function Calling](https://img.shields.io/badge/Tools-Function_Calling-10B981?logoColor=white)](#-built-in-tools)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An autonomous, command-line AI agent built in Python leveraging LLM function calling via the **OpenRouter API**. The agent implements an iterative reasoning loop (**ReAct pattern**) capable of multi-step problem solving, sandboxed file operations (`Read`, `Write`), and local terminal execution (`Bash`) without requiring human intervention between intermediate steps.

---

## 🌟 Key Features

* **🔄 Autonomous Reasoning Loop:** Runs an iterative decision-making loop (`while True`), maintaining conversation memory and dynamically deciding whether to invoke tools or return a final synthesized response.
* **🛠️ Native Tool Execution (Function Calling):**
  * `Read`: Safely reads files within the isolated application workspace.
  * `Write`: Creates and updates files with automatic directory provisioning.
  * `Bash`: Executes terminal commands within the workspace using the active Python runtime.
* **🔒 Sandbox & Path Traversal Protection:** All file reading, writing, and terminal operations are strictly contained within `BASE_DIR` using basename sanitization (`os.path.basename`) to prevent unauthorized file system escape.
* **⚡ Cross-Platform Compatibility:** Dynamic executable detection (`sys.executable`) maps commands correctly across Windows, macOS, and Linux.
* **🛡️ Fault-Tolerant Output Handling:** Subprocess streams employ replacement decoding (`errors="replace"`) to prevent crashes from non-UTF8/localized terminal characters.

---

## 🏗️ Architecture & Execution Flow

```
User Prompt (-p "...")
        │
        ▼
┌──────────────────┐
│   Agent Brain    │ ◄─── OpenRouter LLM (Tool Planning & Reasoning)
└─────────┬────────┘
          │
    Tool Call Requested?
    ├── YES ──► ┌───────────────────────────────────────────────┐
    │           │           Sandboxed Execution                 │
    │           │  • Read: Inspect local files safely           │
    │           │  • Write: Create scripts / documents          │
    │           │  • Bash: Execute terminal commands via Python │
    │           └───────────────────────┬───────────────────────┘
    │                                   │
    │           Tool Output / Observation Appended to Context
    │                                   │
    │                                   ▼
    │           (Loop back to Agent Brain for next step)
    │
    └── NO  ──► Print Final Answer & Terminate Execution
```

---

## 🛠️ Built-in Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `Read` | `file_path` (string) | Reads the contents of a target file inside the sandbox. |
| `Write` | `file_path` (string), `content` (string) | Writes content to a file, creating any required intermediate directories. |
| `Bash` | `command` (string) | Executes shell commands in the workspace using the local Python environment. |

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9 or higher
* An active [OpenRouter](https://openrouter.ai/) account and API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yagizcngz/python_AI-agent.git
   cd python_AI-agent
   ```

2. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your API Key:**

   **PowerShell (Windows):**
   ```powershell
   $env:OPENROUTER_API_KEY="your_openrouter_api_key_here"
   ```

   **Command Prompt (Windows):**
   ```cmd
   set OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

   **Bash / Zsh (Linux & macOS):**
   ```bash
   export OPENROUTER_API_KEY="your_openrouter_api_key_here"
   ```

---

## 💻 Usage & Examples

Run the agent from the project root by supplying a goal or task using the `-p` flag:

### 1. File Inspection (Read Tool)
```bash
python app/main.py -p "Read app/main.py and summarize what this application does in 2 sentences."
```

### 2. Code Generation & File Creation (Write Tool)
```bash
python app/main.py -p "Generate a Python script named fibonacci.py that prints the first 10 Fibonacci numbers. Save it using the Write tool."
```

### 3. Command Execution (Bash Tool)
```bash
python app/main.py -p "Check the files in the current directory and report their names."
```

### 4. Multi-Step Chained Task (Write ➔ Bash ➔ Read)
```bash
python app/main.py -p "Write a Python script called calculate_sum.py that calculates the sum of all numbers from 1 to 500 and writes the result to output.txt. Then run calculate_sum.py using Bash, read output.txt with Read, and tell me the final number."
```

---

## 🔒 Security & Containment

This agent is designed for safe local experimentation:
* **Directory Jail:** Target file paths are stripped using `os.path.basename` and resolved relative to `BASE_DIR`, preventing access to sensitive parent directories (`../`).
* **Environment Isolation:** API keys and sensitive tokens are read strictly from environment variables rather than hardcoded in source files.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Yağız Cengiz**
* GitHub: [@yagizcngz](https://github.com/yagizcngz)
* Email: [yagizcengiz55@gmail.com](mailto:yagizcengiz55@gmail.com)
