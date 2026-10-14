"""One tool round trip by hand: tool_use -> run it -> tool_result.

    python -m experiments.m1.manual_tool_call [bad]
"""

import sys

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage
from loop.tools import TOOLS, run_tool

SYSTEM = (
    "You are Harborline's customer support assistant. Use the tools "
    "to check who is writing and to look up any order they mention. "
    "Call independent tools together, in one turn. "
    "Reply in two sentences or fewer."
)
ticket = data.tickets()[7]  # T-008: where is order HL-10196?
question = ticket["message"]
if sys.argv[1:] == ["bad"]:
    question = "Hi, where is my order 12345? No shipping email yet."
sender = ticket["customer_email"]
messages = [{"role": "user", "content": f"From: {sender}\n\n{question}"}]

load_dotenv()
client = anthropic.Anthropic()


def ask():
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM,
        tools=TOOLS, messages=messages,
    )
    log_usage(response, "1.3 manual tool call")
    print(f"--- {response.stop_reason}, "
          f"{response.usage.input_tokens:,} tokens in")
    for block in response.content:  # by type, never by position
        if block.type == "tool_use":
            print("[tool_use]", block.name, block.input,
                  "id", block.id[-4:])
        elif block.type == "text":
            print("[text]", block.text)
        else:
            print(f"[{block.type}]")
    return response


response = ask()  # 1. Claude asks for tools
if response.stop_reason != "tool_use":
    sys.exit("No tool call this time.")

calls = [b for b in response.content if b.type == "tool_use"]
results = [run_tool(call) for call in calls]  # 2. we run each call
for result in results:
    error = result.get("is_error", False)
    print("[tool_result] id", result["tool_use_id"][-4:],
          f"is_error={error}", result["content"][:45])

# 3. Claude's turn as returned, then ONE user turn with every result
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": results})
ask()
