"""Who decides? The same five tickets, through both designs.

    python -m experiments.m1.who_decides
"""

import contextlib
import io
from collections import Counter

import anthropic
from dotenv import load_dotenv

from harborline import data
from harborline.costs import estimate_cost
from loop import agent, workflow

TICKETS = ["T-008", "T-003", "T-014", "T-006", "T-004"]
LABELS = {t["ticket_id"]: t["label"] for t in data.tickets()}
totals = {"workflow": Counter(), "agent": Counter()}


def tally(ticket_id, design, calls, checked, note):
    wanted = LABELS[ticket_id]["order_ids"]  # what the ticket is about
    found = len(set(checked) & set(wanted))
    print(f"{ticket_id}  {design:8}  calls {len(calls)}  "
          f"orders {found}/{len(wanted)}  {note}")
    for call in calls:
        used = call.usage
        totals[design]["tokens"] += used.input_tokens + used.output_tokens
        totals[design]["cost"] += estimate_cost(
            call.model, used.input_tokens, used.output_tokens)
    totals[design].update(calls=len(calls), found=found,
                          wanted=len(wanted))


load_dotenv()
client = anthropic.Anthropic()
for ticket_id in TICKETS:
    message = agent.first_message(ticket_id)
    name, checked, calls, _ = workflow.handle(client, message["content"])
    tally(ticket_id, "workflow", calls, checked, f"route: {name}")
    try:
        with contextlib.redirect_stdout(io.StringIO()):  # its turns
            responses = agent.run(client, [message])
    except agent.LoopStopped as stop:  # no answer: record it, go on
        tally(ticket_id, "agent", [], [], str(stop))
        continue
    uses = [b for r in responses for b in r.content
            if b.type == "tool_use"]
    looked_up = [b.input["order_id"] for b in uses
                 if b.name == "lookup_order"]
    tally(ticket_id, "agent", responses, looked_up,
          f"tool calls: {len(uses)}")

print()
for design, t in totals.items():
    print(f"{design:8}  calls {t['calls']}  tokens {t['tokens']:,}  "
          f"${t['cost']:.4f}  orders {t['found']}/{t['wanted']}")
