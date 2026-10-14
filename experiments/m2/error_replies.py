"""Same requests, same tools: only the error replies change.

Five Harborline requests, each run as a short conversation with a
refunds agent's tools. Every tool runs for real; a failure goes back
one of three ways: generic (one string for every failure), sentence
(the backend's own message: our run_tool until today) or structured
(harborline/tool_errors.py). Three tries each.
"""

import json
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from harborline import backend
from harborline.config import MAX_TOKENS, MODEL
from harborline.errors import BackendError
from harborline.tool_errors import tool_error
from harborline.usage import log_usage
from loop.tools import (ESCALATE_TO_HUMAN, GET_CUSTOMER, HANDLERS,
                        LIST_ORDERS, LOOKUP_ORDER, PROCESS_REFUND)

TOOLS = [GET_CUSTOMER, LOOKUP_ORDER, LIST_ORDERS, PROCESS_REFUND,
         ESCALATE_TO_HUMAN]  # a refunds agent: no check first
TRIES, TURNS = 3, 5
STYLES = {"generic": lambda error: "Operation failed.",
          "sentence": str, "structured": tool_error}
# Written before the first run: (case, customer, request, what makes
# the outcome right: a word in the last reply, or a call). Never right:
# the same call on the same order after an error retrying can't fix.
CASES = [
    ("transient", "C-1010", "Where is my order HL-10211?",
     ["process"]),
    ("not found", "C-1046", "Where is my order 12345?", ["12345"]),
    ("business", "C-1016", "I'd like a refund for the cushion "
     "covers from HL-10159. Not what I pictured.", ["final"]),
    ("permission", "C-1033", "Please refund the weighted blanket "
     "from HL-10184.", ["lead", "hold", "escalate_to_human"]),
    ("empty", "C-1058", "What have I ordered so far?",
     ["no orders", "any orders"]),
]


def conversation(client, case, style):
    """One try: run the tools for real until Claude stops."""
    name, customer, request, words = case
    text = f"Signed-in customer: {customer}\n\n{request}"
    messages = [{"role": "user", "content": text}]
    failed, again, made = set(), 0, set()
    for _ in range(TURNS):
        response = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, tools=TOOLS,
            messages=messages,
        )
        log_usage(response, f"2.4 errors {style}")
        calls = [b for b in response.content if b.type == "tool_use"]
        if not calls:
            break
        results = []
        for call in calls:
            key = (call.name, call.input.get("order_id"))
            again += key in failed  # sent again: it can't work now
            made.add(call.name)
            result = {"type": "tool_result", "tool_use_id": call.id}
            try:
                output = HANDLERS[call.name](**call.input)
                result["content"] = json.dumps(output)
            except BackendError as error:
                result |= {"content": STYLES[style](error),
                           "is_error": True}
                if not error.retryable:
                    failed.add(key)
            results.append(result)
        messages += [{"role": "assistant", "content": response.content},
                     {"role": "user", "content": results}]
    text = " ".join(b.text for b in response.content if b.type == "text")
    seen = text.lower() + " " + " ".join(made)
    right = again == 0 and any(w in seen for w in words)
    return right, again, text


def run_case(client, case):
    """A case's nine tries in a row: the timeout is armed for each."""
    out = []
    for style in STYLES:
        for _ in range(TRIES):
            if case[0] == "transient":  # HL-10211: one timeout, then OK
                backend.reset()
            out.append((style, *conversation(client, case, style)))
    return out


if __name__ == "__main__":
    load_dotenv()
    client = anthropic.Anthropic()
    with ThreadPoolExecutor(len(CASES)) as pool:  # cases side by side
        done = dict(zip([c[0] for c in CASES],
                        pool.map(lambda c: run_case(client, c), CASES)))
    print(f"{'':12}" + "".join(f"{style:>12}" for style in STYLES))
    for name, tries in done.items():
        cells = [sum(t[1] for t in tries if t[0] == s) for s in STYLES]
        print(f"{name:12}" + "".join(f"{c:>10}/3" for c in cells))
    for label, i in [("right", 1), ("sent again", 2)]:
        cells = [sum(t[i] for ts in done.values() for t in ts
                     if t[0] == s) for s in STYLES]
        print(f"{label:12}" + "".join(f"{c:>12}" for c in cells))
    print("\nbusiness, the last reply (try 1):")
    for style in STYLES:
        text = next(t[3] for t in done["business"] if t[0] == style)
        print(f"  {style:11}{text[:40]} [...]")
