"""Harborline's backend as tools that Claude can ask to call."""

import json

from harborline import backend, policy
from harborline.errors import BackendError

GET_CUSTOMER = {
    "name": "get_customer",
    "description": (
        "Find one customer account: ID, name, email, phone, city, "
        "tier and status. Use it for questions about the account "
        "itself, such as the email or phone on file. Pass the email "
        "if you have it: it matches one account, so the result is "
        "verified. A full name can match several people and returns "
        "unverified candidates: ask which one is theirs. For orders, "
        "use lookup_order or list_orders instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "email": {"type": "string",
                      "description": "The customer's email address"},
            "name": {"type": "string",
                     "description": "The customer's full name"},
        },
    },
}
LOOKUP_ORDER = {
    "name": "lookup_order",
    "description": (
        "Get one order by its ID: status, items, total, shipping fee, "
        "payment, tracking and dates. Use it whenever the customer "
        "gives an order number, for example to see if it shipped or "
        "what it contained. IDs are HL- plus five digits; customers "
        "often drop the HL- (10234, #10234) or type it in lower case: "
        "pass HL-10234 anyway. No order number at all? Use "
        "list_orders to find the order first; never guess an ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string",
                         "description": "HL- plus five digits, like "
                                        "HL-10234"},
        },
        "required": ["order_id"],
    },
}
LIST_ORDERS = {
    "name": "list_orders",
    "description": (
        "List one customer's orders, newest first (up to 10): ID, "
        "date placed, item names and total. Use it when the customer "
        "asks about an order but has no order ID, such as an order "
        "from last week or a chair they bought. No status, tracking "
        "or shipping fee here: call lookup_order with the ID you "
        "find. An empty list is a valid answer: no orders yet."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string",
                            "description": "The customer ID"},
        },
        "required": ["customer_id"],
    },
}
PROCESS_REFUND = {
    "name": "process_refund",
    "description": (
        "Refund an order, or one item on it, when the refund policy "
        "allows it; the tool checks the policy and refuses what it "
        "does not allow. Use it when a customer asks for money back: "
        "a damaged or wrong item, a return, a late delivery, a fee "
        "charged in error. It needs the amount and, for an item, its "
        "SKU: get both from lookup_order first. Above $500? Use "
        "escalate_to_human instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string",
                         "description": "The order ID"},
            "reason": {"type": "string", "enum": list(policy.REASONS),
                       "description": "Why the customer wants it"},
            "amount": {"type": "number",
                       "description": "The amount in US dollars"},
            "sku": {"type": "string",
                    "description": "The item's SKU, for item refunds"},
        },
        "required": ["order_id", "reason", "amount"],
    },
}
ESCALATE_TO_HUMAN = {
    "name": "escalate_to_human",
    "description": (
        "Hand the case to a person in the support-leads queue; it "
        "returns an escalation ID. Use it when the customer asks for "
        "a person, when a refund is above $500, or when the account "
        "is on review hold. Write the summary for whoever takes the "
        "case: what the customer wants and what you checked. Do not "
        "escalate what lookup_order or list_orders can answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string",
                            "description": "The customer ID"},
            "reason": {"type": "string",
                       "description": "Why a person is needed"},
            "summary": {"type": "string",
                        "description": "The case so far"},
        },
        "required": ["customer_id", "reason", "summary"],
    },
}
TOOLS = [GET_CUSTOMER, LOOKUP_ORDER, LIST_ORDERS, PROCESS_REFUND,
         ESCALATE_TO_HUMAN]

HANDLERS = {
    "get_customer": backend.get_customer,
    "lookup_order": backend.lookup_order,
    "list_orders": backend.list_orders,
    "process_refund": backend.process_refund,
    "escalate_to_human": backend.escalate_to_human,
}


def run_tool(call):
    """Run one tool_use block; return the tool_result block for it."""
    result = {"type": "tool_result", "tool_use_id": call.id}
    handler = HANDLERS.get(call.name)
    if handler is None:
        return result | {"content": f"Unknown tool {call.name}.",
                         "is_error": True}
    try:
        output = handler(**call.input)
    except BackendError as error:  # not found, bad input, ...
        return result | {"content": str(error), "is_error": True}
    return result | {"content": json.dumps(output)}
