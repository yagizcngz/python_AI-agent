import argparse
import json
import os
import sys

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # Konuşma geçmişi
    messages = [{"role": "user", "content": args.p}]
    
    tools = [
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
        }
    ]

    print("Logs from your program will appear here!", file=sys.stderr)

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages, 
            tools=tools,
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        message = chat.choices[0].message

        # --- İŞTE O GERİ GELEN KRİTİK DÜZELTME ---
        # API'nin kafası karışmasın ve elindeki araçları unutmasın diye
        # ham mesajı tertemiz bir sözlüğe (dict) çevirip geçmişe ekliyoruz.
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
        # ----------------------------------------

        if message.tool_calls:
            for tool_call in message.tool_calls:
                
                if tool_call.function.name == "Read":
                    arguments = json.loads(tool_call.function.arguments)
                    file_path = arguments["file_path"]
                    
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                    except Exception as e:
                        content = f"Error reading file: {e}"
                        print(content, file=sys.stderr)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })
                
                elif tool_call.function.name == "Write":
                    arguments = json.loads(tool_call.function.arguments)
                    file_path = arguments["file_path"]
                    file_content = arguments["content"]
                    
                    try:
                        directory = os.path.dirname(file_path)
                        if directory:
                            os.makedirs(directory, exist_ok=True)
                            
                        with open(file_path, "w") as f:
                            f.write(file_content)
                        
                        content = "File written successfully."
                    except Exception as e:
                        content = f"Error writing file: {e}"
                        print(content, file=sys.stderr)
                        
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })
                    
        else:
            if message.content:
                sys.stdout.write(message.content)
                sys.stdout.flush()
            
            break


if __name__ == "__main__":
    main()