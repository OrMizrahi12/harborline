"""Harborline's backend as tools that Claude can ask to call."""

import json

from harborline import backend
from harborline.errors import BackendError

GET_CUSTOMER = {
    "name": "get_customer",
    "description": "Find a Harborline customer by email address. "
                   "Use it to check who is writing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "email": {"type": "string",
                      "description": "The customer's email address"},
        },
        "required": ["email"],
    },
}
LOOKUP_ORDER = {
    "name": "lookup_order",
    "description": "Look up one Harborline order: its status, items, "
                   "total and tracking.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string",
                         "description": "The order ID, as the customer "
                                        "wrote it"},
        },
        "required": ["order_id"],
    },
}
TOOLS = [GET_CUSTOMER, LOOKUP_ORDER]

HANDLERS = {
    "get_customer": backend.get_customer,
    "lookup_order": backend.lookup_order,
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
