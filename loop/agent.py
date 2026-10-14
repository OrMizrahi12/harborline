"""Harborline's agentic loop: Claude decides, our code runs the tools.

    python -m loop.agent T-003
"""

import sys

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import BUSINESS_DATE, MAX_TOKENS, MODEL
from harborline.usage import log_usage
from loop.tools import TOOLS, run_tool

SYSTEM = (
    "You are Harborline's customer support agent. "
    f"Today is {BUSINESS_DATE}. Verify the sender with get_customer "
    "first; only then look up their orders. Before each tool call, "
    "say in a few words what you are checking. You can't issue "
    "refunds yet: say what the policy allows. Answer in four "
    "sentences or fewer, in plain text.\n\n" + data.refund_policy()
)
MAX_TURNS = 10  # a safety net for runaway loops, not how we stop


class LoopStopped(Exception):
    """The loop ended without a finished answer."""


def first_message(ticket_id):
    """A support ticket as the customer's first message."""
    for ticket in data.tickets():
        if ticket["ticket_id"] == ticket_id:
            sender = ticket["customer_email"]
            text = f"From: {sender}\n\n{ticket['message']}"
            return {"role": "user", "content": text}
    raise SystemExit(f"No ticket {ticket_id}")


def show(turn, response):
    print(f"turn {turn}: {response.stop_reason}")
    for block in response.content:  # by type, never by position
        if block.type == "text":
            print("  [text]", block.text)
        elif block.type == "tool_use":
            print("  [tool_use]", block.name, block.input)
        else:
            print(f"  [{block.type}]")


def run(client, messages):
    """Call Claude until it ends its turn; return every response."""
    responses = []
    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        log_usage(response, "1.4 agent")
        responses.append(response)
        show(turn, response)
        if response.stop_reason not in ("tool_use", "end_turn"):
            raise LoopStopped(f"stopped on {response.stop_reason}")
        messages.append({"role": "assistant",
                         "content": response.content})  # as returned
        if response.stop_reason == "end_turn":
            return responses
        results = [run_tool(block) for block in response.content
                   if block.type == "tool_use"]
        for result in results:
            error = " is_error" if result.get("is_error") else ""
            print(f"  [tool_result{error}]", result["content"][:60])
        messages.append({"role": "user", "content": results})
    raise LoopStopped(f"no end_turn after {MAX_TURNS} turns")


if __name__ == "__main__":
    load_dotenv()
    messages = [first_message(sys.argv[1])]
    run(anthropic.Anthropic(), messages)
    print("\nHistory:")
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            kinds = "text"
        else:
            kinds = ", ".join(b["type"] if isinstance(b, dict)
                              else b.type for b in content)
        print(f"  {message['role']:9} {kinds}")
