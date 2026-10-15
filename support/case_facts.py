"""Case facts: the exact facts of a case, kept outside the summary.

A long conversation gets summarized, and a summary can blur amounts,
dates and promises. So what the tools establish is kept here instead,
one entry per order, and sent with every turn, exactly as they are.

    python -m support.case_facts HL-10187    # an order, full and trimmed
"""

import json
import sys

from harborline import backend, normalize

KEEP = ("order_id", "status", "promised_by", "delivered_at", "items",
        "shipping_fee", "total", "payment")  # what refunds and status need
ITEM = ("sku", "name", "category", "unit_price", "final_sale")

facts = {"customer": None, "orders": {}}


def start_case():
    """A new conversation: no facts yet."""
    facts.update(customer=None, orders={})


def trim(order):
    """Only the fields that matter, before they pile up in context."""
    short = {field: order[field] for field in KEEP if field in order}
    short["items"] = [{k: item[k] for k in ITEM} for item in order["items"]]
    short["payment"] = order["payment"]["method"]
    return short


async def record(input_data, tool_use_id, context):
    """A PostToolUse hook: keep what each tool call established."""
    try:
        output = json.loads(input_data["tool_response"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError):
        return {}  # an error, not a result
    if output.get("verified"):                                # get_customer
        customer = output["customer"]
        facts["customer"] = {k: customer[k] for k in
                             ("customer_id", "name", "email")}
        facts["customer"]["verified"] = True
    elif "refund_id" in output:                               # process_refund
        order = facts["orders"].setdefault(output["order_id"], {})
        order.setdefault("refunds", []).append(
            {"refund_id": output["refund_id"], "amount": output["amount"]})
    elif "order_id" in output:                                # lookup_order
        clean = normalize.order(output)
        order = facts["orders"].setdefault(clean["order_id"], {})
        order.update(items=[i["name"] for i in clean["items"]],
                     delivered=clean.get("delivered_at"),
                     total=clean["total"])
    return {}


def block():
    """The facts as JSON, for the top of every prompt."""
    return ("## Case facts (exact, from the tools)\n"
            + json.dumps(facts, indent=1))


if __name__ == "__main__":
    order = normalize.order(backend.lookup_order(sys.argv[1]))
    full, short = json.dumps(order), json.dumps(trim(order))
    print(f"full     {len(order):2} fields  {len(full)} characters")
    print(f"trimmed  {len(trim(order)):2} fields  {len(short)} characters")
    print(short)
