"""Harborline's fixed workflow: our code decides every step.

Claude fills in one label, then writes one reply. Which steps run,
and in what order, is decided here, before any ticket arrives.

    python -m loop.workflow T-008
"""

import json
import re
import sys

import anthropic
from dotenv import load_dotenv

from harborline import backend, data
from harborline.config import BUSINESS_DATE, MAX_TOKENS, MODEL
from harborline.errors import BackendError
from harborline.usage import log_usage
from loop.agent import first_message

ROUTE = {
    "name": "route_ticket",
    "description": "Route a Harborline support ticket. status: where "
                   "an order is. refund: returning an item. other: "
                   "anything else.",
    "input_schema": {
        "type": "object",
        "properties": {
            "route": {"type": "string",
                      "enum": ["status", "refund", "other"]},
        },
        "required": ["route"],
    },
}
ROLE = (
    "You are Harborline's customer support agent. "
    f"Today is {BUSINESS_DATE}. Answer from the facts given, "
    "in three sentences or fewer. "
)
TASKS = {  # one specialized prompt per route
    "status": "Say where the order is and when it should arrive.",
    "refund": "Say what the policy allows. You can't issue refunds "
              "yet.\n\n" + data.refund_policy(),
}
HUMAN = "(sent to the human queue)"


def route(client, ticket):
    """Step 1, routing: a forced tool call, read as a label."""
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, tools=[ROUTE],
        tool_choice={"type": "tool", "name": "route_ticket"},
        messages=[{"role": "user", "content": ticket}],
    )
    log_usage(response, "1.5 workflow")
    call = next(b for b in response.content if b.type == "tool_use")
    return call.input["route"], response


def write(client, name, ticket, facts):
    """Step 3: one reply, from facts our code fetched. No tools."""
    response = client.messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=ROLE + TASKS[name],
        messages=[{"role": "user", "content": f"{ticket}\n\n{facts}"}],
    )
    log_usage(response, "1.5 workflow")
    reply = "".join(b.text for b in response.content
                    if b.type == "text")
    return reply, response


def handle(client, ticket):
    """Route one ticket, then run that route's fixed steps."""
    name, first = route(client, ticket)
    order_id = re.search(r"HL-\d{5}", ticket)  # the first ID only
    if name not in TASKS or order_id is None:  # gate: no fixed path
        return name, [], [first], HUMAN
    email = re.search(r"From: (\S+)", ticket).group(1)
    try:  # step 2: always these two lookups, in this order
        customer = backend.get_customer(email=email)
        order = backend.lookup_order(order_id.group(0))
    except BackendError:
        return name, [], [first], HUMAN
    facts = json.dumps({"customer": customer, "order": order})
    reply, last = write(client, name, ticket, facts)
    return name, [order["order_id"]], [first, last], reply


if __name__ == "__main__":
    load_dotenv()
    ticket = first_message(sys.argv[1])["content"]
    name, checked, calls, reply = handle(anthropic.Anthropic(), ticket)
    print(f"route: {name}  orders checked: {checked}  "
          f"calls: {len(calls)}")
    print(reply)
