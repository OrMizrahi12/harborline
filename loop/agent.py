"""Harborline's agentic loop: Claude decides, our code runs the tools.

Lab 1: every stop reason has its own branch.

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
MAX_TOKENS_CEILING = 4 * MAX_TOKENS  # the most room one retry may get
MAX_CONTINUATIONS = 3  # pause_turn: send the paused turn back this often


class LoopStopped(Exception):
    """The loop ended without a finished answer."""


class CutOff(LoopStopped):
    """Still cut off by max_tokens with the most room we allow."""


class Refused(LoopStopped):
    """Claude declined (stop_reason "refusal"). Never resend it as is."""

    def __init__(self, category):
        super().__init__(f"refused ({category})")
        self.category = category


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


def refusal_category(response):
    details = getattr(response, "stop_details", None)
    return getattr(details, "category", None) or "unknown"


def run(client, messages):
    """Call Claude until it ends its turn; return every response."""
    responses = []
    max_tokens = MAX_TOKENS
    continuations = 0
    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        log_usage(response, "lab 1 agent")
        responses.append(response)
        show(turn, response)
        reason = response.stop_reason

        if reason == "max_tokens":
            # Cut off: a half reply or a half tool call. Don't keep it;
            # send the same request again with more room, up to a ceiling.
            if max_tokens >= MAX_TOKENS_CEILING:
                raise CutOff(f"still cut off at max_tokens={max_tokens}")
            max_tokens = min(2 * max_tokens, MAX_TOKENS_CEILING)
            print(f"  retrying with max_tokens={max_tokens}")
            continue
        if reason == "refusal":
            # A normal response, not an error. The same request usually
            # gets the same answer: stop, and let a person take over.
            raise Refused(refusal_category(response))
        if reason == "pause_turn":
            # Server-side work isn't finished: send the turn back as is.
            continuations += 1
            if continuations > MAX_CONTINUATIONS:
                raise LoopStopped("paused too many times")
            messages.append({"role": "assistant",
                             "content": response.content})
            continue
        if reason not in ("tool_use", "end_turn"):
            # stop_sequence (we set none), model_context_window_exceeded, ...
            raise LoopStopped(f"stopped on {reason}")

        messages.append({"role": "assistant",
                         "content": response.content})  # as returned
        if reason == "end_turn":
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
    try:
        run(anthropic.Anthropic(), messages)
    except Refused as stop:
        print(f"\nRefused ({stop.category}): hand this ticket to a person.")
    except LoopStopped as stop:
        print(f"\nNo answer: {stop}. Hand this ticket to a person.")
    print("\nHistory:")
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            kinds = "text"
        else:
            kinds = ", ".join(b["type"] if isinstance(b, dict)
                              else b.type for b in content)
        print(f"  {message['role']:9} {kinds}")
