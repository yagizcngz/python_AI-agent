"""
Autonomous AI Agent CLI powered by OpenRouter API.
Executes autonomous reasoning loops (ReAct pattern) with sandboxed 
file operations (Read, Write) and local shell execution (Bash).
"""

import argparse
import json
import os
import sys
import subprocess  

from openai import OpenAI

# Anchor workspace directory to current file location for deterministic execution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def get_api_key() -> str:
    """Retrieve API key from environment variable or fallback text file."""
    key = os.getenv("OPENROUTER_API_KEY")
    if key and key.strip():
        return key.strip()

    # Search for fallback key file in project directories
    search_paths = [
        os.path.join(BASE_DIR, "..", "API_KEYS_OPEN_ROUTER.txt"),
        os.path.join(BASE_DIR, "API_KEYS_OPEN_ROUTER.txt"),
    ]
    for path in search_paths:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
    return ""


RECOMMENDED_FREE_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "poolside/laguna-xs-2.1:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-26b-a4b-it:free",
]


def list_free_models(client: OpenAI):
    """Fetch and print all available free models directly from OpenRouter."""
    print("Fetching active free models from OpenRouter...", file=sys.stderr)
    try:
        models = client.models.list()
        free_models = [m.id for m in models.data if ":free" in m.id]
    except Exception as e:
        print(f"Notice: Failed to fetch live models from OpenRouter ({e}). Showing defaults.", file=sys.stderr)
        free_models = RECOMMENDED_FREE_MODELS

    print(f"\n[+] Active Free Models on OpenRouter ({len(free_models)} found):\n")
    for idx, model_id in enumerate(free_models, start=1):
        print(f"   {idx:2d}. {model_id}")
    print("\nHow to run with any model:")
    print(f'   py app/main.py -m "{free_models[0]}" -p "your task prompt"\n')
    print("Or set default in PowerShell:")
    print(f'   $env:OPENROUTER_MODEL = "{free_models[0]}"\n')


def print_model_suggestions(current_model: str):
    """Print curated alternative free models and copy-paste commands to help user switch."""
    alternatives = [m for m in RECOMMENDED_FREE_MODELS if m != current_model]
    print("\n[!] Suggested alternative free models to try:", file=sys.stderr)
    for alt in alternatives:
        print(f"   * {alt}", file=sys.stderr)
    print("\nTo view all active free models, run:", file=sys.stderr)
    print("   py app/main.py --list-models", file=sys.stderr)
    print("\nHow to switch models:", file=sys.stderr)
    print(f'   1. CLI flag:   py app/main.py -m "{alternatives[0]}" -p "..."', file=sys.stderr)
    print(f'   2. PowerShell: $env:OPENROUTER_MODEL = "{alternatives[0]}"\n', file=sys.stderr)


def main():
    default_model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

    p = argparse.ArgumentParser(description="Autonomous AI Agent CLI")
    p.add_argument("-p", required=False, help="User prompt / task for the agent")
    p.add_argument(
        "-m", "--model",
        default=default_model,
        help=f"OpenRouter model identifier (default: {default_model}, can also be set via $env:OPENROUTER_MODEL)"
    )
    p.add_argument(
        "-l", "--list-models",
        action="store_true",
        help="List all active free models on OpenRouter and exit"
    )
    args = p.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("Error: OPENROUTER_API_KEY is not set and no key found in API_KEYS_OPEN_ROUTER.txt.", file=sys.stderr)
        print("Set it in PowerShell via: $env:OPENROUTER_API_KEY=\"your_key_here\"", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    if args.list_models:
        list_free_models(client)
        sys.exit(0)

    if not args.p:
        p.error("the following arguments are required: -p")

    # Initialize conversation history with OS-aware instructions
    messages = [
        {"role": "system", "content": "You are a helpful assistant. The user is on a Windows machine. Always use Windows-compatible shell commands (e.g., use 'dir' instead of 'ls', and avoid 'mkdir -p' - just use 'mkdir')."},
        {"role": "user", "content": args.p}
    ]
    
    tools = [
        # --- Read Tool ---
        {
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Read and return the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        # --- Write Tool ---
        {
            "type": "function",
            "function": {
                "name": "Write",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "required": ["file_path", "content"],
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to write to"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                        }
                    }
                }
            }
        },
        # --- Bash Tool ---
        {
            "type": "function",
            "function": {
                "name": "Bash",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to execute"
                        }
                    }
                }
            }
        }
    ]

    print("Logs from your program will appear here!", file=sys.stderr)

    while True:
        try:
            chat = client.chat.completions.create(
                model=args.model,
                messages=messages,
                tools=tools,
            )
        except Exception as e:
            print(f"Critical error connecting to OpenRouter API with model '{args.model}': {e}", file=sys.stderr)
            print_model_suggestions(args.model)
            break

        # Fallback guard: Validate non-empty response
        if not chat.choices or len(chat.choices) == 0:
            print(f"Error: Empty response received from model '{args.model}' (rate limit or server load).", file=sys.stderr)
            print_model_suggestions(args.model)
            break

        message = chat.choices[0].message

        # Append assistant message to context memory
        assistant_msg = {"role": "assistant"}
        if message.content:
            assistant_msg["content"] = message.content
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls
            ]
            
        messages.append(assistant_msg)

        # Handle tool execution loop
        if message.tool_calls:
            for tool_call in message.tool_calls:
                
                # --- READ EXECUTION ---
                if tool_call.function.name == "Read":
                    arguments = json.loads(tool_call.function.arguments)
                    file_path = arguments["file_path"]
                    
                    # Sandbox Security: Enforce BASE_DIR scoping to prevent path traversal
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)

                    try:
                        with open(absolute_file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except Exception as e:
                        content = f"Error reading file: {e}"
                        print(content, file=sys.stderr)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })
                
                # --- WRITE EXECUTION ---
                elif tool_call.function.name == "Write":
                    arguments = json.loads(tool_call.function.arguments)
                    file_path = arguments.get("file_path") or arguments.get("filename")
                    file_content = arguments.get("content") or arguments.get("file_content")

                    # Sandbox Security: Confine writes strictly to BASE_DIR
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)

                    try:
                        os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
                        with open(absolute_file_path, "w", encoding="utf-8", errors="replace") as f:
                            f.write(file_content)
                        result = f"File {file_path} written successfully."
                    except Exception as e:
                        result = f"Error writing file: {e}"
                        print(result, file=sys.stderr)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                # --- BASH EXECUTION ---
                elif tool_call.function.name == "Bash":
                    arguments = json.loads(tool_call.function.arguments)
                    command = arguments.get("command") or arguments.get("cmd")
                    
                    if not command and arguments:
                        command = list(arguments.values())[0]
                    
                    if command:
                        # Use active Python runtime executable across cross-platform environments
                        python_exe = sys.executable
                        command = command.replace("python3 ", f'"{python_exe}" ').replace("python ", f'"{python_exe}" ')
                        
                        try:
                            # Confine command execution working directory strictly to BASE_DIR
                            process = subprocess.run(
                                command, 
                                shell=True, 
                                capture_output=True, 
                                text=True, 
                                cwd=BASE_DIR, 
                                errors="replace"
                            )
                            result = f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}"
                        except Exception as e:
                            result = f"Error: {e}"
                            print(result, file=sys.stderr)
                    else:
                        result = "Error: No command found."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

        else:
            # Model synthesized final response without invoking further tools
            if message.content:
                print(message.content)
            else:
                print("Notice: Model completed without returning output or calling tools.", file=sys.stderr)
            break


if __name__ == "__main__":
    main()