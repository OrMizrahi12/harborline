"""Harborline's backend as Agent SDK tools, served in-process.

The same backend calls and descriptions as harborline-mcp (Lesson 2.5),
but no separate process: the MCP server runs inside our app.
"""

import json

from claude_agent_sdk import create_sdk_mcp_server, tool

from harborline import backend
from harborline.errors import BackendError
from harborline.tool_errors import tool_error
from loop.tools import GET_CUSTOMER, LOOKUP_ORDER
from loop.tools import ESCALATE_TO_HUMAN, PROCESS_REFUND


def reply(handler, **arguments):
    """Run one backend call: JSON text, or an error Claude can read."""
    try:
        output = handler(**arguments)
    except BackendError as error:  # Lesson 2.4's structured body
        text = tool_error(error)
        return {"content": [{"type": "text", "text": text}],
                "is_error": True}
    text = json.dumps(output)
    return {"content": [{"type": "text", "text": text}]}


@tool("get_customer", GET_CUSTOMER["description"],
      GET_CUSTOMER["input_schema"])
async def get_customer(args):
    return reply(backend.get_customer, email=args.get("email"),
                 name=args.get("name"))


@tool("lookup_order", LOOKUP_ORDER["description"],
      LOOKUP_ORDER["input_schema"])
async def lookup_order(args):
    return reply(backend.lookup_order, order_id=args["order_id"])


@tool("process_refund", PROCESS_REFUND["description"],
      PROCESS_REFUND["input_schema"])
async def process_refund(args):
    return reply(backend.process_refund, order_id=args["order_id"],
                 amount=args["amount"], reason=args["reason"],
                 sku=args.get("sku"))


@tool("escalate_to_human", ESCALATE_TO_HUMAN["description"],
      ESCALATE_TO_HUMAN["input_schema"])
async def escalate_to_human(args):
    return reply(backend.escalate_to_human,
                 customer_id=args["customer_id"],
                 reason=args["reason"], summary=args["summary"])


TOOLS = [get_customer, lookup_order, process_refund, escalate_to_human]
server = create_sdk_mcp_server("harborline", version="1.0.0", tools=TOOLS)
NAMES = [f"mcp__harborline__{t.name}" for t in TOOLS]  # for allowed_tools
