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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the agent workspace. Use this for any task that requires running a command on the local system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute",
                    }
                },
                "required": ["command"],
            },
        },
    }
]

TOOL_FUNCTIONS = {
    "run_command": run_command,
}


def ask_gpt(messages):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
        tools=TOOLS,
        temperature=0.1,
    )
    return response.choices[0].message


def run_agent():
    messages = []

    while True:
        user_input = input("\n>> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        messages.append({"role": "user", "content": user_input})

        response_message = ask_gpt(messages)
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)

            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if fn_name == "run_command":
                    cmd = args.get("command", "").strip()

                    if not cmd:
                        tool_output = "Invalid tool call: empty command."
                        print(f"\n{tool_output}")
                    else:
                        print(f"\n[Proposed Command]\n{cmd}")
                        confirm = input("\nRun this command? (y/n): ").strip().lower()

                        if confirm != "y":
                            tool_output = "User declined to run the command."
                        else:
                            tool_output = run_command(cmd)

                        print(f"\n[Tool Output]\n{tool_output}")
                else:
                    tool_output = f"Unknown tool: {fn_name}"
                    print(f"\n{tool_output}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })

            # Get follow-up response after tool execution
            follow_up = ask_gpt(messages)
            if follow_up.content:
                print(f"\nGPT:\n{follow_up.content}")
            messages.append(follow_up)
        else:
            content = response_message.content or ""
            print(f"\nGPT:\n{content}")
            messages.append(response_message)


if __name__ == "__main__":
    run_agent()
