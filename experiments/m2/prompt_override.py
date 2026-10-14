"""Does one line in the system prompt change which tool Claude picks?

    python -m experiments.m2.prompt_override
    python -m experiments.m2.prompt_override "<line 2>" "<line 3>"

Column 1 sends no system prompt. Each line you pass gets its own
column, sent as the whole system prompt. 16 labeled requests, 3 tries
per column, scored on the first tool Claude calls.
"""

import sys
import textwrap
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.config import MAX_TOKENS, MODEL
from harborline.usage import log_usage
from loop.tools import TOOLS

SIGNED_IN = "Signed-in customer: C-1046\n\n"  # list_orders needs an ID
# Written before the first run: a refund needs the order's facts, so
# looking the order up or checking the policy first is valid too.
ALSO_OK = {"process_refund": ["lookup_order", "check_refund"]}
TRIES = 3


def first_call(client, request, line):
    """Claude's first tool call as (name, input), or its stop reason."""
    system = {"system": line} if line else {}  # no line: no system
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, tools=TOOLS, **system,
        messages=[{"role": "user", "content": SIGNED_IN + request}],
    )
    label = "2.2 with a line" if line else "2.2 no line"
    record = log_usage(response, label)
    for block in response.content:  # by type, never by position
        if block.type == "tool_use":
            return (block.name, block.input), record
    return (f"({response.stop_reason})", {}), record


if __name__ == "__main__":
    load_dotenv()
    lines = [None, *sys.argv[1:]]  # None: no system prompt at all
    for n, line in enumerate(lines, 1):
        print(f"{n}: " + textwrap.shorten(line or "(none)", 55))
    print()
    client = anthropic.Anthropic()
    pool = ThreadPoolExecutor(TRIES * len(lines))  # side by side
    cases = data.tool_routing_cases()
    right, tokens, cost = Counter(), 0, 0.0
    for case in cases:
        want = case["expected_tool"]
        good = [want, *ALSO_OK.get(want, [])]
        jobs = [[pool.submit(first_call, client, case["request"], line)
                 for _ in range(TRIES)] for line in lines]
        row, notes = f"{case['id']}  {want:17}", []
        for n, column in enumerate(jobs, 1):
            calls = [job.result() for job in column]
            for _, record in calls:
                tokens += record["input_tokens"]
                cost += record["cost_usd"]
            misses = [call for call, _ in calls if call[0] not in good]
            right[n] += TRIES - len(misses)
            row += f"  {TRIES - len(misses)}/{TRIES}"
            if misses:
                name = Counter(m[0] for m in misses).most_common(1)[0][0]
                args = next(a for m, a in misses if m == name)
                shown = f"{name} {args}" if args else name
                notes.append(f"     {n}: " + textwrap.shorten(shown, 51))
        print(row)
        if notes:
            print("     " + textwrap.shorten(case["request"], 54))
            print("\n".join(notes))

    print()
    for n in range(1, len(lines) + 1):
        print(f"{n}: {right[n]}/{TRIES * len(cases)} as labeled")
    print(f"{tokens:,} tokens in  ${cost:.4f}")
