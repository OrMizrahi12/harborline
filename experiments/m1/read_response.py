"""Read every part of a reply, and decide the next step from its stop_reason.

    python -m experiments.m1.read_response plain|tool
"""

import sys

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage

LOOKUP_ORDER = {  # a tool definition; Lesson 1.3 runs it for real
    "name": "lookup_order",
    "description": "Look up one Harborline order by its ID, such as HL-10234.",
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
}
CASES = {
    "plain": {},
    "tool": {"tools": [LOOKUP_ORDER]},
}


def show(response):
    for block in response.content:  # by type, never by position
        if block.type == "thinking":
            print(f"[thinking] {len(block.thinking)} characters, "
                  f"signature {len(block.signature)} characters")
        elif block.type == "text":
            print(f"[text] {block.text}")
        elif block.type == "tool_use":
            print(f"[tool_use] {block.name} {block.input} id={block.id}")
        else:
            print(f"[{block.type}]")
    print("usage:", response.usage.to_json(indent=None))  # as returned
    print("stop_reason:", response.stop_reason)
    print("message id:", response.id)
    print("request id:", response._request_id)


def next_step(response):
    has_text = any(block.type == "text" for block in response.content)
    match response.stop_reason:
        case "end_turn":
            return "done: use the text"
        case "tool_use":
            return "run the tool, then send its result back (Lesson 1.3)"
        case "max_tokens":
            where = "mid-answer" if has_text else "before any text"
            return f"cut off {where}: don't use it; raise max_tokens or lower effort"
        case "pause_turn":
            return "a server tool paused: send the content back as-is"
        case "refusal":
            category = response.stop_details.category
            return f"declined ({category}): don't use it; log the request ID"
        case other:
            return f"unexpected stop_reason {other}: log it and stop"


case = sys.argv[1] if len(sys.argv) > 1 else "plain"
load_dotenv()
client = anthropic.Anthropic()
request = {
    "model": MODEL,
    "max_tokens": MAX_TOKENS,
    "system": "You are Harborline's customer support assistant. "
              "Reply in two sentences or fewer.",
    "messages": [
        {"role": "user", "content": data.tickets()[7]["message"]}  # T-008
    ],
}
response = client.messages.create(**(request | CASES[case]))
show(response)
record = log_usage(response, f"1.2 {case}")
print("next step:", next_step(response))
print(f"logged: runs/usage.jsonl, about ${record['cost_usd']:.6f}")
