"""Which tool does Claude call, and with what input? 3 tries each.

    python -m experiments.m2.routing_eval before   (then: after)
"""

import json
import sys
import textwrap
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.backend import ORDER_ID_PATTERN
from harborline.config import MAX_TOKENS, MODEL, ROOT_DIR
from harborline.usage import log_usage
from loop.tools import TOOLS, run_tool

LOOKUPS = ["get_customer", "lookup_order", "list_orders", "check_refund"]
TRIES = 3  # one try per request is an anecdote, not a measurement
SAVED = ROOT_DIR / "runs" / "routing-before.json"
# Held out: written for this lesson, labeled before the first run and
# never edited after it. (id, customer, request, tool, input it needs)
HELD_OUT = [
    ("H1", "C-1013", "Has order 10190 shipped?", "lookup_order",
     {"order_id": "HL-10190"}),
    ("H2", "C-1031", "Where is my order #10199?", "lookup_order",
     {"order_id": "HL-10199"}),
    ("H3", "C-1037", "Can you track hl 10203?", "lookup_order",
     {"order_id": "HL-10203"}),
    ("H4", "C-1037", "What came in order 10164?", "lookup_order",
     {"order_id": "HL-10164"}),
    ("H5", "C-1047", "My espresso machine from HL-10192 arrived "
     "dented. Refund it.", "escalate_to_human", {}),
    ("H6", "C-1012", "The desk from HL-10177 came damaged. Refund it.",
     "escalate_to_human", {}),
    ("H7", "C-1031", "My lamp from HL-10163 arrived broken. Refund it.",
     "process_refund", {"order_id": "HL-10163"}),
    ("H8", "C-1060", "The mixer from HL-10175 arrived damaged. Refund "
     "it.", "process_refund", {"order_id": "HL-10175"}),
]


def decide(client, customer, request, want, label, tools=TOOLS):
    """Claude's first call that matters. Lookups on the way to another
    tool run for real (two rounds at most); nothing else ever runs."""
    text = f"Signed-in customer: {customer}\n\n{request}"
    messages, records = [{"role": "user", "content": text}], []
    for _ in range(3):
        response = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, tools=tools,  # no system
            messages=messages,
        )
        records.append(log_usage(response, f"2.1 routing {label}"))
        calls = [b for b in response.content if b.type == "tool_use"]
        for call in calls:
            if call.name == want or call.name not in LOOKUPS:
                return call.name, call.input, records
        if not calls:
            return f"({response.stop_reason})", {}, records
        results = [run_tool(call) for call in calls]
        messages += [{"role": "assistant", "content": response.content},
                     {"role": "user", "content": results}]
    return "(lookups only)", {}, records


def correct(got, given, want, needs, customer):
    """The right tool, a valid order ID, the signed-in customer."""
    order_id = str(given.get("order_id", "HL-00000"))
    return (got == want and ORDER_ID_PATTERN.match(order_id)
            and given.get("customer_id", customer) == customer
            and all(given.get(k) == v for k, v in needs.items()))


if __name__ == "__main__":
    load_dotenv()
    label = sys.argv[1]  # "before" or "after"
    before = json.loads(SAVED.read_text()) if label == "after" else None
    client = anthropic.Anthropic()
    pool = ThreadPoolExecutor(TRIES)  # the tries run side by side
    labeled = [(c["id"], "C-1046", c["request"], c["expected_tool"], {})
               for c in data.tool_routing_cases()]
    scores, tokens, cost = {}, 0, 0.0
    for title, cases in [("labeled", labeled), ("held-out", HELD_OUT)]:
        print(f"-- {title}")
        for case_id, customer, request, want, needs in cases:
            tries = list(pool.map(lambda _: decide(
                client, customer, request, want, label), range(TRIES)))
            misses = []
            for got, given, records in tries:
                tokens += sum(r["input_tokens"] for r in records)
                cost += sum(r["cost_usd"] for r in records)
                if not correct(got, given, want, needs, customer):
                    if got == want:  # the right tool, a wrong input
                        got += " " + str(given.get("order_id", ""))
                    misses.append(got.strip()[:20])
            right = scores[case_id] = TRIES - len(misses)
            shown = Counter(misses or [want]).most_common(1)[0][0]
            line = f"{case_id}  {want:17} {shown:20} {right}/{TRIES}"
            was = before["scores"][case_id] if before else right
            print(line + (f"  was {was}/{TRIES}" if was != right else ""))
            if misses:
                print("     " + textwrap.shorten(request, 54))

    result = {"scores": scores, "tokens": tokens, "cost": cost}
    if label == "before":
        SAVED.write_text(json.dumps(result))
    print()
    for name, run in [("before", before), (label, result)]:
        if run:
            s = [f"{sum(run['scores'][c[0]] for c in cases)}/"
                 f"{TRIES * len(cases)}" for cases in (labeled, HELD_OUT)]
            print(f"{name + ':':7} labeled {s[0]}  held-out {s[1]}  "
                  f"{run['tokens']:,} in  ${run['cost']:.4f}")
