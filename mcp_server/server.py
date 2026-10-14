"""harborline-mcp: Harborline's backend as an MCP server.

Tools are actions Claude can call. Resources are documents and catalogs
the app can read and give to Claude, with no tool call. Prompts are
templates a user picks. Tool descriptions: Lessons 2.1 and 2.2's.
"""

import json
import os
import sys
from typing import Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent

from harborline import backend, data
from harborline.errors import BackendError
from harborline.tool_errors import tool_error
from loop.tools import (GET_CUSTOMER, LIST_ORDERS, LOOKUP_ORDER,
                        PROCESS_REFUND)

app = MCPServer("harborline", instructions=(
    "Harborline's customer, order and refund systems. Use these tools "
    "for any question about a customer, an order or a refund. Don't "
    "read or search data/ for that: it holds seed files, and it never "
    "shows the refunds made through these tools."))
Reason = Literal["changed_mind", "damaged", "defective", "wrong_item",
                 "cancel_before_shipment", "late_delivery",
                 "shipping_charged_in_error"]  # policy.REASONS


def call(handler, **arguments) -> CallToolResult:
    """Run one backend call: JSON text, or an error with isError."""
    try:
        output = handler(**arguments)
    except BackendError as error:  # Lesson 2.4's structured body
        body = TextContent(type="text", text=tool_error(error))
        return CallToolResult(content=[body], is_error=True)
    body = TextContent(type="text", text=json.dumps(output))
    return CallToolResult(content=[body])  # [] stays a success


@app.tool(description=GET_CUSTOMER["description"])
def get_customer(email: str | None = None,
                 name: str | None = None) -> CallToolResult:
    return call(backend.get_customer, email=email, name=name)


@app.tool(description=LOOKUP_ORDER["description"])
def lookup_order(order_id: str) -> CallToolResult:
    return call(backend.lookup_order, order_id=order_id)


@app.tool(description=LIST_ORDERS["description"])
def list_orders(customer_id: str) -> CallToolResult:
    return call(backend.list_orders, customer_id=customer_id)


@app.tool(description=PROCESS_REFUND["description"])
def process_refund(order_id: str, reason: Reason, amount: float,
                   sku: str | None = None) -> CallToolResult:
    return call(backend.process_refund, order_id=order_id,
                reason=reason, amount=amount, sku=sku)


@app.resource("harborline://policy/refunds", mime_type="text/markdown",
              description="The refund and returns policy, in full.")
def refund_policy() -> str:
    return data.refund_policy()


@app.resource("harborline://catalog/products",
              mime_type="application/json",
              description="Every product: SKU, name, category, price "
                          "and whether it is final sale.")
def product_catalog() -> str:
    return json.dumps(data.products(), indent=1)



@app.prompt(description="Start a conversation about one order.")
def order_help(order_id: str) -> str:
    return (f"A customer is asking about order {order_id}. Look it up "
            "with lookup_order, then answer from what it returns.")


if __name__ == "__main__":
    if not os.environ.get("HARBORLINE_API_TOKEN", "").startswith("hl_"):
        sys.exit("Set HARBORLINE_API_TOKEN: see .env.example")
    app.run()  # stdio: the host starts this process and talks to it
