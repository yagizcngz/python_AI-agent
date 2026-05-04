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

    # 1. Konuşma geçmişini (messages) döngünün DIŞINDA tanımlıyoruz.
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
        }
    ]

    print("Logs from your program will appear here!", file=sys.stderr)

    # 2. Ajan Döngüsü (Agent Loop) Başlıyor
    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages, # Güncel konuşma geçmişini yolluyoruz
            tools=tools,
        )

        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")

        message = chat.choices[0].message

        # 3. Yapay zekanın verdiği cevabı konuşma geçmişine (messages) ekliyoruz
        messages.append(message)

        # 4. Eğer yapay zeka bir araç çağırdıysa:
        if message.tool_calls:
            # Birden fazla araç çağrısı olabileceği için döngüye alıyoruz
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
                    
                    # 5. DİKKAT: Artık dosyayı ekrana (stdout) YAZDIRMIYORUZ!
                    # Bunun yerine dosyanın içeriğini yapay zekaya "tool" rolüyle geri gönderiyoruz.
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })
                    
        # 6. Eğer araç çağırmadıysa (Yani sonuca ulaştıysa):
        else:
            if message.content:
                sys.stdout.write(message.content)
                sys.stdout.flush()
            
            # Sonucu yazdırdıktan sonra döngüyü kırıp programı bitiriyoruz.
            break


if __name__ == "__main__":
    main()