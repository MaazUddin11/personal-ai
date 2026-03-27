import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from tools.shell import run_command

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "system.txt")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()


def ask_gpt(messages):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def extract_json(text: str):
    text = text.strip()

    if not text.startswith("{"):
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_agent():
    messages = []

    while True:
        user_input = input("\n>> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        messages.append({"role": "user", "content": user_input})

        reply = ask_gpt(messages)
        action = extract_json(reply)

        if action and action.get("action") == "run_command":
            cmd = action.get("input", "").strip()

            if not cmd:
                print("\nGPT:\nInvalid tool call, empty command.")
                messages.append({"role": "assistant", "content": "Invalid tool call, empty command."})
                continue

            print(f"\n[Proposed Command]\n{cmd}")
            confirm = input("\nRun this command? (y/n): ").strip().lower()

            if confirm != "y":
                tool_output = "User declined to run the command."
                print(f"\n[Tool Output]\n{tool_output}")
            else:
                tool_output = run_command(cmd)
                print(f"\n[Tool Output]\n{tool_output}")

            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"Tool output:\n{tool_output}"})
            continue

        print("\nGPT:\n", reply)
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    run_agent()